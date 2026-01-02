# 🪜 Sigma9 Development Steps

Based on [Master Plan v2.0](../Plan/masterplan.md) and [@PROJECT_DNA.md](../../@PROJECT_DNA.md).

> **Rule**: Before completing each step, you MUST write a devlog in `docs/devlog/step_X.Y.md`.

---

## Phase 1: Foundation (Local Windows MVP)

### Step 1.1: Project Setup & Structure ✅ COMPLETED
- [x] 1.1.1: Initialize git repository
- [x] 1.1.2: Create directory structure as defined in `masterplan.md` (12.1)
- [x] 1.1.3: Create `requirements.txt`
- [x] 1.1.4: Setup `docs/devlog` and `docs/Plan/steps`

### Step 1.2: Mock Data & Strategy Interface ✅ COMPLETED
- [x] 1.2.1: Implement `StrategyBase` class (ABC) in `backend/core/strategy_base.py`
- [x] 1.2.2: Implement `Signal` data class
- [x] 1.2.3: Create a dummy strategy `RandomWalker` inheriting `StrategyBase` to test the interface
- [x] 1.2.4: Create a mock price feed generator (sine wave or random walk) for local testing without IBKR


### Step 1.3: GUI Dashboard Skeleton ✅ COMPLETED
- [x] 1.3.1: Create main PyQt6 window with Glassmorphism / Acrylic effect
- [x] 1.3.2: Implement the 5-panel layout (Top, Left, Center, Right, Bottom)
- [x] 1.3.3: Integrate `TradingView Lightweight Charts` via `QWebEngineView` (placeholder)
- [x] 1.3.4: Ensure bidirectional communication stub between GUI and Backend

---

## Phase 2: Core Engine (Strategy & Data)

### Step 2.0: Market Data Pipeline (Polygon + SQLite)
- [x] 2.0.1: `backend/data/database.py` Setup (SQLAlchemy 2.0 + Alembic)
- [x] 2.0.2: `backend/data/polygon_client.py` Implementation (Auth & Rate Limiting)
- [x] 2.0.3: `backend/data/polygon_loader.py` - Historical OHLCV (Grouped Daily Fetch)
- [x] 2.0.4: `update_market_data()` - Incremental Update Logic
- [x] 2.0.5: Implement Universe Scanner (DB-based Filtering)
- [x] 2.0.6: Implement Fundamental Data Fetch (Market Cap, Float)
- [x] 2.0.7: Implement Multi-ticker Real-time Subscription (Top 50 Watchlist)
- [x] 2.0.8: `SeismographStrategy` Integration (DB-based Watchlist Generation)

### Step 2.1: IBKR Connector (Data Feed) ✅ COMPLETED
- [x] 2.1.1: Implement `IBKRConnector` using `ib_insync`
- [x] 2.1.2: Connect to TWS/Gateway (Paper Trading)
- [x] 2.1.3: Verify real-time data streaming for a single ticker (e.g., SPY)
- [x] 2.1.4: Handle connection loss/restore logic

### Step 2.2: Seismograph Strategy - Scanning (Phase 1) ✅ COMPLETED
- [x] 2.2.1: Implement `SeismographStrategy` skeleton
- [x] 2.2.2: Implement `calculate_watchlist_score()` for identifying Accumulation
- [x] 2.2.3: Implement `Universe Filter` (Price, Market Cap, Volume)
- [x] 2.2.4: Verify Watchlist generation with live/delayed data
- [x] 2.2.5: [Refinement] Update Watchlist structure to support metadata (accum_score, stage) for Trading Restrictions
- [x] 2.2.6: [New] Implement `Scanner Orchestrator` (Load Daily History from DB -> Run Strategy -> Aggregation)
- [x] 2.2.7: [New] Implement `Symbol Mapping Service` (Polygon Tickers <-> IBKR Tickers)
- [x] 2.2.8: [New] Implement `Watchlist Persistence` (Save Watchlist + Metadata to JSON/DB)

### Step 2.3: Seismograph Strategy - Trigger (Phase 2) ✅ COMPLETED
- [x] 2.3.1: Implement `on_tick()` logic for Ignition detection
- [x] 2.3.2: Implement `Tick Velocity` and `Volume Burst` logic
- [x] 2.3.3: Implement `Anti-Trap` filters
- [x] 2.3.4: [Refinement] Enforce "Monitoring Only" restriction for Stage 1-2 stocks in `on_tick()`
- [x] 2.3.5: [New] Implement `Context Loader` (Load Watchlist Metadata into Trigger Engine)
- [x] 2.3.6: [New] Verify `Tick Stream` consistency (Timestamp/Price) vs IBKR Real-time Feed
- [x] 2.3.7: [Refinement] Replace all mock data with real data

### Step 2.4: Core Indicators & Chart Visualization (Backend-Driven)
- [x] 2.4.1: [Backend] Implement `TechnicalAnalysis` module (VWAP, ATR, MA) using pandas/numpy
- [x] 2.4.2: [Backend] Implement Dynamic Stop-Loss logic based on ATR
- [x] 2.4.3: [API] Update WebSocket packet to include indicator values (VWAP, SL/TP levels)
- [x] 2.4.4: [Frontend] Integrate `TradingView Lightweight Charts` for multi-timeframe visualization
- [x] 2.4.5: [Frontend] Render VWAP & ATR lines (received from Backend) on Lightweight Charts
- [x] 2.4.6: [Frontend] Visualize Trade Markers & Ignition Points on Lightweight Charts
- [x] 2.4.7: [Frontend] Integrate `ChartWidget` into `Sigma9Dashboard` center panel
- [x] 2.4.8: [Frontend] Add sample data loading on Dashboard startup
- [x] 2.4.9: [Frontend] Verify complete GUI with chart visualization

### Step 2.5: Strategy Loader & Plugin System (masterplan 13) ✅ COMPLETED
- [x] 2.5.1: Implement `StrategyLoader` class with `discover_strategies()`
- [x] 2.5.2: Implement `load_strategy()` and `reload_strategy()` for hot-reload
- [x] 2.5.3: Create `_template.py` for new strategy development
- [x] 2.5.4: Add strategy selector dropdown in GUI

### Step 2.6: Backtesting Framework (Basic) ✅ COMPLETED
- [x] 2.6.1: Implement `BacktestEngine` (simulated exchange)
- [x] 2.6.2: Implement historical data replay using `market_data.db`
- [x] 2.6.3: Verify `SeismographStrategy` with 2024 historical data
- [x] 2.6.4: Generate Performance Report (CAGR, MDD, Win Rate)

### Step 2.7: Multi-Timeframe Chart Support ✅ COMPLETED
> Intraday data source: Polygon API (Free tier limited)

- [x] 2.7.1: [Backend] Implement Intraday Data API (1m, 5m, 15m, 1h) - `routes.py` + `polygon_client.py`
- [x] 2.7.2: [Backend] Add `intraday_bars` table to database *(using Polygon API directly, no local cache)*
- [x] 2.7.3: [Frontend] Timeframe change handler → data reload
- [x] 2.7.4: [Frontend] Dynamic data loading on pan/zoom *(2-Tier Cache: Memory + SQLite)*
- [x] 2.7.5: [Frontend] Fix Doji candle rendering bug (wick height=0 caused $1 pen width interpretation)


---

## Phase 3: Execution & Management

### Step 3.1: Order Management System (OMS) ✅ COMPLETED
- [x] 3.1.1: Implement order placement logic in `IBKRConnector`
- [x] 3.1.2: Implement Server-Side OCA (One-Cancels-All) groups (Stop Loss, Time Stop, Profit Taker)
- [x] 3.1.3: Verify order states (Pending, Filled, Cancelled) reflect in GUI

### Step 3.2: Risk Manager & Position Sizing ✅ COMPLETED
- [x] 3.2.1: Implement `RiskManager` class
- [x] 3.2.2: Implement Kelly Criterion position sizing logic
- [x] 3.2.3: Enforce Daily/Weekly Loss Limits
- [x] 3.2.4: Implement "Kill Switch" functionality (Cancel All + Liquidate All)

### Step 3.3: Double Tap & Harvest ✅ COMPLETED
- [x] 3.3.1: Implement Trailing Stop logic (Harvest)
- [x] 3.3.2: Implement `Double Tap` re-entry logic (Cooldown, VWAP check)
- [x] 3.3.3: Update OMS to handle these multi-stage exit scenarios

### Step 3.4: GUI Control Panel (masterplan 14) ✅ COMPLETED
- [x] 3.4.1: Implement Connect/Disconnect button with Backend WebSocket
- [x] 3.4.2: Implement Boot Engine / Shutdown Engine buttons
- [x] 3.4.3: Implement Strategy Reload button
- [x] 3.4.4: Add connection status indicator (🔴🟡🟠🟢)
- [x] 3.4.5: Implement loading overlay for async operations
- [x] 3.4.6: Auto-connect to Backend on GUI startup
- [x] 3.4.7: Auto-start Scanner when strategy is selected/changed
- [x] 3.4.8: Auto-update Watchlist panel when Scanner produces results

---

## Phase 4: Intelligence & Refinement

> 📌 **Strategic Shift**: "Architecture First" 접근법 채택. 기능 추가 전 Client-Server 구조 분리를 선행하여 기술 부채 방지.

### Step 4.1: Architecture Transition (Client-Server Split) ✅ COMPLETED
- [x] 4.1.1: **Refactor Config**: Split `settings.yaml` into `server_config.yaml` and `client_config.yaml`
- [x] 4.1.2: **Server Core**: Create `backend/server.py` with FastAPI + uvicorn
- [x] 4.1.3: **API Endpoints**: Implement `/api/status`, `/api/control`, `/ws/feed`
- [x] 4.1.4: **Job Scheduler**: Implement `APScheduler` for auto-scanning at market open (AWS Ready)
- [x] 4.1.5: **Verify Independent Server**: Ensure Server runs without GUI dependency

### Step 4.2: Frontend Integration (Client Adapter) ✅ COMPLETED
- [x] 4.2.1: **BackendClient Refactor**: Replace direct imports with `RestAdapter` and `WsAdapter`
- [x] 4.2.2: **State Sync**: Implement `sync_initial_state()` logic on connection
- [x] 4.2.3: **Settings Dialog Restructure**: Reorganize Settings into tabbed layout
  - [x] 4.2.3.1: Create `QTabWidget` structure with 3 tabs: **Connection**, **Backend**, **Theme**
  - [x] 4.2.3.2: **Theme Tab**: Migrate existing settings (Window Opacity, Acrylic Alpha, Particle Opacity, Tint Color)
  - [x] 4.2.3.3: **Connection Tab**: Server Host/Port, Auto-connect toggle, Reconnect interval, Timeout settings
  - [x] 4.2.3.4: **Backend Tab**: Scheduler controls (Market Open Scan toggle, Scan offset minutes, Daily Data Update toggle, Update time picker)
- [x] 4.2.4: **Verify Decoupling**: Run GUI with remote Server (localhost)
- [x] 4.2.5: **Right Panel Oracle Section**: Trading + Oracle sections in Right Panel
- [x] 4.2.6: **Local Server Launch**: Add "Start/Shutdown Local Server" buttons in Backend tab (Windows subprocess)

### Step 4.3: Reliability & Logging
- [ ] 4.3.1: **Structured Logging**: Setup `loguru` on Server with JSON rotation
- [ ] 4.3.2: **Log Streaming**: Stream `INFO`+ logs via WebSocket to Client Console
- [ ] 4.3.3: **Trade Journal DB**: Persist trade history to SQLite (Server-side)

### Step 4.4: Intelligence (Oracle Panel)
- [ ] 4.4.1: **Oracle Service**: Implement `LLMOracle` on Server side (OpenAI/Anthropic)
- [ ] 4.4.2: **Analysis Endpoints**: `/api/oracle/analyze/{ticker}` & `/api/oracle/reflection`
- [ ] 4.4.3: **Oracle UI Integration**: Implement `OracleWidget` in Right Panel (Chat Interface + Markdown View)
- [ ] 4.4.4: **Feature Implementation**: Coding for [Why?], [Fundamental], [Reflection] buttons

### Step 4.A: Tiered Watchlist System
> 📋 상세 계획: [step_4.a_plan.md](./step_4.a_plan.md)

**선행 필수**: Step 2.7 (Multi-Timeframe) 완료 후 Phase 4.A.0 진행

#### Phase 4.A.0: 실시간 데이터 파이프라인 ✅ COMPLETED
> 📝 **데이터 소스 전환**: IBKR 실시간 시세 → **Massive.com WebSocket (AM/T 채널)**  
> 📝 IBKR는 **주문 실행 전용**으로 역할 축소

- [x] 4.A.0.1: Massive WebSocket 클라이언트 (`massive_ws_client.py`)
- [x] 4.A.0.2: TickBroadcaster → GUI WebSocket 브릿지 (`tick_broadcaster.py`)
- [x] 4.A.0.3: Chart 실시간 업데이트 (`update_realtime_bar()`)
- [x] 4.A.0.4: SubscriptionManager 구독 동기화 (`subscription_manager.py`)

#### Phase 4.A.0.b: Tick Dispatcher Integration ✅ COMPLETED
- [x] 4.A.0.b.1: TickDispatcher 생성 (`tick_dispatcher.py`)
- [x] 4.A.0.b.2: Strategy (Seismograph) `on_tick` 연결
- [/] 4.A.0.b.3: TradingEngine 연결 ⏭️ SKIP (Phase 5에서 구현)
- [x] 4.A.0.b.4: TrailingStop `on_price_update` 연결
- [x] 4.A.0.b.5: Tier 2 GUI `tick_received` 연결
- [x] 4.A.0.b.6: T 채널 자동 구독 (`sync_tick_subscriptions`)

#### Phase 4.A.0.c: Pipeline 버그 수정 ✅ COMPLETED
- [x] 4.A.0.c.1: P0 - `listen()` 루프 추가
- [x] 4.A.0.c.2: P1 - 초기 구독 트리거
- [x] 4.A.0.c.3: P2 - 문자열/필드 수정

#### Phase 4.A.0.d: 틱 기반 실시간 캔들 업데이트 ✅ COMPLETED
> 📝 현재 조회 중인 차트의 마지막 캔들이 틱 데이터에 따라 실시간으로 "출렁이는" 효과
> 📝 약 300ms 주기로 스로틀링하여 성능 최적화

- [x] 4.A.0.d.1: `Dashboard._on_tick_received()` → 현재 차트 종목 필터링 + 300ms 스로틀링
- [x] 4.A.0.d.2: `PyQtGraphChart.update_current_candle(price, volume)` 메서드 추가
- [x] 4.A.0.d.3: `CandlestickItem.update_bar(index, bar)` 마지막 캔들 갱신 로직 (기존 메서드 활용)

#### Phase 4.A.1: Tier 1 Enhancement
- [ ] 4.A.1.1: Dollar Volume 컬럼 추가 (K/M/B 표기)
- [ ] 4.A.1.2: 헤더 정렬 기능 (등락율/Score/Ignition)
- [ ] 4.A.1.3: Tier 1 주기적 갱신 (1분/5분)

#### Phase 4.A.2: Tier 2 Hot Zone
- [ ] 4.A.2.1: Tier 2 데이터 모델 (zenV, zenP 포함)
- [ ] 4.A.2.2: Ignition ≥ 70 시 Tier 2 승격
- [ ] 4.A.2.3: Day Gainers → Tier 2 자동 추가
- [ ] 4.A.2.4: Tier 2 GUI 패널 (Watchlist 상단)
- [ ] 4.A.2.5: Tier 2 Tick-level 실시간 업데이트 (1초)

#### Phase 4.A.3: Z-Score Indicator
- [ ] 4.A.3.1: zenV (Normalized Volume) 계산
- [ ] 4.A.3.2: zenP (Normalized Price) 계산
- [ ] 4.A.3.3: GUI에 Z-score 표시

#### Phase 4.A.4: zenV-zenP Divergence 전략
- [ ] 4.A.4.1: "High zenV + Low zenP" 조건 탐지
- [ ] 4.A.4.2: Divergence 기반 진입 시그널
- [ ] 4.A.4.3: 기존 Ignition 로직과 병행

---

## Phase 5: Cloud Migration (Prepare for AWS)

### Step 5.1: Backend/Frontend Separation
- [ ] 5.1.1: Refactor creating distinct `backend/` and `frontend/` entry points if not already strict
- [ ] 5.1.2: Verify FastAPI server running independently
- [ ] 5.1.3: Verify Frontend client connecting via REST/WebSocket to localhost

### Step 5.2: Dockerization
- [ ] 5.2.1: Create `Dockerfile` for Backend
- [ ] 5.2.2: Verify container build and run locally

### Step 5.3: AWS Deployment (Simulated/Actual)
- [ ] 5.3.1: (Optional) Deploy to AWS EC2 for final field test
- [ ] 5.3.2: Verify latency and connectivity

