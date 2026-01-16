# [DOC-001] Chunk 2B: Frontend 클래스 도표화 Devlog

> **작성일**: 2026-01-17 04:52
> **계획서**: [DOC-001](../../Plan/26-01-17/04-31_DOC-001_full_architecture_document.md)

## 진행 현황

| Chunk | 상태 | 완료 시간 |
|-------|------|----------|
| Chunk 1 | ✅ 완료 | 04:42 |
| Chunk 2A | ✅ 완료 | 04:50 |
| Chunk 2B | ✅ 완료 | 04:55 |

---

## Frontend 클래스 인벤토리

### GUI Layer - Main Window

| 파일 | 클래스 | 역할 | 메서드 수 |
|------|--------|------|----------|
| `dashboard.py` | Sigma9Dashboard | 메인 5-Panel 대시보드 | 79개 |
| `custom_window.py` | CustomAcrylicWindow | Acrylic 효과 윈도우 | ~10개 |
| `control_panel.py` | ControlPanel | TOP 컨트롤 버튼 패널 | ~15개 |
| `theme.py` | ThemeManager | 테마 관리 (Singleton) | ~5개 |
| `window_effects.py` | WindowBlurEffect | 윈도우 블러 효과 | ~5개 |

### GUI Layer - Panels (8개)

| 파일 | 클래스 | 역할 |
|------|--------|------|
| `panels/watchlist_panel.py` | WatchlistPanel | Tier1 Watchlist 표시 |
| `panels/tier2_panel.py` | Tier2Panel | Tier2 Hot Zone 표시 |
| `panels/chart_panel.py` | ChartPanel | 차트 영역 래퍼 |
| `panels/position_panel.py` | PositionPanel | 포지션 P&L 표시 |
| `panels/oracle_panel.py` | OraclePanel | LLM Oracle 채팅 |
| `panels/log_panel.py` | LogPanel | 로그 콘솔 |
| `panels/resample_panel.py` | ResamplePanel | 차트 리샘플링 |
| `panels/__init__.py` | (re-export) | 패널 공개 인터페이스 |

### GUI Layer - Chart

| 파일 | 클래스 | 역할 |
|------|--------|------|
| `chart/finplot_chart.py` | FinplotChartWidget | finplot 기반 차트 |
| `chart/chart_data_manager.py` | ChartDataManager | L1 캐시 관리 |
| `chart_widget.py` | ChartWidget | TradingView 차트 (Legacy) |

### GUI Layer - Widgets

| 파일 | 클래스 | 역할 |
|------|--------|------|
| `widgets/ticker_search_bar.py` | TickerSearchBar | 티커 검색 입력 |
| `widgets/time_display_widget.py` | TimeDisplayWidget | 시간 표시 |

### GUI Layer - State

| 파일 | 클래스 | 역할 |
|------|--------|------|
| `state/dashboard_state.py` | DashboardState | GUI 상태 관리 (Singleton) |
| `watchlist_model.py` | WatchlistModel | Watchlist Qt 모델 |

### Services Layer (4개)

| 파일 | 클래스 | 역할 |
|------|--------|------|
| `backend_client.py` | BackendClient | HTTP/WS 통합 클라이언트 (Singleton) |
| `rest_adapter.py` | RestAdapter | REST API 어댑터 |
| `ws_adapter.py` | WsAdapter | WebSocket 어댑터 |
| `chart_data_service.py` | ChartDataService | 차트 데이터 로드 서비스 |

---

## 주요 클래스 상세

### BackendClient PyQt Signals

| Signal | 타입 | 용도 |
|--------|------|------|
| `connected` | bool | 연결 상태 변경 |
| `state_changed` | ConnectionState | 상태 변경 |
| `watchlist_updated` | list | Watchlist 업데이트 |
| `ignition_updated` | dict | Ignition Score |
| `bar_received` | dict | 실시간 OHLCV |
| `tick_received` | dict | 실시간 틱 |
| `heartbeat_received` | dict | 서버 하트비트 |

---

## Frontend 총계

| 구분 | 개수 |
|------|------|
| **GUI 클래스** | 21개 |
| **Services 클래스** | 4개 |
| **총 클래스** | 25개 |

---

## 다음 단계

→ **Chunk 3**: 연결 관계 매트릭스
