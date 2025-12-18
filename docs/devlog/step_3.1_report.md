# Step 3.1 Report: Order Management System (OMS)

**날짜**: 2025-12-18  
**작업자**: Antigravity Agent

---

## 📋 개요

Step 3.1에서는 IBKR 주문 배치 및 Server-Side OCA 그룹을 구현했습니다.

---

## ✅ 완료 항목

### 3.1.1: IBKRConnector 주문 메서드

**파일**: `backend/broker/ibkr_connector.py`

| 메서드 | 설명 |
|--------|------|
| `place_market_order()` | 시장가 주문 |
| `place_stop_order()` | Stop Loss 주문 |
| `place_oca_group()` | OCA 그룹 (Stop + Limit) |
| `cancel_order()` | 개별 취소 |
| `cancel_all_orders()` | 전체 취소 |
| `get_positions()` | 포지션 조회 |
| `get_open_orders()` | 미체결 조회 |

**추가 Signals:**
- `order_placed`, `order_filled`, `order_cancelled`
- `order_error`, `positions_update`

### 3.1.2: OCA 그룹

masterplan 5.1절 기준 구현:
- Stop Loss: entry × (1 - 2%)
- Profit Target: entry × (1 + 8%)
- `ocaType=1` (Cancel on Fill)

### 3.1.3: OrderManager

**파일**: `backend/core/order_manager.py`

| 클래스 | 설명 |
|--------|------|
| `OrderStatus` | Enum (Pending, Filled, Cancelled 등) |
| `OrderType` | Enum (MKT, LMT, STP 등) |
| `OrderRecord` | 주문 기록 데이터클래스 |
| `Position` | 포지션 정보 |
| `OrderManager` | 주문 상태 관리 |

---

## 🧪 테스트 결과

**파일**: `tests/test_order_manager.py`

```
================== 18 passed, 1 warning in 0.21s ===================
```

| 테스트 클래스 | 테스트 수 |
|--------------|----------|
| `TestOrderRecord` | 2 |
| `TestOrderStatus` | 1 |
| `TestPosition` | 4 |
| `TestOrderManager` | 9 |
| `TestIBKRConnectorOrderMethods` | 2 |

---

## 📁 생성/수정된 파일

| 파일 | 변경 |
|------|------|
| `backend/broker/ibkr_connector.py` | 주문 메서드 추가 (+370 lines) |
| `backend/core/order_manager.py` | 신규 생성 |
| `tests/test_order_manager.py` | 신규 생성 |
| `docs/Plan/steps/step_3.1_plan.md` | 계획 문서 |

---

## 🔜 다음 단계

- **Step 3.2**: Risk Manager & Position Sizing
