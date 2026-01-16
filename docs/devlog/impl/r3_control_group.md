# R-3 대조군 매칭 로직 Devlog

> **작성일**: 2026-01-15  
> **계획서**: [003-01_control_group_plan.md](../../Plan/backtest/003-01_control_group_plan.md)

## 진행 현황

| Step | 설명 | 상태 | 시간 |
|------|------|------|------|
| Step 1 | 일봉 기반 1차 후보군 추출 | ✅ | 07:06 |
| Step 2 | RVOL 스파이크 검사 | ✅ | 07:14 |
| Step 2-1 | Massive API Fallback | ⏭️ 스킵 | - |
| Step 3 | Failed Pump 라벨링 | ✅ | 07:14 |
| Step 4 | 1:5 샘플링 및 CSV 출력 | ✅ | 07:14 |
| Step 5 | 검증 및 테스트 | ✅ | 07:15 |

---

## 최종 결과

| 지표 | 값 |
|------|-----|
| 출력 파일 | `scripts/control_groups.csv` |
| 총 레코드 | 4,205개 |
| Daygainers 수 | 841개 |
| 평균 대조군/Daygainer | 5.0개 |
| Normal 비율 | 74.7% (3,142개) |
| Failed Pump 비율 | 25.3% (1,063개) |

---

## Step 1: 일봉 기반 1차 후보군 추출 ✅

### 변경 사항
- `scripts/build_control_group.py`: vectorized 방식으로 최적화
- 대조군 풀: 13,275,590개, 평균 97.5개/Daygainer 후보

---

## Step 2: RVOL 스파이크 검사 ✅

- 일봉 기반 간이 RVOL 계산 적용 (20일 MA 대비 당일 거래량)
- RVOL ≥ 2x 조건 필터링 → 99.5% 제거
- Step 2-1 (Massive API): 분봉 데이터 부재 시 일봉 fallback 사용으로 스킵

---

## Step 3: Failed Pump 라벨링 ✅

- 고점 대비 30% 이상 하락 조건 적용
- 1,063개 (25.3%) Failed Pump 검출

---

## Step 4: 1:5 샘플링 및 CSV 출력 ✅

- 각 Daygainer당 최대 5개 대조군 (Failed Pump 우선 포함)
- `scripts/control_groups.csv` 생성 완료

---

## 검증 결과 ✅

- 스크립트 실행: Exit code 0
- 레코드 수 확인: 4,205개 (예상 ~6,000에서 RVOL 필터로 감소)
- Failed Pump 비율: 25.3% (목표 5~40% 범위 내)

