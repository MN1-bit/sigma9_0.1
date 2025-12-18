# Step 2.2: Seismograph Strategy - Scanning (Phase 1) 구현 계획

> **작성일**: 2025-12-18  
> **Phase**: 2 (Core Engine)  
> **목표**: Sigma9 핵심 전략의 Scanning 단계 구현

---

## 1. 배경 및 목적

`masterplan.md` Section 3 (Phase 1: The Setup)에 정의된 **Seismograph Strategy**의 스캐닝 로직을 구현한다.

### 핵심 개념
- **Phase 1 (Scanning)**: 일봉 기반으로 "매집 중인 종목"을 탐지하여 Watchlist 생성
- **Phase 2 (Trigger)**: 실시간 틱 기반으로 "폭발 순간" 포착 (Step 2.3에서 구현)

---

## 2. 구현 상세

### 2.1 Universe Filter (`get_universe_filter()`)

> masterplan.md 3.1절

| Filter | Value | 코드 키 |
|--------|-------|---------|
| Price | $2.00 ~ $10.00 | `price_min`, `price_max` |
| Market Cap | $50M ~ $300M | `market_cap_min`, `market_cap_max` |
| Float | < 15M shares | `float_max` |
| Avg Volume | > 100K/day | `avg_volume_min` |
| Change% | 0% ~ 5% | `change_pct_min`, `change_pct_max` |

---

### 2.2 Accumulation Score (`calculate_watchlist_score()`)

> masterplan.md 3.2절

4가지 신호를 가중 합산하여 0~100점 계산:

| 신호 | 조건 | Weight | 구현 |
|------|------|--------|------|
| **매집봉** | 가격 변동 ±2.5% AND 거래량 > 3× 평균 | 30% | `_check_accumulation_bar()` |
| **OBV Divergence** | 주가 기울기 ≤ 0 AND OBV 기울기 > 0 | 40% | `_check_obv_divergence()` |
| **Volume Dry-out** | 최근 3일 거래량 < 20일 평균의 40% | 20% | `_check_volume_dryout()` |
| **Tight Range (VCP)** | 5일 ATR < 20일 ATR의 50% | 10% | `_check_tight_range()` |

---

### 2.3 Exclusion Filter

| 조건 | 설명 |
|------|------|
| Pre-market Gap > +5% | 이미 터진 종목 제외 |
| Recent High 대비 -30% 이상 | 급락 종목 제외 |
| 52주 신저가 부근 | 바닥권 종목 제외 |

---

## 3. Proposed Changes

### 3.1 전략 구현

#### [NEW] [seismograph.py](file:///d:/Codes/Sigma9-0.1/backend/strategies/seismograph.py)

**클래스 구조**:
```
SeismographStrategy(StrategyBase)
├── 클래스 속성
│   ├── name = "Seismograph"
│   ├── version = "1.0.0"
│   └── description = "매집 탐지 + 폭발 포착 전략"
│
├── Scanning Layer (Phase 1)
│   ├── get_universe_filter()
│   ├── calculate_watchlist_score(ticker, daily_data)
│   ├── _check_accumulation_bar(data)
│   ├── _check_obv_divergence(data)
│   ├── _check_volume_dryout(data)
│   └── _check_tight_range(data)
│
├── Trading Layer (Stub - Phase 2에서 구현)
│   ├── on_tick() → NotImplemented stub
│   └── on_bar() → NotImplemented stub
│
└── Config Layer
    ├── get_config()
    └── set_config()
```

**설정 파라미터** (GUI 조정 가능):
```python
config = {
    "accumulation_threshold": {"value": 60, "min": 40, "max": 80},
    "spike_volume_multiplier": {"value": 3.0, "min": 2.0, "max": 5.0},
    "obv_lookback": {"value": 20, "min": 10, "max": 30},
    "dryout_threshold": {"value": 0.4, "min": 0.3, "max": 0.6},
    "atr_ratio_threshold": {"value": 0.5, "min": 0.3, "max": 0.7},
}
```

---

### 3.2 패키지 업데이트

#### [MODIFY] [__init__.py](file:///d:/Codes/Sigma9-0.1/backend/strategies/__init__.py)

`SeismographStrategy` export 추가

---

## 4. Verification Plan

### 4.1 Syntax Check (자동)

```powershell
python -m py_compile backend/strategies/seismograph.py
```

---

### 4.2 Unit Tests (자동)

기존 `tests/test_strategies.py`에 SeismographStrategy 테스트 추가:

| 테스트 | 설명 |
|--------|------|
| `test_seismograph_instantiation` | 클래스 생성 성공 |
| `test_seismograph_universe_filter` | 필터 조건 반환 확인 |
| `test_accumulation_bar_detection` | 매집봉 탐지 로직 |
| `test_obv_divergence_detection` | OBV 다이버전스 탐지 |
| `test_watchlist_score_calculation` | 점수 0~100 범위 확인 |

```powershell
pytest tests/test_strategies.py -v -k "seismograph"
```

---

### 4.3 Integration Test (Mock 데이터)

`MockPriceFeed`로 생성한 가상 일봉 데이터로 Watchlist 점수 계산:

```powershell
python -c "from backend.strategies.seismograph import SeismographStrategy; print(SeismographStrategy())"
```

---

## 5. 의존성

추가 필요 없음 (기존 `pandas`, `numpy` 활용)

---

## 6. 다음 단계

Step 2.2 완료 후:
- **Step 2.3**: Seismograph Strategy - Trigger (Phase 2)
  - `on_tick()` 로직 구현
  - Tick Velocity, Volume Burst 계산
  - Anti-Trap 필터 적용
