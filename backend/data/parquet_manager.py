# ============================================================================
# Parquet Manager - Parquet 파일 Read/Write 관리
# ============================================================================
# 📌 이 파일의 역할:
#   - Parquet 포맷으로 시장 데이터 저장 및 조회
#   - 티커별 분봉 파일 (AAPL_1m.parquet, AAPL_1h.parquet)
#   - 전체 일봉 통합 파일 (daily_all.parquet)
#   - SQLite 대비 컬럼형 저장소로 분석 쿼리 최적화
#
# 📖 사용 예시:
#   >>> pm = ParquetManager("data/parquet")
#   >>> df = pd.DataFrame([{"ticker": "AAPL", "date": "2024-01-01", ...}])
#   >>> pm.append_daily(df)
#   >>> result = pm.read_daily("AAPL", days=30)
# ============================================================================

from pathlib import Path
from typing import Callable, Optional
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from loguru import logger
from datetime import datetime, timedelta


# ═══════════════════════════════════════════════════════════════════════════
# 리샘플링 규칙 상수
# ═══════════════════════════════════════════════════════════════════════════
# ELI5: 파생 타임프레임을 어떤 소스에서 생성할지 정의합니다.
#       예: 5분봉 = 1분봉 5개의 OHLCV를 집계
RESAMPLE_RULES: dict[str, tuple[str, str]] = {
    "3m": ("1m", "3min"),   # 1분봉 3개 → 3분봉
    "5m": ("1m", "5min"),   # 1분봉 5개 → 5분봉
    "15m": ("1m", "15min"), # 1분봉 15개 → 15분봉
    "4h": ("1h", "4h"),     # 1시간봉 4개 → 4시간봉
    "1W": ("1D", "W-FRI"),  # 일봉 5개 → 주봉 (금요일 기준)
}


# ═══════════════════════════════════════════════════════════════════════════
# ParquetManager 클래스
# ═══════════════════════════════════════════════════════════════════════════


class ParquetManager:
    """
    Parquet 파일 Read/Write 관리자

    SQLite의 DailyBar/IntradayBar 데이터를 Parquet 포맷으로 저장합니다.
    컬럼형 저장소 특성상 대용량 데이터 분석에 최적화되어 있습니다.

    Attributes:
        base_dir: Parquet 파일 저장 베이스 디렉터리
        intraday_dir: 분봉 파일 저장 디렉터리 (티커별 분리)
        daily_path: 일봉 통합 파일 경로

    Example:
        >>> pm = ParquetManager("data/parquet")
        >>> df = pd.DataFrame([{"ticker": "AAPL", "date": "2024-01-01", ...}])
        >>> pm.append_daily(df)
        >>> result = pm.read_daily("AAPL", days=30)
    """

    def __init__(self, base_dir: str = "data/parquet"):
        """
        ParquetManager 초기화

        Args:
            base_dir: Parquet 파일 저장 루트 디렉터리
        """
        # 경로 설정 (ELI5: 파일을 저장할 폴더 위치를 정합니다)
        self.base_dir = Path(base_dir)
        self.intraday_dir = self.base_dir / "intraday"
        self.daily_path = self.base_dir / "daily" / "all_daily.parquet"

        # 디렉터리 자동 생성 (ELI5: 폴더가 없으면 만들어줍니다)
        self.intraday_dir.mkdir(parents=True, exist_ok=True)
        self.daily_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"📦 ParquetManager initialized: {self.base_dir}")

    # ═══════════════════════════════════════════════════════════════════════
    # Daily (일봉) - 전체 티커 통합 파일
    # ═══════════════════════════════════════════════════════════════════════

    def write_daily(self, df: pd.DataFrame) -> int:
        """
        일봉 데이터 전체 덮어쓰기 (초기 마이그레이션용)

        [12-002] 티커 정렬 + Row Group 크기 설정으로 Predicate Pushdown 최적화

        Args:
            df: 저장할 DataFrame (ticker, date, open, high, low, close, volume 필수)

        Returns:
            int: 저장된 레코드 수
        """
        if df.empty:
            return 0

        # [12-002] 데이터 정렬 (티커, 날짜 순) - Row Group 내 티커 연속 배치
        # ELI5: 같은 티커끼리 모아두면 특정 티커만 빠르게 찾을 수 있습니다
        df = df.sort_values(["ticker", "date"]).reset_index(drop=True)

        # [12-002] Row Group 크기 설정 (50만 행) - Predicate Pushdown 효율화
        # ELI5: 파일을 작은 블록으로 나눠서 필요한 블록만 읽습니다
        pq.write_table(
            pa.Table.from_pandas(df),
            self.daily_path,
            compression="snappy",
            row_group_size=500_000,  # 50만 행 = ~25-30 Row Groups
        )

        logger.info(f"📝 Daily written: {len(df)} rows → {self.daily_path}")
        return len(df)

    def append_daily(self, df: pd.DataFrame) -> int:
        """
        일봉 데이터 추가 (증분 업데이트용)

        기존 데이터와 병합하며, 중복 제거 (ticker + date 기준)

        Args:
            df: 추가할 DataFrame

        Returns:
            int: 최종 저장된 레코드 수
        """
        if df.empty:
            return 0

        # 기존 데이터 읽기 (ELI5: 이미 저장된 데이터를 불러옵니다)
        if self.daily_path.exists():
            existing = pq.read_table(self.daily_path).to_pandas()
            # 병합 후 중복 제거 (ELI5: 같은 날짜의 데이터는 최신 것만 남깁니다)
            combined = pd.concat([existing, df], ignore_index=True)
            combined = combined.drop_duplicates(subset=["ticker", "date"], keep="last")
        else:
            combined = df

        return self.write_daily(combined)

    def read_daily(
        self,
        ticker: Optional[str] = None,
        days: Optional[int] = None,
        start_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        일봉 데이터 조회

        [12-002] Predicate Pushdown 적용 - 티커 지정 시 Row Group 레벨 필터링

        Args:
            ticker: 종목 심볼 (None이면 전체)
            days: 조회할 일수 (None 또는 0이면 전체 조회)
            start_date: 시작 날짜 (YYYY-MM-DD)

        Returns:
            pd.DataFrame: 조회된 데이터 (빈 경우 빈 DataFrame)
        """
        if not self.daily_path.exists():
            return pd.DataFrame()

        # [12-002] Predicate Pushdown - Row Group 레벨에서 필터링
        # ELI5: 티커가 지정되면 해당 티커가 있는 블록만 읽어서 빠릅니다
        if ticker:
            # PyArrow filters: Row Group 통계로 필요한 블록만 로드
            filters = [("ticker", "=", ticker)]
            df = pq.read_table(self.daily_path, filters=filters).to_pandas()
        else:
            # 전체 조회
            df = pq.read_table(self.daily_path).to_pandas()

        if df.empty:
            return df

        # 날짜 필터 (ELI5: 최근 N일 데이터만 골라냅니다)
        if start_date:
            df = df[df["date"] >= start_date]
        elif days and days > 0:
            # 데이터 내 상위 N개 날짜만 추출
            if not df.empty:
                unique_dates = sorted(df["date"].unique(), reverse=True)[:days]
                df = df[df["date"].isin(unique_dates)]

        return df.sort_values(["ticker", "date"]).reset_index(drop=True)

    def read_daily_bulk(
        self,
        tickers: list[str] | None = None,
        days: int = 20,
    ) -> dict[str, list[dict]]:
        """
        [12-002] 여러 티커의 일봉 데이터를 한 번에 조회

        ELI5: 파일을 1회만 읽고 티커별로 데이터를 나눕니다.
              티커 10,000개를 조회하더라도 파일 읽기는 1번만 수행됩니다.

        기존 read_daily()와의 차이:
        - read_daily(ticker): 티커마다 파일 읽기 → O(N) I/O
        - read_daily_bulk(tickers): 파일 1회 읽기 → O(1) I/O

        Args:
            tickers: 조회할 티커 목록 (None이면 전체 티커)
            days: 조회할 일수 (기본값: 20)

        Returns:
            dict[str, list[dict]]: 티커 → 일봉 데이터 (오래된 순 정렬)
                예: {"AAPL": [{"date": "2024-01-01", ...}, ...], ...}
        """
        if not self.daily_path.exists():
            return {}

        # Step 1: 파일 전체 읽기 (ELI5: 책 한 권 전체를 한 번에 읽습니다)
        df = pq.read_table(self.daily_path).to_pandas()

        if df.empty:
            return {}

        # Step 2: 날짜 필터링 (ELI5: 최근 N일치만 골라냅니다)
        # 전체 데이터에서 unique 날짜 추출 → 최신 N개 선택
        unique_dates = sorted(df["date"].unique(), reverse=True)[:days]
        df = df[df["date"].isin(unique_dates)]

        # Step 3: 티커 필터링 (ELI5: 요청한 티커만 골라냅니다)
        if tickers:
            df = df[df["ticker"].isin(tickers)]

        # Step 4: 티커별 그룹화 (ELI5: 티커마다 데이터를 묶어서 딕셔너리로 반환)
        # 각 티커의 데이터를 날짜순 정렬 후 dict 리스트로 변환
        result = {}
        for ticker, group in df.groupby("ticker"):
            sorted_data = group.sort_values("date").to_dict("records")
            result[ticker] = sorted_data

        return result

    # ═══════════════════════════════════════════════════════════════════════
    # Intraday (분봉/시봉) - 티커별 분리 파일
    # ═══════════════════════════════════════════════════════════════════════

    def _get_intraday_path(self, ticker: str, timeframe: str) -> Path:
        """
        Intraday 파일 경로 생성

        Args:
            ticker: 종목 심볼 (예: "AAPL")
            timeframe: 타임프레임 ("1m", "5m", "15m", "1h")

        Returns:
            Path: 파일 경로 (예: data/parquet/intraday/AAPL_1m.parquet)
        """
        return self.intraday_dir / f"{ticker}_{timeframe}.parquet"

    def write_intraday(self, ticker: str, timeframe: str, df: pd.DataFrame) -> int:
        """
        Intraday 데이터 전체 덮어쓰기

        Args:
            ticker: 종목 심볼
            timeframe: 타임프레임 ("1m", "5m", "15m", "1h")
            df: 저장할 DataFrame

        Returns:
            int: 저장된 레코드 수
        """
        if df.empty:
            return 0

        path = self._get_intraday_path(ticker, timeframe)

        # 시간순 정렬 (ELI5: 오래된 데이터부터 최신 순으로 정렬)
        df = df.sort_values("timestamp").reset_index(drop=True)

        pq.write_table(
            pa.Table.from_pandas(df),
            path,
            compression="snappy",
        )

        logger.debug(f"📝 Intraday written: {ticker}_{timeframe} → {len(df)} rows")
        return len(df)

    def append_intraday(self, ticker: str, timeframe: str, df: pd.DataFrame) -> int:
        """
        Intraday 데이터 추가 (증분 업데이트)

        Args:
            ticker: 종목 심볼
            timeframe: 타임프레임
            df: 추가할 DataFrame

        Returns:
            int: 최종 저장된 레코드 수
        """
        if df.empty:
            return 0

        path = self._get_intraday_path(ticker, timeframe)

        if path.exists():
            existing = pq.read_table(path).to_pandas()
            combined = pd.concat([existing, df], ignore_index=True)
            # timestamp 기준 중복 제거
            combined = combined.drop_duplicates(subset=["timestamp"], keep="last")
        else:
            combined = df

        return self.write_intraday(ticker, timeframe, combined)

    def read_intraday(
        self,
        ticker: str,
        timeframe: str,
        days: int = 2,
        start_timestamp: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Intraday 데이터 조회

        Args:
            ticker: 종목 심볼
            timeframe: 타임프레임 ("1m", "5m", "15m", "1h")
            days: 조회할 일수 (기본 2일)
            start_timestamp: 시작 Unix timestamp (밀리초)

        Returns:
            pd.DataFrame: 조회된 데이터
        """
        path = self._get_intraday_path(ticker, timeframe)

        if not path.exists():
            return pd.DataFrame()

        df = pq.read_table(path).to_pandas()

        if df.empty:
            return df

        # 시간 필터 (ELI5: 최근 N일의 데이터만 가져옵니다)
        if start_timestamp:
            df = df[df["timestamp"] >= start_timestamp]
        else:
            cutoff_ts = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            df = df[df["timestamp"] >= cutoff_ts]

        return df.sort_values("timestamp").reset_index(drop=True)

    # ═══════════════════════════════════════════════════════════════════════
    # On-demand 리샘플링 (09-002)
    # ═══════════════════════════════════════════════════════════════════════

    def get_intraday_bars(
        self,
        ticker: str,
        tf: str,
        auto_fill: bool = True,
        days: int = 14,
    ) -> pd.DataFrame:
        """
        Intraday 데이터 조회 (On-demand 리샘플링 지원)

        ELI5: 요청한 타임프레임 파일이 없으면 소스에서 자동으로 리샘플링합니다.
              예) 5m 파일이 없으면 → 1m 파일에서 5분봉 생성 → 저장 → 반환

        Args:
            ticker: 종목 심볼 (예: "AAPL")
            tf: 타임프레임 ("1m", "3m", "5m", "15m", "1h", "4h", "1W")
            auto_fill: True면 파일 없을 때 자동 리샘플링 시도
            days: 조회할 일수 (기본 14일)

        Returns:
            pd.DataFrame: OHLCV 데이터 (빈 경우 빈 DataFrame)
        """
        path = self._get_intraday_path(ticker, tf)

        if not path.exists():
            if auto_fill and tf in RESAMPLE_RULES:
                logger.warning(f"[GAP-FILL] {ticker}/{tf} 파일 없음, 리샘플링 시도")
                return self._try_resample(ticker, tf)
            return pd.DataFrame()

        return self.read_intraday(ticker, tf, days=days)

    def _try_resample(self, ticker: str, tf: str) -> pd.DataFrame:
        """
        소스 타임프레임에서 타겟 타임프레임으로 리샘플링 시도

        ELI5: 1분봉이 있으면 5분봉을 만들어줍니다 (1분봉 5개를 합쳐서).

        Args:
            ticker: 종목 심볼
            tf: 타겟 타임프레임 (예: "5m")

        Returns:
            pd.DataFrame: 리샘플링된 데이터 (실패 시 빈 DataFrame)
        """
        rule = RESAMPLE_RULES.get(tf)
        if not rule:
            logger.error(f"[GAP-FILL] {tf}에 대한 리샘플 규칙 없음")
            return pd.DataFrame()

        source_tf, pandas_rule = rule

        # 소스 데이터 로드 (auto_fill=False로 재귀 방지)
        source_df = self.read_intraday(ticker, source_tf, days=30)
        if source_df.empty:
            logger.error(f"[GAP-FILL] {ticker}/{source_tf} 소스 데이터 없음")
            return pd.DataFrame()

        logger.info(f"[RESAMPLE] {ticker} {source_tf}→{tf} 시작 ({len(source_df)} bars)")

        # 리샘플링 수행
        resampled = self._resample_df(source_df, pandas_rule)
        if resampled.empty:
            logger.error(f"[RESAMPLE] {ticker}/{tf} 리샘플링 결과 비어있음")
            return pd.DataFrame()

        # 저장
        self.write_intraday(ticker, tf, resampled)
        logger.info(f"[RESAMPLE] {ticker} {tf} 저장 ({len(resampled)} bars)")

        return resampled

    def _resample_df(self, df: pd.DataFrame, rule: str) -> pd.DataFrame:
        """
        DataFrame을 pandas resample로 OHLCV 집계

        ELI5: 1분봉 5개를 하나의 5분봉으로 만듭니다.
              - Open: 첫 번째 봉의 시가
              - High: 가장 높은 고가
              - Low: 가장 낮은 저가
              - Close: 마지막 봉의 종가
              - Volume: 전체 거래량 합계

        Args:
            df: 소스 DataFrame (timestamp, open, high, low, close, volume 필수)
            rule: pandas resample 규칙 (예: "5min", "4h", "W-FRI")

        Returns:
            pd.DataFrame: 리샘플링된 OHLCV 데이터
        """
        if df.empty:
            return pd.DataFrame()

        # timestamp 컬럼을 DatetimeIndex로 변환
        # ELI5: timestamp를 날짜/시간 형태로 바꿔서 시간 기준으로 그룹화 가능하게
        df = df.copy()
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("datetime")

        # OHLCV 리샘플링 (ELI5: 시간 범위별로 데이터 집계)
        resampled = df.resample(rule, closed="left", label="left").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }).dropna(subset=["open"])  # NaN 행 제거

        # timestamp 컬럼 복원
        resampled = resampled.reset_index()
        resampled["timestamp"] = resampled["datetime"].astype("int64") // 10**6
        resampled = resampled.drop(columns=["datetime"])

        return resampled[["timestamp", "open", "high", "low", "close", "volume"]]

    def resample_all_tickers(
        self,
        target_tf: str,
        callback: Callable[[str, int, int], None] | None = None,
        max_history: timedelta = timedelta(weeks=2),
    ) -> int:
        """
        모든 티커에 대해 target_tf 리샘플링 수행

        ELI5: 저장된 모든 1분봉 파일들을 5분봉으로 변환합니다.
              진행 상황을 callback으로 알려줍니다.

        Args:
            target_tf: 타겟 타임프레임 (예: "5m", "15m")
            callback: 진행상황 콜백 (ticker, current, total) - GUI 연동용
            max_history: 최대 이력 기간 (기본 2주)

        Returns:
            int: 성공적으로 리샘플링된 티커 수
        """
        rule = RESAMPLE_RULES.get(target_tf)
        if not rule:
            logger.error(f"[RESAMPLE-ALL] {target_tf}에 대한 규칙 없음")
            return 0

        source_tf = rule[0]
        tickers = self.get_intraday_tickers(source_tf)
        total = len(tickers)

        if total == 0:
            logger.warning(f"[RESAMPLE-ALL] {source_tf} 티커 없음")
            return 0

        logger.info(f"[RESAMPLE-ALL] {target_tf} 일괄 리샘플 시작 ({total} tickers)")

        success_count = 0
        for i, ticker in enumerate(tickers, 1):
            try:
                # 콜백 호출 (GUI 진행 상태 업데이트용)
                if callback:
                    callback(ticker, i, total)

                # 리샘플링 시도
                result = self.get_intraday_bars(ticker, target_tf, auto_fill=True)
                if not result.empty:
                    success_count += 1

            except Exception as e:
                logger.error(f"[RESAMPLE-ALL] {ticker} 실패: {e}")

        logger.info(f"[RESAMPLE-ALL] 완료: {success_count}/{total} 성공")
        return success_count

    # ═══════════════════════════════════════════════════════════════════════
    # 유틸리티
    # ═══════════════════════════════════════════════════════════════════════

    def get_available_tickers(self) -> list[str]:
        """
        저장된 일봉 데이터의 티커 목록 반환

        Returns:
            list[str]: 티커 목록
        """
        if not self.daily_path.exists():
            return []

        df = pq.read_table(self.daily_path, columns=["ticker"]).to_pandas()
        return df["ticker"].unique().tolist()

    def get_intraday_tickers(self, timeframe: str = "1m") -> list[str]:
        """
        저장된 intraday 데이터의 티커 목록 반환

        파일명에서 티커를 추출합니다 (예: AAPL_1m.parquet → AAPL)

        Args:
            timeframe: 타임프레임 (기본값: "1m")

        Returns:
            list[str]: 티커 목록
        """
        if not self.intraday_dir.exists():
            return []

        # ELI5: intraday 폴더에서 *_1m.parquet 파일들을 찾아서 티커 이름만 추출
        pattern = f"*_{timeframe}.parquet"
        files = list(self.intraday_dir.glob(pattern))

        tickers = []
        for f in files:
            # AAPL_1m.parquet → AAPL
            ticker = f.stem.replace(f"_{timeframe}", "")
            tickers.append(ticker)

        return sorted(tickers)

    def get_stats(self) -> dict:
        """
        저장소 통계 반환

        Returns:
            dict: 통계 정보
                - daily_rows: 일봉 레코드 수
                - daily_tickers: 일봉 티커 수
                - daily_file_size_mb: 일봉 파일 크기 (MB)
                - intraday_files: 분봉 파일 수
        """
        stats = {
            "daily_rows": 0,
            "daily_tickers": 0,
            "daily_file_size_mb": 0.0,
            "intraday_files": 0,
        }

        if self.daily_path.exists():
            df = pq.read_table(self.daily_path).to_pandas()
            stats["daily_rows"] = len(df)
            stats["daily_tickers"] = df["ticker"].nunique()
            stats["daily_file_size_mb"] = self.daily_path.stat().st_size / (1024 * 1024)

        stats["intraday_files"] = len(list(self.intraday_dir.glob("*.parquet")))

        return stats

    def delete_ticker_intraday(self, ticker: str) -> bool:
        """
        특정 티커의 모든 Intraday 파일 삭제

        Args:
            ticker: 종목 심볼

        Returns:
            bool: 삭제 성공 여부
        """
        deleted = False
        for timeframe in ["1m", "5m", "15m", "1h"]:
            path = self._get_intraday_path(ticker, timeframe)
            if path.exists():
                path.unlink()
                deleted = True
                logger.info(f"🗑️ Deleted: {path}")
        return deleted
