# 3-Stage 백테스트 재구현 계획서

> **작성일**: 2026-01-15 | **예상**: 8h  
> **기반**: [reflect01.md](./reflect/reflect01.md), [reflect02.md](./reflect/reflect02.md)

---

## 1. 목표

**reflect01/02 권장사항 기반 3-Stage 파이프라인 구현:**
- Stage 0: D-1 Attempt Scanner (has_attempt 예측)
- Stage 1: Success vs Fail Classifier (is_success 예측)
- Stage 2: Alert Policy (운영 최적화)

---

## 2. 레이어 체크

> **참조**: [REFACTORING.md](../../refactor/REFACTORING.md)

- [x] 레이어 규칙 위반 없음 (독립 스크립트)
- [x] 순환 의존성 없음 (scripts/ 폴더 내 분석용)
- [x] DI Container 등록 필요: **아니오** (백엔드 서비스 아님)

---

## 3. 기존 솔루션 검색 결과

| 솔루션 | 출처 | 채택 여부 | 사유 |
|--------|------|----------|------|
| **pandas-ta** | PyPI | ✅ 유지 | 130+ 지표, CCI 개별 검증 |
| **XGBoost** | PyPI | ✅ 유지 | 분류기 + L1/L2 정규화 |
| **SHAP** | PyPI | ✅ 유지 | 피처 중요도 분석 |
| **Polars** | PyPI | ✅ 채택 | 대용량 분봉 처리 |
| **DuckDB** | PyPI | ⏸️ 대기 | 필요시 조인 최적화 |

---

## 4. 변경/생성 파일

| 파일 | 유형 | 예상 라인 | 설명 |
|------|-----|----------|------|
| `scripts/build_minute_volume_profile.py` | [NEW] | ~100 | minute-of-day별 기대 거래량 계산 |
| `scripts/detect_attempt.py` | [NEW] | ~150 | Attempt Trigger 탐지 |
| `scripts/label_attempt_outcome.py` | [NEW] | ~80 | Success/Failed Pump 라벨링 |
| `scripts/build_d1_features_v2.py` | [NEW] | ~200 | D-1 피처 (pandas_ta 130개 + 괴리) |
| `scripts/build_attempt_features.py` | [NEW] | ~200 | t_attempt 직전 분봉 피처 |
| `scripts/train_stage0.py` | [NEW] | ~150 | Stage 0 학습 (has_attempt) |
| `scripts/train_stage1.py` | [NEW] | ~150 | Stage 1 학습 (is_success) |
| `scripts/evaluate_recall_at_n.py` | [NEW] | ~100 | 일별 Recall@N 평가 |

**출력 파일:**
| 파일 | 설명 |
|------|------|
| `data/backtest/ref_minute_volume_profile.parquet` | minute-of-day별 기대 거래량 |
| `data/backtest/event_attempt.parquet` | Attempt 이벤트 테이블 |
| `data/backtest/label_attempt_outcome.parquet` | Attempt 성공/실패 라벨 |
| `data/backtest/feat_d1_asof.parquet` | Stage 0용 D-1 피처 |
| `data/backtest/feat_intraday_at_attempt.parquet` | Stage 1용 분봉 피처 |

---

## 5. 실행 단계

### Phase 1: 데이터 정비 (~2h)

#### Step 1.1: minute_volume_profile 생성
```bash
python scripts/build_minute_volume_profile.py
```
- 분봉 데이터에서 minute-of-day별 20일 평균 거래량 계산
- asof_date 기준 point-in-time 강제

#### Step 1.2: Attempt 탐지
```bash
python scripts/detect_attempt.py
```
- minute_rvol = volume / exp_volume_20d
- Attempt 조건: minute_rvol ≥ 3.0 AND (ret_5m ≥ 1.5% OR breakout)
- 하루 첫 Attempt만 저장 (attempt_id=1)

#### Step 1.3: Attempt 라벨링
```bash
python scripts/label_attempt_outcome.py
```
- is_success = is_daygainer
- is_failed_pump = HOD 대비 -30% 드로다운

---

### Phase 2: Stage 0 구현 (~2h)

#### Step 2.1: D-1 피처 생성
```bash
python scripts/build_d1_features_v2.py
```
- pandas_ta 130개 지표 전체 사용
- 괴리 피처 추가 (rsi_5_14_div, macd_signal_div 등)
- CCI 이상치 검증 및 필터링
- asof_date = D-1 강제

#### Step 2.2: Stage 0 학습
```bash
python scripts/train_stage0.py
```
- X = feat_d1_asof
- y = has_attempt
- Split: trade_date 그룹 기준 (TimeSeriesGroupKFold)
- Train: 2021-2024, Test: 2025

---

### Phase 3: Stage 1 구현 (~2h)

#### Step 3.1: Attempt 피처 생성
```bash
python scripts/build_attempt_features.py
```
- t_attempt 직전까지의 분봉 피처만 사용
- 윈도우: 15/30/60/120분
- 핵심 20개 × 4 윈도우 = 80개

#### Step 3.2: Stage 1 학습
```bash
python scripts/train_stage1.py
```
- X = feat_intraday_at_attempt (+ D-1 일부)
- y = is_success
- Negative: is_failed_pump

---

### Phase 4: 평가 및 검증 (~2h)

#### Step 4.1: Recall@N 평가
```bash
python scripts/evaluate_recall_at_n.py
```
- Stage 0: Recall@200, Candidates/day
- Stage 1: Alerts/day, Success Rate

#### Step 4.2: 연도별 안정성
- 2021/2022/2023/2024/2025 분리 평가
- 룰 일관성 체크

---

## 6. 핵심 정의

### Attempt Trigger
```python
minute_rvol(t) >= 3.0  # 동일 minute-of-day 20일 평균 대비
AND (
    ret_5m(t) >= +1.5%       # 5분 수익률
    OR breakout_flag(t)      # 60분 박스 상단 돌파
)
```

### Failed Pump
```
has_attempt = 1
AND is_daygainer = 0
AND drawdown_from_hod >= 30%
```

---

## 7. 검증

### 자동 검증
```bash
ruff check scripts/*.py
```

### 성과 기준

| 지표 | Stage | 목표 |
|------|-------|------|
| Recall@200 | 0 | ≥ 70% |
| Candidates/day | 0 | 150-250 |
| Alerts/day | 1 | 20-50 |
| Success Rate | 1 | ≥ 50% |

---

## 8. 의존성 순서

```
Phase 1.1 → 1.2 → 1.3 (순차)
Phase 2.1 → 2.2 (순차)
Phase 3.1 → 3.2 (순차)
Phase 2, 3은 Phase 1 완료 후 병렬 가능
```

---

**문서 이력**
| 버전 | 일자 | 변경 내용 |
|------|------|----------|
| 1.0 | 2026-01-15 | 초안 (reflect01/02 기반 3-Stage 설계) |
