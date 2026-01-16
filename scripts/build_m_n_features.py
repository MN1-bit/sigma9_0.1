"""
R-4 Phase B: M-n 피처 추출

분봉 데이터로 T0(급등 시작점) 탐지 및 윈도우 기반 Anomaly 피처 계산.
2가지 T0 탐지 방식 병렬 실험: Threshold (+6%) vs Acceleration.

Usage:
    python scripts/build_m_n_features.py
"""

import logging
from datetime import date
from pathlib import Path

import pandas as pd

# ==================================================
# 설정
# ==================================================
INTRADAY_DIR = Path("data/parquet/1m")
COVERAGE_CSV = Path("scripts/minute_coverage_report.csv")
CONTROL_CSV = Path("scripts/control_groups.csv")
D1_FEATURES = Path("scripts/d1_features.parquet")
OUTPUT_PARQUET = Path("scripts/m_n_features.parquet")

# T0 탐지 파라미터
T0_THRESHOLD_PCT = 6.0  # 방식 A: 전일 종가 대비 +6% 돌파
T0_ACCEL_THRESHOLD = 0.002  # 방식 B: 가속도 임계값

# 분석 윈도우 (분 단위)
WINDOWS = [15, 30, 60, 120]

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ==================================================
# T0 탐지
# ==================================================


def detect_t0_threshold(df: pd.DataFrame, prev_close: float) -> pd.Timestamp | None:
    """
    방식 A: 전일 종가 대비 +6% 최초 돌파 시점.
    
    ELI5: 
    - 어제 100원에 마감했으면, 오늘 106원 넘는 첫 순간이 T0
    - 급등주는 이 시점부터 가속하는 경우 많음
    """
    threshold_price = prev_close * (1 + T0_THRESHOLD_PCT / 100)
    above_threshold = df[df["close"] >= threshold_price]
    
    if len(above_threshold) > 0:
        return above_threshold["_ts"].iloc[0]
    return None


def detect_t0_acceleration(df: pd.DataFrame) -> pd.Timestamp | None:
    """
    방식 B: 가격 가속도 기반 T0.
    
    ELI5:
    - 10분간 평균 상승률 계산
    - 상승률이 갑자기 빨라지는 첫 순간이 T0
    - 느린 상승/급등 모두 포착 가능
    """
    if len(df) < 15:
        return None
    
    # 10분 이동 수익률
    df = df.copy()
    df["return_10m"] = df["close"].pct_change(10) / 10
    df["acceleration"] = df["return_10m"].diff()
    
    # 첫 가속 시점
    accel_points = df[df["acceleration"] > T0_ACCEL_THRESHOLD]
    
    if len(accel_points) > 0:
        return accel_points["_ts"].iloc[0]
    return None


def detect_t0_fallback(df: pd.DataFrame) -> pd.Timestamp:
    """
    T0 Fallback: 장중 최고가 도달 시점.
    
    ELI5: T0를 못 찾으면, 그날 가장 높았을 때를 T0로 사용
    """
    max_idx = df["high"].idxmax()
    return df.loc[max_idx, "_ts"]


# ==================================================
# M-n 피처 계산
# ==================================================


def calculate_window_features(
    df: pd.DataFrame, 
    t0: pd.Timestamp, 
    window_minutes: int
) -> dict:
    """
    T0 직전 윈도우의 Anomaly 피처 계산.
    
    ELI5:
    - T0 15분 전 ~ T0 1분 전 데이터 추출
    - 거래량 폭발, 가격 모멘텀 등 이상 징후 측정
    """
    # 윈도우 범위
    window_start = t0 - pd.Timedelta(minutes=window_minutes)
    window_end = t0 - pd.Timedelta(minutes=1)
    
    window_data = df[(df["_ts"] >= window_start) & (df["_ts"] <= window_end)]
    
    if len(window_data) < 3:
        return {
            f"vol_zscore_max_{window_minutes}m": None,
            f"vol_accel_{window_minutes}m": None,
            f"rvol_spike_count_{window_minutes}m": None,
            f"price_momentum_{window_minutes}m": None,
            f"window_rows_{window_minutes}m": 0,
        }
    
    # 1. 거래량 z-score 최대값
    # ELI5: 윈도우 내에서 "평소보다 얼마나 많이 거래됐는지" 최대값
    vol_mean = window_data["volume"].mean()
    vol_std = window_data["volume"].std()
    if vol_std > 0:
        vol_zscore = (window_data["volume"] - vol_mean) / vol_std
        vol_zscore_max = vol_zscore.max()
    else:
        vol_zscore_max = 0
    
    # 2. 거래량 가속 (후반 vs 초반)
    # ELI5: 윈도우 끝에 거래량이 몰리면 양수
    half_point = len(window_data) // 2
    if half_point > 0:
        vol_first_half = window_data["volume"].iloc[:half_point].mean()
        vol_second_half = window_data["volume"].iloc[half_point:].mean()
        vol_accel = (vol_second_half / vol_first_half - 1) if vol_first_half > 0 else 0
    else:
        vol_accel = 0
    
    # 3. RVOL 스파이크 카운트 (1.5배 이상)
    # ELI5: 거래량이 평균의 1.5배 넘는 봉이 몇 개인지
    rvol_threshold = vol_mean * 1.5
    rvol_spike_count = int((window_data["volume"] >= rvol_threshold).sum())
    
    # 4. 가격 모멘텀 (윈도우 내 변화율 %)
    # ELI5: 윈도우 시작 ~ 끝 사이 가격이 얼마나 올랐는지
    first_close = window_data["close"].iloc[0]
    last_close = window_data["close"].iloc[-1]
    price_momentum = ((last_close / first_close) - 1) * 100 if first_close > 0 else 0
    
    return {
        f"vol_zscore_max_{window_minutes}m": round(vol_zscore_max, 3),
        f"vol_accel_{window_minutes}m": round(vol_accel, 3),
        f"rvol_spike_count_{window_minutes}m": rvol_spike_count,
        f"price_momentum_{window_minutes}m": round(price_momentum, 3),
        f"window_rows_{window_minutes}m": len(window_data),
    }


def calculate_premarket_features(
    df: pd.DataFrame, 
    target_date: date,
    prev_close: float | None = None
) -> dict:
    """
    프리마켓(4:00-9:30 AM) 피처 계산.
    
    002-02 토론 결과 반영: 5개 피처 확장
    - premarket_rvol: 프리마켓 거래량 / 전일 평균 (추정치 사용)
    - premarket_range: (고점 - 저점) / 시가
    - premarket_close_location: 종가가 프리마켓 범위의 어디에? (0~1)
    - gap_pct: 전일 종가 대비 프리마켓 시가 갭
    - premarket_volume_profile: 후반 vs 초반 거래량 비율
    
    ELI5: 장 시작 전 거래 활동이 활발하면 급등 확률 높음
    """
    # 프리마켓 시간 필터 (4:00 AM ~ 9:29 AM)
    premarket = df[(df["_ts"].dt.hour >= 4) & 
                   ((df["_ts"].dt.hour < 9) | 
                    ((df["_ts"].dt.hour == 9) & (df["_ts"].dt.minute < 30)))]
    
    if len(premarket) == 0:
        return {
            "premarket_rvol": None,
            "premarket_range": None,
            "premarket_close_location": None,
            "gap_pct": None,
            "premarket_volume_profile": None,
            "has_premarket": False,
        }
    
    premarket_volume = premarket["volume"].sum()
    premarket_high = premarket["high"].max()
    premarket_low = premarket["low"].min()
    premarket_open = premarket["open"].iloc[0]
    premarket_close = premarket["close"].iloc[-1]
    
    # 1. premarket_rvol: 프리마켓 거래량 vs 추정 평균
    # ELI5: 평소 프리마켓보다 몇 배 거래됐는지
    # 정확한 계산은 어려우므로 절대값 사용 (추후 정규화)
    premarket_rvol = float(premarket_volume)  # 원시값, 추후 정규화
    
    # 2. premarket_range: (고점 - 저점) / 시가
    # ELI5: 프리마켓 변동폭이 클수록 관심 많음
    premarket_range = (
        ((premarket_high - premarket_low) / premarket_open) * 100
        if premarket_open > 0 else None
    )
    
    # 3. premarket_close_location: 종가가 범위의 어디에?
    # ELI5: 0 = 저점, 1 = 고점, 0.5 = 중간
    pm_range = premarket_high - premarket_low
    premarket_close_location = (
        (premarket_close - premarket_low) / pm_range 
        if pm_range > 0 else 0.5
    )
    
    # 4. gap_pct: 전일 종가 대비 프리마켓 시가 갭
    # ELI5: 어젯밤 뉴스로 갭업 했는지
    gap_pct = (
        ((premarket_open / prev_close) - 1) * 100
        if prev_close and prev_close > 0 else None
    )
    
    # 5. premarket_volume_profile: 후반 vs 초반 거래량
    # ELI5: 장 시작 직전에 거래량 몰리면 양수
    half_idx = len(premarket) // 2
    if half_idx > 0:
        vol_first = premarket["volume"].iloc[:half_idx].sum()
        vol_second = premarket["volume"].iloc[half_idx:].sum()
        premarket_volume_profile = (
            (vol_second / vol_first - 1) if vol_first > 0 else 0
        )
    else:
        premarket_volume_profile = 0
    
    return {
        "premarket_rvol": round(premarket_rvol, 2),
        "premarket_range": round(premarket_range, 3) if premarket_range else None,
        "premarket_close_location": round(premarket_close_location, 3),
        "gap_pct": round(gap_pct, 3) if gap_pct else None,
        "premarket_volume_profile": round(premarket_volume_profile, 3),
        "has_premarket": True,
    }


# ==================================================
# 메인 로직
# ==================================================


def load_targets_with_minute_data() -> pd.DataFrame:
    """분봉 데이터가 있는 (ticker, date) 조합만 로드."""
    coverage = pd.read_csv(COVERAGE_CSV)
    with_data = coverage[coverage["has_data"]].copy()
    with_data["target_date"] = pd.to_datetime(with_data["target_date"]).dt.date
    
    # control_groups.csv와 조인하여 라벨 정보 가져오기
    control = pd.read_csv(CONTROL_CSV)
    
    # Daygainer 매핑
    dg_map = control[["daygainer_date", "daygainer_ticker", "price_tier"]].drop_duplicates()
    dg_map["label"] = "daygainer"
    dg_map = dg_map.rename(columns={"daygainer_date": "date", "daygainer_ticker": "ticker"})
    dg_map["date"] = pd.to_datetime(dg_map["date"]).dt.date
    
    # Control 매핑
    ctrl_map = control[["daygainer_date", "control_ticker", "control_type", "price_tier"]].copy()
    ctrl_map["label"] = "control_" + ctrl_map["control_type"]
    ctrl_map = ctrl_map.rename(columns={"daygainer_date": "date", "control_ticker": "ticker"})
    ctrl_map["date"] = pd.to_datetime(ctrl_map["date"]).dt.date
    ctrl_map = ctrl_map.drop(columns=["control_type"])
    
    label_map = pd.concat([dg_map, ctrl_map]).drop_duplicates(subset=["ticker", "date"])
    
    # 조인
    with_data = with_data.merge(
        label_map, 
        left_on=["ticker", "target_date"], 
        right_on=["ticker", "date"],
        how="left"
    )
    
    logger.info(f"분봉 데이터 있는 타겟: {len(with_data)}건")
    return with_data


def get_prev_close(ticker: str, target_date: date, d1_df: pd.DataFrame) -> float | None:
    """D-1 피처에서 전일 종가 가져오기."""
    row = d1_df[(d1_df["ticker"] == ticker) & (d1_df["target_date"] == target_date)]
    if len(row) > 0:
        return row["close_d1"].iloc[0]
    return None


def process_single_ticker(
    ticker: str, 
    target_date: date, 
    label: str,
    price_tier: str,
    d1_df: pd.DataFrame
) -> dict | None:
    """단일 (ticker, date) M-n 피처 계산."""
    parquet_path = INTRADAY_DIR / f"{ticker}.parquet"
    
    if not parquet_path.exists():
        return None
    
    try:
        df = pd.read_parquet(parquet_path)
        
        # 타임스탬프 변환
        if str(df["timestamp"].dtype) in ["int64", "float64"]:
            df["_ts"] = pd.to_datetime(df["timestamp"], unit="ms")
        else:
            df["_ts"] = pd.to_datetime(df["timestamp"])
        
        df["_date"] = df["_ts"].dt.date
        
        # 해당 날짜 필터
        day_data = df[df["_date"] == target_date].copy()
        
        if len(day_data) < 10:
            return None
        
        day_data = day_data.sort_values("_ts").reset_index(drop=True)
        
        # 전일 종가
        prev_close = get_prev_close(ticker, target_date, d1_df)
        
        # T0 탐지 (방식 A, B 병렬)
        t0_threshold = detect_t0_threshold(day_data, prev_close) if prev_close else None
        t0_accel = detect_t0_acceleration(day_data)
        t0_fallback = detect_t0_fallback(day_data)
        
        # 결과 구성
        result = {
            "ticker": ticker,
            "target_date": target_date,
            "label": label,
            "price_tier": price_tier,
            "prev_close": prev_close,
            "day_rows": len(day_data),
            "t0_threshold": str(t0_threshold) if t0_threshold else None,
            "t0_accel": str(t0_accel) if t0_accel else None,
            "t0_fallback": str(t0_fallback),
        }
        
        # 프리마켓 피처 (5개, 002-02 확장)
        premarket_features = calculate_premarket_features(day_data, target_date, prev_close)
        result.update(premarket_features)
        
        # 윈도우별 피처 (T0 방식 A 기준)
        t0_for_features = t0_threshold or t0_fallback
        for window in WINDOWS:
            window_features = calculate_window_features(day_data, t0_for_features, window)
            result.update(window_features)
        
        return result
        
    except Exception as e:
        logger.error(f"{ticker} {target_date} 처리 오류: {e}")
        return None


def build_m_n_features() -> pd.DataFrame:
    """M-n 피처 추출 메인."""
    targets = load_targets_with_minute_data()
    
    # D-1 피처 로드
    d1_df = pd.read_parquet(D1_FEATURES)
    d1_df["target_date"] = pd.to_datetime(d1_df["target_date"]).dt.date
    
    results = []
    total = len(targets)
    
    logger.info(f"M-n 피처 계산 시작: {total}건")
    
    for idx, row in targets.iterrows():
        ticker = row["ticker"]
        target_date = row["target_date"]
        label = row.get("label", "unknown")
        price_tier = row.get("price_tier", "unknown")
        
        result = process_single_ticker(ticker, target_date, label, price_tier, d1_df)
        
        if result:
            results.append(result)
        
        if (idx + 1) % 10 == 0:
            logger.info(f"진행: {idx + 1}/{total}")
    
    df = pd.DataFrame(results)
    
    # 통계 출력
    logger.info("=" * 60)
    logger.info("M-n 피처 추출 결과")
    logger.info("=" * 60)
    logger.info(f"처리 대상: {total}건")
    logger.info(f"성공: {len(df)}건")
    logger.info(f"T0 Threshold 탐지 성공: {df['t0_threshold'].notna().sum()}건")
    logger.info(f"T0 Accel 탐지 성공: {df['t0_accel'].notna().sum()}건")
    logger.info(f"프리마켓 데이터 있음: {df['has_premarket'].sum()}건")
    
    return df


def main() -> None:
    """메인 실행."""
    logger.info("=" * 60)
    logger.info("R-4 Phase B: M-n 피처 추출")
    logger.info("=" * 60)
    
    df = build_m_n_features()
    
    if len(df) == 0:
        logger.warning("추출된 피처 없음!")
        return
    
    # 저장
    df.to_parquet(OUTPUT_PARQUET, index=False)
    logger.info(f"저장 완료: {OUTPUT_PARQUET}")
    
    # 샘플 출력
    print("\n샘플 출력:")
    print(df[["ticker", "target_date", "label", "t0_threshold", "vol_zscore_max_15m", "price_momentum_15m"]].head(10).to_string(index=False))
    
    logger.info("=" * 60)
    logger.info("완료")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
