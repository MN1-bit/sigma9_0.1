# IBKR 주문 시스템 완성 및 Trailing Stop 네이티브 마이그레이션

> **상태**: ✅ 완료
> **작성일**: 2026-01-10
> **우선순위**: 높음

---

## 1. 목표

IBKR 주문 시스템을 완성하여:

1. **Trailing Stop**: 클라이언트 사이드 → IBKR 네이티브로 마이그레이션
2. **전체 주문 타입 구현**: 미구현 주문 타입 추가
3. 이후 100ms 배칭 리팩터링 안전하게 진행 가능

---

## 2. 현재 구현 상태

| 주문 타입 | 메서드 | 상태 |
|----------|-------|------|
| MKT (시장가) | `place_market_order()` | ✅ 구현됨 |
| STP (스탑) | `place_stop_order()` | ✅ 구현됨 |
| LMT + STP OCA | `place_oca_group()` | ✅ 구현됨 |
| **LMT (지정가)** | - | ❌ 미구현 |
| **STP LMT (스탑 리밋)** | - | ❌ 미구현 |
| **TRAIL (트레일링)** | - | ❌ 미구현 (잘못된 구현 있음) |
| **TRAIL LIMIT** | - | ❌ 미구현 |
| **MOC (종가 시장가)** | - | ❌ 미구현 |
| **LOC (종가 지정가)** | - | ❌ 미구현 |
| **Bracket (브라켓)** | - | ❌ 미구현 (ib_insync 네이티브) |

---

## 3. 제안 솔루션

### 3.1 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `backend/broker/ibkr_connector.py` | 6개 주문 메서드 추가 |
| `backend/core/trailing_stop.py` | `on_price_update()` 제거, 네이티브 사용 |
| `backend/startup/realtime.py` | `trailing_stop` 틱 핸들러 등록 제거 |

---

## 4. 실행 단계

### Step 1: Limit Order 추가

```python
def place_limit_order(
    self,
    symbol: str,
    qty: int,
    limit_price: float,
    action: str = "BUY",
    tif: str = "DAY",  # Time In Force: DAY, GTC, IOC, FOK
    oca_group: Optional[str] = None,
) -> Optional[int]:
    """
    지정가 주문 배치
    
    Args:
        symbol: 종목 심볼
        qty: 수량
        limit_price: 지정가
        action: "BUY" 또는 "SELL"
        tif: 유효 기간 (DAY, GTC, IOC, FOK)
        oca_group: OCA 그룹 ID (선택)
    """
    contract = Stock(symbol, "SMART", "USD")
    order = LimitOrder(action, qty, limit_price)
    order.tif = tif
    if oca_group:
        order.ocaGroup = oca_group
        order.ocaType = 1
    # ... (기존 패턴과 동일)
```

### Step 2: Stop Limit Order 추가

```python
def place_stop_limit_order(
    self,
    symbol: str,
    qty: int,
    stop_price: float,
    limit_price: float,
    action: str = "SELL",
    oca_group: Optional[str] = None,
) -> Optional[int]:
    """
    Stop Limit 주문 배치
    
    Stop 가격 도달 시 Limit 주문으로 전환됨.
    슬리피지 방지에 유용.
    """
    contract = Stock(symbol, "SMART", "USD")
    order = Order()
    order.action = action
    order.totalQuantity = qty
    order.orderType = "STP LMT"
    order.auxPrice = stop_price      # Stop 가격
    order.lmtPrice = limit_price     # Limit 가격
    # ...
```

### Step 3: Trailing Stop Order 추가

```python
def place_trailing_stop_order(
    self,
    symbol: str,
    qty: int,
    trail_amount: float,  # 달러 단위 (예: ATR × 1.5)
    action: str = "SELL",
    oca_group: Optional[str] = None,
) -> Optional[int]:
    """
    IBKR 네이티브 Trailing Stop 주문 배치
    
    서버 사이드에서 자동으로 고점 추적.
    """
    contract = Stock(symbol, "SMART", "USD")
    order = Order()
    order.action = action
    order.totalQuantity = qty
    order.orderType = "TRAIL"
    order.auxPrice = trail_amount
    # ...
```

### Step 4: Trailing Stop Limit Order 추가

```python
def place_trailing_stop_limit_order(
    self,
    symbol: str,
    qty: int,
    trail_amount: float,
    limit_offset: float,  # Stop 트리거 후 Limit 오프셋
    action: str = "SELL",
) -> Optional[int]:
    """
    Trailing Stop Limit 주문 배치
    
    Trailing Stop이 트리거되면 Limit 주문으로 전환.
    """
    order = Order()
    order.action = action
    order.totalQuantity = qty
    order.orderType = "TRAIL LIMIT"
    order.auxPrice = trail_amount
    order.lmtPrice = 0  # 트리거 시 계산됨
    order.trailStopPrice = trail_amount
    # ...
```

### Step 5: MOC / LOC 주문 추가

```python
def place_moc_order(
    self,
    symbol: str,
    qty: int,
    action: str = "SELL",
) -> Optional[int]:
    """
    Market-on-Close 주문 배치
    
    장 마감 시 시장가로 체결.
    EOD 청산에 유용.
    """
    order = Order()
    order.action = action
    order.totalQuantity = qty
    order.orderType = "MOC"
    # ...

def place_loc_order(
    self,
    symbol: str,
    qty: int,
    limit_price: float,
    action: str = "SELL",
) -> Optional[int]:
    """
    Limit-on-Close 주문 배치
    
    장 마감 시 지정가 이상/이하로만 체결.
    """
    order = Order()
    order.action = action
    order.totalQuantity = qty
    order.orderType = "LOC"
    order.lmtPrice = limit_price
    # ...
```

### Step 6: ib_insync 네이티브 Bracket Order

```python
def place_bracket_order(
    self,
    symbol: str,
    qty: int,
    entry_price: float,
    take_profit_price: float,
    stop_loss_price: float,
    action: str = "BUY",
) -> Optional[Tuple[int, int, int]]:
    """
    ib_insync 네이티브 Bracket 주문 배치
    
    3개 주문이 연결됨: Parent + Take Profit + Stop Loss
    Parent 체결 시 자식 주문 활성화.
    
    Returns:
        Tuple[parent_id, tp_id, sl_id] 또는 None
    """
    contract = Stock(symbol, "SMART", "USD")
    
    # ib_insync 네이티브 bracketOrder 사용
    bracket = self.ib.bracketOrder(
        action=action,
        quantity=qty,
        limitPrice=entry_price,
        takeProfitPrice=take_profit_price,
        stopLossPrice=stop_loss_price,
    )
    
    order_ids = []
    for order in bracket:
        trade = self.ib.placeOrder(contract, order)
        order_ids.append(trade.order.orderId)
        self._active_orders[trade.order.orderId] = trade
        # 콜백 등록...
    
    return tuple(order_ids)
```

### Step 7: TrailingStopManager 단순화

```diff
# backend/core/trailing_stop.py

- def on_price_update(self, symbol: str, current_price: float):
-     # 클라이언트 사이드 고점 추적 로직 (200줄 삭제)
-     ...

+ def create_trailing(self, symbol, qty, atr) -> Optional[int]:
+     """IBKR 네이티브 Trailing Stop 주문 전송"""
+     trail_amount = atr * self.atr_multiplier
+     return self.connector.place_trailing_stop_order(
+         symbol=symbol,
+         qty=qty,
+         trail_amount=trail_amount,
+     )
```

### Step 8: realtime.py에서 틱 핸들러 제거

```diff
# backend/startup/realtime.py

- result.tick_dispatcher.register("trailing_stop", trailing_tick_handler)
+ # TrailingStopManager는 IBKR 네이티브 주문 사용 (틱 폴링 불필요)
```

---

## 5. 최종 주문 시스템 구조

```
IBKRConnector
├── place_market_order()      # MKT
├── place_limit_order()       # LMT (신규)
├── place_stop_order()        # STP
├── place_stop_limit_order()  # STP LMT (신규)
├── place_trailing_stop_order()       # TRAIL (신규)
├── place_trailing_stop_limit_order() # TRAIL LIMIT (신규)
├── place_moc_order()         # MOC (신규)
├── place_loc_order()         # LOC (신규)
├── place_bracket_order()     # Bracket (신규, ib_insync 네이티브)
├── place_oca_group()         # 기존 OCA (호환성 유지)
├── cancel_order()
├── cancel_all_orders()
├── get_positions()
└── get_open_orders()
```

---

## 6. 검증 계획

### 6.1 단위 테스트

```bash
python -m pytest tests/test_ibkr_orders.py -v
```

테스트 케이스:
1. 각 주문 타입별 Order 객체 생성 확인
2. `orderType` 필드 검증
3. OCA 그룹 연결 검증

### 6.2 수동 검증 (Paper Trading)

> [!IMPORTANT]
> IBKR Paper Trading 계정 필요 (포트 4002)

1. 각 주문 타입 수동 테스트
2. TWS에서 주문 타입 확인
3. 체결/취소 콜백 검증

---

## 7. 예상 결과

| 항목 | 수정 전 | 수정 후 |
|------|--------|--------|
| 지원 주문 타입 | 3개 | **11개** |
| Trailing Stop 틱 콜백 | 매 틱 | 없음 (서버 사이드) |
| 100ms 배칭 영향 | 주의 필요 | 영향 없음 |

---

## 8. 관련 문서

- [ib_insync Order 문서](https://ib-insync.readthedocs.io/api.html#order)
- [IBKR Available Orders](https://interactivebrokers.github.io/tws-api/available_orders.html)
- [IBKR Bracket Orders](https://interactivebrokers.github.io/tws-api/bracket_order.html)
