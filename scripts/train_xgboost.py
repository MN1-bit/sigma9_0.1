"""
R-4 Phase E Step 3: XGBoost + SHAP 분석

D-1 + M-n 통합 피처셋으로 XGBoost 분류기 학습 후 SHAP로 유의미 피처 도출.
스캐너 필터 조건 발굴이 목표.

Usage:
    python scripts/train_xgboost.py

Output:
    scripts/feature_importance.csv  - SHAP 기반 피처 랭킹
    scripts/shap_summary.png        - SHAP Summary Plot
    scripts/ml_report.json          - CV 점수, AUC, 모델 파라미터
"""

import json
import logging
from pathlib import Path

import pandas as pd
import numpy as np

# ML 라이브러리 임포트
try:
    from xgboost import XGBClassifier
except ImportError:
    print("xgboost 설치 필요: pip install xgboost")
    raise

try:
    import shap
except ImportError:
    print("shap 설치 필요: pip install shap")
    raise

from sklearn.model_selection import cross_val_score, TimeSeriesSplit
from sklearn.metrics import roc_auc_score

# ==================================================
# 설정
# ==================================================
D1_EXTENDED = Path("scripts/d1_features_extended.parquet")
D1_BASIC = Path("scripts/d1_features.parquet")
M_N_FEATURES = Path("scripts/m_n_features.parquet")
OUTPUT_IMPORTANCE = Path("scripts/feature_importance.csv")
OUTPUT_PLOT = Path("scripts/shap_summary.png")
OUTPUT_REPORT = Path("scripts/ml_report.json")

# 제외할 컬럼 (피처가 아닌 메타데이터)
EXCLUDE_COLS = [
    "ticker", "target_date", "label", "price_tier", 
    "t0_threshold", "t0_accel", "t0_fallback",
    "has_premarket", "day_rows", "prev_close",
    "market_regime", "day_of_week",  # 레짐은 별도 처리
]

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ==================================================
# 데이터 로드 및 전처리
# ==================================================

def load_and_merge_features() -> pd.DataFrame:
    """
    D-1 피처와 M-n 피처 통합.
    
    ELI5: 
    - D-1: 장 시작 전 알 수 있는 정보 (전일 지표)
    - M-n: 장중 급등 직전 정보 (분봉 지표)
    - 둘을 합쳐서 "급등 패턴" 학습
    """
    logger.info("피처 데이터 로드 중...")
    
    # D-1 피처 (확장 버전 우선, 없으면 기본)
    if D1_EXTENDED.exists():
        d1_df = pd.read_parquet(D1_EXTENDED)
        logger.info(f"D-1 확장 피처: {len(d1_df):,} rows, {len(d1_df.columns)} cols")
    elif D1_BASIC.exists():
        d1_df = pd.read_parquet(D1_BASIC)
        logger.info(f"D-1 기본 피처: {len(d1_df):,} rows, {len(d1_df.columns)} cols")
    else:
        raise FileNotFoundError("D-1 피처 파일 없음")
    
    d1_df["target_date"] = pd.to_datetime(d1_df["target_date"]).dt.date
    
    # M-n 피처 (선택적)
    if M_N_FEATURES.exists():
        mn_df = pd.read_parquet(M_N_FEATURES)
        mn_df["target_date"] = pd.to_datetime(mn_df["target_date"]).dt.date
        logger.info(f"M-n 피처: {len(mn_df):,} rows, {len(mn_df.columns)} cols")
        
        # 병합 (D-1 피처에 M-n 피처 추가)
        # M-n에만 있는 컬럼 추가
        mn_only_cols = [c for c in mn_df.columns if c not in d1_df.columns]
        if mn_only_cols:
            merge_df = mn_df[["ticker", "target_date"] + mn_only_cols]
            df = d1_df.merge(merge_df, on=["ticker", "target_date"], how="left")
            logger.info(f"병합 후: {len(df):,} rows, {len(df.columns)} cols")
        else:
            df = d1_df
    else:
        logger.info("M-n 피처 없음, D-1만 사용")
        df = d1_df
    
    return df


def prepare_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, list]:
    """
    학습용 피처와 라벨 분리.
    
    ELI5:
    - X = 피처 (숫자 데이터만)
    - y = 라벨 (1 = Daygainer, 0 = Control)
    - 결측값은 -999로 채움 (XGBoost가 처리)
    """
    # 라벨 생성: Daygainer = 1, Control = 0
    df = df.copy()
    df["y"] = (df["label"] == "daygainer").astype(int)
    
    # 피처 컬럼 선택 (숫자 + 제외 목록 아닌 것)
    feature_cols = [
        c for c in df.columns 
        if c not in EXCLUDE_COLS + ["y", "label"]
        and df[c].dtype in ["float64", "int64", "float32", "int32"]
    ]
    
    logger.info(f"피처 수: {len(feature_cols)}개")
    
    # X, y 분리
    X = df[feature_cols].copy()
    y = df["y"]
    
    # 결측값 처리 (XGBoost는 NaN 처리 가능하지만 명시적으로)
    X = X.fillna(-999)
    
    # 무한값 처리
    X = X.replace([np.inf, -np.inf], -999)
    
    logger.info(f"라벨 분포: Daygainer={y.sum()}, Control={len(y) - y.sum()}")
    
    return X, y, feature_cols


# ==================================================
# 모델 학습
# ==================================================

def train_xgboost(
    X: pd.DataFrame, 
    y: pd.Series,
    cv_splits: int = 5
) -> tuple[XGBClassifier, dict]:
    """
    XGBoost 분류기 학습 + CV 평가.
    
    ELI5:
    - XGBoost는 트리 기반 ML로 피처 중요도 자동 추출
    - 5-Fold CV로 과적합 여부 확인
    - AUC 0.6 이상이면 "랜덤보다 유의미"
    """
    logger.info("XGBoost 학습 시작...")
    
    # 모델 정의 (002-02 합의: L1/L2 정규화에 의존)
    model = XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        reg_alpha=0.1,    # L1 정규화
        reg_lambda=1.0,   # L2 정규화
        random_state=42,
        n_jobs=-1,
        use_label_encoder=False,
        eval_metric="logloss",
    )
    
    # TimeSeriesSplit CV (시간순 분할)
    tscv = TimeSeriesSplit(n_splits=cv_splits)
    
    # Cross-validation
    cv_scores = cross_val_score(
        model, X, y, 
        cv=tscv, 
        scoring="roc_auc",
        n_jobs=-1
    )
    
    logger.info(f"CV AUC: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
    logger.info(f"CV 점수: {[f'{s:.3f}' for s in cv_scores]}")
    
    # 전체 데이터로 학습
    model.fit(X, y)
    
    # 학습 데이터 AUC
    y_pred = model.predict_proba(X)[:, 1]
    train_auc = roc_auc_score(y, y_pred)
    logger.info(f"Train AUC: {train_auc:.3f}")
    
    results = {
        "cv_auc_mean": float(cv_scores.mean()),
        "cv_auc_std": float(cv_scores.std()),
        "cv_scores": [float(s) for s in cv_scores],
        "train_auc": float(train_auc),
        "n_features": len(X.columns),
        "n_samples": len(X),
        "n_positive": int(y.sum()),
        "n_negative": int(len(y) - y.sum()),
    }
    
    return model, results


# ==================================================
# SHAP 분석
# ==================================================

def analyze_shap(
    model: XGBClassifier, 
    X: pd.DataFrame,
    top_k: int = 30
) -> pd.DataFrame:
    """
    SHAP 분석으로 피처 중요도 추출.
    
    ELI5:
    - SHAP = 각 피처가 예측에 얼마나 기여했는지 측정
    - 값이 클수록 Daygainer 예측에 중요한 피처
    - 상위 20~30개가 스캐너 필터 후보
    """
    logger.info("SHAP 분석 시작...")
    
    # TreeExplainer (XGBoost에 최적화)
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    
    # 피처별 평균 SHAP (절대값)
    # ELI5: 각 피처가 평균적으로 얼마나 영향을 줬는지
    mean_shap = np.abs(shap_values).mean(axis=0)
    
    importance_df = pd.DataFrame({
        "feature": X.columns,
        "mean_abs_shap": mean_shap,
    }).sort_values("mean_abs_shap", ascending=False)
    
    importance_df["rank"] = range(1, len(importance_df) + 1)
    
    # 상위 K개 출력
    logger.info(f"\n상위 {top_k}개 피처:")
    print("-" * 50)
    for _, row in importance_df.head(top_k).iterrows():
        print(f"  {row['rank']:3d}. {row['feature']:40s} SHAP={row['mean_abs_shap']:.4f}")
    
    # SHAP Summary Plot 저장
    try:
        import matplotlib
        matplotlib.use("Agg")  # 백엔드 설정
        import matplotlib.pyplot as plt
        
        plt.figure(figsize=(12, 10))
        shap.summary_plot(
            shap_values, X, 
            max_display=top_k,
            show=False,
            plot_size=(12, 10)
        )
        plt.tight_layout()
        plt.savefig(OUTPUT_PLOT, dpi=150, bbox_inches="tight")
        plt.close()
        logger.info(f"SHAP Plot 저장: {OUTPUT_PLOT}")
    except Exception as e:
        logger.warning(f"SHAP Plot 저장 실패: {e}")
    
    return importance_df


# ==================================================
# 메인
# ==================================================

def main() -> None:
    """메인 실행."""
    logger.info("=" * 60)
    logger.info("R-4 Phase E Step 3: XGBoost + SHAP 분석")
    logger.info("=" * 60)
    
    # 데이터 로드
    df = load_and_merge_features()
    
    # 피처 준비
    X, y, feature_cols = prepare_features(df)
    
    if len(X) < 100:
        logger.error(f"샘플 부족: {len(X)}건 (최소 100건 필요)")
        return
    
    # XGBoost 학습
    model, results = train_xgboost(X, y)
    
    # SHAP 분석
    importance_df = analyze_shap(model, X, top_k=30)
    
    # 결과 저장
    importance_df.to_csv(OUTPUT_IMPORTANCE, index=False)
    logger.info(f"피처 중요도 저장: {OUTPUT_IMPORTANCE}")
    
    # 리포트 저장
    report = {
        **results,
        "top_20_features": importance_df.head(20)["feature"].tolist(),
        "model_params": model.get_params(),
    }
    with open(OUTPUT_REPORT, "w") as f:
        json.dump(report, f, indent=2)
    logger.info(f"ML 리포트 저장: {OUTPUT_REPORT}")
    
    # 스캐너 필터 조건 제안
    logger.info("\n" + "=" * 60)
    logger.info("스캐너 필터 조건 제안 (상위 5개 피처)")
    logger.info("=" * 60)
    top_5 = importance_df.head(5)["feature"].tolist()
    print(f"""
# 예시 스캐너 필터 (실제 임계값은 EDA 필요)
def scanner_filter(features):
    return (
        features['{top_5[0]}'] > X['{top_5[0]}'].quantile(0.75) and
        features['{top_5[1]}'] > X['{top_5[1]}'].quantile(0.75)
    )
""")
    
    logger.info("=" * 60)
    logger.info("완료")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
