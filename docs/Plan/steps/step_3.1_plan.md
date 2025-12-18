# Step 3.1: Order Management System (OMS) 구현 계획

> **작성일**: 2025-12-18  
> **Phase**: 3 (Execution & Management)  
> **목표**: IBKR 주문 배치 및 Server-Side OCA 그룹 구현

---

## 1. 배경 및 목적

`masterplan.md` Section 5.1에 정의된 **Server-Side OCA Group**을 구현합니다.

- **OCA (One-Cancels-All)**: 진입 즉시 3개 주문을 묶어 전송
- **자동 청산**: Stop Loss, Time Stop, Trailing Stop 중 하나 발동 시 나머지 취소
- **GUI 연동**: 주문 상태를 실시간으로 화면에 반영

---

## 2. 현재 상태 분석

| 파일 | 상태 | 비고 |
|------|------|------|
| `ibkr_connector.py` | ⚠️ 부분 구현 | 연결 + 시세 구독만 있음 |
| `strategy_base.py` | ✅ 완료 | Signal 데이터 반환 가능 |
| `seismograph.py` | ✅ 완료 | BUY Signal 생성 가능 |
| `order_manager.py` | ❌ 미구현 | **이번 단계에서 구현** |

---

## 3. Proposed Changes

### 3.1 Backend Broker

#### [MODIFY] [ibkr_connector.py](file:///d:/Codes/Sigma9-0.1/backend/broker/ibkr_connector.py)

주문 관련 메서드 및 Signal 추가:

| Method | Description |
|--------|-------------|
| `place_market_order(symbol, qty, action)` | 시장가 주문 배치 |
| `place_stop_order(symbol, qty, stop_price)` | Stop Loss 주문 |
| `place_trailing_stop(symbol, qty, trail_amt)` | Trailing Stop 주문 |
| `place_oca_group(symbol, qty, entry_price)` | OCA 그룹 (3개 주문 묶음) |
| `cancel_order(order_id)` | 개별 주문 취소 |
| `cancel_all_orders()` | 모든 주문 취소 |
| `get_open_orders()` | 미체결 주문 조회 |
| `get_positions()` | 현재 포지션 조회 |

**OCA 그룹 구성 (masterplan 5.1):**

| Order | Type | Condition |
|-------|------|-----------|
| Safety Stop | Stop Loss @ -2.0% | 매집 실패 시 즉시 손절 |
| Time Stop | GTD 3분 후 시장가 | 미발화 시 탈출 |
| Profit Harvester | TRAIL (ATR×1.5) | +3% 도달 시 활성화 |

**추가 PyQt Signals:**

| Signal | Parameters | Description |
|--------|------------|-------------|
| `order_placed` | `dict` | 주문 접수됨 |
| `order_filled` | `dict` | 주문 체결됨 |
| `order_cancelled` | `dict` | 주문 취소됨 |
| `order_error` | `str, str` | 주문 오류 (order_id, message) |
| `positions_update` | `list` | 포지션 목록 변경 |

---

### 3.2 Backend Core

#### [NEW] [order_manager.py](file:///d:/Codes/Sigma9-0.1/backend/core/order_manager.py)

주문 상태 관리 클래스:

```
OrderManager
├── __init__(connector: IBKRConnector)
│
├── execute_entry(signal: Signal) → str
│   └── Signal 기반 진입 주문 실행 → order_id 반환
│
├── execute_oca_exit(order_id, entry_price) → List[str]
│   └── OCA 그룹 주문 배치 → order_ids 반환
│
├── track_order(order_id) → OrderStatus
│   └── 주문 상태 조회 (Pending, PartialFill, Filled, Cancelled)
│
├── on_fill(trade) → None
│   └── 체결 콜백 - 포지션/P&L 업데이트
│
└── get_active_positions() → List[Position]
    └── 활성 포지션 목록 반환
```

**OrderStatus Enum:**
- `PENDING`: 미체결 대기
- `PARTIAL_FILL`: 부분 체결
- `FILLED`: 전량 체결
- `CANCELLED`: 취소됨
- `ERROR`: 오류

---

### 3.3 Tests

#### [NEW] [test_order_manager.py](file:///d:/Codes/Sigma9-0.1/tests/test_order_manager.py)

Mock IBKR를 사용한 유닛 테스트:

| 테스트 | 검증 내용 |
|--------|----------|
| `test_place_market_order` | 시장가 주문 배치 확인 |
| `test_place_oca_group` | OCA 그룹 3개 주문 생성 확인 |
| `test_cancel_order` | 주문 취소 확인 |
| `test_order_status_tracking` | 상태 변경 추적 확인 |
| `test_on_fill_callback` | 체결 콜백 처리 확인 |

---

## 4. Verification Plan

### 4.1 Syntax Check

```powershell
cd d:\Codes\Sigma9-0.1
python -m py_compile backend/broker/ibkr_connector.py
python -m py_compile backend/core/order_manager.py
```

### 4.2 Unit Tests

```powershell
cd d:\Codes\Sigma9-0.1
pytest tests/test_order_manager.py -v
```

### 4.3 Integration Test (Paper Trading)

> ⚠️ **주의**: 실거래 전 반드시 Paper Trading에서 검증

1. TWS Paper Trading 연결 (포트 4002)
2. 단일 시장가 주문 테스트
3. OCA 그룹 배치 테스트
4. Stop Loss 트리거 확인
5. GUI에서 주문 상태 반영 확인

---

## 5. 핵심 코드 스니펫

### ib_insync OCA 그룹 예시

```python
from ib_insync import IB, Stock, MarketOrder, StopOrder

# OCA 그룹 ID 생성
oca_group = f"OCA_{symbol}_{int(time.time())}"

# 3개 주문 생성 (같은 ocaGroup, ocaType=1)
orders = [
    MarketOrder("SELL", qty, ocaGroup=oca_group, ocaType=1, tif="GTC"),
    StopOrder("SELL", qty, stop_price, ocaGroup=oca_group, ocaType=1),
    # Trailing Stop은 별도 API 사용
]

# 주문 배치
for order in orders:
    trade = ib.placeOrder(contract, order)
```

---

## 6. 의존성

추가 설치 필요 없음 (기존 `ib_insync` 사용)

---

## 7. 다음 단계

- **Step 3.2**: Risk Manager & Position Sizing
- **Step 3.3**: Double Tap & Harvest
