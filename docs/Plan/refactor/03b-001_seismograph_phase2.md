# 03b-001: seismograph Phase 2 (로직 분리)

> **작성일**: 2026-01-08 01:06
> **우선순위**: 3b | **예상 소요**: 4-5h | **위험도**: 중간
> **선행 조건**: 03-001 완료 (패키지화)

## 1. 목표

Phase 1에서 패키지 구조는 완성됨. 이제 **내부 로직을 실제로 분리**:
- Signal 계산 함수 → `signals/` 모듈
- Score 계산 함수 → `scoring/` 모듈
- `seismograph_backup.py` 삭제

## 2. 분리 대상 (REFACTORING.md 3b 세부 작업)

| 작업 | 원본 메서드 | 이동 대상 |
|------|-------------|----------|
| Tight Range | `_calc_tight_range_intensity*()` | `signals/tight_range.py` |
| OBV Divergence | `_calc_obv_divergence_intensity*()` | `signals/obv_divergence.py` |
| Accumulation Bar | `_calc_accumulation_bar_intensity*()` | `signals/accumulation_bar.py` |
| Volume Dryout | `_calc_volume_dryout_intensity*()` | `signals/volume_dryout.py` |
| Score V1 | `calculate_watchlist_score()` | `scoring/v1.py` |
| Score V2 | `calculate_watchlist_score_v2()` | `scoring/v2.py` |
| Score V3 | `calculate_watchlist_score_v3()` | `scoring/v3.py` |

## 3. 실행 계획

### Step 1: signals/ 모듈 분리
각 시그널 계산 함수를 별도 파일로 추출

### Step 2: scoring/ 모듈 분리
V1, V2, V3 스코어 계산 로직 분리

### Step 3: __init__.py 정리
분리된 모듈 import 후 위임 패턴 적용

### Step 4: 백업 파일 삭제
`seismograph_backup.py` 삭제

## 4. 검증 계획
- [ ] 모든 파일 ≤500 라인
- [ ] `lint-imports` 통과
- [ ] `python -m backend` 정상 시작
- [ ] Score V1/V2/V3 계산 정상

## 5. 롤백 계획
- git checkout으로 `seismograph/__init__.py` 복원
