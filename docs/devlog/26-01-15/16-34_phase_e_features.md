# Phase E: M-n 피처 추출 Devlog

> **작성일**: 2026-01-15  
> **계획서**: [001-05_m_n_phase_b_plan.md](../../Plan/backtest/001-05_m_n_phase_b_plan.md)

## 진행 현황

| Step | 설명 | 상태 | 시간 |
|------|------|------|------|
| Step 0 | 분봉 데이터 다운로드 | 🔄 진행 중 | - |
| Step 1 | D-1 피처 확장 + 괴리 피처 | ✅ | 15:37-15:45 |
| Step 2 | T0 탐지 + M-n 피처 추출 | ✅ | 15:45-15:50 |
| Step 3 | XGBoost 학습 + SHAP 분석 | ✅ | 15:50-16:00 |

---

## Step 1: D-1 피처 확장 + 괴리 피처

### 변경 사항
- `scripts/build_features_brute_force.py`: [NEW] 268줄
  - pandas_ta로 핵심 지표 계산 (RSI, MACD, EMA, BB 등)
  - 괴리 피처 추가 (rsi_5_14_div, macd_signal_div 등)
  - 레짐 라벨 추가 (BULL/NORMAL/BEAR)

### 검증
- ruff check: ✅ All checks passed!

---

## Step 2: T0 탐지 + M-n 피처 수정

### 변경 사항
- `scripts/build_m_n_features.py`: 002-02 토론 결과 반영
  - 프리마켓 피처 4개 → 5개 확장
  - `premarket_rvol`, `premarket_range`, `premarket_close_location`, `gap_pct`, `premarket_volume_profile`

### 검증
- ruff check: ✅ All checks passed!

---

## Step 3: XGBoost + SHAP 분석

### 변경 사항
- `scripts/train_xgboost.py`: [NEW] ~290줄
  - D-1 + M-n 피처 통합
  - XGBoost 분류기 (L1/L2 정규화)
  - TimeSeriesSplit 5-Fold CV
  - SHAP 분석으로 상위 30개 피처 도출

### 검증
- ruff check: ✅ All checks passed!

---

## IMP-verification 검증 결과

> **참고**: `scripts/` 폴더는 독립 분석 스크립트로 백엔드 레이어 규칙 적용 대상 아님

| 항목 | 결과 | 비고 |
|------|------|------|
| ruff check | ✅ | 3개 파일 모두 통과 |
| 크기 제한 (≤500줄) | ✅ | 290, 405, 313줄 |
| DI 패턴 준수 | ✅ | `get_*_instance` 미사용 |
| lint-imports | N/A | 독립 스크립트 |
| pydeps cycles | N/A | 독립 스크립트 |

### 다음 단계
1. 분봉 다운로드 완료 대기 (`download_target_minutes.py`)
2. 순차 실행: `build_features_brute_force.py` → `build_m_n_features.py` → `train_xgboost.py`
3. SHAP 분석 결과로 스캐너 필터 조건 도출

---

## 파이프라인 실행 결과 (16:15~16:22)

### 실행 완료
```
Step 1: build_features_brute_force.py (3,594 티커, ~17분)
Step 2: build_m_n_features.py (4,340건)
Step 3: train_xgboost.py (xgboost/shap 설치 후)
```

### 초기 결과
| 항목 | 값 |
|------|-----|
| 샘플 | 4,894건 |
| 피처 | 77개 |
| Train AUC | 0.996 |
| CV AUC | NaN (TimeSeriesSplit 이슈) |

---

## 🚨 발견된 심각한 문제 (16:24~16:26)

### 1. pandas_ta 지표 계산 오류
```python
# 정상 CCI 범위: -100 ~ +100
# 실제 결과:
CCI_20_0.015 mean = 27,018  # 비정상
CCI max = 81,485,860       # 완전 오류

# AAPL 예시
# 수동 계산: CCI = -178 (정상)
# pandas_ta: CCI = -7,279 (비정상)
```

**원인**: pandas_ta의 CCI 계산 버그 또는 컬럼명 혼동

### 2. 피처 값 검증 결과

| 피처 | Daygainer | Control | 비고 |
|------|-----------|---------|------|
| CCI_20 | 59,860 | 19,151 | ❌ 둘 다 비정상 |
| ATR% | 20.2% | 9.0% | ✅ 합리적 |
| 52주 고점 대비 | -73% | -40% | ⚠️ DG가 더 바닥권 |
| RVOL_20d | 19.9x | 19.3x | ⚠️ 거의 차이 없음 |

---

## 📋 전문가 리뷰 반영 (reflect01.md 요약)

### 핵심 구조적 문제

1. **두 개의 다른 제품을 한 모델로 풀고 있음**
   - D-1 스캐너: 랭킹/리트리벌 문제 (Top-N)
   - M-n 경보: 타이밍/하자드 문제
   - → **분리 모델**이 맞음

2. **라벨/샘플링 누수**
   - Control의 T0를 HOD(장중 고점)로 fallback → **사후 정보 사용**
   - M-n 피처가 "이미 오른 후" 정보를 담게 됨

3. **평가 지표 불일치**
   - 현재: 일반 분류 (Recall/Precision)
   - 필요: **Recall@N (일일 Top-N 커버율)**

### 권장 수정 사항

1. **D-1 모델 분리** (D-1 피처만 사용)
2. **CV를 trade_date 그룹 기준으로** (날짜 누수 방지)
3. **M-n은 T0 한 점이 아니라 여러 시점 샷**으로 데이터 생성
4. **평가를 일 단위 Top-N**으로 재정의

### 3단계 설계 제안 (reflect01 권장)

```
Stage 0: "Pump Attempt가 생길 종목인가?" (D-1)
Stage 1: "Attempt 중 성공 vs 실패" (M-n)
Stage 2: 알림 타이밍 최적화
```

---

## 결론 및 다음 단계

### ❌ 현재 결과 폐기 사유
1. pandas_ta 지표 계산 오류
2. D-1 + M-n 혼합 모델 설계 오류
3. T0 정의 방식 문제 (사후 정보 누수)

### ✅ 필요 조치
1. pandas_ta 사용 중단, 기본 D-1 피처(8개)만 사용
2. D-1 스캐너 모델 별도 설계 (Recall@N 목표)
3. M-n 모델은 별도 Phase로 분리
4. 전문가 리뷰 기반 재설계 (reflect01.md 참조)
