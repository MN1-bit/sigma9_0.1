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

---

## Phase 3: Execution & Management

### Step 3.1: Order Management System (OMS)
- [ ] 3.1.1: Implement order placement logic in `IBKRConnector`
- [ ] 3.1.2: Implement Server-Side OCA (One-Cancels-All) groups (Stop Loss, Time Stop, Profit Taker)
- [ ] 3.1.3: Verify order states (Pending, Filled, Cancelled) reflect in GUI

### Step 3.2: Risk Manager & Position Sizing
- [ ] 3.2.1: Implement `RiskManager` class
- [ ] 3.2.2: Implement Kelly Criterion position sizing logic
- [ ] 3.2.3: Enforce Daily/Weekly Loss Limits
- [ ] 3.2.4: Implement "Kill Switch" functionality (Cancel All + Liquidate All)

### Step 3.3: Double Tap & Harvest
- [ ] 3.3.1: Implement Trailing Stop logic (Harvest)
- [ ] 3.3.2: Implement `Double Tap` re-entry logic (Cooldown, VWAP check)
- [ ] 3.3.3: Update OMS to handle these multi-stage exit scenarios

### Step 3.4: GUI Control Panel (masterplan 14)
- [ ] 3.4.1: Implement Connect/Disconnect button with Backend WebSocket
- [ ] 3.4.2: Implement Boot Engine / Shutdown Engine buttons
- [ ] 3.4.3: Implement Strategy Reload button
- [ ] 3.4.4: Add connection status indicator (🔴🟡🟠🟢)
- [ ] 3.4.5: Implement loading overlay for async operations

---

## Phase 4: Intelligence & Refinement

### Step 4.1: LLM Oracle Integration
- [ ] 4.1.1: Implement `LLMOracle` class
- [ ] 4.1.2: Connect to OpenAI/Anthropic API
- [ ] 4.1.3: Implement `explain_selection()` and `technical_analysis()` features
- [ ] 4.1.4: Display LLM insights in GUI (Tooltip/Panel)

### Step 4.2: Logging & Persistence (masterplan 15)
- [ ] 4.2.1: Setup `loguru` with structured JSON logging
- [ ] 4.2.2: Implement SQLite database for trade history and journal
- [ ] 4.2.3: Ensure valid logs are generated for every major action
- [ ] 4.2.4: Setup Alembic for schema migration

### Step 4.3: FastAPI Server & API Layer (masterplan 2.3)
- [ ] 4.3.1: Implement `server.py` with FastAPI + uvicorn
- [ ] 4.3.2: Implement REST endpoints (`/api/watchlist`, `/api/positions`, `/api/order`)
- [ ] 4.3.3: Implement WebSocket handlers (`/ws/market`, `/ws/trade`)
- [ ] 4.3.4: Implement `/api/kill-switch` endpoint
- [ ] 4.3.5: Add JWT/API Key authentication

### Step 4.4: GUI Panel Integration (masterplan 7.1)
- [ ] 4.4.1: Implement Watchlist panel (Left) with score display
- [ ] 4.4.2: Implement Positions panel (Right) with P&L and Force Sell
- [ ] 4.4.3: Implement Log console panel (Bottom) with real-time streaming
- [ ] 4.4.4: Connect panels to Backend via WebSocket

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

