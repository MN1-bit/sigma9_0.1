# 급등 전 스캐닝 전략: 구현 토론 (v3)

> **문서 번호**: 001-01 부속 토론 v3  
> **작성일**: 2026-01-15  
> **선행 문서**: [_detection_debate02.md](./_detection_debate02.md)  
> **어젠다**:  
> 1. 어떤 ML 모델을 사용할 것인가?  
> 2. Massive API에서 Top Daygainer 히스토리 접근 가능한가?  
> 3. 초기 가설로 사용할 수 있는 로직은?  
> 4. 활용 가능한 오픈소스/라이브러리는?

---

## 등장인물

| 역할 | 관점 |
|------|------|
| **백엔드 개발자** | 시스템 통합, API 연동 |
| **ML 엔지니어** | 모델 선정, 학습 파이프라인 |
| **퀀트** | 피처 설계, 통계적 유효성 |
| **단타 트레이더** | 실전 패턴, 도메인 지식 |
| **금융공학 리서처** | 학술 문헌, 기관 사례 |

---

## 1라운드: ML 모델 선정

### 🤖 ML 엔지니어

> 분류 문제니까 모델 후보를 정리해봅시다.

| 모델 | 장점 | 단점 | Daygainer 탐지 적합성 |
|------|------|------|---------------------|
| **XGBoost** | 빠름, 해석 용이 (SHAP), 정형 데이터 강자 | 시계열 특성 미반영 | ⭐⭐⭐⭐⭐ |
| **LightGBM** | XGBoost보다 빠름, 대용량 | 과적합 주의 | ⭐⭐⭐⭐⭐ |
| **CatBoost** | 범주형 자동 처리 | 속도 느림 | ⭐⭐⭐⭐ |
| **Random Forest** | 단순, 안정적 | 성능 한계 | ⭐⭐⭐ |
| **TabNet** | 딥러닝 기반, Attention | 블랙박스, 데이터 많이 필요 | ⭐⭐⭐ |
| **Logistic Reg** | 해석 최고, 베이스라인 | 비선형 패턴 못 잡음 | ⭐⭐ (베이스라인) |

---

### 📊 퀀트

**제 의견: XGBoost 또는 LightGBM**

이유:
1. **해석성**: SHAP으로 피처 기여도 분석 필수 → Gradient Boosting 계열 최적
2. **샘플 수**: Daygainer 수백~수천 개 수준 → 딥러닝 불필요
3. **피처 유형**: 대부분 정형 수치 데이터 → 트리 기반 강점

---

### 💹 단타 트레이더

XGBoost면 충분해 보이는데, **클래스 불균형**은 어떻게 하죠?

Daygainer : 대조군 = 1 : 4 비율이면 불균형 심한 거 아닌가요?

---

### 🤖 ML 엔지니어

**클래스 불균형 대응 전략**:

| 방법 | 설명 | 적용 |
|------|------|------|
| `scale_pos_weight` | XGBoost 내장 파라미터 | ✅ 기본 적용 |
| SMOTE | 소수 클래스 오버샘플링 | △ 신중히 |
| Undersampling | 다수 클래스 축소 | △ 데이터 손실 |
| Focal Loss | 어려운 샘플에 가중치 | △ 구현 복잡 |
| Threshold 조정 | 0.5 대신 최적 임계값 | ✅ PR Curve로 결정 |

**권장**: `scale_pos_weight=4` + Precision-Recall 기반 평가

---

### 🏦 금융공학 리서처

**앙상블 고려할까요?**

```
Stage 1: XGBoost (기본)
Stage 2: LightGBM (동일 피처)
Stage 3: 두 모델 예측값 평균 or 스태킹
```

하지만 초기엔 **단일 XGBoost로 충분**합니다.  
앙상블은 성능 병목 확인 후 검토.

---

### 합의: 모델 선정

> [!IMPORTANT]
> **확정: XGBoost**
> - 베이스라인: Logistic Regression
> - 주력: XGBoost (SHAP 연동)
> - 대안: LightGBM (대용량 시)

---

## 2라운드: Daygainer 히스토리 데이터 소스 탐색

### 🔧 백엔드 개발자

> Daygainer 히스토리 데이터(티커 + 등락률)를 확보할 수 있는 소스가 있을까요?

---

### 🏦 금융공학 리서처

**외부 API 소스 조사 결과**:

| 제공자 | 엔드포인트 | 히스토리 지원 | 비용 | 평가 |
|--------|-----------|--------------|------|------|
| **Benzinga** | Market Movers API | ✅ **2003년부터** | 유료 (Enterprise) | ⭐⭐⭐⭐⭐ |
| **Financial Modeling Prep** | Biggest Gainers API | △ 당일 위주 | 무료/유료 | ⭐⭐⭐ |
| **Intrinio** | Top Gainers by Exchange | △ 당일 스냅샷 | 유료 | ⭐⭐⭐ |
| **EODHD** | EOD API + 직접 계산 | ✅ 1972년부터 (일봉) | $20/월~ | ⭐⭐⭐⭐ |
| **Massive/Polygon** | Snapshot Gainers | ❌ 당일만 | 보유중 | ⭐⭐ |
| **Alpaca** | Top Market Movers | ❌ 당일만 | 무료 | ⭐⭐ |

---

### 📊 퀀트

**Benzinga가 가장 유력**해 보이네요. 2003년부터 히스토리가 있다면:
- 약 20년치 × 252일 × Top 20 = **10만+ Daygainer 샘플**
- 별도 필터링 (시총, 섹터, 거래량) 지원 여부 확인 필요

하지만 **Enterprise 가격이 문제**입니다. 월 수백 달러 예상.

---

### 🔧 백엔드 개발자

**Massive/Polygon 상세 조사**:

```
# 현재 Massive API
GET /v2/snapshot/locale/us/markets/stocks/gainers
→ 당일 Top 20 Gainers 스냅샷만 제공
→ 히스토리 파라미터 없음

# 개별 일봉
GET /v2/aggs/ticker/{ticker}/range/1/day/{from}/{to}
→ 개별 종목 조회 가능, Daygainer 여부 직접 계산 필요
```

**결론**: Massive에서 과거 Daygainer 목록 **직접 조회 불가**

---

### 🏦 금융공학 리서처

**무료/저비용 대안 정리**:

| 방법 | 데이터 소스 | 장점 | 단점 |
|------|------------|------|------|
| **직접 계산** | 보유 Parquet 일봉 | 무료, 즉시 가능 | 계산 로직 직접 구현 |
| **EODHD EOD API** | 외부 API | 저렴 ($20/월), 장기 히스토리 | 별도 수집 필요 |
| **Yahoo Finance** | yfinance 라이브러리 | 무료 | 불안정, Rate Limit |
| **웹 스크래핑** | Finviz, TradingView | 무료 | ToS 위반 가능, 불안정 |

---

### � 단타 트레이더

**실용적 제안**: 일단 **직접 계산**으로 시작하죠.

우리 Parquet에 전 종목 일봉이 있으니:
1. 전 종목 일봉 로드
2. 각 날짜별 등락률 계산
3. 상위 N개 또는 임계값 이상 필터링

나중에 Benzinga 같은 유료 소스로 **검증 및 보완** 가능.

---

### 📊 퀀트

**직접 계산 로직**:

```python
import pandas as pd

def extract_daygainers(daily_df, threshold=0.10, min_volume=100_000, min_price=1.0):
    """
    일봉 데이터에서 Daygainer 추출
    
    Args:
        daily_df: 전 종목 일봉 (columns: date, ticker, open, close, volume, ...)
        threshold: 최소 등락률 (0.10 = 10%)
        min_volume: 최소 거래량
        min_price: 최소 가격
    """
    # 등락률 계산 (시가 대비)
    daily_df['change_pct'] = (daily_df['close'] - daily_df['open']) / daily_df['open']
    
    # 필터링
    daygainers = daily_df[
        (daily_df['change_pct'] >= threshold) &
        (daily_df['volume'] >= min_volume) &
        (daily_df['close'] >= min_price)
    ]
    
    return daygainers[['date', 'ticker', 'change_pct', 'volume', 'close']]
```

---

### 🔧 백엔드 개발자

**데이터 가용성 체크**:

| 데이터 | 상태 | 위치 |
|--------|------|------|
| 전 종목 일봉 | ✅ 보유 | `data/parquet/daily/` |
| 일봉 기간 | ? | 확인 필요 (예상 2020~현재) |
| 종목 수 | ? | 확인 필요 (예상 5000+) |

> [!WARNING]
> **확인 필요**: 우리 Parquet에 몇 년치 데이터가 있는지 점검 필요

---

### 💹 단타 트레이더

**Daygainer 정의 기준** 제안:

| 기준 | 값 | 근거 |
|------|-----|------|
| 최소 등락률 | +10% | 의미 있는 급등 |
| 최소 거래량 | 10만주 | 유동성 확보 |
| 최소 가격 | $1 | 페니스톡 제외 |
| 최대 시총 | $10B | 소형·중형주 집중 (옵션) |

---

### 🏦 금융공학 리서처

**장기 로드맵 제안**:

```
Phase 1: 직접 계산 (무료)
  - 보유 Parquet 일봉 활용
  - MVP 빠르게 구축

Phase 2: 유료 API 검증 (선택)
  - Benzinga 트라이얼로 우리 데이터 정확도 검증
  - 불일치 분석 (상장폐지, 스플릿 등)

Phase 3: 데이터 보강 (필요시)
  - 더 긴 히스토리 필요시 EODHD 또는 Benzinga 도입
```

---

### 합의: Daygainer 데이터 소스

> [!IMPORTANT]
> **확정 방안**:  
> 1. **1차**: 보유 Parquet 일봉에서 직접 계산  
> 2. **정의**: 등락률 ≥10%, 거래량 ≥10만주, 가격 ≥$1  
> 3. **검증**: Benzinga/FMP 트라이얼로 샘플 대조 (선택)  
> 4. **보강**: 장기 히스토리 필요시 EODHD 검토

---

### 추가 조사 필요 항목

| 항목 | 담당 | 상태 |
|------|------|------|
| 보유 Parquet 일봉 기간 확인 | 개발자 | 🔲 TBD |
| Benzinga API 가격 문의 | 리서처 | 🔲 TBD |
| EODHD 샘플 데이터 테스트 | 개발자 | 🔲 TBD |

---

## 3라운드: 초기 가설 — 어떤 피처가 유효할까

### 💹 단타 트레이더

제 경험 기반 **급등 전 징후**:

| 징후 | 피처화 | 설명 |
|------|--------|------|
| "거래량 서서히 증가" | `rvol_d1`, `rvol_d2` | D-1, D-2 RVOL |
| "눌림목 후 반등" | `pullback_depth` | 최근 고점 대비 하락폭 |
| "박스권 상단 터치" | `dist_to_resistance` | 저항선까지 거리 |
| "갭업 후 유지" | `gap_hold_ratio` | 장중 갭 유지율 |
| "종가 꼬리" | `candle_tail_ratio` | (종가-저가)/(고가-저가) |
| "섹터 강세" | `sector_momentum` | 섹터 평균 수익률 |

---

### 📊 퀀트

**학술 문헌 기반 피처**:

| 피처 | 출처 | 설명 |
|------|------|------|
| **RSI(14)** | Wilder | 과매도 구간 탈출 |
| **ATR 확대** | Wilder | 변동성 증가 |
| **20일선 돌파** | 기술적 분석 | 추세 전환 |
| **볼린저 밴드 %B** | Bollinger | 밴드 내 위치 |
| **OBV 기울기** | Granville | 거래량 추세 |
| **52주 저점 대비 위치** | Momentum | 바닥권 여부 |

---

### 🏦 금융공학 리서처

**팩터 투자 관점 피처**:

| 팩터 | 피처 | 설명 |
|------|------|------|
| **Momentum** | `ret_5d`, `ret_20d` | 최근 수익률 |
| **Reversal** | `ret_1d_lag` | 전일 하락 후 반등 |
| **Size** | `log_mcap` | 시총 (로그) |
| **Liquidity** | `adv_20d` | 20일 평균 거래대금 |
| **Volatility** | `realized_vol_20d` | 실현 변동성 |

---

### 🤖 ML 엔지니어

**피처 분류 정리**:

```
1. 가격 기반
   - gap_pct, candle_body_ratio, candle_tail_ratio
   - dist_to_52w_high, dist_to_52w_low

2. 거래량 기반
   - rvol_1d, rvol_5d, obv_slope
   - volume_ma_ratio (당일 거래량 / 20일 평균)

3. 기술적 지표
   - rsi_14, macd_hist, bb_pct_b
   - ma_cross_5_20, atr_14

4. 시장/섹터
   - sector_ret_1d, spy_ret_1d
   - relative_strength (종목 수익률 - SPY 수익률)

5. 메타
   - log_mcap, log_float, price
```

---

### 합의: 초기 피처 셋

> [!TIP]
> **Phase 1 피처 (20개)**
> 
> 가격: `gap_pct`, `candle_tail_ratio`, `dist_to_52w_high`  
> 거래량: `rvol_1d`, `rvol_5d`, `obv_slope`  
> 기술: `rsi_14`, `atr_14`, `bb_pct_b`, `ma_cross_5_20`  
> 시장: `sector_ret_1d`, `relative_strength`  
> 메타: `log_mcap`, `log_float`

---

## 4라운드: 활용 가능한 오픈소스/라이브러리

### 🔧 백엔드 개발자

**Python 생태계 정리**:

#### 데이터 처리
| 라이브러리 | 용도 | 비고 |
|------------|------|------|
| `pandas` | 데이터프레임 | 필수 |
| `polars` | 대용량 처리 | pandas 대안 |
| `pyarrow` | Parquet I/O | 필수 |

#### 기술적 지표 계산
| 라이브러리 | 용도 | 비고 |
|------------|------|------|
| **`ta-lib`** | 150+ 지표 | C 래퍼, 빠름, 설치 번거로움 |
| **`pandas-ta`** | 130+ 지표 | 순수 Python, 설치 쉬움 |
| `tulipy` | 빠른 지표 계산 | C 기반 |
| `finta` | 경량 지표 라이브러리 | |

#### ML/통계
| 라이브러리 | 용도 | 비고 |
|------------|------|------|
| `scikit-learn` | 전처리, 평가 | 필수 |
| **`xgboost`** | 분류 모델 | 주력 |
| `lightgbm` | 대안 모델 | |
| **`shap`** | 모델 해석 | 필수 |
| `optuna` | 하이퍼파라미터 튜닝 | |
| `imbalanced-learn` | SMOTE 등 | 불균형 대응 |

---

### 📊 퀀트

**백테스트/알파 연구용**:

| 라이브러리 | 용도 | 비고 |
|------------|------|------|
| `alphalens` | 팩터 분석 | Quantopian 출신 |
| `pyfolio` | 포트폴리오 분석 | Quantopian 출신 |
| `vectorbt` | 빠른 백테스트 | 벡터화 |
| `backtrader` | 이벤트 기반 백테스트 | 우리 플랫폼 |

---

### 🏦 금융공학 리서처

**주목할 오픈소스 프로젝트**:

| 프로젝트 | 설명 | 참고 가치 |
|----------|------|-----------|
| **`qlib`** (Microsoft) | 퀀트 연구 플랫폼 | 피처 엔지니어링, 모델 평가 |
| `finrl` | 강화학습 기반 트레이딩 | 참고만 |
| `zipline` | Quantopian 백테스터 | 레거시 |
| `bt` | 간단한 백테스트 | |

---

### 합의: 기술 스택 확정

```yaml
데이터 처리:
  - pandas, pyarrow

지표 계산:
  - pandas-ta (1차)
  - ta-lib (성능 필요시)

ML:
  - scikit-learn
  - xgboost
  - shap
  - optuna

백테스트:
  - backtrader (기존 플랫폼)

참고:
  - qlib (피처 설계)
  - alphalens (팩터 분석)
```

---

## 5라운드: 결론 및 다음 단계

### 합의 사항 요약

| 항목 | 결정 |
|------|------|
| ML 모델 | **XGBoost** (베이스라인: Logistic Reg) |
| Daygainer 데이터 | Parquet 일봉에서 직접 계산 |
| 정의 | 등락률 ≥10%, 거래량 ≥10만주, 가격 ≥$1 |
| 초기 피처 | 20개 (가격/거래량/기술/시장/메타) |
| 지표 라이브러리 | `pandas-ta` |
| 해석 도구 | `shap` |

---

## 부록: XGBoost 사용법 가이드

### A.1 설치

```bash
pip install xgboost shap pandas-ta scikit-learn optuna
```

### A.2 기본 사용법

```python
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_recall_curve, average_precision_score
import shap

# 데이터 준비
X = df_features.drop(columns=['is_daygainer'])
y = df_features['is_daygainer']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

# 클래스 불균형 처리
scale_pos_weight = len(y_train[y_train==0]) / len(y_train[y_train==1])

# 모델 학습
model = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=6,
    learning_rate=0.1,
    scale_pos_weight=scale_pos_weight,
    use_label_encoder=False,
    eval_metric='aucpr',
    random_state=42
)

model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    early_stopping_rounds=10,
    verbose=False
)
```

### A.3 평가

```python
from sklearn.metrics import classification_report, precision_recall_curve
import matplotlib.pyplot as plt

# 예측
y_proba = model.predict_proba(X_test)[:, 1]
y_pred = (y_proba >= 0.5).astype(int)

# 분류 리포트
print(classification_report(y_test, y_pred))

# Precision-Recall Curve
precision, recall, thresholds = precision_recall_curve(y_test, y_proba)
plt.plot(recall, precision)
plt.xlabel('Recall')
plt.ylabel('Precision')
plt.title('PR Curve')
plt.show()

# Average Precision (PR AUC)
ap = average_precision_score(y_test, y_proba)
print(f"Average Precision: {ap:.4f}")
```

### A.4 최적 임계값 찾기

```python
from sklearn.metrics import f1_score

# F1 최적 임계값
f1_scores = [f1_score(y_test, y_proba >= t) for t in thresholds]
best_threshold = thresholds[np.argmax(f1_scores)]
print(f"Best Threshold: {best_threshold:.3f}")

# Precision@K (상위 K개 정밀도)
def precision_at_k(y_true, y_proba, k=20):
    top_k_idx = np.argsort(y_proba)[-k:]
    return y_true.iloc[top_k_idx].mean()

p_at_20 = precision_at_k(y_test, y_proba, k=20)
print(f"Precision@20: {p_at_20:.2%}")
```

### A.5 SHAP 해석

```python
import shap

# TreeExplainer (XGBoost에 최적화)
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# 전역 피처 중요도
shap.summary_plot(shap_values, X_test, plot_type="bar")

# 개별 예측 해석 (첫 번째 샘플)
shap.force_plot(
    explainer.expected_value, 
    shap_values[0], 
    X_test.iloc[0]
)

# Beeswarm Plot (분포 시각화)
shap.summary_plot(shap_values, X_test)
```

### A.6 Optuna 하이퍼파라미터 튜닝

```python
import optuna
from sklearn.model_selection import cross_val_score

def objective(trial):
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 50, 300),
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'scale_pos_weight': scale_pos_weight,
        'use_label_encoder': False,
        'eval_metric': 'aucpr',
        'random_state': 42
    }
    
    model = xgb.XGBClassifier(**params)
    scores = cross_val_score(
        model, X_train, y_train, 
        cv=5, scoring='average_precision'
    )
    return scores.mean()

study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=50)

print(f"Best params: {study.best_params}")
print(f"Best AP: {study.best_value:.4f}")
```

### A.7 시계열 교차 검증

```python
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=5)

for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
    X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
    y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]
    
    model.fit(X_tr, y_tr)
    y_proba = model.predict_proba(X_val)[:, 1]
    ap = average_precision_score(y_val, y_proba)
    print(f"Fold {fold+1} AP: {ap:.4f}")
```

### A.8 피처 중요도 (내장)

```python
# XGBoost 내장 중요도
importance = model.get_booster().get_score(importance_type='gain')
sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)

for feature, score in sorted_importance[:10]:
    print(f"{feature}: {score:.4f}")
```

---

## 부록 B: pandas-ta 사용법

### B.1 설치

```bash
pip install pandas-ta
```

### B.2 기본 사용법

```python
import pandas as pd
import pandas_ta as ta

# 데이터 로드 (OHLCV 컬럼 필요)
df = pd.read_parquet("AAPL.parquet")

# 단일 지표
df['rsi_14'] = ta.rsi(df['close'], length=14)
df['atr_14'] = ta.atr(df['high'], df['low'], df['close'], length=14)

# 복합 지표 (MACD)
macd = ta.macd(df['close'])
df = pd.concat([df, macd], axis=1)

# 볼린저 밴드
bbands = ta.bbands(df['close'], length=20)
df = pd.concat([df, bbands], axis=1)

# 이동평균
df['sma_20'] = ta.sma(df['close'], length=20)
df['ema_5'] = ta.ema(df['close'], length=5)
```

### B.3 전략 헬퍼 (한 번에 여러 지표)

```python
# 커스텀 전략
MyStrategy = ta.Strategy(
    name="Daygainer Indicators",
    ta=[
        {"kind": "rsi", "length": 14},
        {"kind": "atr", "length": 14},
        {"kind": "bbands", "length": 20},
        {"kind": "macd"},
        {"kind": "obv"},
        {"kind": "sma", "length": 5},
        {"kind": "sma", "length": 20},
    ]
)

# 적용
df.ta.strategy(MyStrategy)
```

---

**문서 이력**
| 버전 | 일자 | 변경 내용 |
|------|------|----------|
| 3.0 | 2026-01-15 | 구현 토론 (모델, 데이터, 피처, 라이브러리) |
