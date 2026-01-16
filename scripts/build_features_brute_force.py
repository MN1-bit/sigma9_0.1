"""
R-4 Phase E Step 1: D-1 피처 확장 (Brute Force)

pandas_ta로 130개 지표 일괄 계산 + 괴리 피처 + 레짐 라벨.
기존 d1_features.parquet을 확장하여 전체 피처셋 생성.

Usage:
    python scripts/build_features_brute_force.py

Output:
    scripts/d1_features_extended.parquet
"""

import logging
from pathlib import Path

import pandas as pd

# pandas_ta 임포트 (설치 필요: pip install pandas_ta)
try:
    import pandas_ta as ta  # noqa: F401 - df.ta 확장 메서드로 사용됨
except ImportError:
    print("pandas_ta 설치 필요: pip install pandas_ta")
    raise

# ==================================================
# 설정
# ==================================================
DAILY_PARQUET = Path("data/parquet/daily/all_daily.parquet")
D1_FEATURES = Path("scripts/d1_features.parquet")
OUTPUT_PARQUET = Path("scripts/d1_features_extended.parquet")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ==================================================
# 레짐 라벨링
# ==================================================

def label_regime(target_date: pd.Timestamp) -> str:
    """
    시장 레짐 라벨링.
    
    ELI5:
    - 2021년 상반기: 밈스탁 광풍 (BULL)
    - 2022년: 금리 인상으로 하락장 (BEAR)
    - 그 외: 정상 시장 (NORMAL)
    """
    year = target_date.year
    month = target_date.month
    
    if year == 2021 and month <= 6:
        return "BULL"  # 밈스탁 광풍, AMC/GME 시즌
    elif year == 2022:
        return "BEAR"  # 금리 인상 하락장
    else:
        return "NORMAL"


# ==================================================
# 괴리 피처 계산
# ==================================================

DIVERGENCE_PAIRS = [
    # (short, long, name) - 단기 지표와 장기 지표의 차이
    ("RSI_5", "RSI_14", "rsi_5_14_div"),
    ("EMA_9", "EMA_21", "ema_9_21_div_pct"),  # %로 계산
    ("SMA_10", "SMA_50", "sma_10_50_div_pct"),
]


def calculate_divergence_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    괴리 피처 계산.
    
    ELI5:
    - RSI_5 - RSI_14: 단기 과열 vs 중기 여력
    - 두 지표가 벌어지면 "괴리" = 트레이딩 신호
    """
    result = df.copy()
    
    # RSI 괴리: RSI_5 - RSI_14
    if "RSI_5" in result.columns and "RSI_14" in result.columns:
        result["rsi_5_14_div"] = result["RSI_5"] - result["RSI_14"]
    
    # EMA 괴리: (EMA_9 / EMA_21 - 1) * 100
    if "EMA_9" in result.columns and "EMA_21" in result.columns:
        result["ema_9_21_div_pct"] = (
            (result["EMA_9"] / result["EMA_21"] - 1) * 100
        ).where(result["EMA_21"] > 0)
    
    # SMA 괴리
    if "SMA_10" in result.columns and "SMA_50" in result.columns:
        result["sma_10_50_div_pct"] = (
            (result["SMA_10"] / result["SMA_50"] - 1) * 100
        ).where(result["SMA_50"] > 0)
    
    # MACD vs Signal 괴리
    if "MACD_12_26_9" in result.columns and "MACDs_12_26_9" in result.columns:
        result["macd_signal_div"] = result["MACD_12_26_9"] - result["MACDs_12_26_9"]
    
    # Stoch %K - %D 괴리
    if "STOCHk_14_3_3" in result.columns and "STOCHd_14_3_3" in result.columns:
        result["stoch_kd_div"] = result["STOCHk_14_3_3"] - result["STOCHd_14_3_3"]
    
    # BB 위치: (close - BB_lower) / (BB_upper - BB_lower)
    # ELI5: 0 = 하단밴드, 0.5 = 중앙, 1 = 상단밴드
    if all(c in result.columns for c in ["BBL_20_2.0", "BBU_20_2.0", "close"]):
        bb_range = result["BBU_20_2.0"] - result["BBL_20_2.0"]
        result["bb_position"] = (
            (result["close"] - result["BBL_20_2.0"]) / bb_range
        ).where(bb_range > 0)
    
    # BB 폭: (상단 - 하단) / 중앙
    if all(c in result.columns for c in ["BBL_20_2.0", "BBU_20_2.0", "BBM_20_2.0"]):
        result["bb_width"] = (
            (result["BBU_20_2.0"] - result["BBL_20_2.0"]) / result["BBM_20_2.0"]
        ).where(result["BBM_20_2.0"] > 0)
    
    return result


# ==================================================
# 메인 피처 빌더
# ==================================================

def calculate_all_indicators(ticker_df: pd.DataFrame) -> pd.DataFrame:
    """
    단일 티커에 대해 pandas_ta로 모든 지표 계산.
    
    ELI5:
    - pandas_ta.strategy("All")은 130개 이상 지표를 한번에 계산
    - 하지만 메모리/시간 효율을 위해 핵심 지표만 선택
    """
    if len(ticker_df) < 30:
        # 데이터 부족 시 빈 DataFrame 반환
        return ticker_df
    
    df = ticker_df.copy()
    df = df.sort_values("date")
    
    # pandas_ta에 필요한 컬럼명 매핑
    if "date" in df.columns:
        df = df.set_index("date")
    
    # 핵심 지표 계산 (전략별)
    try:
        # Momentum 지표
        df.ta.rsi(length=5, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.stoch(k=14, d=3, smooth_k=3, append=True)
        df.ta.cci(length=20, append=True)
        df.ta.willr(length=14, append=True)
        df.ta.mom(length=10, append=True)
        df.ta.roc(length=10, append=True)
        
        # Trend 지표
        df.ta.ema(length=9, append=True)
        df.ta.ema(length=21, append=True)
        df.ta.sma(length=10, append=True)
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=50, append=True)
        df.ta.adx(length=14, append=True)
        df.ta.aroon(length=25, append=True)
        
        # Volatility 지표
        df.ta.atr(length=14, append=True)
        df.ta.bbands(length=20, std=2, append=True)
        df.ta.kc(length=20, scalar=1.5, append=True)
        
        # Volume 지표
        df.ta.obv(append=True)
        df.ta.cmf(length=20, append=True)
        df.ta.mfi(length=14, append=True)
        df.ta.ad(append=True)
        
    except Exception as e:
        logger.warning(f"지표 계산 실패: {e}")
    
    # Index 복원
    df = df.reset_index()
    
    return df


def build_extended_features() -> pd.DataFrame:
    """
    D-1 피처 확장 실행.
    
    1. 기존 d1_features.parquet 로드
    2. 각 (ticker, target_date) 조합에 대해 D-1 시점까지의 지표 계산
    3. 괴리 피처 + 레짐 라벨 추가
    """
    # 데이터 로드
    logger.info("데이터 로드 중...")
    
    daily_df = pd.read_parquet(DAILY_PARQUET)
    daily_df["date"] = pd.to_datetime(daily_df["date"]).dt.date
    logger.info(f"일봉 데이터: {len(daily_df):,} rows")
    
    d1_df = pd.read_parquet(D1_FEATURES)
    d1_df["target_date"] = pd.to_datetime(d1_df["target_date"]).dt.date
    logger.info(f"D-1 피처: {len(d1_df):,} rows")
    
    # 고유 티커 목록
    unique_tickers = d1_df["ticker"].unique()
    logger.info(f"고유 티커: {len(unique_tickers)}개")
    
    # 티커별로 지표 계산
    logger.info("지표 계산 시작...")
    ticker_indicators = {}
    
    for i, ticker in enumerate(unique_tickers):
        ticker_data = daily_df[daily_df["ticker"] == ticker].copy()
        
        if len(ticker_data) >= 30:
            indicators = calculate_all_indicators(ticker_data)
            ticker_indicators[ticker] = indicators
        
        if (i + 1) % 200 == 0:
            logger.info(f"진행: {i + 1}/{len(unique_tickers)} 티커")
    
    logger.info(f"지표 계산 완료: {len(ticker_indicators)} 티커")
    
    # D-1 피처에 지표 병합
    results = []
    
    for idx, row in d1_df.iterrows():
        ticker = row["ticker"]
        target_date = row["target_date"]
        
        result_row = row.to_dict()
        
        # 레짐 라벨 추가
        result_row["market_regime"] = label_regime(pd.Timestamp(target_date))
        result_row["day_of_week"] = pd.Timestamp(target_date).dayofweek
        
        # 지표 병합
        if ticker in ticker_indicators:
            ind_df = ticker_indicators[ticker]
            
            # D-1 시점 데이터 찾기
            d1_data = ind_df[ind_df["date"] < target_date]
            
            if len(d1_data) > 0:
                d1_row = d1_data.iloc[-1]
                
                # 지표 컬럼들 추출
                indicator_cols = [
                    c for c in d1_row.index 
                    if c not in ["ticker", "date", "open", "high", "low", "close", "volume"]
                ]
                
                for col in indicator_cols:
                    val = d1_row[col]
                    if pd.notna(val):
                        result_row[col] = float(val)
        
        results.append(result_row)
        
        if (idx + 1) % 1000 == 0:
            logger.info(f"병합 진행: {idx + 1}/{len(d1_df)}")
    
    df = pd.DataFrame(results)
    
    # 괴리 피처 계산
    logger.info("괴리 피처 계산 중...")
    df = calculate_divergence_features(df)
    
    # 통계 출력
    logger.info("=" * 60)
    logger.info("확장 피처 결과")
    logger.info("=" * 60)
    logger.info(f"전체 샘플: {len(df):,}건")
    logger.info(f"피처 수: {len(df.columns)}개")
    logger.info(f"레짐 분포:\n{df['market_regime'].value_counts().to_string()}")
    
    # 결측값 비율 (주요 지표)
    indicator_cols = [c for c in df.columns if c.startswith(("RSI", "MACD", "EMA", "BB"))]
    for col in indicator_cols[:5]:
        null_pct = df[col].isna().mean() * 100
        logger.info(f"{col} 결측률: {null_pct:.1f}%")
    
    return df


def main() -> None:
    """메인 실행."""
    logger.info("=" * 60)
    logger.info("R-4 Phase E Step 1: D-1 피처 확장 (Brute Force)")
    logger.info("=" * 60)
    
    df = build_extended_features()
    
    # 저장
    df.to_parquet(OUTPUT_PARQUET, index=False)
    logger.info(f"저장 완료: {OUTPUT_PARQUET}")
    
    # 피처 목록 출력
    print("\n생성된 피처 목록:")
    print("-" * 40)
    for col in sorted(df.columns):
        print(f"  {col}")
    
    logger.info("=" * 60)
    logger.info("완료")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
