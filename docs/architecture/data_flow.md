# Sigma9 Data Flow Diagram

> **버전**: v2.5 (Step 2.5 완료 후)  
> **업데이트**: 2025-12-18

---

## 전체 데이터 흐름

```mermaid
flowchart TB
    subgraph External["📡 External Data Sources"]
        POLYGON["Polygon.io API"]
        IBKR["IBKR TWS/Gateway"]
    end

    subgraph Database["💾 Local Storage"]
        SQLITE[("SQLite DB<br/>market_data.db")]
        JSON["watchlist.json"]
    end

    subgraph Backend["⚙️ Backend Engine"]
        subgraph DataPipeline["Data Pipeline"]
            POLY_LOADER["PolygonLoader<br/>(Historical OHLCV)"]
            DB_MODULE["DatabaseManager<br/>(SQLAlchemy)"]
        end

        subgraph Scanner["Phase 1: Scanner"]
            SCANNER_ORCH["ScannerOrchestrator"]
            SEISMO_SCAN["SeismographStrategy<br/>calculate_watchlist_score()"]
        end

        subgraph Trigger["Phase 2: Trigger"]
            IBKR_CONN["IBKRConnector<br/>(Real-time Ticks)"]
            SEISMO_TRIG["SeismographStrategy<br/>on_tick() + Ignition"]
        end

        subgraph Core["Core Modules"]
            STRATEGY_LOADER["StrategyLoader<br/>(Plugin System)"]
            TECH_ANALYSIS["TechnicalAnalysis<br/>(VWAP, ATR, SL/TP)"]
        end
    end

    subgraph Frontend["🖥️ PyQt6 Dashboard"]
        DASHBOARD["Sigma9Dashboard"]
        CHART["ChartWidget<br/>(TradingView LWC)"]
        WATCHLIST_UI["Watchlist Panel"]
        LOG_CONSOLE["Log Console"]
        STRATEGY_COMBO["Strategy Dropdown"]
    end

    %% Data Flow
    POLYGON -->|"Grouped Daily API"| POLY_LOADER
    POLY_LOADER -->|"Store OHLCV"| SQLITE
    
    SQLITE -->|"Load History"| SCANNER_ORCH
    SCANNER_ORCH -->|"Daily Data"| SEISMO_SCAN
    SEISMO_SCAN -->|"Accum Score"| SCANNER_ORCH
    SCANNER_ORCH -->|"Top 50"| JSON
    
    JSON -->|"Load Watchlist"| IBKR_CONN
    IBKR -->|"Real-time Ticks"| IBKR_CONN
    IBKR_CONN -->|"Tick Stream"| SEISMO_TRIG
    SEISMO_TRIG -->|"BUY Signal"| DASHBOARD
    
    SEISMO_TRIG -->|"Price Data"| TECH_ANALYSIS
    TECH_ANALYSIS -->|"Indicators"| CHART
    
    STRATEGY_LOADER -->|"Load/Reload"| SEISMO_SCAN
    STRATEGY_LOADER -->|"Load/Reload"| SEISMO_TRIG
    STRATEGY_COMBO -->|"Select Strategy"| STRATEGY_LOADER
    
    JSON -->|"Display"| WATCHLIST_UI
    SEISMO_TRIG -->|"Log Events"| LOG_CONSOLE
    
    %% Styling
    classDef external fill:#4a5568,stroke:#718096,color:#fff
    classDef storage fill:#2d3748,stroke:#4a5568,color:#fff
    classDef backend fill:#2b6cb0,stroke:#3182ce,color:#fff
    classDef frontend fill:#276749,stroke:#38a169,color:#fff
    
    class POLYGON,IBKR external
    class SQLITE,JSON storage
    class POLY_LOADER,DB_MODULE,SCANNER_ORCH,SEISMO_SCAN,SEISMO_TRIG,IBKR_CONN,STRATEGY_LOADER,TECH_ANALYSIS backend
    class DASHBOARD,CHART,WATCHLIST_UI,LOG_CONSOLE,STRATEGY_COMBO frontend
```

---

## 데이터 흐름 요약

| Phase | 흐름 | 설명 |
|-------|------|------|
| **Data Ingestion** | Polygon → SQLite | 일봉 히스토리 수집 및 저장 |
| **Phase 1: Scanning** | SQLite → Strategy → JSON | 매집 점수 계산 → Top 50 Watchlist 생성 |
| **Phase 2: Trigger** | IBKR → Strategy → Signal | 실시간 틱 분석 → Ignition 감지 → BUY Signal |
| **Visualization** | Strategy → Chart | VWAP, ATR, 마커 렌더링 |
| **Plugin System** | Dropdown → Loader → Strategy | 전략 동적 로드/핫 리로드 |

---

## 모듈 매핑

| 다이어그램 노드 | 실제 파일 |
|----------------|----------|
| `PolygonLoader` | `backend/data/polygon_loader.py` |
| `DatabaseManager` | `backend/data/database.py` |
| `ScannerOrchestrator` | `backend/data/scanner.py` |
| `SeismographStrategy` | `backend/strategies/seismograph.py` |
| `IBKRConnector` | `backend/broker/ibkr_connector.py` |
| `StrategyLoader` | `backend/core/strategy_loader.py` |
| `TechnicalAnalysis` | `backend/core/technical_analysis.py` |
| `Sigma9Dashboard` | `frontend/gui/dashboard.py` |
| `ChartWidget` | `frontend/gui/chart_widget.py` |
