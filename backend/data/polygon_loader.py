# ============================================================================
# Polygon Data Loader - 증분 업데이트 로직
# ============================================================================
# 📌 이 파일의 역할:
#   - Polygon API에서 데이터를 가져와 SQLite에 저장
#   - 증분 업데이트 (Incremental Update) 로직 구현
#   - 최초 로드 및 일일 동기화 지원
#
# 🔄 증분 업데이트 전략:
#   1. DB의 마지막 업데이트 날짜 확인
#   2. 누락된 거래일 계산 (주말/휴일 제외)
#   3. 각 날짜별 Grouped Daily API 호출
#   4. DB에 Upsert
#
# 📅 거래일 계산:
#   - 주말 (토, 일) 제외
#   - 미국 공휴일 (추후 추가 가능)
#
# 📖 사용 예시:
#   >>> loader = PolygonLoader(db, client)
#   >>> count = await loader.update_market_data()
#   >>> print(f"{count}개 레코드 업데이트")
# ============================================================================

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger

from .database import MarketDB
from .polygon_client import PolygonClient, PolygonAPIError


# ═══════════════════════════════════════════════════════════════════════════
# 미국 공휴일 리스트 (2024-2025)
# ═══════════════════════════════════════════════════════════════════════════
# 주식 시장 휴장일 (NYSE/NASDAQ 기준)
# 정확한 날짜는 매년 업데이트 필요
US_HOLIDAYS_2024 = {
    "2024-01-01",  # New Year's Day
    "2024-01-15",  # MLK Day
    "2024-02-19",  # Presidents Day
    "2024-03-29",  # Good Friday
    "2024-05-27",  # Memorial Day
    "2024-06-19",  # Juneteenth
    "2024-07-04",  # Independence Day
    "2024-09-02",  # Labor Day
    "2024-11-28",  # Thanksgiving
    "2024-12-25",  # Christmas
}

US_HOLIDAYS_2025 = {
    "2025-01-01",  # New Year's Day
    "2025-01-20",  # MLK Day
    "2025-02-17",  # Presidents Day
    "2025-04-18",  # Good Friday
    "2025-05-26",  # Memorial Day
    "2025-06-19",  # Juneteenth
    "2025-07-04",  # Independence Day
    "2025-09-01",  # Labor Day
    "2025-11-27",  # Thanksgiving
    "2025-12-25",  # Christmas
}

# 전체 휴일 세트
US_HOLIDAYS = US_HOLIDAYS_2024 | US_HOLIDAYS_2025


# ═══════════════════════════════════════════════════════════════════════════
# PolygonLoader 클래스
# ═══════════════════════════════════════════════════════════════════════════

class PolygonLoader:
    """
    Polygon.io → SQLite 데이터 동기화 로더
    
    시장 데이터의 증분 업데이트를 담당합니다.
    DB에 없는 날짜만 API로 가져와서 저장합니다.
    
    Attributes:
        db: MarketDB 인스턴스
        client: PolygonClient 인스턴스
    
    Example:
        >>> db = MarketDB("data/market_data.db")
        >>> await db.initialize()
        >>> 
        >>> async with PolygonClient(api_key) as client:
        ...     loader = PolygonLoader(db, client)
        ...     
        ...     # 최초 1년치 로드
        ...     await loader.initial_load(days=365)
        ...     
        ...     # 이후 증분 업데이트
        ...     await loader.update_market_data()
    """
    
    def __init__(self, db: MarketDB, client: PolygonClient):
        """
        PolygonLoader 초기화
        
        Args:
            db: MarketDB 인스턴스 (initialize() 호출 완료 상태)
            client: PolygonClient 인스턴스
        """
        self.db = db
        self.client = client
        
        logger.debug("📦 PolygonLoader 초기화")
    
    # ═══════════════════════════════════════════════════════════════════════
    # 날짜 유틸리티
    # ═══════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def is_trading_day(date: datetime) -> bool:
        """
        거래일인지 확인
        
        주말과 공휴일은 거래일이 아닙니다.
        
        Args:
            date: 확인할 날짜
        
        Returns:
            bool: 거래일이면 True
        """
        # 주말 체크 (0=월, 5=토, 6=일)
        if date.weekday() >= 5:
            return False
        
        # 공휴일 체크
        date_str = date.strftime("%Y-%m-%d")
        if date_str in US_HOLIDAYS:
            return False
        
        return True
    
    @staticmethod
    def get_trading_days_between(
        start_date: datetime,
        end_date: datetime
    ) -> list[str]:
        """
        두 날짜 사이의 거래일 리스트 반환
        
        Args:
            start_date: 시작일 (포함)
            end_date: 종료일 (포함)
        
        Returns:
            list[str]: 거래일 리스트 (YYYY-MM-DD 형식)
        """
        trading_days = []
        current = start_date
        
        while current <= end_date:
            if PolygonLoader.is_trading_day(current):
                trading_days.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        
        return trading_days
    
    @staticmethod
    def get_last_trading_day() -> str:
        """
        가장 최근 거래일 반환
        
        오늘이 거래일이고 장이 끝났으면 오늘,
        아니면 가장 최근 거래일을 반환합니다.
        
        Returns:
            str: 가장 최근 거래일 (YYYY-MM-DD)
        
        Note:
            - 현재 시간이 미국 동부 시간 기준 16:30 이후면 오늘 포함
            - 그 전이면 어제까지만 포함 (오늘 데이터는 아직 없음)
        """
        now = datetime.now()
        
        # TODO: 미국 동부 시간 기준으로 변환 필요
        # 현재는 단순히 어제까지만 반환 (안전하게)
        candidate = now - timedelta(days=1)
        
        # 거래일 찾기
        while not PolygonLoader.is_trading_day(candidate):
            candidate -= timedelta(days=1)
        
        return candidate.strftime("%Y-%m-%d")
    
    # ═══════════════════════════════════════════════════════════════════════
    # 데이터 로드 메서드
    # ═══════════════════════════════════════════════════════════════════════
    
    async def initial_load(self, days: int = 365) -> int:
        """
        최초 N일치 히스토리 데이터 로드
        
        DB가 비어있을 때 처음으로 대량의 히스토리 데이터를 가져옵니다.
        Free Tier에서는 Rate Limit (5 req/min) 때문에 시간이 오래 걸립니다.
        
        Args:
            days: 가져올 일수 (기본값: 365일 = 약 252 거래일)
        
        Returns:
            int: 총 저장된 레코드 수
        
        Example:
            >>> count = await loader.initial_load(days=365)
            >>> print(f"1년치 {count}개 레코드 로드 완료")
        
        Note:
            - 365일 ≈ 252 거래일 ≈ 252 API 호출
            - Free Tier (5 req/min) 기준 약 50분 소요
            - 중간에 실패해도 이미 저장된 데이터는 유지됨
        """
        end_date = datetime.now() - timedelta(days=1)  # 어제까지
        start_date = end_date - timedelta(days=days)
        
        # 거래일 리스트 생성
        trading_days = self.get_trading_days_between(start_date, end_date)
        
        logger.info(f"📥 Initial Load 시작: {start_date.date()} ~ {end_date.date()} ({len(trading_days)} 거래일)")
        
        total_records = 0
        success_count = 0
        error_count = 0
        
        for i, date in enumerate(trading_days):
            try:
                # ─────────────────────────────────────────────────────────
                # API 호출
                # ─────────────────────────────────────────────────────────
                bars = await self.client.fetch_grouped_daily(date)
                
                if bars:
                    # ─────────────────────────────────────────────────────
                    # DB 저장
                    # ─────────────────────────────────────────────────────
                    count = await self.db.upsert_bulk(bars)
                    total_records += count
                    success_count += 1
                
                # 진행 상황 로그 (10일마다)
                if (i + 1) % 10 == 0:
                    logger.info(f"📊 진행: {i + 1}/{len(trading_days)} 일 완료 ({total_records:,} 레코드)")
                    
            except PolygonAPIError as e:
                logger.error(f"❌ {date} 로드 실패: {e}")
                error_count += 1
                # 에러가 많으면 중단
                if error_count > 5:
                    logger.error("🛑 에러가 너무 많아 로드 중단")
                    break
        
        logger.info(f"✅ Initial Load 완료: {total_records:,} 레코드 저장 (성공 {success_count}, 실패 {error_count})")
        return total_records
    
    async def update_market_data(self) -> int:
        """
        증분 업데이트 - 누락된 날짜만 가져오기
        
        DB에 저장된 가장 최근 날짜를 확인하고,
        그 이후부터 오늘(어제)까지의 데이터만 가져옵니다.
        
        일일 배치 작업으로 사용하기 적합합니다.
        
        Returns:
            int: 새로 저장된 레코드 수
        
        Example:
            >>> # 매일 장 시작 전 실행
            >>> count = await loader.update_market_data()
            >>> print(f"{count}개 레코드 업데이트")
        """
        # ─────────────────────────────────────────────────────────────────
        # 1. DB의 마지막 날짜 확인
        # ─────────────────────────────────────────────────────────────────
        latest_date = await self.db.get_latest_date()
        
        if latest_date is None:
            # DB가 비어있으면 initial_load() 추천
            logger.warning("⚠️ DB가 비어있습니다. initial_load()를 먼저 실행하세요.")
            # 최근 30일만 가져오기 (빠른 시작)
            return await self.initial_load(days=30)
        
        logger.info(f"📅 DB 마지막 날짜: {latest_date}")
        
        # ─────────────────────────────────────────────────────────────────
        # 2. 누락된 거래일 계산
        # ─────────────────────────────────────────────────────────────────
        start_date = datetime.strptime(latest_date, "%Y-%m-%d") + timedelta(days=1)
        end_date = datetime.now() - timedelta(days=1)  # 어제까지
        
        if start_date > end_date:
            logger.info("✅ 이미 최신 상태입니다.")
            return 0
        
        missing_days = self.get_trading_days_between(start_date, end_date)
        
        if not missing_days:
            logger.info("✅ 누락된 거래일 없음")
            return 0
        
        logger.info(f"📥 {len(missing_days)}개 거래일 업데이트 필요: {missing_days[0]} ~ {missing_days[-1]}")
        
        # ─────────────────────────────────────────────────────────────────
        # 3. 각 날짜별 데이터 가져오기
        # ─────────────────────────────────────────────────────────────────
        total_records = 0
        
        for date in missing_days:
            try:
                bars = await self.client.fetch_grouped_daily(date)
                
                if bars:
                    count = await self.db.upsert_bulk(bars)
                    total_records += count
                    logger.debug(f"📊 {date}: {count}개 레코드 저장")
                    
            except PolygonAPIError as e:
                logger.error(f"❌ {date} 업데이트 실패: {e}")
                # 개별 날짜 실패는 무시하고 계속 진행
                continue
        
        logger.info(f"✅ 증분 업데이트 완료: {total_records:,} 레코드")
        return total_records
    
    async def fetch_single_day(self, date: str) -> int:
        """
        특정 날짜 하루 데이터만 가져오기
        
        Args:
            date: 가져올 날짜 (YYYY-MM-DD)
        
        Returns:
            int: 저장된 레코드 수
        """
        try:
            bars = await self.client.fetch_grouped_daily(date)
            
            if bars:
                count = await self.db.upsert_bulk(bars)
                logger.info(f"✅ {date}: {count}개 레코드 저장")
                return count
            else:
                logger.info(f"📭 {date}: 데이터 없음")
                return 0
                
        except PolygonAPIError as e:
            logger.error(f"❌ {date} 가져오기 실패: {e}")
            raise
    
    # ═══════════════════════════════════════════════════════════════════════
    # 상태 확인
    # ═══════════════════════════════════════════════════════════════════════
    
    async def get_sync_status(self) -> dict:
        """
        데이터 동기화 상태 확인
        
        Returns:
            dict: 동기화 상태 정보
                - db_latest_date: DB의 가장 최근 날짜
                - market_latest_date: 시장의 가장 최근 거래일
                - missing_days: 누락된 거래일 수
                - is_up_to_date: 최신 상태 여부
        """
        latest_date = await self.db.get_latest_date()
        market_latest = self.get_last_trading_day()
        
        # DB가 비어있으면 최신 상태가 아님
        if latest_date is None:
            return {
                "db_latest_date": None,
                "market_latest_date": market_latest,
                "missing_days": -1,  # 알 수 없음 (DB가 비어있음)
                "is_up_to_date": False,
            }
        
        missing_days = 0
        if latest_date < market_latest:
            start = datetime.strptime(latest_date, "%Y-%m-%d") + timedelta(days=1)
            end = datetime.strptime(market_latest, "%Y-%m-%d")
            missing_days = len(self.get_trading_days_between(start, end))
        
        return {
            "db_latest_date": latest_date,
            "market_latest_date": market_latest,
            "missing_days": missing_days,
            "is_up_to_date": missing_days == 0,
        }
    
    # ═══════════════════════════════════════════════════════════════════════
    # Fundamental Data Fetch
    # ═══════════════════════════════════════════════════════════════════════
    
    async def fetch_fundamentals_batch(
        self,
        tickers: list[str],
        delay_between_batches: float = 12.0,
        batch_size: int = 5,
    ) -> int:
        """
        여러 종목의 Fundamental Data를 배치로 가져와 DB에 저장
        
        Rate Limit을 고려하여 배치 단위로 처리합니다.
        Free Tier (5 req/min)에서는 5개씩 처리 후 12초 대기합니다.
        
        Args:
            tickers: 종목 심볼 리스트
            delay_between_batches: 배치 간 대기 시간 (초)
            batch_size: 한 번에 처리할 종목 수
        
        Returns:
            int: 성공적으로 업데이트된 종목 수
        
        Example:
            >>> # Watchlist 상위 50개 종목의 Fundamental 가져오기
            >>> watchlist = await scanner.run_daily_scan()
            >>> tickers = [item["ticker"] for item in watchlist]
            >>> count = await loader.fetch_fundamentals_batch(tickers)
            >>> print(f"{count}개 종목 Fundamental 업데이트")
        
        Note:
            - 50개 종목 처리 시 약 2분 소요 (Free Tier 기준)
            - 이미 DB에 있는 종목도 최신 정보로 업데이트
        """
        logger.info(f"📊 Fundamental Data 배치 조회 시작: {len(tickers)}개 종목")
        
        success_count = 0
        error_count = 0
        
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            
            for ticker in batch:
                try:
                    # Polygon API 호출
                    details = await self.client.fetch_ticker_details(ticker)
                    
                    if details and details.get("ticker"):
                        # DB에 저장
                        await self.db.update_fundamentals([details])
                        success_count += 1
                        mc = details.get('market_cap') or 0
                        logger.debug(f"✅ {ticker}: Market Cap ${mc:,.0f}")
                    else:
                        logger.debug(f"⚠️ {ticker}: 데이터 없음")
                        
                except PolygonAPIError as e:
                    logger.warning(f"⚠️ {ticker} 조회 실패: {e}")
                    error_count += 1
                    continue
            
            # 진행 상황 로그
            progress = min(i + batch_size, len(tickers))
            logger.info(f"📊 진행: {progress}/{len(tickers)} 종목 완료")
            
            # 다음 배치 전 대기 (마지막 배치 제외)
            if i + batch_size < len(tickers):
                logger.debug(f"⏳ Rate Limit 대기: {delay_between_batches}초...")
                await asyncio.sleep(delay_between_batches)
        
        logger.info(f"✅ Fundamental Data 완료: {success_count}개 성공, {error_count}개 실패")
        return success_count


# ═══════════════════════════════════════════════════════════════════════════
# 편의 함수 (standalone 사용)
# ═══════════════════════════════════════════════════════════════════════════

async def create_and_update(
    db_path: str = "data/market_data.db",
    api_key: Optional[str] = None,
    initial_days: int = 30,
) -> int:
    """
    데이터베이스 생성 및 업데이트 (원스텁)
    
    서버 시작 시 또는 독립 실행 시 사용할 수 있는 편의 함수입니다.
    
    Args:
        db_path: SQLite DB 경로
        api_key: Polygon API 키 (없으면 환경변수에서 가져옴)
        initial_days: DB가 비어있을 때 로드할 일수
    
    Returns:
        int: 처리된 레코드 수
    
    Example:
        >>> import asyncio
        >>> count = asyncio.run(create_and_update(api_key="your_key"))
    """
    import os
    
    # API 키 확인
    if api_key is None:
        api_key = os.getenv("POLYGON_API_KEY")
    
    if not api_key:
        raise ValueError("POLYGON_API_KEY 환경변수를 설정하거나 api_key를 전달하세요.")
    
    # DB 초기화
    db = MarketDB(db_path)
    await db.initialize()
    
    # Polygon 클라이언트 생성
    async with PolygonClient(api_key) as client:
        loader = PolygonLoader(db, client)
        
        # 상태 확인
        status = await loader.get_sync_status()
        logger.info(f"📊 동기화 상태: {status}")
        
        # DB가 비어있으면 초기 로드
        if status["db_latest_date"] is None:
            return await loader.initial_load(days=initial_days)
        
        # 증분 업데이트
        return await loader.update_market_data()


# ═══════════════════════════════════════════════════════════════════════════
# CLI 실행 (테스트용)
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    독립 실행 테스트
    
    Usage:
        python polygon_loader.py
    
    환경변수:
        POLYGON_API_KEY: Polygon.io API 키
    """
    import os
    import sys
    
    # 로거 설정
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")
    
    api_key = os.getenv("POLYGON_API_KEY")
    if not api_key:
        print("❌ POLYGON_API_KEY 환경변수를 설정하세요.")
        sys.exit(1)
    
    async def main():
        count = await create_and_update(api_key=api_key, initial_days=7)
        print(f"\n✅ 완료: {count}개 레코드 처리")
    
    asyncio.run(main())
