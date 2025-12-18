# ============================================================================
# Market Data Database - SQLAlchemy 2.0 Async
# ============================================================================
# 📌 이 파일의 역할:
#   - 시장 데이터를 SQLite에 저장하고 조회하는 데이터베이스 레이어
#   - ORM 모델 정의 (DailyBar, Ticker)
#   - Bulk Insert/Upsert 최적화
#
# 🗄️ 테이블 구조:
#   - daily_bars: 일별 OHLCV 시계열 데이터 (Composite PK: ticker + date)
#   - tickers: 종목 메타정보 + 펀더멘털 (시가총액, Float 등)
#
# ⚙️ 최적화:
#   - WAL Mode (Write-Ahead Logging) 활성화로 동시성 향상
#   - Bulk Upsert로 대량 데이터 빠르게 처리
#
# 📖 사용 예시:
#   >>> db = MarketDB("data/market_data.db")
#   >>> await db.initialize()
#   >>> await db.upsert_bulk([bar1, bar2, bar3])
# ============================================================================

import os
from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import String, Float, Integer, Text, select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from loguru import logger


# ═══════════════════════════════════════════════════════════════════════════
# ORM Base 클래스
# ═══════════════════════════════════════════════════════════════════════════

class Base(DeclarativeBase):
    """
    SQLAlchemy ORM의 기본 클래스
    
    모든 ORM 모델은 이 클래스를 상속받습니다.
    SQLAlchemy 2.0 스타일의 DeclarativeBase를 사용합니다.
    """
    pass


# ═══════════════════════════════════════════════════════════════════════════
# DailyBar 모델 - 일봉 시계열 데이터
# ═══════════════════════════════════════════════════════════════════════════

class DailyBar(Base):
    """
    일별 OHLCV 데이터 모델
    
    Polygon.io의 Grouped Daily API에서 받아온 데이터를 저장합니다.
    각 종목(ticker)과 날짜(date)의 조합이 Primary Key입니다.
    
    Attributes:
        ticker: 종목 심볼 (예: "AAPL", "MSFT")
        date: 거래일 (YYYY-MM-DD 형식)
        open: 시가 (Opening Price)
        high: 고가 (High Price)
        low: 저가 (Low Price)
        close: 종가 (Closing Price)
        volume: 거래량 (체결 수량)
        vwap: 거래량 가중 평균가 (Volume Weighted Average Price)
        transactions: 체결 건수 (거래 횟수)
    
    Example:
        >>> bar = DailyBar(
        ...     ticker="AAPL",
        ...     date="2024-12-17",
        ...     open=150.0,
        ...     high=152.5,
        ...     low=149.0,
        ...     close=151.0,
        ...     volume=50000000,
        ...     vwap=150.8,
        ...     transactions=100000
        ... )
    """
    __tablename__ = "daily_bars"
    
    # ─────────────────────────────────────────────────────────────────────
    # Primary Key (Composite: ticker + date)
    # ─────────────────────────────────────────────────────────────────────
    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    date: Mapped[str] = mapped_column(String(10), primary_key=True)  # YYYY-MM-DD
    
    # ─────────────────────────────────────────────────────────────────────
    # OHLCV 데이터
    # ─────────────────────────────────────────────────────────────────────
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # ─────────────────────────────────────────────────────────────────────
    # 추가 메타데이터
    # ─────────────────────────────────────────────────────────────────────
    vwap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    transactions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    def __repr__(self) -> str:
        return f"<DailyBar({self.ticker} @ {self.date}: O={self.open} H={self.high} L={self.low} C={self.close} V={self.volume})>"
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환 (API 응답용)"""
        return {
            "ticker": self.ticker,
            "date": self.date,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "vwap": self.vwap,
            "transactions": self.transactions,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Ticker 모델 - 종목 메타정보 + 펀더멘털
# ═══════════════════════════════════════════════════════════════════════════

class Ticker(Base):
    """
    종목 메타정보 및 펀더멘털 데이터 모델
    
    Universe Filter에 사용되는 시가총액, Float 등의 정보를 저장합니다.
    Polygon.io의 Ticker Details API에서 가져옵니다.
    
    Attributes:
        ticker: 종목 심볼 (Primary Key)
        name: 종목명 (회사명)
        market_cap: 시가총액 (USD)
        outstanding_shares: 총 발행 주식 수
        float_shares: 유통 주식 수 (거래 가능한 주식)
        primary_exchange: 주 거래소 (NYSE, NASDAQ 등)
        last_updated: 마지막 업데이트 날짜
    
    Note:
        - market_cap과 float_shares는 Universe Filter에서 중요하게 사용됩니다.
        - masterplan.md 3.1절의 필터 조건 참고:
          * Market Cap: $50M ~ $300M (마이크로캡)
          * Float: < 15M shares (Low Float)
    """
    __tablename__ = "tickers"
    
    # ─────────────────────────────────────────────────────────────────────
    # Primary Key
    # ─────────────────────────────────────────────────────────────────────
    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    
    # ─────────────────────────────────────────────────────────────────────
    # 기본 정보
    # ─────────────────────────────────────────────────────────────────────
    name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    primary_exchange: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # ─────────────────────────────────────────────────────────────────────
    # 펀더멘털 (Universe Filter용)
    # ─────────────────────────────────────────────────────────────────────
    market_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    outstanding_shares: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    float_shares: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # ─────────────────────────────────────────────────────────────────────
    # 메타데이터
    # ─────────────────────────────────────────────────────────────────────
    last_updated: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    
    def __repr__(self) -> str:
        return f"<Ticker({self.ticker}: {self.name}, MCap=${self.market_cap:,.0f})>" if self.market_cap else f"<Ticker({self.ticker})>"
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환 (API 응답용)"""
        return {
            "ticker": self.ticker,
            "name": self.name,
            "market_cap": self.market_cap,
            "outstanding_shares": self.outstanding_shares,
            "float_shares": self.float_shares,
            "primary_exchange": self.primary_exchange,
            "last_updated": self.last_updated,
        }


# ═══════════════════════════════════════════════════════════════════════════
# MarketDB 클래스 - 데이터베이스 매니저
# ═══════════════════════════════════════════════════════════════════════════

class MarketDB:
    """
    시장 데이터 데이터베이스 매니저
    
    SQLite 데이터베이스에 대한 CRUD 작업을 담당합니다.
    WAL 모드로 동시성을 최적화하고, Bulk Upsert로 대량 데이터를 빠르게 처리합니다.
    
    Attributes:
        db_path: SQLite 파일 경로
        engine: SQLAlchemy Async Engine
        session_factory: Async Session 팩토리
    
    Example:
        >>> db = MarketDB("data/market_data.db")
        >>> await db.initialize()  # 테이블 생성 + WAL 모드
        >>> 
        >>> # 데이터 조회
        >>> bars = await db.get_daily_bars("AAPL", days=20)
        >>> 
        >>> # 데이터 삽입/업데이트
        >>> await db.upsert_bulk([bar1, bar2, bar3])
    """
    
    def __init__(self, db_path: str = "data/market_data.db"):
        """
        MarketDB 초기화
        
        Args:
            db_path: SQLite 파일 경로 (기본값: "data/market_data.db")
        
        Note:
            - 파일이 없으면 자동 생성됩니다.
            - 경로의 상위 디렉토리가 없으면 생성합니다.
        """
        self.db_path = db_path
        
        # ─────────────────────────────────────────────────────────────────
        # 디렉토리 생성 (없으면)
        # ─────────────────────────────────────────────────────────────────
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            logger.info(f"📁 데이터베이스 디렉토리 생성: {db_dir}")
        
        # ─────────────────────────────────────────────────────────────────
        # SQLAlchemy Async Engine 생성
        # - aiosqlite 드라이버 사용 (비동기 SQLite)
        # - echo=False: SQL 쿼리 로깅 비활성화 (성능)
        # ─────────────────────────────────────────────────────────────────
        self.engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}",
            echo=False,  # SQL 쿼리 로깅 (디버그 시 True)
        )
        
        # ─────────────────────────────────────────────────────────────────
        # Session Factory 생성
        # - expire_on_commit=False: 커밋 후에도 객체 접근 가능
        # ─────────────────────────────────────────────────────────────────
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        logger.debug(f"🗄️ MarketDB 초기화: {db_path}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # 초기화 메서드
    # ═══════════════════════════════════════════════════════════════════════
    
    async def initialize(self) -> None:
        """
        데이터베이스 초기화
        
        테이블이 없으면 생성하고, WAL 모드를 활성화합니다.
        
        WAL (Write-Ahead Logging) 모드:
            - 읽기와 쓰기를 동시에 할 수 있어서 동시성이 향상됩니다.
            - 쓰기 작업이 더 빨라집니다 (특히 Bulk Insert).
            - 전원 장애 시에도 데이터 무결성이 보장됩니다.
        """
        # ─────────────────────────────────────────────────────────────────
        # 테이블 생성 (없으면)
        # ─────────────────────────────────────────────────────────────────
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # ─────────────────────────────────────────────────────────────────
        # WAL 모드 활성화
        # ─────────────────────────────────────────────────────────────────
        async with self.session_factory() as session:
            await session.execute(text("PRAGMA journal_mode=WAL"))
            await session.execute(text("PRAGMA synchronous=NORMAL"))  # 성능 향상
            await session.commit()
        
        logger.info("✅ 데이터베이스 초기화 완료 (WAL Mode 활성화)")
    
    # ═══════════════════════════════════════════════════════════════════════
    # DailyBar CRUD
    # ═══════════════════════════════════════════════════════════════════════
    
    async def upsert_bulk(self, bars: Sequence[dict], chunk_size: int = 500) -> int:
        """
        일봉 데이터 Bulk Upsert (INSERT OR REPLACE)
        
        같은 (ticker, date) 조합이 있으면 업데이트하고,
        없으면 새로 삽입합니다.
        
        SQLite의 파라미터 제한을 피하기 위해 청크 단위로 처리합니다.
        
        Args:
            bars: 딕셔너리 리스트. 각 딕셔너리는 다음 키를 가집니다:
                  ticker, date, open, high, low, close, volume, vwap, transactions
            chunk_size: 한 번에 처리할 레코드 수 (기본값: 500)
        
        Returns:
            int: 처리된 레코드 수
        
        Example:
            >>> bars = [
            ...     {"ticker": "AAPL", "date": "2024-12-17", "open": 150.0, ...},
            ...     {"ticker": "MSFT", "date": "2024-12-17", "open": 380.0, ...},
            ... ]
            >>> count = await db.upsert_bulk(bars)
            >>> print(f"{count}개 레코드 처리됨")
        """
        if not bars:
            return 0
        
        total_count = 0
        
        # ─────────────────────────────────────────────────────────────────
        # 청크 단위로 분할 처리
        # SQLite는 한 쿼리에 999개 파라미터 제한이 있음
        # 각 레코드가 9개 컬럼 → 약 100개 레코드가 한계
        # 안전하게 500개씩 처리 (9*500=4500 < SQLITE_MAX_VARIABLE_NUMBER)
        # ─────────────────────────────────────────────────────────────────
        for i in range(0, len(bars), chunk_size):
            chunk = bars[i:i + chunk_size]
            
            async with self.session_factory() as session:
                # ─────────────────────────────────────────────────────────
                # SQLite INSERT OR REPLACE 사용
                # - Primary Key 충돌 시 기존 레코드를 새 값으로 교체
                # ─────────────────────────────────────────────────────────
                stmt = sqlite_insert(DailyBar).values(list(chunk))
                stmt = stmt.on_conflict_do_update(
                    index_elements=["ticker", "date"],
                    set_={
                        "open": stmt.excluded.open,
                        "high": stmt.excluded.high,
                        "low": stmt.excluded.low,
                        "close": stmt.excluded.close,
                        "volume": stmt.excluded.volume,
                        "vwap": stmt.excluded.vwap,
                        "transactions": stmt.excluded.transactions,
                    }
                )
                
                await session.execute(stmt)
                await session.commit()
            
            total_count += len(chunk)
        
        logger.debug(f"📊 {total_count}개 일봉 데이터 Upsert 완료")
        return total_count
    
    async def get_daily_bars(
        self, 
        ticker: str, 
        days: int = 20,
        end_date: Optional[str] = None
    ) -> list[DailyBar]:
        """
        특정 종목의 최근 N일 일봉 데이터 조회
        
        Seismograph 전략의 매집 탐지에 사용됩니다.
        날짜 내림차순으로 정렬하여 최신 데이터부터 반환합니다.
        
        Args:
            ticker: 종목 심볼 (예: "AAPL")
            days: 가져올 일수 (기본값: 20)
            end_date: 조회 종료일 (기본값: None = 오늘)
        
        Returns:
            list[DailyBar]: 일봉 데이터 리스트 (최신순)
        
        Example:
            >>> bars = await db.get_daily_bars("AAPL", days=20)
            >>> for bar in bars:
            ...     print(f"{bar.date}: Close={bar.close}")
        """
        async with self.session_factory() as session:
            query = (
                select(DailyBar)
                .where(DailyBar.ticker == ticker)
            )
            
            if end_date:
                query = query.where(DailyBar.date <= end_date)
            
            query = query.order_by(DailyBar.date.desc()).limit(days)
            
            result = await session.execute(query)
            return list(result.scalars().all())
    
    async def get_latest_date(self) -> Optional[str]:
        """
        DB에 저장된 가장 최근 날짜 조회
        
        증분 업데이트 시 이 날짜 이후의 데이터만 가져옵니다.
        
        Returns:
            str | None: 가장 최근 날짜 (YYYY-MM-DD) 또는 데이터가 없으면 None
        
        Example:
            >>> latest = await db.get_latest_date()
            >>> print(f"마지막 업데이트: {latest}")  # "2024-12-16"
        """
        async with self.session_factory() as session:
            result = await session.execute(
                select(DailyBar.date)
                .order_by(DailyBar.date.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            return row
    
    async def get_all_tickers_with_data(self) -> list[str]:
        """
        데이터가 있는 모든 종목 심볼 조회
        
        Universe Filter 적용 전 전체 종목 리스트를 가져올 때 사용합니다.
        
        Returns:
            list[str]: 종목 심볼 리스트
        """
        async with self.session_factory() as session:
            result = await session.execute(
                select(DailyBar.ticker).distinct()
            )
            return [row[0] for row in result.all()]
    
    # ═══════════════════════════════════════════════════════════════════════
    # Ticker CRUD
    # ═══════════════════════════════════════════════════════════════════════
    
    async def update_fundamentals(self, tickers: Sequence[dict]) -> int:
        """
        종목 펀더멘털 정보 Bulk Upsert
        
        Args:
            tickers: 딕셔너리 리스트. 각 딕셔너리는 다음 키를 가집니다:
                     ticker, name, market_cap, outstanding_shares, 
                     float_shares, primary_exchange, last_updated
        
        Returns:
            int: 처리된 레코드 수
        """
        if not tickers:
            return 0
        
        async with self.session_factory() as session:
            stmt = sqlite_insert(Ticker).values(tickers)
            stmt = stmt.on_conflict_do_update(
                index_elements=["ticker"],
                set_={
                    "name": stmt.excluded.name,
                    "market_cap": stmt.excluded.market_cap,
                    "outstanding_shares": stmt.excluded.outstanding_shares,
                    "float_shares": stmt.excluded.float_shares,
                    "primary_exchange": stmt.excluded.primary_exchange,
                    "last_updated": stmt.excluded.last_updated,
                }
            )
            
            await session.execute(stmt)
            await session.commit()
        
        logger.debug(f"📋 {len(tickers)}개 종목 펀더멘털 Upsert 완료")
        return len(tickers)
    
    async def get_ticker_info(self, ticker: str) -> Optional[Ticker]:
        """
        특정 종목의 메타정보 조회
        
        Args:
            ticker: 종목 심볼
        
        Returns:
            Ticker | None: 종목 정보 또는 없으면 None
        """
        async with self.session_factory() as session:
            result = await session.execute(
                select(Ticker).where(Ticker.ticker == ticker)
            )
            return result.scalar_one_or_none()
    
    async def get_universe_candidates(
        self,
        min_price: float = 2.0,
        max_price: float = 10.0,
        min_market_cap: float = 50_000_000,  # $50M
        max_market_cap: float = 300_000_000,  # $300M
        max_float: float = 15_000_000,  # 15M shares
        min_volume: int = 100_000,
    ) -> list[str]:
        """
        Universe Filter 조건에 맞는 종목 조회
        
        masterplan.md 3.1절 기준으로 필터링합니다:
        - Price: $2.00 ~ $10.00
        - Market Cap: $50M ~ $300M
        - Float: < 15M shares
        - Avg Volume: > 100K/day
        
        Args:
            min_price, max_price: 가격 범위
            min_market_cap, max_market_cap: 시가총액 범위
            max_float: 최대 Float
            min_volume: 최소 평균 거래량
        
        Returns:
            list[str]: 조건에 맞는 종목 심볼 리스트
        """
        # TODO: 실제 구현 시 DailyBar와 Ticker를 JOIN하여 필터링
        # 현재는 Ticker 테이블만으로 기본 필터링
        async with self.session_factory() as session:
            query = (
                select(Ticker.ticker)
                .where(Ticker.market_cap >= min_market_cap)
                .where(Ticker.market_cap <= max_market_cap)
                .where(Ticker.float_shares <= max_float)
            )
            
            result = await session.execute(query)
            return [row[0] for row in result.all()]
    
    # ═══════════════════════════════════════════════════════════════════════
    # 유틸리티
    # ═══════════════════════════════════════════════════════════════════════
    
    async def get_stats(self) -> dict:
        """
        데이터베이스 통계 조회
        
        Returns:
            dict: 통계 정보
                  - total_bars: 총 일봉 레코드 수
                  - total_tickers: 총 종목 수
                  - latest_date: 가장 최근 날짜
                  - oldest_date: 가장 오래된 날짜
        """
        async with self.session_factory() as session:
            # 총 레코드 수
            bar_count = await session.execute(
                text("SELECT COUNT(*) FROM daily_bars")
            )
            total_bars = bar_count.scalar() or 0
            
            ticker_count = await session.execute(
                text("SELECT COUNT(*) FROM tickers")
            )
            total_tickers = ticker_count.scalar() or 0
            
            # 날짜 범위
            dates = await session.execute(
                text("SELECT MIN(date), MAX(date) FROM daily_bars")
            )
            date_row = dates.one_or_none()
            oldest_date = date_row[0] if date_row else None
            latest_date = date_row[1] if date_row else None
        
        return {
            "total_bars": total_bars,
            "total_tickers": total_tickers,
            "oldest_date": oldest_date,
            "latest_date": latest_date,
        }
    
    async def close(self) -> None:
        """
        데이터베이스 연결 종료
        
        애플리케이션 종료 시 호출하여 리소스를 정리합니다.
        """
        await self.engine.dispose()
        logger.debug("🗄️ MarketDB 연결 종료")
