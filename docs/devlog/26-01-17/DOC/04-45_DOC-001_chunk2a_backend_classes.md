# [DOC-001] Chunk 2A: Backend 클래스 도표화 Devlog

> **작성일**: 2026-01-17 04:45
> **계획서**: [DOC-001](../../Plan/26-01-17/04-31_DOC-001_full_architecture_document.md)

## 진행 현황

| Chunk | 상태 | 완료 시간 |
|-------|------|----------|
| Chunk 1 | ✅ 완료 | 04:42 |
| Chunk 2A | ✅ 완료 | 04:50 |

---

## Container 서비스 인벤토리 (24개)

### Data Layer (6개)

| Provider | 클래스 | 유형 | 의존성 |
|----------|--------|------|--------|
| `massive_client` | MassiveClient | Singleton | - |
| `massive_ws` | MassiveWebSocketClient | Singleton | - |
| `parquet_manager` | ParquetManager | Singleton | - |
| `data_repository` | DataRepository | Singleton | parquet_manager, massive_client |
| `database` | MarketDB | Singleton | config.db_path |
| `watchlist_store` | WatchlistStore | Singleton | - |

### Strategy Layer (5개)

| Provider | 클래스 | 유형 | 의존성 |
|----------|--------|------|--------|
| `ticker_info_service` | TickerInfoService | Singleton | - |
| `symbol_mapper` | SymbolMapper | Singleton | - |
| `scoring_strategy` | SeismographStrategy | Singleton | - |
| `trading_context` | TradingContext | Singleton | - |
| `config` | Configuration | Config | - |

### Core Layer (8개)

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
| `event_sequencer` | EventSequencer | Factory | - |

### Broker Layer (5개)

| Provider | 클래스 | 유형 | 의존성 |
|----------|--------|------|--------|
| `ibkr_connector` | IBKRConnector | Singleton | - |
| `order_manager` | OrderManager | Singleton | ibkr_connector |
| `risk_manager` | RiskManager | Singleton | ibkr_connector |
| `trailing_stop_manager` | TrailingStopManager | Singleton | ibkr_connector |
| `double_tap_manager` | DoubleTapManager | Singleton | ibkr_connector, order_manager, trailing_stop_manager |

---

## 계층별 클래스 상세 (Core 주요 클래스)

### backend/core/ 주요 클래스

| 파일 | 클래스 | 역할 |
|------|--------|------|
| `realtime_scanner.py` | RealtimeScanner | 1초 폴링 Gainers API 스캔 |
| `ignition_monitor.py` | IgnitionMonitor | Trigger Score 모니터링 |
| `scanner.py` | Scanner | Pre-market 일괄 스캔 |
| `scheduler.py` | TradingScheduler | APScheduler 기반 자동 실행 |
| `tick_broadcaster.py` | TickBroadcaster | Massive → GUI WebSocket 브릿지 |
| `tick_dispatcher.py` | TickDispatcher | 내부 컴포넌트 틱 배포 |
| `subscription_manager.py` | SubscriptionManager | Watchlist ↔ Massive 구독 동기화 |
| `order_manager.py` | OrderManager | 주문 실행/추적 |
| `risk_manager.py` | RiskManager | Kelly 포지션 사이징, Kill Switch |
| `trailing_stop.py` | TrailingStopManager | Trailing Stop 주문 |
| `double_tap.py` | DoubleTapManager | 1차 청산 후 재진입 |
| `trading_context.py` | TradingContext | 활성 티커 상태 관리 |
| `backtest_engine.py` | BacktestEngine | 백테스트 엔진 |
| `strategy_base.py` | StrategyBase | 전략 ABC |
| `strategy_loader.py` | StrategyLoader | 전략 동적 로드 |

### backend/data/ 주요 클래스

| 파일 | 클래스 | 역할 |
|------|--------|------|
| `data_repository.py` | DataRepository | 통합 데이터 접근 레이어 |
| `parquet_manager.py` | ParquetManager | Parquet I/O |
| `database.py` | MarketDB | SQLite 데이터베이스 |
| `massive_client.py` | MassiveClient | REST API 클라이언트 |
| `massive_ws_client.py` | MassiveWebSocketClient | WebSocket 클라이언트 |
| `ticker_info_service.py` | TickerInfoService | 티커 종합 정보 |
| `symbol_mapper.py` | SymbolMapper | Massive ↔ IBKR 심볼 매핑 |
| `watchlist_store.py` | WatchlistStore | Watchlist JSON 저장 |

---

## 다음 단계

→ **Chunk 2B**: Frontend 클래스 도표화
