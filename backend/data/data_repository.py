# ============================================================================
# Data Repository - 통합 데이터 접근 레이어
# ============================================================================
# 📌 이 파일의 역할:
#   - 모든 시장 데이터 접근을 단일 인터페이스로 통합
#   - Parquet을 Primary Storage로 사용
#   - On-Demand Gap Fill 지원 (누락 데이터 자동 API 호출)
#   - 보조지표 캐싱 + 스코어 FlushPolicy 적용
#
# 📖 사용 예시:
#   >>> repo = DataRepository(parquet_manager, massive_client)
#   >>> df = await repo.get_daily_bars("AAPL", days=60)
#   >>> repo.update_score("AAPL", "v3", {"score": 85, ...})
#
# 📌 [11-002] DataRepository 리팩터링
# ============================================================================

from pathlib import Path
from typing import Any, Optional
import time
import pandas as pd
from loguru import logger

from backend.data.parquet_manager import ParquetManager
from backend.data.flush_policy import FlushPolicy, IntervalFlush


# ═══════════════════════════════════════════════════════════════════════════
# DataRepository 클래스
# ═══════════════════════════════════════════════════════════════════════════


class DataRepository:
    """
    통합 데이터 접근 레이어

    모든 시장 데이터 접근은 이 클래스를 통해 이루어집니다.
    Parquet을 Primary Storage로 사용하며, On-Demand Gap Fill을 지원합니다.

    ELI5: 데이터가 필요하면 이 클래스한테 물어보세요.
          로컬에 없으면 알아서 API 호출해서 가져와 줍니다.

    Attributes:
        _pm: ParquetManager 인스턴스 (Low-Level I/O)
        _client: MassiveClient 인스턴스 (API 호출용, None 가능)
        _flush_policy: 스코어 Flush 정책
        _score_cache: 메모리 스코어 캐시
        _indicator_cache: 보조지표 메모리 캐시

    Example:
        >>> pm = ParquetManager("data/parquet")
        >>> repo = DataRepository(pm, massive_client=client)
        >>> df = await repo.get_daily_bars("AAPL", days=60)
    """

    def __init__(
        self,
        parquet_manager: ParquetManager,
        massive_client: Optional[Any] = None,
        flush_policy: Optional[FlushPolicy] = None,
    ):
        """
        DataRepository 초기화

        Args:
            parquet_manager: Parquet I/O 담당 (필수)
            massive_client: Massive API 클라이언트 (Gap Fill용, 선택)
            flush_policy: 스코어 Flush 정책 (기본: IntervalFlush(30초))
        """
        # 핵심 의존성
        self._pm = parquet_manager
        self._client = massive_client

        # FlushPolicy (ELI5: 스코어를 언제 파일에 저장할지 결정)
        self._flush_policy = flush_policy or IntervalFlush(interval_seconds=30.0)

        # 스코어 캐시 (메모리) - {ticker: score_data}
        self._score_cache: dict[str, dict[str, Any]] = {}
        self._last_flush = time.time()
        self._update_count = 0

        # 보조지표 캐시 경로
        self._indicator_dir = Path(self._pm.base_dir) / "indicators"
        self._indicator_dir.mkdir(parents=True, exist_ok=True)

        # 스코어 저장 경로
        self._scores_dir = Path(self._pm.base_dir) / "scores"
        self._scores_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"📦 DataRepository initialized (FlushPolicy: {type(self._flush_policy).__name__})")

    # ═══════════════════════════════════════════════════════════════════════
    # Daily/Intraday Data (auto_fill=True 기본값)
    # ═══════════════════════════════════════════════════════════════════════

    async def get_daily_bars(
        self,
        ticker: str,
        days: int = 60,
        *,
        auto_fill: bool = True,
    ) -> pd.DataFrame:
        """
        일봉 데이터 조회 (누락 시 API 자동 호출)

        ELI5: "AAPL 60일치 일봉 줘" → 없으면 API에서 가져와서 저장 후 반환

        Args:
            ticker: 종목 심볼 (예: "AAPL")
            days: 조회할 일수 (기본 60일)
            auto_fill: True면 누락 데이터 API 호출 후 저장 (기본값: True)

        Returns:
            pd.DataFrame: 일봉 데이터 (빈 경우 빈 DataFrame)
        """
        # 1. 로컬 Parquet에서 먼저 조회
        df = self._pm.read_daily(ticker, days)

        # 2. auto_fill=True이고 데이터가 부족하면 Gap Fill
        if auto_fill and self._has_daily_gaps(df, ticker, days):
            await self._fill_daily_gaps(ticker, days)
            # 다시 조회
            df = self._pm.read_daily(ticker, days)

        return df

    async def get_intraday_bars(
        self,
        ticker: str,
        timeframe: str,
        days: int = 2,
        *,
        auto_fill: bool = True,
    ) -> pd.DataFrame:
        """
        분봉/시봉 데이터 조회 (누락 시 API 자동 호출)

        ELI5: "AAPL 1분봉 2일치 줘" → 없으면 API에서 가져옴

        Args:
            ticker: 종목 심볼
            timeframe: 타임프레임 ("1m", "5m", "15m", "1h")
            days: 조회할 일수 (기본 2일)
            auto_fill: True면 누락 데이터 API 호출 후 저장

        Returns:
            pd.DataFrame: Intraday 데이터
        """
        # 1. 로컬에서 먼저 조회
        df = self._pm.read_intraday(ticker, timeframe, days)

        # 2. auto_fill=True이고 데이터가 부족하면 Gap Fill
        if auto_fill and self._has_intraday_gaps(df, ticker, timeframe, days):
            await self._fill_intraday_gaps(ticker, timeframe, days)
            df = self._pm.read_intraday(ticker, timeframe, days)

        return df

    def get_all_tickers(self) -> list[str]:
        """
        저장된 일봉 데이터의 티커 목록

        Returns:
            list[str]: 사용 가능한 티커 목록
        """
        return self._pm.get_available_tickers()

    def get_daily_bars_bulk(
        self,
        tickers: list[str] | None = None,
        days: int = 20,
    ) -> dict[str, list[dict]]:
        """
        [12-002] 여러 티커의 일봉 데이터를 벌크로 조회

        ELI5: Parquet 파일 1회 읽기로 모든 티커 데이터를 가져옵니다.
              티커 10,000개를 조회해도 파일 I/O는 1번만 발생합니다.

        주의: auto_fill을 지원하지 않습니다. 로컬 데이터만 반환합니다.
              API 호출이 필요하면 get_daily_bars()를 사용하세요.

        Args:
            tickers: 조회할 티커 목록 (None이면 전체)
            days: 조회할 일수 (기본값: 20)

        Returns:
            dict[str, list[dict]]: 티커 → 일봉 데이터 (날짜순 정렬)
                예: {"AAPL": [{"date": "2024-01-01", ...}, ...], ...}
        """
        return self._pm.read_daily_bulk(tickers=tickers, days=days)

    # ═══════════════════════════════════════════════════════════════════════
    # Gap Detection & Fill (누락 감지 및 보충)
    # ═══════════════════════════════════════════════════════════════════════

    def _has_daily_gaps(self, df: pd.DataFrame, ticker: str, days: int) -> bool:
        """
        일봉 데이터 누락 여부 판단

        ELI5: 60일치 요청했는데 30일치만 있으면 "누락"

        Args:
            df: 현재 조회된 데이터
            ticker: 티커 (로깅용)
            days: 요청한 일수

        Returns:
            bool: True면 Gap Fill 필요
        """
        if df.empty:
            # 데이터 없음 = Gap
            logger.debug(f"📭 No daily data for {ticker}, gap fill needed")
            return True

        # 실제 거래일 수 계산 (주말 제외하면 약 70%)
        expected_trading_days = int(days * 0.7)

        if len(df) < expected_trading_days:
            logger.debug(
                f"📭 Insufficient daily data for {ticker}: "
                f"{len(df)}/{expected_trading_days} expected"
            )
            return True

        return False

    def _has_intraday_gaps(
        self, df: pd.DataFrame, ticker: str, timeframe: str, days: int
    ) -> bool:
        """
        Intraday 데이터 누락 여부 판단

        Args:
            df: 현재 조회된 데이터
            ticker: 티커
            timeframe: 타임프레임
            days: 요청한 일수

        Returns:
            bool: True면 Gap Fill 필요
        """
        if df.empty:
            logger.debug(f"📭 No intraday data for {ticker}_{timeframe}, gap fill needed")
            return True

        # 1분봉 기준 하루 약 390분 (6.5시간 * 60분)
        # 시봉 기준 하루 약 7시간
        bars_per_day = {"1m": 390, "5m": 78, "15m": 26, "1h": 7}.get(timeframe, 390)
        expected_bars = bars_per_day * days * 0.5  # 보수적으로 50%

        if len(df) < expected_bars:
            logger.debug(
                f"📭 Insufficient intraday data for {ticker}_{timeframe}: "
                f"{len(df)}/{int(expected_bars)} expected"
            )
            return True

        return False

    async def _fill_daily_gaps(self, ticker: str, days: int) -> None:
        """
        일봉 Gap Fill (Massive API 호출)

        Args:
            ticker: 종목 심볼
            days: 조회할 일수
        """
        if not self._client:
            logger.warning(f"⚠️ Cannot fill daily gaps for {ticker}: no API client")
            return

        try:
            logger.info(f"🔄 Filling daily gaps for {ticker} ({days} days)")

            # Massive API 호출 (daily bars)
            bars = await self._client.get_bars(ticker, interval="1d", limit=days)

            if not bars:
                logger.warning(f"⚠️ No daily bars returned for {ticker}")
                return

            # DataFrame 변환 및 저장
            df = self._bars_to_daily_df(ticker, bars)
            if not df.empty:
                self._pm.append_daily(df)
                logger.info(f"✅ Daily gap filled for {ticker}: {len(df)} bars")

        except Exception as e:
            logger.error(f"❌ Failed to fill daily gaps for {ticker}: {e}")

    async def _fill_intraday_gaps(
        self, ticker: str, timeframe: str, days: int
    ) -> None:
        """
        Intraday Gap Fill (Massive API 호출)

        Args:
            ticker: 종목 심볼
            timeframe: 타임프레임
            days: 조회할 일수
        """
        if not self._client:
            logger.warning(f"⚠️ Cannot fill intraday gaps for {ticker}: no API client")
            return

        try:
            logger.info(f"🔄 Filling intraday gaps for {ticker}_{timeframe} ({days} days)")

            # Massive API 호출
            # timeframe 변환: "1m" -> "1min", "1h" -> "1hour"
            api_interval = self._timeframe_to_api_interval(timeframe)
            bars = await self._client.get_bars(ticker, interval=api_interval, limit=days * 400)

            if not bars:
                logger.warning(f"⚠️ No intraday bars returned for {ticker}")
                return

            # DataFrame 변환 및 저장
            df = self._bars_to_intraday_df(bars)
            if not df.empty:
                self._pm.append_intraday(ticker, timeframe, df)
                logger.info(f"✅ Intraday gap filled for {ticker}_{timeframe}: {len(df)} bars")

        except Exception as e:
            logger.error(f"❌ Failed to fill intraday gaps for {ticker}: {e}")

    def _timeframe_to_api_interval(self, timeframe: str) -> str:
        """
        ParquetManager timeframe → Massive API interval 변환

        Args:
            timeframe: "1m", "5m", "15m", "1h"

        Returns:
            str: API interval ("1min", "5min", "15min", "1hour")
        """
        mapping = {
            "1m": "1min",
            "5m": "5min",
            "15m": "15min",
            "1h": "1hour",
        }
        return mapping.get(timeframe, "1min")

    def _bars_to_daily_df(self, ticker: str, bars: list[dict]) -> pd.DataFrame:
        """
        API 응답을 일봉 DataFrame으로 변환

        Args:
            ticker: 종목 심볼
            bars: API 응답 바 리스트

        Returns:
            pd.DataFrame: 일봉 데이터
        """
        if not bars:
            return pd.DataFrame()

        records = []
        for bar in bars:
            records.append({
                "ticker": ticker,
                "date": bar.get("date") or bar.get("t", ""),
                "open": bar.get("open") or bar.get("o", 0),
                "high": bar.get("high") or bar.get("h", 0),
                "low": bar.get("low") or bar.get("l", 0),
                "close": bar.get("close") or bar.get("c", 0),
                "volume": bar.get("volume") or bar.get("v", 0),
            })

        return pd.DataFrame(records)

    def _bars_to_intraday_df(self, bars: list[dict]) -> pd.DataFrame:
        """
        API 응답을 Intraday DataFrame으로 변환

        Args:
            bars: API 응답 바 리스트

        Returns:
            pd.DataFrame: Intraday 데이터
        """
        if not bars:
            return pd.DataFrame()

        records = []
        for bar in bars:
            records.append({
                "timestamp": bar.get("timestamp") or bar.get("t", 0),
                "open": bar.get("open") or bar.get("o", 0),
                "high": bar.get("high") or bar.get("h", 0),
                "low": bar.get("low") or bar.get("l", 0),
                "close": bar.get("close") or bar.get("c", 0),
                "volume": bar.get("volume") or bar.get("v", 0),
            })

        return pd.DataFrame(records)

    # ═══════════════════════════════════════════════════════════════════════
    # Indicators (On-Demand 생산 + 저장)
    # ═══════════════════════════════════════════════════════════════════════

    def get_indicator(
        self,
        ticker: str,
        indicator: str,
        days: int = 60,
    ) -> Optional[pd.Series]:
        """
        보조지표 조회 (캐시 우선, 없으면 계산 후 저장)

        ELI5: "SMA 20일 줘" → 이미 계산했으면 바로 반환,
              없으면 계산해서 저장 후 반환

        Args:
            ticker: 종목 심볼
            indicator: 지표 이름 (예: "sma_20", "rsi_14")
            days: 계산에 사용할 일수

        Returns:
            pd.Series: 계산된 지표 (없으면 None)
        """
        # 1. 캐시에서 먼저 확인
        cached = self._load_indicator_cache(ticker, indicator)
        if cached is not None:
            return cached

        # 2. 계산
        result = self._calculate_indicator(ticker, indicator, days)

        # 3. 저장 (On-Demand 생산 시 항상 저장)
        if result is not None:
            self._save_indicator_cache(ticker, indicator, result)

        return result

    def _load_indicator_cache(self, ticker: str, indicator: str) -> Optional[pd.Series]:
        """
        보조지표 캐시 로드

        Args:
            ticker: 종목 심볼
            indicator: 지표 이름

        Returns:
            pd.Series: 캐시된 지표 (없으면 None)
        """
        path = self._indicator_dir / f"{indicator}_{ticker}.parquet"
        if not path.exists():
            return None

        try:
            import pyarrow.parquet as pq
            df = pq.read_table(path).to_pandas()
            if "value" in df.columns:
                return df["value"]
            return None
        except Exception as e:
            logger.warning(f"⚠️ Failed to load indicator cache: {e}")
            return None

    def _save_indicator_cache(self, ticker: str, indicator: str, data: pd.Series) -> None:
        """
        보조지표 캐시 저장

        Args:
            ticker: 종목 심볼
            indicator: 지표 이름
            data: 계산된 지표 시리즈
        """
        path = self._indicator_dir / f"{indicator}_{ticker}.parquet"
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq

            df = pd.DataFrame({"value": data})
            pq.write_table(pa.Table.from_pandas(df), path, compression="snappy")
            logger.debug(f"💾 Indicator cached: {indicator}_{ticker}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to save indicator cache: {e}")

    def _calculate_indicator(
        self, ticker: str, indicator: str, days: int
    ) -> Optional[pd.Series]:
        """
        보조지표 계산

        지원 지표:
            - sma_{period}: 단순 이동평균
            - ema_{period}: 지수 이동평균
            - rsi_{period}: RSI

        Args:
            ticker: 종목 심볼
            indicator: 지표 이름 (예: "sma_20")
            days: 계산에 사용할 일수

        Returns:
            pd.Series: 계산된 지표 (실패 시 None)
        """
        # 일봉 데이터 조회 (동기 버전, cache only)
        df = self._pm.read_daily(ticker, days)
        if df.empty or "close" not in df.columns:
            return None

        close = df["close"]

        # 지표 파싱 (예: "sma_20" → type="sma", period=20)
        parts = indicator.split("_")
        if len(parts) != 2:
            logger.warning(f"⚠️ Unknown indicator format: {indicator}")
            return None

        ind_type, period_str = parts
        try:
            period = int(period_str)
        except ValueError:
            logger.warning(f"⚠️ Invalid indicator period: {indicator}")
            return None

        # 지표 계산
        if ind_type == "sma":
            return close.rolling(window=period).mean()
        elif ind_type == "ema":
            return close.ewm(span=period, adjust=False).mean()
        elif ind_type == "rsi":
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss.replace(0, float("nan"))
            return 100 - (100 / (1 + rs))
        else:
            logger.warning(f"⚠️ Unsupported indicator type: {ind_type}")
            return None

    # ═══════════════════════════════════════════════════════════════════════
    # Scores (메모리 캐시 + 설정 기반 Flush)
    # ═══════════════════════════════════════════════════════════════════════

    def update_score(
        self,
        ticker: str,
        version: str,
        score_data: dict[str, Any],
    ) -> None:
        """
        스코어 업데이트 (갱신 주기에 따라 호출)

        메모리 캐시에 저장하고, FlushPolicy에 따라 Parquet 저장

        Args:
            ticker: 종목 심볼
            version: 스코어 버전 (예: "v3")
            score_data: 스코어 데이터 딕셔너리
        """
        # 메모리 캐시에 저장
        self._score_cache[ticker] = {
            "ticker": ticker,
            **score_data,
        }
        self._update_count += 1

        # FlushPolicy에 따라 저장 여부 결정
        if self._flush_policy.should_flush(self._last_flush, self._update_count):
            self._flush_scores(version)

    def get_score(self, ticker: str) -> dict[str, Any]:
        """
        스코어 조회 (메모리 캐시 우선)

        Args:
            ticker: 종목 심볼

        Returns:
            dict: 스코어 데이터 (없으면 빈 딕셔너리)
        """
        return self._score_cache.get(ticker, {})

    def get_all_scores(self) -> dict[str, dict[str, Any]]:
        """
        전체 스코어 캐시 반환

        Returns:
            dict: {ticker: score_data} 형태
        """
        return self._score_cache.copy()

    def _flush_scores(self, version: str = "v3") -> None:
        """
        스코어 Parquet 저장 (내부 호출)

        Args:
            version: 스코어 버전
        """
        if not self._score_cache:
            return

        try:
            import pyarrow as pa
            import pyarrow.parquet as pq

            df = pd.DataFrame(list(self._score_cache.values()))
            path = self._scores_dir / f"current_{version}.parquet"
            pq.write_table(pa.Table.from_pandas(df), path, compression="snappy")

            # 상태 리셋
            self._last_flush = time.time()
            self._update_count = 0

            logger.debug(f"💾 Scores flushed: {len(df)} tickers → {path}")
        except Exception as e:
            logger.error(f"❌ Failed to flush scores: {e}")

    def force_flush(self, version: str = "v3") -> None:
        """
        강제 Flush (장 마감, 서버 종료 시 호출)

        Args:
            version: 스코어 버전
        """
        logger.info("⚡ Force flushing scores...")
        self._flush_scores(version)

    # ═══════════════════════════════════════════════════════════════════════
    # Utilities
    # ═══════════════════════════════════════════════════════════════════════

    def get_stats(self) -> dict[str, Any]:
        """
        DataRepository 통계 반환

        Returns:
            dict: 통계 정보
        """
        pm_stats = self._pm.get_stats()
        return {
            **pm_stats,
            "score_cache_size": len(self._score_cache),
            "flush_policy": type(self._flush_policy).__name__,
            "update_count": self._update_count,
        }
