# Step 2.3: Seismograph Strategy - Trigger (Phase 2) 구현 계획

> **작성일**: 2025-12-18  
> **Phase**: 2 (Core Engine)  
> **목표**: 실시간 틱 기반 Ignition(폭발) 감지 로직 구현

---

## 1. 배경 및 목적

`masterplan.md` Section 4에 정의된 **Phase 2: The Trigger** 로직을 구현합니다.

- **Phase 1 (Scanning)**: ✅ Step 2.2에서 완료 (일봉 기반 Watchlist 생성)
- **Phase 2 (Trigger)**: 🎯 이번 단계 (실시간 틱 기반 폭발 감지)

---

## 2. Ignition Score 구성

> masterplan.md 4.1절

| 조건 | 로직 | Weight |
|------|------|--------|
| **Tick Velocity** | 10초 체결 > 1분 평균의 8× | 35% |
| **Volume Burst** | 1분 거래량 > 5분 평균의 6× | 30% |
| **Price Break** | 현재가 > 박스권 상단 + 0.5% | 20% |
| **Buy Pressure** | 시장가 매수/매도 > 1.8 | 15% |

**→ Ignition Score ≥ 70점 시: BUY Signal 생성**

---

## 3. Anti-Trap Filter

> masterplan.md 4.2절

| 조건 | 설명 | 구현 |
|------|------|------|
| Spread < 1.0% | 스프레드 너무 넓으면 SKIP | `_check_spread()` |
| 장 시작 후 15분 이후 | 오프닝 노이즈 회피 | `_check_market_open_time()` |
| VWAP 위에 위치 | 당일 평균 이상에서만 진입 | `_check_above_vwap()` |

---

## 4. Proposed Changes

### 4.1 전략 수정

#### [MODIFY] [seismograph.py](file:///d:/Codes/Sigma9-0.1/backend/strategies/seismograph.py)

**새로 추가할 메서드**:

```
SeismographStrategy
├── Ignition Score 계산
│   ├── _calculate_tick_velocity(ticker) → float
│   ├── _calculate_volume_burst(ticker) → float
│   ├── _calculate_price_break(ticker) → float
│   └── _calculate_buy_pressure(ticker) → float
│
├── Anti-Trap Filter
│   ├── _check_spread(ticker, bid, ask) → bool
│   ├── _check_market_open_time(timestamp) → bool
│   ├── _check_above_vwap(ticker, price) → bool
│   └── _check_anti_trap_filter(ticker, price, bid, ask, timestamp) → bool
│
└── 기존 stub 수정
    ├── calculate_trigger_score() → 가중합 계산
    └── on_tick() → 틱 버퍼 + Ignition + Signal 생성
```

**내부 버퍼 구조**:

```python
@dataclass
class TickData:
    price: float
    volume: int
    timestamp: datetime
    side: str  # "B" (buy) or "S" (sell)

self._tick_buffer: Dict[str, deque[TickData]]  # 최근 60초
self._bar_1m: Dict[str, List[BarData]]         # 최근 5분봉
self._vwap: Dict[str, float]                   # 당일 VWAP
self._box_high: Dict[str, float]               # 박스권 고점
self._box_low: Dict[str, float]                # 박스권 저점
```

---

### 4.2 테스트 추가

#### [MODIFY] [test_strategies.py](file:///d:/Codes/Sigma9-0.1/tests/test_strategies.py)

`TestSeismographStrategy` 클래스 추가:

| 테스트 | 검증 내용 |
|--------|----------|
| `test_seismograph_instantiation` | 인스턴스 생성 |
| `test_calculate_trigger_score_range` | 0~100 범위 |
| `test_on_tick_generates_buy_signal` | 조건 충족 시 BUY |
| `test_anti_trap_blocks_early_entry` | 15분 전 차단 |

---

## 5. Verification Plan

### 5.1 Syntax Check

```powershell
python -m py_compile backend/strategies/seismograph.py
```

### 5.2 Unit Tests

```powershell
pytest tests/test_strategies.py -v -k "seismograph"
```

### 5.3 Demo Script

```powershell
python backend/strategies/seismograph.py
```

---

## 6. 의존성

추가 필요 없음 (기존 `collections.deque` 활용)

---

## 7. 다음 단계

- **Step 2.4.7 (Dashboard 통합)**: ChartWidget을 Dashboard center panel에 통합
- **Step 3.1**: Order Management System (OMS)

---

## 8. Step 2.4: Core Indicators & Chart Integration

> **추가일**: 2025-12-18

### 8.1 목표
TechnicalAnalysis 모듈 및 TradingView Chart를 Dashboard에 통합

### 8.2 구현 단계

| Step | 설명 | 상태 |
|------|------|------|
| 2.4.1 | TechnicalAnalysis 모듈 (VWAP, ATR, MA, RSI) | ✅ |
| 2.4.2 | DynamicStopLoss 클래스 | ✅ |
| 2.4.3 | Signal에 indicators/sl_tp 메타데이터 추가 | ✅ |
| 2.4.4 | ChartWidget (TradingView Lightweight Charts) | ✅ |
| 2.4.5 | VWAP/ATR 라인 렌더링 | ✅ |
| 2.4.6 | Trade Markers (BUY/SELL/Ignition) | ✅ |
| 2.4.7 | Dashboard center panel에 ChartWidget 통합 | 🔄 |
| 2.4.8 | 시작 시 샘플 데이터 로드 | ⏳ |
| 2.4.9 | 완전한 GUI 검증 | ⏳ |

