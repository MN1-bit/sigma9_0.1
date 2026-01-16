"""
R-3 대조군 매칭 로직 (Control Group Builder)

Daygainer(75%+ 급등주)에 대응하는 대조군 자동 매칭.
- 같은 날, 비슷한 조건에서 급등하지 않은 종목 추출
- "Failed Pump" 패턴 별도 라벨링
- ML 학습용 데이터셋 생성
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional
import logging

# ============================================================
# 설정
# ============================================================

# 데이터 경로
DAILY_PARQUET = Path("d:/Codes/Sigma9-0.1/data/parquet/daily/all_daily.parquet")
INTRADAY_DIR = Path("d:/Codes/Sigma9-0.1/data/parquet/1m")
DAYGAINERS_CSV = Path("d:/Codes/Sigma9-0.1/scripts/daygainers_75plus.csv")
OUTPUT_CSV = Path("d:/Codes/Sigma9-0.1/scripts/control_groups.csv")

# 대조군 조건 (v4 확정)
CONTROL_CHANGE_MIN = -50.0  # 등락률 하한 %
CONTROL_CHANGE_MAX = 10.0   # 등락률 상한 %
MIN_PRICE = 0.1             # 최소 가격 $
RVOL_SPIKE_THRESHOLD = 2.0  # RVOL 스파이크 임계값
FAILED_PUMP_DROP = 0.30     # Failed Pump 고점 대비 하락률
CONTROL_RATIO = 5           # Daygainer당 대조군 수

# 가격 구간 (Price Tier)
# ELI5: 같은 가격대끼리 비교해야 공정함. $0.5 주식과 $100 주식은 다른 세상.
PRICE_TIERS = {
    'penny': (0.1, 1.0),      # $0.1 ~ $1
    'low': (1.0, 5.0),        # $1 ~ $5
    'mid': (5.0, 20.0),       # $5 ~ $20
    'high': (20.0, float('inf'))  # $20+
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================
# Step 1: 일봉 기반 1차 후보군 추출
# ============================================================

def get_price_tier(price: float) -> Optional[str]:
    """
    가격을 기준으로 Tier 반환.
    
    ELI5: 주식 가격을 4개 구간으로 나눔. 페니주($0.1~$1), 저가주($1~$5), 
          중가주($5~$20), 고가주($20+). 같은 구간끼리 비교해야 의미있음.
    """
    for tier_name, (low, high) in PRICE_TIERS.items():
        if low <= price < high:
            return tier_name
    return None


def load_daily_data() -> pd.DataFrame:
    """일봉 데이터 로드 및 전처리."""
    logger.info(f"Loading daily data from {DAILY_PARQUET}")
    df = pd.read_parquet(DAILY_PARQUET)
    
    # 컬럼명 소문자로 통일
    df.columns = df.columns.str.lower()
    
    # 등락률 계산 (시가 대비 종가)
    df['change_pct'] = (df['close'] - df['open']) / df['open'] * 100
    
    # 가격 티어 할당
    df['price_tier'] = df['close'].apply(get_price_tier)
    
    # 날짜 정규화
    df['date'] = pd.to_datetime(df['date']).dt.date
    
    logger.info(f"Loaded {len(df):,} daily records")
    return df


def load_daygainers() -> pd.DataFrame:
    """Daygainer 목록 로드."""
    logger.info(f"Loading daygainers from {DAYGAINERS_CSV}")
    df = pd.read_csv(DAYGAINERS_CSV)
    df['date'] = pd.to_datetime(df['date']).dt.date
    logger.info(f"Loaded {len(df):,} daygainers")
    return df


def find_control_candidates(
    daily_df: pd.DataFrame,
    daygainer_date,
    daygainer_ticker: str,
    daygainer_price_tier: str
) -> pd.DataFrame:
    """
    특정 Daygainer에 대한 대조군 후보 찾기.
    
    조건:
    - 동일 날짜
    - 등락률 -50% ~ +10%
    - 가격 >= $0.1
    - 동일 가격 티어
    - Daygainer 자신 제외
    
    Args:
        daily_df: 일봉 데이터프레임
        daygainer_date: Daygainer 발생일
        daygainer_ticker: Daygainer 티커
        daygainer_price_tier: Daygainer의 가격 티어
    
    Returns:
        조건 충족하는 후보 종목 데이터프레임
    """
    mask = (
        (daily_df['date'] == daygainer_date) &
        (daily_df['ticker'] != daygainer_ticker) &
        (daily_df['change_pct'] >= CONTROL_CHANGE_MIN) &
        (daily_df['change_pct'] <= CONTROL_CHANGE_MAX) &
        (daily_df['close'] >= MIN_PRICE) &
        (daily_df['price_tier'] == daygainer_price_tier)
    )
    
    return daily_df[mask].copy()


def step1_extract_candidates_vectorized(daily_df: pd.DataFrame, daygainers_df: pd.DataFrame) -> pd.DataFrame:
    """
    Step 1: 각 Daygainer에 대해 1차 후보군 추출 (Vectorized 버전).
    
    ELI5: 
    - row-by-row 루프 대신 한번에 모든 날짜/티어 조합을 매칭
    - 1,300만 레코드를 효율적으로 필터링
    
    Returns:
        DataFrame with columns: [dg_date, dg_ticker, control_ticker, control_change_pct, control_close, price_tier]
    """
    logger.info("Step 1: Extracting control candidates (vectorized)...")
    
    # 1. Daygainer에 가격 티어 추가
    daygainers_df = daygainers_df.copy()
    daygainers_df['price_tier'] = daygainers_df['close'].apply(get_price_tier)
    daygainers_df = daygainers_df.dropna(subset=['price_tier'])
    
    # 2. 대조군 조건 충족하는 일봉만 필터링 (한번에)
    control_mask = (
        (daily_df['change_pct'] >= CONTROL_CHANGE_MIN) &
        (daily_df['change_pct'] <= CONTROL_CHANGE_MAX) &
        (daily_df['close'] >= MIN_PRICE) &
        (daily_df['price_tier'].notna())
    )
    control_pool = daily_df[control_mask][['date', 'ticker', 'close', 'change_pct', 'price_tier', 'high']].copy()
    control_pool.columns = ['date', 'control_ticker', 'control_close', 'control_change_pct', 'price_tier', 'control_high']
    
    logger.info(f"  - 대조군 풀: {len(control_pool):,}개 (전체 {len(daily_df):,}개 중)")
    
    # 3. Daygainer와 대조군 풀 조인 (날짜 + 가격티어)
    dg_subset = daygainers_df[['date', 'ticker', 'price_tier']].copy()
    dg_subset.columns = ['date', 'dg_ticker', 'price_tier']
    
    merged = pd.merge(
        dg_subset,
        control_pool,
        on=['date', 'price_tier'],
        how='inner'
    )
    
    # 4. 자기 자신 제외
    merged = merged[merged['dg_ticker'] != merged['control_ticker']]
    
    logger.info(f"Step 1 완료: {len(merged):,} control-daygainer pairs")
    logger.info(f"  - Daygainers covered: {merged['dg_ticker'].nunique()}")
    logger.info(f"  - 평균 후보/Daygainer: {len(merged) / merged['dg_ticker'].nunique():.1f}개")
    
    return merged


# ============================================================
# Step 2: RVOL 스파이크 검사 (분봉 기반)
# ============================================================

def load_intraday_for_ticker(ticker: str, target_date) -> Optional[pd.DataFrame]:
    """
    특정 종목의 분봉 데이터 로드.
    
    Args:
        ticker: 종목 티커
        target_date: 조회할 날짜 (date object)
    
    Returns:
        해당 날짜의 분봉 데이터 또는 None (없을 경우)
    """
    parquet_path = INTRADAY_DIR / f"{ticker}.parquet"
    
    if not parquet_path.exists():
        return None
    
    try:
        df = pd.read_parquet(parquet_path)
        df.columns = df.columns.str.lower()
        
        # 날짜 필터링
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.date
            df = df[df['date'] == target_date]
        elif 'timestamp' in df.columns:
            df['date'] = pd.to_datetime(df['timestamp']).dt.date
            df = df[df['date'] == target_date]
        
        return df if len(df) > 0 else None
    except Exception as e:
        logger.debug(f"Error loading {ticker}: {e}")
        return None


def calculate_rvol_for_date(ticker: str, target_date, daily_df: pd.DataFrame) -> tuple[bool, float]:
    """
    특정 종목의 특정 날짜 RVOL 스파이크 여부 및 최대 RVOL 계산.
    
    ELI5:
    - RVOL = 현재 거래량 / 평균 거래량
    - 평소보다 2배 이상 거래량이 터진 분봉이 있으면 "관심 받았던" 종목
    
    Returns:
        (has_spike: bool, rvol_max: float)
    """
    # 1. 분봉 데이터 로드
    intraday = load_intraday_for_ticker(ticker, target_date)
    
    if intraday is None or len(intraday) == 0:
        # 분봉 없으면 일봉 기반 fallback: 당일 거래량 / 20일 평균
        ticker_daily = daily_df[daily_df['ticker'] == ticker].sort_values('date')
        if len(ticker_daily) < 20:
            return False, 0.0
        
        # target_date 이전 20일 평균
        before_date = ticker_daily[ticker_daily['date'] < target_date].tail(20)
        if len(before_date) == 0:
            return False, 0.0
        
        avg_vol = before_date['volume'].mean()
        target_row = ticker_daily[ticker_daily['date'] == target_date]
        if len(target_row) == 0 or avg_vol == 0:
            return False, 0.0
        
        day_rvol = target_row['volume'].iloc[0] / avg_vol
        return day_rvol >= RVOL_SPIKE_THRESHOLD, day_rvol
    
    # 2. 분봉별 RVOL 계산 (이 날짜 평균 대비)
    avg_bar_vol = intraday['volume'].mean()
    if avg_bar_vol == 0:
        return False, 0.0
    
    intraday['bar_rvol'] = intraday['volume'] / avg_bar_vol
    rvol_max = intraday['bar_rvol'].max()
    has_spike = rvol_max >= RVOL_SPIKE_THRESHOLD
    
    return has_spike, rvol_max


def step2_filter_by_rvol(candidates_df: pd.DataFrame, daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    Step 2: RVOL 스파이크가 있는 후보만 필터링.
    
    대조군 후보 중 RVOL >= 2x 스파이크가 있는 종목만 남김.
    (= "무언가 관심을 받았지만 급등하지 않은" 종목)
    """
    logger.info("Step 2: Filtering by RVOL spike...")
    
    # 고유 (control_ticker, date) 조합 추출
    unique_controls = candidates_df[['control_ticker', 'date']].drop_duplicates()
    logger.info(f"  - 검사할 고유 종목-날짜 조합: {len(unique_controls):,}개")
    
    # 샘플링 (전체 검사는 시간이 오래 걸림)
    # 일단 전체 후보를 유지하고, rvol_max 컬럼만 추가 (나중에 필터링)
    # TODO: 실제 분봉 데이터 검사는 시간이 많이 걸리므로 일단 일봉 기반 RVOL로 대체
    
    # 일봉 기반 간이 RVOL 계산 (20일 평균 대비 당일 거래량)
    logger.info("  - 일봉 기반 간이 RVOL 계산 중...")
    
    # 날짜별 평균 거래량 테이블 생성
    daily_df_sorted = daily_df.sort_values(['ticker', 'date'])
    daily_df_sorted['vol_ma20'] = daily_df_sorted.groupby('ticker')['volume'].transform(
        lambda x: x.rolling(20, min_periods=5).mean().shift(1)
    )
    daily_df_sorted['day_rvol'] = daily_df_sorted['volume'] / daily_df_sorted['vol_ma20']
    
    # 후보 df에 day_rvol 병합
    rvol_lookup = daily_df_sorted[['ticker', 'date', 'day_rvol']].copy()
    rvol_lookup.columns = ['control_ticker', 'date', 'rvol_max']
    
    result = pd.merge(candidates_df, rvol_lookup, on=['control_ticker', 'date'], how='left')
    result['rvol_max'] = result['rvol_max'].fillna(0)
    
    # RVOL >= 2x 필터링
    result['has_rvol_spike'] = result['rvol_max'] >= RVOL_SPIKE_THRESHOLD
    filtered = result[result['has_rvol_spike']].copy()
    
    logger.info(f"Step 2 완료: {len(filtered):,}개 남음 (RVOL >= {RVOL_SPIKE_THRESHOLD}x)")
    logger.info(f"  - 필터링률: {(1 - len(filtered)/len(result))*100:.1f}% 제거")
    
    return filtered


# ============================================================
# Step 3: Failed Pump 라벨링
# ============================================================

def step3_label_failed_pump(candidates_df: pd.DataFrame) -> pd.DataFrame:
    """
    Step 3: Failed Pump 라벨링.
    
    조건:
    - RVOL 스파이크 존재 (has_rvol_spike = True)
    - 장중 고점 대비 -30% 이상 하락
    """
    logger.info("Step 3: Labeling failed pump...")
    
    df = candidates_df.copy()
    
    # 고점 대비 하락률 계산 (일봉 데이터의 high, close 사용)
    # high_to_close_drop = (high - close) / high
    df['high_to_close_drop'] = (df['control_high'] - df['control_close']) / df['control_high']
    
    # Failed Pump 조건
    df['is_failed_pump'] = (
        df['has_rvol_spike'] & 
        (df['high_to_close_drop'] >= FAILED_PUMP_DROP)
    )
    
    # control_type 라벨
    df['control_type'] = df['is_failed_pump'].apply(lambda x: 'failed_pump' if x else 'normal')
    
    failed_count = df['is_failed_pump'].sum()
    logger.info(f"Step 3 완료: {failed_count:,}개 Failed Pump ({failed_count/len(df)*100:.1f}%)")
    
    return df


# ============================================================
# Step 4: 1:5 샘플링 및 CSV 출력
# ============================================================

def step4_sample_and_export(candidates_df: pd.DataFrame) -> pd.DataFrame:
    """
    Step 4: 각 Daygainer당 최대 5개 대조군 샘플링 후 CSV 출력.
    
    샘플링 전략:
    - Failed Pump 우선 포함 (있으면 1~2개)
    - 나머지는 normal에서 랜덤
    """
    logger.info("Step 4: Sampling and exporting...")
    
    samples = []
    
    for dg_ticker in candidates_df['dg_ticker'].unique():
        dg_group = candidates_df[candidates_df['dg_ticker'] == dg_ticker]
        
        failed_pumps = dg_group[dg_group['control_type'] == 'failed_pump']
        normals = dg_group[dg_group['control_type'] == 'normal']
        
        selected = []
        
        # Failed Pump 먼저 (최대 2개)
        if len(failed_pumps) > 0:
            fp_sample = failed_pumps.sample(n=min(2, len(failed_pumps)), random_state=42)
            selected.append(fp_sample)
        
        # 나머지 Normal에서 채우기
        remaining = CONTROL_RATIO - len(selected[0]) if selected else CONTROL_RATIO
        if len(normals) > 0 and remaining > 0:
            normal_sample = normals.sample(n=min(remaining, len(normals)), random_state=42)
            selected.append(normal_sample)
        
        if selected:
            samples.append(pd.concat(selected))
    
    result = pd.concat(samples, ignore_index=True)
    
    # 출력 컬럼 정리
    output_cols = ['date', 'dg_ticker', 'control_ticker', 'control_type', 'rvol_max', 
                   'control_change_pct', 'control_close', 'price_tier']
    result = result[output_cols]
    result.columns = ['daygainer_date', 'daygainer_ticker', 'control_ticker', 'control_type', 
                      'rvol_max', 'control_change_pct', 'control_close', 'price_tier']
    
    # CSV 저장
    result.to_csv(OUTPUT_CSV, index=False)
    
    logger.info(f"Step 4 완료: {len(result):,}개 레코드 저장")
    logger.info(f"  - 출력: {OUTPUT_CSV}")
    logger.info(f"  - Daygainers: {result['daygainer_ticker'].nunique()}")
    logger.info(f"  - Failed Pump 비율: {(result['control_type'] == 'failed_pump').mean()*100:.1f}%")
    
    return result


# ============================================================
# Main (전체 파이프라인)
# ============================================================

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("R-3 대조군 매칭 시작")
    logger.info("=" * 60)
    
    # 데이터 로드
    daily_df = load_daily_data()
    daygainers_df = load_daygainers()
    
    # Step 1: 1차 후보군 추출
    candidates_df = step1_extract_candidates_vectorized(daily_df, daygainers_df)
    
    # Step 2: RVOL 필터링
    rvol_filtered_df = step2_filter_by_rvol(candidates_df, daily_df)
    
    # Step 3: Failed Pump 라벨링
    labeled_df = step3_label_failed_pump(rvol_filtered_df)
    
    # Step 4: 샘플링 및 CSV 출력
    final_df = step4_sample_and_export(labeled_df)
    
    # 샘플 출력
    print("\n" + "=" * 60)
    print("Sample output (first 10 rows):")
    print("=" * 60)
    print(final_df.head(10).to_string(index=False))
    
    logger.info("=" * 60)
    logger.info("R-3 대조군 매칭 완료!")
    logger.info("=" * 60)
