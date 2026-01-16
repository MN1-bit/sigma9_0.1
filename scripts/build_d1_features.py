"""
R-4 Phase A: D-1 피처 추출

control_groups.csv의 Daygainer/Control 티커에 대해 D-1(전일) 피처 계산.
이 피처는 장 시작 전 워치리스트 생성에 사용됨.

Usage:
    python scripts/build_d1_features.py
"""

import logging
from datetime import date
from pathlib import Path
from typing import NamedTuple

import pandas as pd

# ==================================================
# 설정
# ==================================================
DAILY_PARQUET = Path("data/parquet/daily/all_daily.parquet")
CONTROL_CSV = Path("scripts/control_groups.csv")
OUTPUT_PARQUET = Path("scripts/d1_features.parquet")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class D1Features(NamedTuple):
    """D-1 시점 피처."""
    ticker: str
    target_date: date
    label: str  # 'daygainer', 'control_normal', 'control_failed_pump'
    price_tier: str
    
    # D-1 피처
    close_d1: float | None
    volume_d1: float | None
    rvol_20d: float | None  # 20일 평균 대비 거래량 배수
    price_vs_20ma: float | None  # 20일 이평선 대비 %
    price_vs_52w_high: float | None  # 52주 고점 대비 %
    atr_pct: float | None  # ATR / 종가
    volume_trend_5d: float | None  # 5일 거래량 추세
    gap_count_30d: int | None  # 30일 갭 발생 횟수


# ==================================================
# 핵심 함수
# ==================================================


def load_control_groups() -> pd.DataFrame:
    """
    control_groups.csv 로드 및 고유 (ticker, date, label) 추출.
    
    ELI5: Daygainer와 Control 종목을 구분하여 라벨링.
    """
    df = pd.read_csv(CONTROL_CSV)
    
    # Daygainer 정보 추출
    dg_records = []
    for _, row in df.iterrows():
        dg_records.append({
            "ticker": row["daygainer_ticker"],
            "target_date": row["daygainer_date"],
            "label": "daygainer",
            "price_tier": row["price_tier"],
        })
    
    # Control 정보 추출
    ctrl_records = []
    for _, row in df.iterrows():
        ctrl_type = row["control_type"]
        label = f"control_{ctrl_type}"
        ctrl_records.append({
            "ticker": row["control_ticker"],
            "target_date": row["daygainer_date"],  # Control도 같은 날짜 사용
            "label": label,
            "price_tier": row["price_tier"],
        })
    
    all_records = pd.DataFrame(dg_records + ctrl_records)
    all_records["target_date"] = pd.to_datetime(all_records["target_date"]).dt.date
    
    # 중복 제거 (같은 ticker/date 조합)
    all_records = all_records.drop_duplicates(subset=["ticker", "target_date"])
    
    logger.info(f"로드 완료: 고유 (ticker, date) 조합 {len(all_records)}건")
    logger.info(f"라벨 분포: {all_records['label'].value_counts().to_dict()}")
    
    return all_records


def calculate_d1_features(
    ticker: str, 
    target_date: date, 
    daily_df: pd.DataFrame
) -> dict:
    """
    특정 ticker의 D-1 시점 피처 계산.
    
    ELI5:
    - D-1 = target_date의 전일 (실제 급등 전날)
    - 20일 RVOL = 전일 거래량 / 20일 평균 거래량
    - ATR = 14일 평균 변동폭 (High-Low)
    """
    # 해당 티커 데이터 필터
    ticker_data = daily_df[daily_df["ticker"] == ticker].copy()
    
    if len(ticker_data) == 0:
        return {"has_data": False}
    
    # 날짜 정렬
    ticker_data = ticker_data.sort_values("date")
    ticker_data["date_obj"] = pd.to_datetime(ticker_data["date"]).dt.date
    
    # D-1 시점 = target_date 직전 거래일
    # target_date 이전 데이터만 사용
    before_target = ticker_data[ticker_data["date_obj"] < target_date]
    
    if len(before_target) < 2:
        return {"has_data": False}
    
    # D-1 = 마지막 행
    d1_row = before_target.iloc[-1]
    
    # 기본 피처
    close_d1 = float(d1_row["close"])
    volume_d1 = float(d1_row["volume"])
    
    # RVOL 20일: 최근 20일 평균 대비 D-1 거래량
    # ELI5: "평소보다 몇 배 많이 거래됐는지" 측정
    if len(before_target) >= 21:
        vol_20d = before_target["volume"].iloc[-21:-1].mean()
        rvol_20d = volume_d1 / vol_20d if vol_20d > 0 else None
    else:
        rvol_20d = None
    
    # 20MA 대비 가격: (종가 - 20MA) / 20MA * 100
    # ELI5: "평균 가격보다 얼마나 위/아래에 있는지"
    if len(before_target) >= 20:
        ma_20 = before_target["close"].iloc[-20:].mean()
        price_vs_20ma = ((close_d1 / ma_20) - 1) * 100 if ma_20 > 0 else None
    else:
        price_vs_20ma = None
    
    # 52주 고점 대비: 최근 252 거래일 고점 기준
    # ELI5: "1년 최고점에서 얼마나 떨어져 있는지"
    lookback_52w = min(252, len(before_target))
    if lookback_52w >= 20:
        high_52w = before_target["high"].iloc[-lookback_52w:].max()
        price_vs_52w_high = ((close_d1 / high_52w) - 1) * 100 if high_52w > 0 else None
    else:
        price_vs_52w_high = None
    
    # ATR% (14일): 변동폭 / 종가
    # ELI5: "평균적으로 하루에 몇 % 움직이는지"
    if len(before_target) >= 14:
        recent_14 = before_target.iloc[-14:]
        tr_values = recent_14["high"] - recent_14["low"]
        atr_14 = tr_values.mean()
        atr_pct = (atr_14 / close_d1) * 100 if close_d1 > 0 else None
    else:
        atr_pct = None
    
    # 5일 거래량 추세: 최근 5일 vs 이전 5일
    # ELI5: "거래량이 늘어나는 추세인지"
    if len(before_target) >= 10:
        vol_recent_5 = before_target["volume"].iloc[-5:].mean()
        vol_prev_5 = before_target["volume"].iloc[-10:-5].mean()
        volume_trend_5d = (vol_recent_5 / vol_prev_5 - 1) * 100 if vol_prev_5 > 0 else None
    else:
        volume_trend_5d = None
    
    # 30일 갭 발생 횟수: |Open - PrevClose| > 2%
    # ELI5: "최근 한달간 갭 상승/하락한 횟수"
    if len(before_target) >= 31:
        recent_30 = before_target.iloc[-31:]
        prev_closes = recent_30["close"].shift(1)
        opens = recent_30["open"]
        gap_pct = ((opens - prev_closes) / prev_closes).abs() * 100
        gap_count_30d = int((gap_pct > 2).sum())
    else:
        gap_count_30d = None
    
    return {
        "has_data": True,
        "close_d1": close_d1,
        "volume_d1": volume_d1,
        "rvol_20d": rvol_20d,
        "price_vs_20ma": price_vs_20ma,
        "price_vs_52w_high": price_vs_52w_high,
        "atr_pct": atr_pct,
        "volume_trend_5d": volume_trend_5d,
        "gap_count_30d": gap_count_30d,
    }


def build_d1_features() -> pd.DataFrame:
    """
    전체 D-1 피처 추출 실행.
    
    Returns:
        D-1 피처 DataFrame
    """
    # 데이터 로드
    logger.info("일봉 데이터 로드...")
    daily_df = pd.read_parquet(DAILY_PARQUET)
    logger.info(f"일봉 데이터: {len(daily_df):,} rows")
    
    targets = load_control_groups()
    
    results = []
    total = len(targets)
    success_count = 0
    
    logger.info(f"D-1 피처 계산 시작: {total}건")
    
    for idx, row in targets.iterrows():
        ticker = row["ticker"]
        target_date = row["target_date"]
        label = row["label"]
        price_tier = row["price_tier"]
        
        features = calculate_d1_features(ticker, target_date, daily_df)
        
        if features.get("has_data"):
            success_count += 1
            results.append({
                "ticker": ticker,
                "target_date": target_date,
                "label": label,
                "price_tier": price_tier,
                "close_d1": features["close_d1"],
                "volume_d1": features["volume_d1"],
                "rvol_20d": features["rvol_20d"],
                "price_vs_20ma": features["price_vs_20ma"],
                "price_vs_52w_high": features["price_vs_52w_high"],
                "atr_pct": features["atr_pct"],
                "volume_trend_5d": features["volume_trend_5d"],
                "gap_count_30d": features["gap_count_30d"],
            })
        else:
            # 데이터 없는 경우도 기록 (None 피처)
            results.append({
                "ticker": ticker,
                "target_date": target_date,
                "label": label,
                "price_tier": price_tier,
                "close_d1": None,
                "volume_d1": None,
                "rvol_20d": None,
                "price_vs_20ma": None,
                "price_vs_52w_high": None,
                "atr_pct": None,
                "volume_trend_5d": None,
                "gap_count_30d": None,
            })
        
        if (idx + 1) % 500 == 0:
            logger.info(f"진행: {idx + 1}/{total}")
    
    df = pd.DataFrame(results)
    
    # 통계 출력
    logger.info("=" * 60)
    logger.info("D-1 피처 추출 결과")
    logger.info("=" * 60)
    logger.info(f"전체: {total}건")
    logger.info(f"피처 계산 성공: {success_count}건 ({100 * success_count / total:.1f}%)")
    logger.info(f"라벨 분포:\n{df['label'].value_counts().to_string()}")
    
    # 결측값 비율
    for col in ["rvol_20d", "price_vs_20ma", "atr_pct"]:
        null_pct = df[col].isna().mean() * 100
        logger.info(f"{col} 결측률: {null_pct:.1f}%")
    
    return df


def main() -> None:
    """메인 실행."""
    logger.info("=" * 60)
    logger.info("R-4 Phase A: D-1 피처 추출")
    logger.info("=" * 60)
    
    df = build_d1_features()
    
    # 저장
    df.to_parquet(OUTPUT_PARQUET, index=False)
    logger.info(f"저장 완료: {OUTPUT_PARQUET}")
    
    # 샘플 출력
    print("\n샘플 출력 (피처 있는 데이터 5건):")
    sample = df[df["rvol_20d"].notna()].head(5)
    print(sample.to_string(index=False))
    
    logger.info("=" * 60)
    logger.info("완료")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
