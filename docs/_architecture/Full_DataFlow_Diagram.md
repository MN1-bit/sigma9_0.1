# Sigma9 시스템 Data Flow 통합 다이어그램

> **생성일**: 2026-01-16
> 
> `docs/_architecture/Full_DataFlow.md` 기반 시각화 문서

---

## 1. 전체 시스템 아키텍처 개요

```mermaid
flowchart TB
    subgraph External["🌐 External Services"]
        IBKR["IB Gateway/TWS"]
        MASSIVE_API["Massive.com REST API"]
        MASSIVE_WS["Massive.com WebSocket"]
        LLM_API["LLM Providers<br/>(OpenAI/Anthropic/Google)"]
    end

    subgraph Backend["⚙️ Backend Server (FastAPI)"]
        direction TB
        SERVER["server.py<br/>FastAPI App"]
        CONTAINER["container.py<br/>DI Container"]
        
        subgraph Core["📦 Core Engine"]
            SCANNER["Scanner<br/>Pre-market Scan"]
            RT_SCANNER["RealtimeScanner<br/>1초 폴링"]
            IGNITION["IgnitionMonitor<br/>Trigger Score"]
            SCHEDULER["TradingScheduler<br/>APScheduler"]
        end
        
        subgraph Strategy["🎯 Strategy"]
            SEISMO["SeismographStrategy<br/>v3.0"]
            ZSCORE["ZScoreCalculator"]
            DIVERGE["DivergenceDetector"]
        end
        
        subgraph Trading["💰 Trading"]
            ORDER_MGR["OrderManager"]
            RISK_MGR["RiskManager"]
            TRAILING["TrailingStopManager"]
            DOUBLE_TAP["DoubleTapManager"]
        end
        
        subgraph Data["💾 Data Layer"]
            DATA_REPO["DataRepository"]
            PARQUET["ParquetManager"]
            DB["MarketDB (SQLite)"]
            MASSIVE_CLIENT["MassiveClient"]
        end
        
        subgraph Broker["🏦 Broker"]
            IBKR_CONN["IBKRConnector"]
        end
        
        subgraph Realtime["📡 Realtime"]
            WS_MGR["ConnectionManager"]
            TICK_BROAD["TickBroadcaster"]
            TICK_DISP["TickDispatcher"]
            SUB_MGR["SubscriptionManager"]
        end
    end

    subgraph Frontend["🖥️ Frontend GUI (PyQt6)"]
        direction TB
        DASHBOARD["Sigma9Dashboard"]
        
        subgraph Panels["📊 Panels"]
            WATCHLIST_P["WatchlistPanel"]
            CHART_P["ChartPanel"]
            POSITION_P["PositionPanel"]
            ORACLE_P["OraclePanel"]
            LOG_P["LogPanel"]
            TIER2_P["Tier2Panel"]
        end
        
        subgraph Services["🔌 Services"]
            BACKEND_CLIENT["BackendClient"]
            REST_ADAPTER["RestAdapter"]
            WS_ADAPTER["WsAdapter"]
            CHART_SVC["ChartDataService"]
        end
        
        subgraph State["📋 State"]
            DASH_STATE["DashboardState"]
            WATCHLIST_MODEL["WatchlistModel"]
        end
    end

    %% External connections
    MASSIVE_API --> MASSIVE_CLIENT
    MASSIVE_WS --> TICK_BROAD
    IBKR --> IBKR_CONN
    LLM_API --> ORACLE_P

    %% Backend internal
    SERVER --> CONTAINER
    CONTAINER --> Core
    CONTAINER --> Data
    CONTAINER --> Strategy
    
    MASSIVE_CLIENT --> DATA_REPO
    DATA_REPO --> PARQUET
    DATA_REPO --> DB
    
    SCANNER --> SEISMO
    RT_SCANNER --> SEISMO
    SEISMO --> ZSCORE
    SEISMO --> DIVERGE
    
    IGNITION --> SEISMO
    SCHEDULER --> SCANNER
    
    TICK_BROAD --> TICK_DISP
    TICK_DISP --> SEISMO
    TICK_DISP --> TRAILING
    TICK_DISP --> DOUBLE_TAP
    
    SUB_MGR --> MASSIVE_WS
    
    ORDER_MGR --> IBKR_CONN
    RISK_MGR --> IBKR_CONN
    TRAILING --> ORDER_MGR
    DOUBLE_TAP --> ORDER_MGR
    
    RT_SCANNER --> WS_MGR
    IGNITION --> WS_MGR

    %% Frontend connections
    DASHBOARD --> Panels
    DASHBOARD --> Services
    DASHBOARD --> State

    BACKEND_CLIENT --> REST_ADAPTER
    BACKEND_CLIENT --> WS_ADAPTER
    REST_ADAPTER --> SERVER
    WS_ADAPTER --> WS_MGR

    CHART_SVC --> CHART_P
    WATCHLIST_MODEL --> WATCHLIST_P
    DASH_STATE --> TIER2_P
```

---

## 2. 데이터 파이프라인 (Data Pipeline)

```mermaid
flowchart LR
    subgraph Sources["📥 Data Sources"]
        API["Massive.com<br/>REST API"]
        WS["Massive.com<br/>WebSocket"]
    end

    subgraph Ingestion["⬇️ Ingestion"]
        MC["MassiveClient"]
        MWS["MassiveWSClient"]
    end

    subgraph Storage["💾 Storage"]
        PARQUET["Parquet Files<br/>(daily/1m)"]
        SQLITE["SQLite<br/>(MarketDB)"]
    end

    subgraph Processing["⚙️ Processing"]
        DR["DataRepository"]
        PM["ParquetManager"]
    end

    subgraph Consumers["📤 Consumers"]
        SCANNER["Scanner"]
        BACKTEST["BacktestEngine"]
        STRATEGY["SeismographStrategy"]
        CHART["ChartDataService"]
    end

    API -->|"HTTP GET"| MC
    WS -->|"WSS Stream"| MWS

    MC -->|"DataFrame"| DR
    DR -->|"read/write"| PM
    PM -->|"save"| PARQUET
    DR -->|"upsert"| SQLITE

    DR -->|"OHLCV"| SCANNER
    DR -->|"OHLCV"| BACKTEST
    DR -->|"bars"| STRATEGY
    PM -->|"bars"| CHART
```

---

## 3. 실시간 트레이딩 흐름 (Realtime Trading Flow)

```mermaid
flowchart TB
    subgraph Phase1["📋 Phase 1: Watchlist (Pre-market)"]
        SCHED["TradingScheduler<br/>09:15 ET"]
        SCAN["Scanner.scan()"]
        SCORE["calculate_watchlist_score_v3()"]
        WL["Ranked Watchlist"]
        
        SCHED -->|"trigger"| SCAN
        SCAN -->|"OHLCV"| SCORE
        SCORE -->|"score 0-100"| WL
    end

    subgraph Phase2["🔥 Phase 2: Trigger (Market Hours)"]
        GAIN["Massive Gainers API<br/>1초 폴링"]
        RT["RealtimeScanner"]
        FILTER["TickerFilter"]
        IGN["IgnitionMonitor"]
        TRIG["calculate_trigger_score()"]
        
        GAIN -->|"new gainer"| RT
        RT -->|"filter"| FILTER
        FILTER -->|"valid"| IGN
        IGN -->|"current_price"| TRIG
        TRIG -->|"Ignition 80+"| SIGNAL
    end

    subgraph Phase3["💰 Phase 3: Execution"]
        SIGNAL["Entry Signal"]
        ORDER["OrderManager"]
        RISK["RiskManager"]
        IBKR["IBKRConnector"]
        
        SIGNAL -->|"execute_entry"| ORDER
        ORDER -->|"position_size"| RISK
        RISK -->|"kelly_fraction"| ORDER
        ORDER -->|"place_order"| IBKR
    end

    subgraph Phase4["🛡️ Phase 4: Exit"]
        TICK["TickDispatcher"]
        TRAIL["TrailingStopManager"]
        EXIT["Exit Signal"]
        DT["DoubleTapManager"]
        
        TICK -->|"price"| TRAIL
        TRAIL -->|"stop_triggered"| EXIT
        EXIT -->|"3min cooldown"| DT
        DT -->|"HOD 돌파"| SIGNAL
    end

    WL --> Phase2
    Phase2 --> Phase3
    Phase3 --> Phase4
```

---

## 4. Frontend ↔ Backend 통신 흐름

```mermaid
flowchart LR
    subgraph Frontend["🖥️ Frontend (PyQt6)"]
        DASH["Dashboard"]
        BC["BackendClient"]
        REST["RestAdapter"]
        WSA["WsAdapter"]
    end

    subgraph Backend["⚙️ Backend (FastAPI)"]
        API["REST API<br/>/api/*"]
        WSFEED["WebSocket<br/>/ws/feed"]
        WS_MGR["ConnectionManager"]
    end

    subgraph Messages["📨 WebSocket Messages"]
        LOG["LOG"]
        WATCHLIST["WATCHLIST"]
        IGNITION["IGNITION"]
        BAR["BAR"]
        TICK["TICK"]
        POSITIONS["POSITIONS"]
        HEARTBEAT["HEARTBEAT"]
    end

    DASH --> BC
    BC --> REST
    BC --> WSA
    
    REST -->|"HTTP"| API
    WSA <-->|"WSS"| WSFEED
    
    WSFEED --> WS_MGR
    WS_MGR --> Messages
    
    Messages -->|"broadcast"| WSA
    WSA -->|"PyQt Signals"| DASH
```

---

## 5. 전략 점수 계산 흐름 (Strategy Scoring)

```mermaid
flowchart TB
    subgraph Input["📊 Input Data"]
        BARS["Daily OHLCV<br/>(60일)"]
        TICK["Real-time Tick"]
    end

    subgraph Indicators["📐 Technical Indicators"]
        TA["TechnicalAnalysis"]
        VWAP["VWAP"]
        ATR["ATR"]
        SMA["SMA 20/50"]
        RSI["RSI 14"]
    end

    subgraph ZScore["📈 Z-Score Analysis"]
        ZC["ZScoreCalculator"]
        ZENV["zenV<br/>(Volume Z)"]
        ZENP["zenP<br/>(Price Z)"]
        DIV["DivergenceDetector<br/>zenV≥2, zenP<0.5"]
    end

    subgraph Signals["🎯 Signal Detection"]
        TR["Tight Range<br/>30%"]
        AB["Absorption<br/>20%"]
        AC["Accumulation<br/>20%"]
        MO["Momentum<br/>15%"]
        VO["Volume<br/>15%"]
    end

    subgraph Scoring["💯 Final Score"]
        V2["score_v2<br/>(Watchlist)"]
        V3["score_v3 Pinpoint<br/>(Intensities)"]
        IGN["Ignition Score<br/>(Trigger)"]
    end

    BARS --> TA
    BARS --> ZC
    
    TA --> VWAP
    TA --> ATR
    TA --> SMA
    TA --> RSI
    
    ZC --> ZENV
    ZC --> ZENP
    ZENV --> DIV
    ZENP --> DIV

    VWAP --> Signals
    ATR --> Signals
    DIV --> Signals

    Signals --> TR
    Signals --> AB
    Signals --> AC
    Signals --> MO
    Signals --> VO

    TR --> V3
    AB --> V3
    AC --> V3
    MO --> V3
    VO --> V3

    V3 --> IGN
    TICK --> IGN
```

---

## 6. 리서치 스크립트 파이프라인 (R-3/R-4)

```mermaid
flowchart TB
    subgraph Phase1["📥 Phase 1: Data Collection"]
        P1["all_daily.parquet"]
        A1["analyze_daygainers.py"]
        O1["daygainers_75plus.csv"]
        
        P1 --> A1 --> O1
    end

    subgraph Phase2["🎯 Phase 2: Control Group"]
        I2["daygainers_75plus.csv"]
        A2["build_control_group.py"]
        O2["control_groups.csv"]
        
        I2 --> A2 --> O2
    end

    subgraph Phase3["📊 Phase 3: D-1 Features"]
        I3["control_groups.csv"]
        A3["build_d1_features.py"]
        O3["d1_features.parquet"]
        
        I3 --> A3
        P1 --> A3
        A3 --> O3
    end

    subgraph Phase4["⏱️ Phase 4: Minute Data"]
        I4["control_groups.csv"]
        A4["download_target_minutes.py"]
        O4["1m/*.parquet"]
        
        I4 --> A4 --> O4
    end

    subgraph Phase5["📈 Phase 5: M-n Features"]
        I5["d1_features.parquet"]
        A5["build_m_n_features.py"]
        O5["m_n_features.parquet"]
        
        I5 --> A5
        O4 --> A5
        A5 --> O5
    end

    subgraph Phase6["🤖 Phase 6: Model Training"]
        I6A["d1_features_extended.parquet"]
        I6B["m_n_features.parquet"]
        A6["train_xgboost.py"]
        O6["ml_report.json"]
        
        I6A --> A6
        I6B --> A6
        A6 --> O6
    end

    O1 --> Phase2
    O2 --> Phase3
    O2 --> Phase4
    O3 --> Phase5
    O5 --> Phase6
```

---

## 7. DI 컨테이너 의존성 그래프

```mermaid
flowchart TB
    subgraph External["🌐 External Services"]
        MASSIVE_API["Massive.com API"]
        MASSIVE_WS_EXT["Massive.com WebSocket"]
        IBKR_GW["IB Gateway/TWS"]
    end

    subgraph Container["📦 DI Container"]
        subgraph DataLayer["💾 Data Layer"]
            MC["massive_client"]
            MWS["massive_ws<br/>(WebSocket)"]
            PM["parquet_manager"]
            DB["database (MarketDB)"]
            DR["data_repository"]
        end
        
        subgraph StrategyLayer["🎯 Strategy Layer"]
            WS["watchlist_store"]
            TI["ticker_info_service"]
            SM["symbol_mapper<br/>(Massive↔IBKR)"]
            SS["scoring_strategy<br/>(Seismograph)"]
            TF["ticker_filter"]
        end
        
        subgraph CoreLayer["⚙️ Core Layer"]
            TC["trading_context"]
            RS["realtime_scanner"]
            IM["ignition_monitor"]
            AL["audit_logger"]
            ED["event_deduplicator"]
            ES["event_sequencer"]
        end
        
        subgraph RealtimeLayer["📡 Realtime Layer"]
            TD["tick_dispatcher"]
            TB["tick_broadcaster"]
            SUB["subscription_manager"]
        end
        
        subgraph BrokerLayer["🏦 Broker Layer"]
            IBKR["IBKRConnector"]
            OM["order_manager"]
            RM["risk_manager"]
            TRAIL["trailing_stop"]
            DT["double_tap"]
        end
    end

    %% External connections
    MASSIVE_API -->|"HTTP"| MC
    MASSIVE_WS_EXT <-->|"WSS"| MWS
    IBKR_GW <-->|"ib_insync"| IBKR

    %% Data Layer dependencies
    MC --> DR
    MC --> TI
    PM --> DR
    DB --> DR
    
    %% Realtime Layer dependencies (02-001.5, 02-002)
    MWS --> TB
    MWS --> SUB
    TD --> TB
    
    %% Strategy Layer dependencies
    SM --> TI
    SM --> IBKR
    
    %% Core Layer dependencies
    DR --> RS
    SS --> RS
    TF --> RS
    SS --> IM
    TC --> IM
    RS --> IM
    
    %% Broker Layer dependencies
    IBKR --> OM
    IBKR --> RM
    OM --> TRAIL
    OM --> DT
    RM --> OM
```

---

## 8. GUI 컴포넌트 계층 구조

```mermaid
flowchart TB
    subgraph App["🖥️ Application"]
        MAIN["main.py"]
        QAPP["QApplication"]
    end

    subgraph Window["🪟 Main Window"]
        DASH["Sigma9Dashboard"]
        CTRL["ControlPanel"]
        THEME["ThemeManager"]
        FX["WindowEffects<br/>(Acrylic)"]
    end

    subgraph Panels["📊 Panels"]
        WLP["WatchlistPanel"]
        CP["ChartPanel"]
        PP["PositionPanel"]
        OP["OraclePanel"]
        LP["LogPanel"]
        T2P["Tier2Panel"]
    end

    subgraph Widgets["🔲 Widgets"]
        FPC["FinplotChartWidget"]
        TSB["TickerSearchBar"]
        TDW["TimeDisplayWidget"]
        WLM["WatchlistModel"]
    end

    subgraph State["📋 State Management"]
        DS["DashboardState"]
        SIG["Qt Signals"]
    end

    MAIN --> QAPP --> DASH
    DASH --> CTRL
    DASH --> THEME
    DASH --> FX
    
    DASH --> Panels
    
    WLP --> WLM
    WLP --> T2P
    CP --> FPC
    CTRL --> TSB
    CTRL --> TDW
    
    DASH --> DS
    DS -->|"ticker_changed"| SIG
    DS -->|"tier2_updated"| SIG
    SIG --> Panels
```

---

## 📊 범례 (Legend)

| 기호 | 의미 |
|-----|------|
| 📥 | 데이터 입력 |
| 📤 | 데이터 출력 |
| ⚙️ | 처리/엔진 |
| 💾 | 스토리지 |
| 📡 | 실시간/통신 |
| 🎯 | 전략/분석 |
| 💰 | 트레이딩 |
| 🖥️ | UI/Frontend |
| 📦 | 컨테이너/DI |
| 🌐 | 외부 서비스 |

---

## 9. 클래스 다이어그램 (상속 관계)

```mermaid
classDiagram
    class ABC {
        <<abstract>>
    }
    
    class StrategyBase {
        <<abstract>>
        +name: str
        +calculate_watchlist_score()*
        +calculate_trigger_score()*
        +generate_signal()*
    }
    
    class ScoringStrategy {
        <<abstract>>
        +calculate_score_v2()*
        +calculate_score_v3()*
    }
    
    class SeismographStrategy {
        +name: str = "Seismograph"
        +calculate_watchlist_score()
        +calculate_trigger_score()
        +calculate_score_v2()
        +calculate_score_v3()
    }
    
    StrategyBase <|-- SeismographStrategy
    ScoringStrategy <|-- SeismographStrategy
```

---

## 10. Broker Layer 의존성 체인

```mermaid
flowchart TD
    subgraph BrokerChain["🏦 Broker Layer Dependency Chain"]
        IBKR["IBKRConnector\n(루트)"]
        
        OM["OrderManager"]
        RM["RiskManager"]
        
        TRAIL["TrailingStopManager"]
        
        DT["DoubleTapManager"]
        
        IBKR --> OM
        IBKR --> RM
        IBKR --> TRAIL
        
        OM --> DT
        TRAIL --> DT
        IBKR --> DT
        
        RM -.->|"position sizing"| OM
    end
```

---

## 11. Services Layer 통신 구조

```mermaid
sequenceDiagram
    participant GUI as Sigma9Dashboard
    participant BC as BackendClient
    participant REST as RestAdapter
    participant WS as WsAdapter
    participant BE as Backend Server
    
    GUI->>BC: connect()
    BC->>REST: POST /api/status
    REST->>BE: HTTP Request
    BE-->>REST: Response
    REST-->>BC: ServerStatus
    
    BC->>WS: connect_websocket()
    WS->>BE: WSS /ws/feed
    
    loop Realtime Updates
        BE-->>WS: WATCHLIST / IGNITION / TICK
        WS-->>BC: pyqtSignal
        BC-->>GUI: watchlist_updated / ignition_updated
    end
```

