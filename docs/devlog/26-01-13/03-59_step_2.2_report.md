# Step 2.2 Report: Seismograph Strategy - Scanning

> **작성일**: 2025-12-18  
> **소요 시간**: ~10분  
> **상태**: ✅ 완료

---

## 1. 작업 요약

Sigma9의 핵심 전략인 `SeismographStrategy`의 Scanning 단계(Phase 1)를 구현했습니다.
일봉 데이터 기반으로 "매집 중인 종목"을 탐지하여 Watchlist를 생성합니다.

---

## 2. 생성된 파일

| 파일 | 설명 | 라인 |
|------|------|------|
| [seismograph.py](file:///d:/Codes/Sigma9-0.1/backend/strategies/seismograph.py) | SeismographStrategy 클래스 | ~520 |
| [step_2.2_plan.md](file:///d:/Codes/Sigma9-0.1/docs/Plan/steps/step_2.2_plan.md) | 구현 계획서 | - |

---

## 3. 구현된 기능

### 3.1 Universe Filter

```python
{
    "price_min": 2.00,        # $2 ~ $10
    "price_max": 10.00,
    "market_cap_min": 50M,    # 마이크로캡
    "market_cap_max": 300M,
    "float_max": 15M,         # Low Float
    "avg_volume_min": 100K,   # 최소 유동성
}
```

### 3.2 Accumulation Score (매집 점수)

4가지 신호 가중 합산 (0~100점):

| 신호 | Weight | 메서드 |
|------|--------|--------|
| 매집봉 | 30% | `_check_accumulation_bar()` |
| OBV Divergence | 40% | `_check_obv_divergence()` |
| Volume Dry-out | 20% | `_check_volume_dryout()` |
| Tight Range/VCP | 10% | `_check_tight_range()` |

### 3.3 설정 파라미터

GUI에서 조정 가능한 파라미터:
- `accumulation_threshold`: 60 (40~80)
- `spike_volume_multiplier`: 3.0 (2.0~5.0)
- `obv_lookback`: 20 (10~30)
- `dryout_threshold`: 0.4 (0.3~0.6)
- `atr_ratio_threshold`: 0.5 (0.3~0.7)

---

## 4. 검증 결과

### 4.1 문법 검사 ✅

```powershell
python -m py_compile backend/strategies/seismograph.py
# (에러 없음)
```

### 4.2 데모 테스트 ✅

```
============================================================
Seismograph Strategy 테스트
============================================================

✓ 전략 생성: Seismograph v1.0.0
✓ Universe Filter: 정상 출력
✓ Accumulation Score: 0.0점 (Mock 데이터)
✓ 설정 변경 테스트: 정상

모든 테스트 완료! ✓
============================================================
```

## 5. 🔄 Architecture Update: Stage-Based Priority System

> **업데이트 시간**: 2025-12-18 01:38  
> **근거**: [Research Debate](file:///d:/Codes/Sigma9-0.1/docs/references/research/scoring_vs_filtering_debate.md)

### 5.1 변경 배경

**문제 제기**: 기존 Weighted Sum 방식은 모든 신호를 동등하게 취급하여, 단타 머신의 핵심 목표인 "폭발 임박 종목 최우선 선별"에 부적합.

**해결책**: 4개 신호가 각각 매집의 **서로 다른 단계(Stage)**를 대표한다는 관점에서 재설계.

### 5.2 변경된 로직

**기존 (Weighted Sum):**
```
점수 = 매집봉×30% + OBV×40% + Dryout×20% + Tight×10%
```

**변경 (Stage-Based Priority):**
```
1순위 (100점): Tight Range + OBV → 🔥 폭발 임박
2순위 ( 80점): Tight Range only → 높은 관심
3순위 ( 70점): Accumulation Bar + OBV → 관심 대상
4순위 ( 50점): Accumulation Bar only → 추적 중
5순위 ( 30점): OBV Divergence only → 모니터링
6순위 ( 10점): Volume Dry-out only → 관찰 대상
```

### 5.3 수정된 파일

| 파일 | 변경 내용 |
|------|----------|
| [masterplan.md](file:///d:/Codes/Sigma9-0.1/docs/Plan/masterplan.md) | Section 3.2 재작성 |
| [seismograph.py](file:///d:/Codes/Sigma9-0.1/backend/strategies/seismograph.py) | `calculate_watchlist_score()` 로직 변경 |

### 5.4 검증 ✅

- 문법 검사 통과
- 전략 데모 테스트 통과

---

## 6. 미구현 (Step 2.3에서 처리)

- `on_tick()`: Ignition Score 계산
- `calculate_trigger_score()`: Tick Velocity, Volume Burst
- Anti-Trap Filter 적용

---

- **Step 2.3**: Seismograph Strategy - Trigger (Phase 2)
  - `on_tick()` 로직 구현
  - Tick Velocity, Volume Burst 계산
  - Anti-Trap 필터 적용

---

## 8. Refinement: Watchlist Metadata (Step 2.2.5)

> **완료일**: 2025-12-18

### 8.1 목표
Trading Restrictions (Stage 1-2 종목 Monitoring Only)를 지원하기 위해 Watchlist에 개별 신호 탐지 결과를 메타데이터로 포함.

### 8.2 변경 사항

#### `backend/strategies/seismograph.py`
- `WatchlistItem` dataclass 추가 (score, stage, stage_number, signals, can_trade 포함)
- `calculate_watchlist_score_detailed()` 메서드 추가

#### `backend/core/scanner.py`
- `run_daily_scan()` 수정하여 상세 결과(stage_number, signals, can_trade)를 포함하도록 변경

### 8.3 결과
Watchlist JSON 아웃풋에 상세 메타데이터가 포함되어 2.3 단계의 Trigger 제한 로직을 지원할 준비 완료.

---

## 9. Refinement: Symbol Mapping (Step 2.2.7)

> **완료일**: 2025-12-18

### 9.1 목표
Polygon.io 티커와 IBKR 티커 간 형식 차이(예: `BRK/A` vs `BRK.A`)를 처리하는 매핑 서비스 구현.

### 9.2 변경 사항
- **`backend/data/symbol_mapper.py`** 구현
  - `polygon_to_ibkr()`, `ibkr_to_polygon()` 함수 제공
  - 자동 변환 규칙 및 제외 패턴(워런트, 유닛, 테스트 심볼) 적용
  - Singleton 패턴으로 어디서든 접근 가능

---

## 10. Refinement: Watchlist Persistence (Step 2.2.8)

> **완료일**: 2025-12-18

### 10.1 목표
Watchlist를 JSON 파일로 저장/로드하여 재시작 시 복원 및 히스토리 관리 지원.

### 10.2 변경 사항
- **`backend/data/watchlist_store.py`** 구현
  - `WatchlistStore` 클래스: 저장, 로드, 히스토리 관리
  - 저장 위치: `data/watchlist/watchlist_current.json` 및 `data/watchlist/history/`
  - 메타데이터(생성 시간, 버전, 개수) 포함

---
