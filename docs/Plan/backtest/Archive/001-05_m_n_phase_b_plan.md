# R-4 Phase B: M-n 피처 추출 및 스캐너 필터 도출 계획서

> **작성일**: 2026-01-15 | **버전**: 3.0  
> **예상 소요**: ~4h  
> **선행**: Phase A 완료 (d1_features.parquet 생성)

> [!CAUTION]
> **⚠️ Phase E 결과 폐기 (2026-01-15)**  
> - pandas_ta CCI 계산 오류 발견 (정상 ±100 vs 실제 81M)
> - D-1 + M-n 혼합 모델 설계 오류 (분리 필요)
> - T0 정의 방식 문제 (Control HOD fallback = 사후 정보 누수)
> 
> **→ 3-Stage 재설계로 전환**: [reflect01.md](./reflect/reflect01.md), [reflect02.md](./reflect/reflect02.md) 참조

---

## 0. 재설계 방향 (reflect01/02 반영)

### 0.1 핵심 문제

| 문제 | 기존 | 수정 |
|------|------|------|
| 모델 설계 | D-1 + M-n 혼합 | **분리**: Stage 0 (D-1) + Stage 1 (M-n) |
| T0 정의 | +6% 돌파 or HOD fallback | **Attempt Trigger**: minute_rvol ≥ 3.0 + 가격 조건 |
| 평가 지표 | Recall/Precision | **Recall@N** (일 단위 Top-N) |
| 라벨 | is_daygainer 직접 | **중간 라벨**: has_attempt, is_failed_pump |

### 0.2 3-Stage 아키텍처

```
Stage 0: D-1 Attempt Scanner
  - 입력: D-1 피처 (8~20개, 핵심만)
  - 라벨: has_attempt (장중 Attempt 발생 여부)
  - 평가: Recall@200 ≥ 70%, Candidates/day 150-250

Stage 1: Success vs Fail Classifier  
  - 입력: t_attempt 직전까지의 분봉 피처
  - 라벨: is_success (= is_daygainer), is_failed_pump
  - 평가: Alerts/day, Success Rate ≥ 50%

Stage 2: Alert Policy
  - 알림 예산, 쿨다운, 레짐별 θ
```

### 0.3 필수 수정 사항

1. **pandas_ta 130개 지표 유지** → CCI 등 이상치 개별 검증 후 사용
2. **D-1 모델 별도 설계** → Recall@N 평가 체계
3. **CV를 trade_date 그룹 기준으로** → 날짜 누수 방지
4. **M-n은 Attempt 기반으로 재설계** → t_attempt 직전 피처만 사용

---

## 1. 목표

**스캐너 필터 조건 도출**을 위한 Daygainer vs Control 피처 분석:

```
┌─────────────────────────────────────────────────────────┐
│  목적: "스캐너 필터 조건 도출"                              │
│                                                         │
│  입력: 8,000 종목/일                                      │
│  출력: "주목 후보" 50~100개 (Daygainer 포함률 높이기)        │
│                                                         │
│  → Recall(재현율)이 더 중요: "놓치지 않기" > "틀리지 않기"    │
└─────────────────────────────────────────────────────────┘
```

| 단계 | 역할 |
|------|------|
| **Phase E** (현재) | 스캐너 필터 조건 발굴 |
| **Phase F** (추후) | 매매 타이밍/시그널 (강화학습, Forward-Testing) |

---

## 2. 레이어 체크

> **참조**: [REFACTORING.md](../../refactor/REFACTORING.md)

- [x] 레이어 규칙 위반 없음 (독립 스크립트)
- [x] 순환 의존성 없음 (scripts/ 폴더 내 분석용)
- [x] DI Container 등록 필요: **아니오** (백엔드 서비스 아님)

**참고**: 본 계획서는 `scripts/` 폴더의 독립 분석 스크립트로, 백엔드 레이어 규칙 적용 대상 아님.

---

## 3. 기존 솔루션 검색 결과

| 솔루션 | 출처 | 채택 여부 | 사유 |
|--------|------|----------|------|
| **pandas-ta** | PyPI | ✅ 채택 | 130+ 기술지표, 분봉용 핵심 20개 선별 |
| **XGBoost** | PyPI | ✅ 채택 | 분류기 + 내장 정규화 + 피처 중요도 |
| **SHAP** | PyPI | ✅ 채택 | TreeExplainer로 피처 기여도 분석 |
| **shapiq** | PyPI | ⏸️ 대기 | SHAP 대안, 필요시 추가 검토 |
| **TA-Lib** | PyPI | ❌ 미채택 | C 바인딩 설치 복잡, pandas-ta로 충분 |

---

## 4. 현재 데이터 상태

| 항목 | 값 |
|------|---|
| D-1 피처 완료 | ✅ 4,894건 |
| 분봉 커버리지 | **0.8%** (39/4,894건) → 다운로드 진행 중 |
| 분봉 존재 기간 | 2025-12-30 ~ 2026-01-12 |
| 분봉 누락 기간 | 2021-01-11 ~ 2025-12-23 |

---

## 5. T0 탐지 (Step 3)

### 5.1 방식 A: Threshold T0
```
T0 = 전일 종가 대비 +6% 최초 돌파 시점
```
- 장점: 단순, 직관적
- 단점: 느린 상승 종목에서 급등 중반에 T0 찍힘

### 5.2 방식 B: Acceleration T0
```python
rolling_return = close.pct_change(10) / 10  # 10분 평균 상승률
acceleration = rolling_return.diff()
T0 = acceleration > 0.002 인 첫 시점
```
- 장점: 느린/빠른 급등 모두 시작점 포착
- 단점: threshold 튜닝 필요

### 5.3 Fallback
```
T0 = 장중 최고가 도달 시점 (위 방식 실패 시)
```

> **002-02 합의**: T0 방식 2개 **병렬 유지**, 사후 비교 분석

---

## 6. M-n 피처 구성 (002-02 반영)

### 6.1 D-1 일봉 피처 (~150개)

```
원본 130개 (pandas_ta.strategy("All"))
+ 괴리 피처 20개 (rsi_5_14_div, macd_signal_div, ...)
= ~150개
```

> **002-02 합의**: 다중공선성 허용, 괴리가 알파일 수 있음

### 6.2 M-n 분봉 피처 (~100개)

> **002-02 합의**: 분봉 130개 전체 ❌ → **핵심 20개 × 4 윈도우**

**핵심 20개 지표 (분봉 전용)**:
- Momentum: RSI_5, RSI_14, MACD, Stoch_K, CCI
- Volume: OBV, CMF, MFI, VWAP_deviation
- Volatility: ATR, BB_width, BB_position
- Trend: EMA_9, EMA_20, ADX, Aroon_up
- Custom: vol_zscore, price_accel, spread, tick_count

**계산**:
```python
CORE_MINUTE_INDICATORS = [
    'rsi_5', 'rsi_14', 'macd', 'stoch_k', 'cci',
    'obv', 'cmf', 'mfi', 'vwap_dev',
    'atr', 'bb_width', 'bb_pos',
    'ema_9', 'ema_20', 'adx', 'aroon_up',
    'vol_zscore', 'price_accel', 'spread', 'tick_count'
]
WINDOWS = [15, 30, 60, 120]  # 분

# 20개 × 4윈도우 = 80개 + 윈도우간 변화율 20개 = ~100개
```

### 6.3 프리마켓 피처 (5개)

> **002-02 합의**: 프리마켓 중요성 강화 (T의 실전 경험 반영)

| 피처 | 설명 |
|------|------|
| `premarket_rvol` | 프리마켓 거래량 / 전일 평균 |
| `premarket_range` | (고점 - 저점) / 시가 |
| `premarket_close_location` | 종가가 프리마켓 범위의 어디에? (0~1) |
| `gap_pct` | 전일 종가 대비 프리마켓 종가 갭 |
| `premarket_volume_profile` | 초반 vs 후반 거래량 비율 |

### 6.4 메타 피처 (3개)

```python
market_regime (BULL/NORMAL/BEAR)  # 시장 레짐 라벨
day_of_week  # 요일
time_since_market_open  # T0까지 경과 분
```

### 6.5 총계: ~260개 피처

| 카테고리 | 개수 |
|----------|------|
| D-1 일봉 | ~150개 |
| M-n 분봉 | ~100개 |
| 프리마켓 | 5개 |
| 메타 | 3개 |
| **총계** | **~260개** |

---

## 7. 과적합 방지 전략 (002-02 반영)

| 항목 | 기존 | 수정 |
|------|------|------|
| 다중공선성 | 제거 | ❌ **삭제** - 괴리가 알파일 수 있음 |
| 피처 사전 선택 | SelectKBest 30개 | ❌ **삭제** - 비선형 조합 놓칠 수 있음 |
| 정규화 | - | ✅ XGBoost L1/L2 내장 정규화 의존 |
| 시장 레짐 | 미고려 | ✅ **추가** - BULL/NORMAL/BEAR 라벨 |
| Out-of-Sample | 미적용 | ✅ **추가** - 2024년 학습 → 2025년 테스트 |

```python
# 괴리 피처 예시
df['rsi_5_14_div'] = df['RSI_5'] - df['RSI_14']  # 단기-중기 괴리
df['macd_signal_div'] = df['MACD'] - df['MACD_Signal']  # MACD 괴리

# 시장 레짐 라벨링
def label_regime(date):
    if date.year == 2021 and date.month <= 6:
        return 'BULL'  # 밈스탁 광풍
    elif date.year == 2022:
        return 'BEAR'  # 하락장
    return 'NORMAL'
```

---

## 8. 변경/생성 파일

| 파일 | 유형 | 예상 라인 | 설명 |
|------|-----|----------|------|
| `scripts/build_m_n_features.py` | [NEW] | ~200 | M-n 피처 추출 (T0 탐지 포함) |
| `scripts/build_features_brute_force.py` | [NEW] | ~150 | 130개 지표 일괄 계산 |
| `scripts/train_xgboost.py` | [NEW] | ~100 | XGBoost + SHAP 분석 |
| `scripts/m_n_features.parquet` | [OUT] | - | M-n 피처 데이터 |
| `scripts/all_features.parquet` | [OUT] | - | D-1 + M-n 통합 피처 |
| `scripts/feature_importance.csv` | [OUT] | - | SHAP 기반 피처 랭킹 |
| `scripts/shap_summary.png` | [OUT] | - | SHAP Summary Plot |

---

## 9. 실행 단계

### Step 0: 분봉 데이터 다운로드 (진행 중)
```bash
python scripts/download_target_minutes.py
```
- 4,855건 분봉 다운로드 (현재 실행 중)

### Step 1: D-1 피처 확장 + 괴리 피처
```bash
python scripts/build_features_brute_force.py
```
- pandas_ta로 130개 지표 계산
- 괴리 피처 20개 추가
- 레짐 라벨 추가

### Step 2: T0 탐지 + M-n 피처 추출
```bash
python scripts/build_m_n_features.py
```
- Threshold T0 / Acceleration T0 병렬 탐지
- 핵심 20개 × 4 윈도우 분봉 피처
- 프리마켓 5개 피처

### Step 3: XGBoost 학습 + SHAP 분석
```bash
python scripts/train_xgboost.py
```
- D-1 + M-n 통합 피처셋으로 학습
- 5-Fold CV로 AUC 측정
- SHAP로 상위 20개 유의미 피처 도출

---

## 10. 검증

### 10.1 스크립트 검증
```bash
ruff check scripts/build_m_n_features.py scripts/build_features_brute_force.py scripts/train_xgboost.py
```

### 10.2 파이프라인 검증

| 검증 항목 | 기준 |
|----------|------|
| T0 탐지율 | ≥ 80% (Threshold vs Accel 비교) |
| 분봉 커버리지 | ≥ 90% 샘플에서 윈도우 데이터 확보 |
| 결측값 비율 | < 30% |
| AUC (5-Fold CV) | ≥ 0.60 (랜덤보다 유의미) |

### 10.3 Out-of-Sample 검증

```python
# 2024년 데이터로 학습 → 2025년 데이터로 테스트
train = df[df['target_date'].dt.year <= 2024]
test = df[df['target_date'].dt.year >= 2025]

model.fit(train[features], train['label'])
auc_oos = roc_auc_score(test['label'], model.predict_proba(test[features])[:, 1])
# 기준: AUC ≥ 0.55
```

---

## 11. 예상 시간

| 단계 | 소요 시간 |
|------|----------|
| Step 0: 분봉 다운로드 | ~2-3시간 (진행 중) |
| Step 1: D-1 지표 계산 | ~30초 |
| Step 2: M-n 지표 계산 | ~10분 (핵심 20개로 축소) |
| Step 3: XGBoost + SHAP | ~7분 |
| **합계 (다운로드 제외)** | **~20분** |

---

## 12. 최종 출력물

**스캐너 필터 조건** (예시):
```python
# Phase E 결과 활용
def scanner_filter(ticker_features):
    return (
        ticker_features['rsi_5_14_div'] > 20 and
        ticker_features['premarket_rvol'] > 5 and
        ticker_features['vol_zscore_15m'] > 2.5
    )
    # → True면 워치리스트에 추가
```

---

**문서 이력**
| 버전 | 일자 | 변경 내용 |
|------|------|----------|
| 1.0 | 2026-01-15 | 초안 작성 |
| 1.1 | 2026-01-15 | Phase E (Brute Force ML) 추가 |
| 1.2 | 2026-01-15 | 002-02 토론 결과 반영 |
| 2.0 | 2026-01-15 | IMP-planning 워크플로우 적용, 목적 재정의 (스캐너 필터 도출) |
| 3.0 | 2026-01-15 | **전문가 리뷰 반영 (reflect01/02)**: Phase E 폐기, 3-Stage 재설계 방향 추가 |
