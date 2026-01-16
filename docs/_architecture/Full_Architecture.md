# Sigma9 통합 아키텍처 문서

> **Version**: 1.0  
> **생성일**: 2026-01-17  
> **목적**: 전체 시스템 아키텍처, 클래스 구조, Data Flow 통합 문서

---

## 목차

1. [시스템 개요](#1-시스템-개요)
2. [DI Container 서비스 인벤토리](#2-di-container-서비스-인벤토리)
3. [Backend 클래스 도표](#3-backend-클래스-도표)
4. [Frontend 클래스 도표](#4-frontend-클래스-도표)
5. [연결 관계 매트릭스](#5-연결-관계-매트릭스)
6. [Data Flow 통합](#6-data-flow-통합)
7. [통합/단순화 기회](#7-통합단순화-기회)
8. [Mermaid 다이어그램](#8-mermaid-다이어그램)

---

## 1. 시스템 개요

### 1.1 아키텍처 계층

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (PyQt6)                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Sigma9Dashboard (5-Panel)              │    │
│  │  ┌─────────┬──────────────┬───────────────────────┐ │    │
│  │  │Watchlist│    Chart     │ Positions + Oracle   │ │    │
│  │  └─────────┴──────────────┴───────────────────────┘ │    │
│  │                    LogPanel                         │    │
│  └─────────────────────────────────────────────────────┘    │
│                         ↓↑                                   │
│               BackendClient (REST/WS)                       │
└─────────────────────────────────────────────────────────────┘
                          ↓↑
┌─────────────────────────────────────────────────────────────┐
│                  Backend (FastAPI)                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              DI Container (24 services)             │    │
│  │  ┌────────┬──────────┬────────────┬───────────────┐ │    │
│  │  │  Data  │ Strategy │    Core    │    Broker    │ │    │
│  │  │   6    │    5     │     8      │      5       │ │    │
│  │  └────────┴──────────┴────────────┴───────────────┘ │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          ↓↑
┌─────────────────────────────────────────────────────────────┐
│                   External Services                          │
│  ┌──────────────┬──────────────┬──────────────────────┐     │
│  │ Massive API  │ Massive WS   │   IB Gateway/TWS     │     │
│  │  (REST)      │ (WebSocket)  │    (ib_insync)       │     │
│  └──────────────┴──────────────┴──────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 통계

| 영역 | 파일 수 | 클래스 수 |
|------|---------|----------|
| Backend | 98 | ~50 |
| Frontend | 35 | ~25 |
| DI Services | - | 24 |
| **총계** | 133 | ~75 |

---

## 2. DI Container 서비스 인벤토리

### 2.1 Data Layer (6개)

| Provider | 클래스 | 유형 | 의존성 |
|----------|--------|------|--------|
| `massive_client` | MassiveClient | Singleton | - |
| `massive_ws` | MassiveWebSocketClient | Singleton | - |
| `parquet_manager` | ParquetManager | Singleton | - |
| `data_repository` | DataRepository | Singleton | parquet_manager, massive_client |
| `database` | MarketDB | Singleton | config.db_path |
| `watchlist_store` | WatchlistStore | Singleton | - |

### 2.2 Strategy Layer (5개)

| Provider | 클래스 | 유형 | 의존성 |
|----------|--------|------|--------|
| `ticker_info_service` | TickerInfoService | Singleton | - |
| `symbol_mapper` | SymbolMapper | Singleton | - |
| `scoring_strategy` | SeismographStrategy | Singleton | - |
| `trading_context` | TradingContext | Singleton | - |
| `config` | Configuration | Config | - |

### 2.3 Core Layer (8개)

| Provider | 클래스 | 유형 | 의존성 |
|----------|--------|------|--------|
| `ws_manager` | Object(None) | Object | 외부 주입 |
| `tick_dispatcher` | TickDispatcher | Singleton | - |
| `subscription_manager` | SubscriptionManager | Singleton | massive_ws |
| `tick_broadcaster` | TickBroadcaster | Callable | massive_ws, ws_manager, tick_dispatcher |
| `realtime_scanner` | RealtimeScanner | Singleton | massive_client, ws_manager, data_repository, scoring_strategy |
| `ignition_monitor` | IgnitionMonitor | Singleton | strategy, ws_manager |
| `audit_logger` | AuditLogger | Singleton | - |
| `event_deduplicator` | EventDeduplicator | Factory | - |

### 2.4 Broker Layer (5개)

| Provider | 클래스 | 유형 | 의존성 |
|----------|--------|------|--------|
| `ibkr_connector` | IBKRConnector | Singleton | - |
| `order_manager` | OrderManager | Singleton | ibkr_connector |
| `risk_manager` | RiskManager | Singleton | ibkr_connector |
| `trailing_stop_manager` | TrailingStopManager | Singleton | ibkr_connector |
| `double_tap_manager` | DoubleTapManager | Singleton | ibkr_connector, order_manager, trailing_stop_manager |

---

## 3. Backend 클래스 도표

### 3.1 backend/core/ 주요 클래스

| 파일 | 클래스 | 역할 |
|------|--------|------|
| `realtime_scanner.py` | RealtimeScanner | 1초 폴링 Gainers API 스캔 |
| `ignition_monitor.py` | IgnitionMonitor | Trigger Score 모니터링 |
| `scanner.py` | Scanner | Pre-market 일괄 스캔 |
| `scheduler.py` | TradingScheduler | APScheduler 기반 자동 실행 |
| `tick_broadcaster.py` | TickBroadcaster | Massive → GUI WebSocket 브릿지 |
| `tick_dispatcher.py` | TickDispatcher | 내부 컴포넌트 틱 배포 |
| `order_manager.py` | OrderManager | 주문 실행/추적 |
| `risk_manager.py` | RiskManager | Kelly 포지션 사이징, Kill Switch |
| `trailing_stop.py` | TrailingStopManager | Trailing Stop 주문 |
| `double_tap.py` | DoubleTapManager | 1차 청산 후 재진입 |
| `trading_context.py` | TradingContext | 활성 티커 상태 관리 |
| `backtest_engine.py` | BacktestEngine | 백테스트 엔진 |
| `strategy_base.py` | StrategyBase | 전략 ABC |

### 3.2 backend/data/ 주요 클래스

| 파일 | 클래스 | 역할 |
|------|--------|------|
| `data_repository.py` | DataRepository | 통합 데이터 접근 레이어 |
| `parquet_manager.py` | ParquetManager | Parquet I/O |
| `database.py` | MarketDB | SQLite 데이터베이스 |
| `massive_client.py` | MassiveClient | REST API 클라이언트 |
| `massive_ws_client.py` | MassiveWebSocketClient | WebSocket 클라이언트 |
| `ticker_info_service.py` | TickerInfoService | 티커 종합 정보 |
| `symbol_mapper.py` | SymbolMapper | Massive ↔ IBKR 심볼 매핑 |

---

## 4. Frontend 클래스 도표

### 4.1 GUI Layer

| 파일 | 클래스 | 역할 |
|------|--------|------|
| `dashboard.py` | Sigma9Dashboard | 메인 5-Panel 대시보드 |
| `control_panel.py` | ControlPanel | TOP 컨트롤 패널 |
| `theme.py` | ThemeManager | 테마 관리 |
| `panels/watchlist_panel.py` | WatchlistPanel | Tier1 Watchlist |
| `panels/tier2_panel.py` | Tier2Panel | Tier2 Hot Zone |
| `panels/chart_panel.py` | ChartPanel | 차트 영역 |
| `panels/position_panel.py` | PositionPanel | 포지션 P&L |
| `panels/oracle_panel.py` | OraclePanel | LLM Oracle |
| `panels/log_panel.py` | LogPanel | 로그 콘솔 |

### 4.2 Services Layer

| 파일 | 클래스 | 역할 |
|------|--------|------|
| `backend_client.py` | BackendClient | HTTP/WS 통합 클라이언트 |
| `rest_adapter.py` | RestAdapter | REST API 어댑터 |
| `ws_adapter.py` | WsAdapter | WebSocket 어댑터 |
| `chart_data_service.py` | ChartDataService | 차트 데이터 서비스 |

---

## 5. 연결 관계 매트릭스

### 5.1 상속 관계

| 추상 클래스 | 구현체 |
|------------|--------|
| `StrategyBase (ABC)` | SeismographStrategy |
| `ScoringStrategy (ABC)` | SeismographStrategy |

### 5.2 Broker Layer 의존성 체인

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

### 5.3 컴포지션 관계

| 컨테이너 | 포함 컴포넌트 |
|----------|-------------|
| `Sigma9Dashboard` | ControlPanel, WatchlistPanel, ChartPanel, PositionPanel, OraclePanel, LogPanel |
| `BackendClient` | RestAdapter, WsAdapter |
| `DataRepository` | ParquetManager, MassiveClient |

---

## 6. Data Flow 통합

> **참조**: [Full_DataFlow.md](./Full_DataFlow.md) - 84개 Data Flow 상세

### 6.1 핵심 Data Flow 패턴

**패턴 1: 데이터 수집**
```
Massive API → MassiveClient → DataRepository → ParquetManager → Parquet Files
```

**패턴 2: 실시간 스캔**
```
Massive Gainers API → RealtimeScanner → ScoringStrategy → WebSocket → GUI
```

**패턴 3: Tick 배포**
```
MassiveWebSocketClient → TickBroadcaster → TickDispatcher → (Strategy, TrailingStop, DoubleTap)
```

**패턴 4: 주문 실행**
```
Signal → OrderManager → IBKRConnector → IB Gateway
```

---

## 7. 통합/단순화 기회

### 7.1 식별된 패턴

| 패턴 | 컴포넌트 | 현황 |
|------|----------|------|
| Polling (1초) | RealtimeScanner, IgnitionMonitor | 개별 유지 |
| Tick Distribution | TickBroadcaster, TickDispatcher | 역할 분리 유지 |
| Order Execution | OrderManager, RiskManager | 현재 구조 적절 |

### 7.2 Deferred 통합 후보

| 후보 | 제안 | 결정 |
|------|------|------|
| 폴링 레이어 통합 | RealtimeScanner + IgnitionMonitor 공통 폴링 | ⏳ Deferred |
| BackendClient DI | Singleton → Container | ⏳ Deferred |

---

## 8. Mermaid 다이어그램

> **참조**: [Full_DataFlow_Diagram.md](./Full_DataFlow_Diagram.md) - 8개 통합 다이어그램

### 8.1 포함된 다이어그램

1. 전체 시스템 아키텍처 개요
2. 데이터 파이프라인
3. 실시간 트레이딩 흐름
4. Frontend ↔ Backend 통신
5. 전략 점수 계산 흐름
6. 리서치 스크립트 파이프라인
7. DI 컨테이너 의존성 그래프
8. GUI 컴포넌트 계층 구조

---

## 관련 문서

- [Full_DataFlow.md](./Full_DataFlow.md) - Data Flow 상세 (84개)
- [Full_DataFlow_Diagram.md](./Full_DataFlow_Diagram.md) - Mermaid 다이어그램 (8개)
- [_index.md](./_index.md) - 파일별 체크리스트 (174개)
