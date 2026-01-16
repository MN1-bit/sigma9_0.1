# R-4 Phase B: M-n Features Devlog

> **작성일**: 2026-01-15
> **계획서**: [004-02_m_n_phase_b_plan.md](../../Plan/backtest/004-02_m_n_phase_b_plan.md)

## 진행 현황

| Step | 상태 | 시간 |
|------|------|------|
| Pre | 선행조건 확인 | 14:08 ✅ |
| 1 | 스크립트 검토/Lint 수정 | 14:10 ✅ |
| 2 | 스크립트 실행 | 14:11 ✅ |
| 3 | 결과 분석 | 14:12 ✅ |

---

## Step Pre: 선행조건 확인

### 체크리스트
- `d1_features.parquet`: ✅ 존재 (4,894건)
- `minute_coverage_report.csv`: ✅ 존재 (39건 분봉 보유)
- 기존 `build_m_n_features.py`: ✅ 391줄

---

## Step 1: Lint 수정

### 변경 사항
- `scripts/build_m_n_features.py`:
  - L15: `import numpy as np` 제거 (F401)
  - L210: `== True` → 직접 boolean 평가 (E712)

### 검증
```
ruff check scripts/build_m_n_features.py
All checks passed!
```
- lint: ✅

---

## Step 2: 스크립트 실행

```bash
python scripts/build_m_n_features.py
```

### 출력 파일
- `scripts/m_n_features.parquet`: ✅ 생성

---

## Step 3: 결과 분석

### 피처 추출 결과

| 항목 | 값 |
|------|---|
| 총 레코드 | **35건** |
| 컬럼 수 | 33 |

### T0 탐지율

| 방식 | 탐지 성공 | 비율 |
|------|----------|------|
| Threshold (+6%) | 24/35 | 68.6% |
| Acceleration | 30/35 | 85.7% |

> **관찰**: Acceleration 방식이 Threshold보다 탐지율 높음 (+17.1%p)

### 프리마켓 데이터

| 항목 | 값 |
|------|---|
| has_premarket = True | 8/35 (22.9%) |

### 라벨 분포

| Label | Count |
|-------|-------|
| daygainer | ~7건 |
| control_normal | ~21건 |
| control_failed_pump | ~7건 |

---

## 다음 단계

1. D-1 + M-n 피처셋 결합 ✅
2. Daygainer vs Control 차별화 EDA ✅
3. 유의미 결과 시 → 데이터 확장 (4,855건 분봉 다운로드)

---

## Phase C: Feature Merge & EDA (2026-01-15 14:13)

### 피처 병합

| 항목 | 값 |
|------|---|
| D-1 피처 | 4,894건, 12컬럼 |
| M-n 피처 | 35건, 33컬럼 |
| 병합 결과 | 35건, ~40컬럼 |

### 라벨 분포 (분봉 있는 35건)

| Label | Count |
|-------|-------|
| control_normal | 21 |
| daygainer | 7 |
| control_failed_pump | 7 |

### EDA 결과 요약

> ⚠️ **샘플 수 제한**: 분봉 커버리지 0.8%로 인해 7 Daygainer만 분석 가능

**T0 탐지율**:
- Threshold: DG=?, Normal=?, Failed=?
- Acceleration: DG=?, Normal=?, Failed=?

**Premarket 활동**: 전체 0/8 (0%) - 프리마켓 데이터 부족

### 생성 파일
- `scripts/merged_features.parquet`
- `scripts/eda_features.py`
- `scripts/eda_feature_comparison.csv`

### 결론

현재 샘플 수(7 Daygainer)로는 **통계적 유의성 확보 어려움**.
→ **분봉 데이터 확장 진행** (4,855건 다운로드)

---

## Phase D: 분봉 데이터 확장 (2026-01-15 14:19~)

### 목표
- 4,855건 (ticker, date) 조합의 분봉 데이터 다운로드
- 비동기 병렬 다운로드 (동시 10개 요청)
- 예상 시간: ~8분

### 상태: ✅ 테스트 완료

**테스트 결과** (10건):
- API 연결: ✅
- 데이터 다운로드: ✅  
- Parquet 저장: ✅

### 다음: 전체 다운로드 (4,855건) 대기 중
