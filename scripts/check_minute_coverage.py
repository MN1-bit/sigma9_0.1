"""
R-4 Phase 0: 분봉 데이터 커버리지 확인

control_groups.csv의 모든 (ticker, date) 조합에 대해 분봉 데이터 존재 여부를 확인.
프리마켓(4:00 AM~) 데이터 포함 여부까지 점검.

Usage:
    python scripts/check_minute_coverage.py
"""

import logging
from datetime import date
from pathlib import Path
from typing import NamedTuple

import pandas as pd

# ==================================================
# 설정
# ==================================================
INTRADAY_DIR = Path("data/parquet/1m")
CONTROL_CSV = Path("scripts/control_groups.csv")
OUTPUT_REPORT = Path("scripts/minute_coverage_report.csv")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class CoverageResult(NamedTuple):
    """단일 (ticker, date) 조합의 커버리지 결과."""
    ticker: str
    target_date: date
    has_data: bool
    row_count: int
    has_premarket: bool
    earliest_time: str | None
    latest_time: str | None


# ==================================================
# 핵심 함수
# ==================================================


def load_control_groups() -> pd.DataFrame:
    """
    control_groups.csv 로드 및 고유 (ticker, date) 추출.
    
    ELI5: Daygainer와 Control 종목 모두의 (ticker, date)를 뽑아냄.
    """
    df = pd.read_csv(CONTROL_CSV)
    
    # Daygainer + Control 티커 모두 수집
    # daygainer_date, daygainer_ticker / control_ticker
    dg_pairs = df[["daygainer_date", "daygainer_ticker"]].rename(
        columns={"daygainer_date": "date", "daygainer_ticker": "ticker"}
    )
    ctrl_pairs = df[["daygainer_date", "control_ticker"]].rename(
        columns={"daygainer_date": "date", "control_ticker": "ticker"}
    )
    
    all_pairs = pd.concat([dg_pairs, ctrl_pairs], ignore_index=True).drop_duplicates()
    all_pairs["date"] = pd.to_datetime(all_pairs["date"]).dt.date
    
    logger.info(f"로드 완료: 고유 (ticker, date) 조합 {len(all_pairs)}건")
    return all_pairs


def check_intraday_coverage(ticker: str, target_date: date) -> CoverageResult:
    """
    특정 (ticker, date)의 분봉 데이터 커버리지 확인.
    
    Returns:
        CoverageResult with has_data, row_count, has_premarket status
    """
    # 티커 파일 경로 (특수문자 처리: '.'를 파일명에 포함)
    parquet_path = INTRADAY_DIR / f"{ticker}.parquet"
    
    if not parquet_path.exists():
        return CoverageResult(
            ticker=ticker,
            target_date=target_date,
            has_data=False,
            row_count=0,
            has_premarket=False,
            earliest_time=None,
            latest_time=None,
        )
    
    try:
        df = pd.read_parquet(parquet_path)
        
        # 컬럼명 확인 및 시간 파싱
        # ELI5: 분봉 데이터는 보통 'timestamp' 또는 't' 컬럼에 시간 정보가 있음
        time_col = None
        for col in ["timestamp", "t", "datetime", "time", "date"]:
            if col in df.columns:
                time_col = col
                break
        
        if time_col is None:
            logger.warning(f"{ticker}: 시간 컬럼 찾을 수 없음. 컬럼: {list(df.columns)}")
            return CoverageResult(
                ticker=ticker,
                target_date=target_date,
                has_data=False,
                row_count=0,
                has_premarket=False,
                earliest_time=None,
                latest_time=None,
            )
        
        # 시간 변환
        # ELI5: timestamp가 유닉스 밀리초(1970년 이후 경과 밀리초) 형식일 수 있음
        time_values = df[time_col]
        dtype_str = str(time_values.dtype)
        if dtype_str in ['int64', 'float64'] and time_values.iloc[0] > 1e12:
            # 유닉스 밀리초 형식 (숫자가 매우 큰 경우)
            df["_ts"] = pd.to_datetime(time_values, unit='ms')
        else:
            # 일반 datetime 형식
            df["_ts"] = pd.to_datetime(time_values)
        df["_date"] = df["_ts"].dt.date
        
        # 타겟 날짜 필터링
        day_data = df[df["_date"] == target_date]
        
        if len(day_data) == 0:
            return CoverageResult(
                ticker=ticker,
                target_date=target_date,
                has_data=False,
                row_count=0,
                has_premarket=False,
                earliest_time=None,
                latest_time=None,
            )
        
        # 시간 범위 확인
        earliest = day_data["_ts"].min()
        latest = day_data["_ts"].max()
        
        # 프리마켓 체크: 4:00 AM ~ 9:30 AM ET
        # ELI5: 정규장 시작(9:30) 전에 데이터가 있으면 프리마켓 데이터 존재
        earliest_hour = earliest.hour
        has_premarket = earliest_hour < 9 or (earliest_hour == 9 and earliest.minute < 30)
        
        return CoverageResult(
            ticker=ticker,
            target_date=target_date,
            has_data=True,
            row_count=len(day_data),
            has_premarket=has_premarket,
            earliest_time=earliest.strftime("%H:%M"),
            latest_time=latest.strftime("%H:%M"),
        )
        
    except Exception as e:
        logger.error(f"{ticker} 처리 중 오류: {e}")
        return CoverageResult(
            ticker=ticker,
            target_date=target_date,
            has_data=False,
            row_count=0,
            has_premarket=False,
            earliest_time=None,
            latest_time=None,
        )


def run_coverage_check() -> pd.DataFrame:
    """
    전체 커버리지 체크 실행.
    
    Returns:
        커버리지 리포트 DataFrame
    """
    pairs = load_control_groups()
    results: list[CoverageResult] = []
    
    total = len(pairs)
    logger.info(f"커버리지 체크 시작: {total}건")
    
    for idx, row in pairs.iterrows():
        ticker = row["ticker"]
        target_date = row["date"]
        
        result = check_intraday_coverage(ticker, target_date)
        results.append(result)
        
        if (idx + 1) % 500 == 0:
            logger.info(f"진행: {idx + 1}/{total}")
    
    # 결과 DataFrame 생성
    df = pd.DataFrame(results)
    
    # 통계 출력
    has_data_count = df["has_data"].sum()
    has_premarket_count = df["has_premarket"].sum()
    
    logger.info("=" * 60)
    logger.info("커버리지 리포트")
    logger.info("=" * 60)
    logger.info(f"전체 (ticker, date) 조합: {total}")
    logger.info(f"분봉 데이터 존재: {has_data_count} ({100 * has_data_count / total:.1f}%)")
    logger.info(f"프리마켓 데이터 포함: {has_premarket_count} ({100 * has_premarket_count / total:.1f}%)")
    logger.info(f"누락: {total - has_data_count}")
    
    return df


def main() -> None:
    """메인 실행."""
    logger.info("=" * 60)
    logger.info("R-4 Phase 0: 분봉 데이터 커버리지 확인")
    logger.info("=" * 60)
    
    df = run_coverage_check()
    
    # 리포트 저장
    df.to_csv(OUTPUT_REPORT, index=False)
    logger.info(f"리포트 저장: {OUTPUT_REPORT}")
    
    # 누락 리스트 별도 저장
    missing = df[~df["has_data"]]
    if len(missing) > 0:
        missing_path = Path("scripts/minute_coverage_missing.csv")
        missing.to_csv(missing_path, index=False)
        logger.info(f"누락 리스트 저장: {missing_path} ({len(missing)}건)")
        
        # 샘플 출력
        print("\n누락 샘플 (최대 20건):")
        print(missing.head(20).to_string(index=False))
    else:
        logger.info("누락 데이터 없음! 100% 커버리지")
    
    logger.info("=" * 60)
    logger.info("완료")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
