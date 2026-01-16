# test_order_manager.py

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `tests/test_order_manager.py` |
| **역할** | OrderManager, OrderRecord, Position 단위 테스트 |
| **라인 수** | 334 |

## 테스트 클래스

### `TestOrderRecord`
> OrderRecord 데이터클래스 테스트

| 테스트 | 설명 |
|--------|------|
| `test_order_record_creation` | 생성 테스트 |
| `test_order_record_to_dict` | to_dict() 직렬화 테스트 |

### `TestOrderStatus`
> OrderStatus Enum 테스트

| 테스트 | 설명 |
|--------|------|
| `test_order_statuses` | 모든 상태 존재 확인 |

### `TestPosition`
> Position 데이터클래스 테스트

| 테스트 | 설명 |
|--------|------|
| `test_position_creation` | 생성 테스트 |
| `test_market_value` | 시장가치 계산 (qty × current_price) |
| `test_pnl_pct` | 손익률 계산 (+%) |
| `test_pnl_pct_negative` | 손실률 계산 (-%) |

### `TestOrderManager`
> OrderManager 클래스 테스트

| 테스트 | 설명 |
|--------|------|
| `test_manager_initialization` | 초기화 테스트 |
| `test_execute_entry` | 진입 주문 실행 |
| `test_execute_oca_exit` | OCA 청산 그룹 배치 |
| `test_get_order` | 주문 조회 |
| `test_get_pending_orders` | 미체결 주문 목록 |
| `test_cancel_order` | 주문 취소 |
| `test_on_order_filled_callback` | 체결 콜백 |

### `TestIBKRConnectorOrderMethods`
> IBKRConnector 주문 메서드 Import 확인

| 테스트 | 설명 |
|--------|------|
| `test_import_ibkr_connector` | Signal 존재 확인 |
| `test_order_methods_exist` | 주문 메서드 존재 확인 |

## 🔗 외부 연결 (Connections)

### Tests (테스트 대상)
| 파일 | 테스트 항목 |
|------|------------|
| `backend/core/order_manager.py` | `OrderManager`, `OrderRecord`, `Position` |
| `backend/broker/ibkr_connector.py` | Signal 및 메서드 존재 확인 |

## 외부 의존성
- `pytest`
- `unittest.mock`
