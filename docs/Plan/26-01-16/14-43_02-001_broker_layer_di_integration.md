# Broker Layer DI Container 통합 구현 계획서

> **작성일**: 2026-01-16 16:15 | **예상**: 2h

---

## 1. 목표

DI Container 외부에서 수동 인스턴스화되는 **Broker Layer 5개 컴포넌트**를 `container.py`에 등록:

| 컴포넌트 | 파일 | 현재 상태 |
|---------|------|----------|
| `IBKRConnector` | `backend/broker/ibkr_connector.py` | Container 외부 |
| `OrderManager` | `backend/core/order_manager.py` | 수동 주입 |
| `RiskManager` | `backend/core/risk_manager.py` | 수동 주입 |
| `TrailingStopManager` | `backend/core/trailing_stop.py` | 수동 주입 |
| `DoubleTapManager` | `backend/core/double_tap.py` | 수동 주입 |

**효과**: 테스트 Mock 주입 용이, 생명주기 중앙 관리, 의존성 명시화

---

## 2. 레이어 체크

- [x] 레이어 규칙 위반 없음 (broker → core 순방향만 사용)
- [x] 순환 의존성 없음 (단방향 체인: IBKRConnector → OrderManager → DoubleTapManager)
- [x] DI Container 등록 필요: **예** (5개 Provider 추가)

### 의존성 방향 확인

```
backend.api
    ↓
backend.core (OrderManager, RiskManager, TrailingStop, DoubleTap)
    ↓
backend.broker (IBKRConnector)
```

✅ Container에서 `broker → core` 순서로 의존성 주입 → 역방향 import 없음

---

## 3. 변경 파일

| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
| `backend/container.py` | 수정 | +60줄 |
| `docs/_architecture/Full_DataFlow_Diagram.md` | 수정 | Section 7 업데이트 |

---

## 4. 기존 솔루션 검색 결과

| 솔루션 | 출처 | 채택 여부 | 사유 |
|--------|------|----------|------|
| `dependency-injector` Singleton | 기존 container.py | ✅ 채택 | 프로젝트 표준 |
| 지연 import 패턴 | 기존 container.py | ✅ 채택 | 순환 참조 방지 |

---

## 5. 실행 단계

### Step 1: container.py Broker Layer 추가

```python
# ═══════════════════════════════════════════════════════════════════════════
# Broker Layer
# ═══════════════════════════════════════════════════════════════════════════

@staticmethod
def _create_ibkr_connector():
    from backend.broker.ibkr_connector import IBKRConnector
    return IBKRConnector()

ibkr_connector = providers.Singleton(_create_ibkr_connector)

@staticmethod
def _create_order_manager(connector):
    from backend.core.order_manager import OrderManager
    return OrderManager(connector=connector)

order_manager = providers.Singleton(_create_order_manager, connector=ibkr_connector)

@staticmethod
def _create_risk_manager(connector):
    from backend.core.risk_manager import RiskManager
    return RiskManager(connector=connector)

risk_manager = providers.Singleton(_create_risk_manager, connector=ibkr_connector)

@staticmethod
def _create_trailing_stop_manager(connector):
    from backend.core.trailing_stop import TrailingStopManager
    return TrailingStopManager(connector=connector)

trailing_stop_manager = providers.Singleton(_create_trailing_stop_manager, connector=ibkr_connector)

@staticmethod
def _create_double_tap_manager(connector, order_manager, trailing_manager):
    from backend.core.double_tap import DoubleTapManager
    return DoubleTapManager(
        connector=connector,
        order_manager=order_manager,
        trailing_manager=trailing_manager,
    )

double_tap_manager = providers.Singleton(
    _create_double_tap_manager,
    connector=ibkr_connector,
    order_manager=order_manager,
    trailing_manager=trailing_stop_manager,
)
```

### Step 2: Full_DataFlow_Diagram.md Section 7 업데이트

- Broker Layer `⚠️ Container 외부` 라벨 제거
- 정상 Container 내 노드로 표시

---

## 6. 검증

- [ ] `lint-imports` 통과
- [ ] `pydeps backend --show-cycles --no-output` 순환 없음
- [ ] `pytest tests/test_ibkr_connector.py tests/test_order_manager.py tests/test_double_tap.py -v` PASS
- [ ] Container 수동 테스트:
  ```bash
  python -c "from backend.container import container; print(container.ibkr_connector())"
  ```

---

## 7. 롤백 계획

`container.py`의 Broker Layer 섹션 삭제 → 기존 수동 인스턴스화 유지

---

## ✅ 승인 대기

> **다음**: 승인 후 `/IMP-execution`
