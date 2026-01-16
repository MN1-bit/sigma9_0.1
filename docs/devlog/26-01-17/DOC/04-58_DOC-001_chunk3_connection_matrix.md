# [DOC-001] Chunk 3: 연결 관계 매트릭스 Devlog

> **작성일**: 2026-01-17 04:58
> **계획서**: [DOC-001](../../Plan/26-01-17/04-31_DOC-001_full_architecture_document.md)

## 진행 현황

| Chunk | 상태 | 완료 시간 |
|-------|------|----------|
| Chunk 1 | ✅ 완료 | 04:42 |
| Chunk 2A | ✅ 완료 | 04:50 |
| Chunk 2B | ✅ 완료 | 04:55 |
| Chunk 3 | ✅ 완료 | 05:02 |

---

## 상속 관계 (Inheritance)

### ABC → 구현체

| 추상 클래스 | 위치 | 구현체 |
|------------|------|--------|
| `StrategyBase (ABC)` | `backend/core/strategy_base.py` | SeismographStrategy |
| `ScoringStrategy (ABC)` | `backend/core/interfaces/scoring.py` | SeismographStrategy |

### Enum 클래스

| Enum | 위치 | 용도 |
|------|------|------|
| `TrailingStatus` | `trailing_stop.py` | Trailing Stop 상태 |
| `OrderStatus` | `order_manager.py` | 주문 상태 |
| `OrderType` | `order_manager.py` | 주문 유형 |
| `DoubleTapState` | `double_tap.py` | Double Tap 상태 |
| `ConnectionState` | `backend_client.py` | 연결 상태 |

---

## DI Container 의존성 매트릭스

### Data Layer → 의존성

| Provider | 의존 대상 |
|----------|----------|
| `data_repository` | parquet_manager, massive_client |
| `ticker_info_service` | massive_client |
| `database` | config.db_path |

### Core Layer → 의존성

| Provider | 의존 대상 |
|----------|----------|
| `realtime_scanner` | massive_client, ws_manager, data_repository, scoring_strategy |
| `ignition_monitor` | scoring_strategy, ws_manager |
| `subscription_manager` | massive_ws |
| `tick_broadcaster` | massive_ws, ws_manager, tick_dispatcher |

### Broker Layer → 의존성 (Chain)

```
IBKRConnector (루트)
    ↓
order_manager ← ibkr_connector
risk_manager ← ibkr_connector
    ↓
trailing_stop_manager ← ibkr_connector
    ↓
double_tap_manager ← ibkr_connector, order_manager, trailing_stop_manager
```

---

## 컴포지션 관계 (has-a)

### Frontend

| 컨테이너 | 포함 컴포넌트 |
|----------|-------------|
| `Sigma9Dashboard` | ControlPanel, WatchlistPanel, ChartPanel, PositionPanel, OraclePanel, LogPanel |
| `BackendClient` | RestAdapter, WsAdapter |
| `ChartPanel` | FinplotChartWidget |
| `ControlPanel` | TickerSearchBar, TimeDisplayWidget |

### Backend

| 컨테이너 | 포함 컴포넌트 |
|----------|-------------|
| `DataRepository` | ParquetManager, MassiveClient |
| `DoubleTapManager` | IBKRConnector, OrderManager, TrailingStopManager |

---

## 기존 다이어그램 참조

- **Full_DataFlow_Diagram.md Section 7**: DI Container 의존성 그래프 (Mermaid)
- **Full_DataFlow_Diagram.md Section 8**: GUI 컴포넌트 계층 구조 (Mermaid)

→ Chunk 5B에서 클래스 다이어그램 추가 예정

---

## 다음 단계

→ **Chunk 4**: 통합/단순화 기회 식별
