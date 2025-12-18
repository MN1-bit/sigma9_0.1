# ============================================================================
# Scanner Orchestrator - DB 기반 Watchlist 생성
# ============================================================================
# 📌 이 파일의 역할:
#   - Polygon DB 데이터를 기반으로 Watchlist 생성
#   - SeismographStrategy의 calculate_watchlist_score() 실행
#   - 상위 N개 종목을 Watchlist로 반환
#
# 🔄 스캔 프로세스:
#   1. Universe Filter 통과 종목 추출 (가격, 거래량 기준)
#   2. 각 종목의 최근 20일 데이터 조회
#   3. calculate_watchlist_score() 실행
#   4. 점수 순 정렬 → 상위 50개 반환
#
# 📖 사용 예시:
#   >>> scanner = Scanner(db)
#   >>> watchlist = await scanner.run_daily_scan()
#   >>> print(f"Watchlist: {len(watchlist)}개 종목")
# ============================================================================

from typing import Optional
from loguru import logger

from backend.data.database import MarketDB
from backend.strategies.seismograph import SeismographStrategy


# ═══════════════════════════════════════════════════════════════════════════
# Scanner 클래스
# ═══════════════════════════════════════════════════════════════════════════

class Scanner:
    """
    DB 기반 Watchlist 생성 오케스트레이터
    
    Polygon DB에 저장된 히스토리 데이터를 기반으로
    SeismographStrategy의 Accumulation Score를 계산하고
    상위 N개 종목을 Watchlist로 반환합니다.
    
    Attributes:
        db: MarketDB 인스턴스
        strategy: SeismographStrategy 인스턴스
        watchlist_size: Watchlist 크기 (기본값: 50)
    
    Example:
        >>> db = MarketDB("data/market_data.db")
        >>> await db.initialize()
        >>> 
        >>> scanner = Scanner(db)
        >>> watchlist = await scanner.run_daily_scan()
        >>> for item in watchlist[:10]:
        ...     print(f"{item['ticker']}: {item['score']:.1f}점")
    """
    
    def __init__(
        self,
        db: MarketDB,
        watchlist_size: int = 50,
    ):
        """
        Scanner 초기화
        
        Args:
            db: MarketDB 인스턴스 (initialize() 호출 완료 상태)
            watchlist_size: Watchlist에 포함할 종목 수
        """
        self.db = db
        self.watchlist_size = watchlist_size
        
        # SeismographStrategy 인스턴스 생성
        self.strategy = SeismographStrategy()
        
        logger.debug(f"🔍 Scanner 초기화 (Watchlist Size: {watchlist_size})")
    
    # ═══════════════════════════════════════════════════════════════════════
    # 스캔 메서드
    # ═══════════════════════════════════════════════════════════════════════
    
    async def run_daily_scan(
        self,
        min_price: float = 2.0,
        max_price: float = 20.0,
        min_volume: int = 100_000,
        lookback_days: int = 20,
    ) -> list[dict]:
        """
        일일 스캔 실행 - Watchlist 생성
        
        Args:
            min_price: 최소 종가 (기본값: $2.00)
            max_price: 최대 종가 (기본값: $20.00)
            min_volume: 최소 평균 거래량 (기본값: 100K)
            lookback_days: 데이터 조회 기간 (기본값: 20일)
        
        Returns:
            list[dict]: Watchlist (점수 내림차순 정렬)
                [
                    {"ticker": "AAPL", "score": 100.0, "stage": "Stage 4", ...},
                    ...
                ]
        """
        logger.info("🔍 Daily Scan 시작...")
        
        # ─────────────────────────────────────────────────────────────────
        # 1. Universe 후보 추출
        # ─────────────────────────────────────────────────────────────────
        candidates = await self._get_universe_candidates(
            min_price=min_price,
            max_price=max_price,
            min_volume=min_volume,
        )
        
        if not candidates:
            logger.warning("⚠️ Universe 후보가 없습니다. 데이터를 확인하세요.")
            return []
        
        logger.info(f"📊 Universe 후보: {len(candidates)}개 종목")
        
        # ─────────────────────────────────────────────────────────────────
        # 2. 각 종목 스코어링
        # ─────────────────────────────────────────────────────────────────
        results = []
        processed = 0
        
        for ticker in candidates:
            try:
                # DB에서 최근 N일 데이터 조회
                bars = await self.db.get_daily_bars(ticker, days=lookback_days)
                
                # 최소 5일 데이터 필요 (lookback_days보다 적어도 진행)
                if not bars or len(bars) < 5:
                    continue
                
                # DailyBar ORM 객체를 dict 리스트로 변환
                data = [bar.to_dict() for bar in reversed(bars)]  # 오래된 순으로 정렬
                
                # Accumulation Score 상세 계산 (Step 2.2.5 메타데이터 포함)
                result = self.strategy.calculate_watchlist_score_detailed(ticker, data)
                
                # 50점 초과만 Watchlist에 추가 (50점 이하는 관찰 가치 낮음)
                if result["score"] > 50:
                    # 변동률 계산: (최근 종가 - 전일 종가) / 전일 종가 * 100
                    last_close = data[-1]["close"] if data else 0
                    prev_close = data[-2]["close"] if len(data) >= 2 else last_close
                    change_pct = ((last_close - prev_close) / prev_close * 100) if prev_close > 0 else 0.0
                    
                    results.append({
                        "ticker": ticker,
                        "score": result["score"],
                        "stage": result["stage"],
                        "stage_number": result["stage_number"],
                        "signals": result["signals"],
                        "can_trade": result["can_trade"],
                        "last_close": last_close,
                        "change_pct": round(change_pct, 2),  # 소수점 2자리
                        "avg_volume": sum(d["volume"] for d in data) / len(data) if data else 0,
                    })
                
                processed += 1
                
                # 진행 상황 로그 (100개마다)
                if processed % 100 == 0:
                    logger.debug(f"📊 진행: {processed}/{len(candidates)}")
                    
            except Exception as e:
                logger.debug(f"⚠️ {ticker} 스캔 실패: {e}")
                continue
        
        # ─────────────────────────────────────────────────────────────────
        # 3. 점수 순 정렬 → 상위 N개 선택
        # ─────────────────────────────────────────────────────────────────
        results.sort(key=lambda x: x["score"], reverse=True)
        watchlist = results[:self.watchlist_size]
        
        logger.info(f"✅ Daily Scan 완료: {len(watchlist)}개 Watchlist 생성 (총 {len(results)}개 탐지)")
        
        # 상위 5개 로그
        for i, item in enumerate(watchlist[:5]):
            logger.info(f"  {i+1}. {item['ticker']}: {item['score']:.0f}점 ({item['stage']})")
        
        return watchlist
    
    # ═══════════════════════════════════════════════════════════════════════
    # Universe Filter
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _get_universe_candidates(
        self,
        min_price: float,
        max_price: float,
        min_volume: int,
    ) -> list[str]:
        """
        Universe 후보 종목 추출
        
        가격, 거래량 조건으로 필터링합니다.
        
        Args:
            min_price: 최소 종가
            max_price: 최대 종가
            min_volume: 최소 평균 거래량
        
        Returns:
            list[str]: 종목 심볼 리스트
        """
        # 현재 DB에 있는 모든 종목 조회
        all_tickers = await self.db.get_all_tickers_with_data()
        
        if not all_tickers:
            return []
        
        # 간단 필터: 최근 종가와 거래량으로 필터링
        # TODO: 더 효율적인 쿼리 기반 필터링 구현
        candidates = []
        
        for ticker in all_tickers:
            try:
                bars = await self.db.get_daily_bars(ticker, days=5)
                
                if not bars:
                    continue
                
                # 최근 종가
                last_close = bars[0].close
                
                # 최근 5일 평균 거래량
                avg_volume = sum(b.volume for b in bars) / len(bars)
                
                # 필터 조건 체크
                if min_price <= last_close <= max_price and avg_volume >= min_volume:
                    candidates.append(ticker)
                    
            except Exception:
                continue
        
        return candidates
    
    # ═══════════════════════════════════════════════════════════════════════
    # 유틸리티
    # ═══════════════════════════════════════════════════════════════════════
    
    @staticmethod
    def _score_to_stage(score: float) -> str:
        """
        점수를 Stage 문자열로 변환
        
        Args:
            score: Accumulation Score
        
        Returns:
            str: Stage 문자열
        """
        if score >= 100:
            return "Stage 4 (폭발 임박 🔥)"
        elif score >= 80:
            return "Stage 4 (Tight Range)"
        elif score >= 70:
            return "Stage 3 (관심 대상)"
        elif score >= 50:
            return "Stage 3 (Accum Bar)"
        elif score >= 30:
            return "Stage 2 (OBV Divergence)"
        elif score >= 10:
            return "Stage 1 (Volume Dry-out)"
        else:
            return "No Signal"


# ═══════════════════════════════════════════════════════════════════════════
# 편의 함수
# ═══════════════════════════════════════════════════════════════════════════

async def run_scan(db_path: str = "data/market_data.db") -> list[dict]:
    """
    스캔 실행 편의 함수
    
    Args:
        db_path: MarketDB 경로
    
    Returns:
        list[dict]: Watchlist
    """
    db = MarketDB(db_path)
    await db.initialize()
    
    scanner = Scanner(db)
    watchlist = await scanner.run_daily_scan()
    
    await db.close()
    return watchlist


# ═══════════════════════════════════════════════════════════════════════════
# CLI 실행
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    독립 실행 테스트
    
    Usage:
        python scanner.py
    """
    import asyncio
    import sys
    
    # 로거 설정
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")
    
    async def main():
        watchlist = await run_scan()
        
        print("\n" + "=" * 60)
        print("📋 WATCHLIST")
        print("=" * 60)
        
        for i, item in enumerate(watchlist, 1):
            print(f"{i:3}. {item['ticker']:6} | {item['score']:5.0f}점 | {item['stage']}")
    
    asyncio.run(main())
