# Sigma9 Dataflow Documentation Index

> **Version**: v1.0 (2026-01-08)

시스템 전체 데이터 흐름을 도메인별로 문서화합니다.

## Domain Documents

| # | Domain | Description | File |
|---|--------|-------------|------|
| 1 | Market Data | Massive API → Backend → Frontend | [01_market_data.md](01_market_data.md) |
| 2 | Watchlist Lifecycle | Scan → Score → Persist → Broadcast | [02_watchlist.md](02_watchlist.md) |
| 3 | Strategy Calculation | Signals → Scoring (V1/V2/V3) | [03_strategy.md](03_strategy.md) |
| 4 | Realtime Sync | WebSocket broadcast to GUI | [04_realtime_sync.md](04_realtime_sync.md) |
| 5 | Order Execution | Ignition → Broker → Fill | [05_order_execution.md](05_order_execution.md) |
| 6 | Frontend State | API → Dashboard → Panels | [06_frontend_state.md](06_frontend_state.md) |

## Diagram Files

각 도메인에 대응하는 Graphviz DOT 파일이 `docs/diagrams/dataflow/` 디렉토리에 생성됩니다.

---

## Quick Reference: System-Wide Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL                                        │
│  Massive.com (REST/WS)  ←──────────────────────→  IBKR TWS (주문)            │
└─────────────────────────────────────────────────────────────────────────────┘
                    ↓                                      ↑
┌─────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │ MassiveWS   │───→│ TickBroad-  │───→│ Connection  │    │   Broker    │   │
│  │ Client      │    │ caster      │    │ Manager     │    │   Gateway   │   │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘   │
│         │                 │                   │                  ↑          │
│         ↓                 ↓                   │                  │          │
│  ┌─────────────┐    ┌─────────────┐           │            ┌─────────────┐  │
│  │ Realtime    │───→│ Seismograph │───────────┘            │ Ignition    │  │
│  │ Scanner     │    │ Strategy    │                        │ Monitor     │  │
│  └─────────────┘    └─────────────┘                        └─────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                    ↓ WebSocket
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────────┐  │
│  │ Backend     │───→│ Dashboard   │───→│ Panels (Watchlist, Tier2, Chart)│  │
│  │ Client      │    │             │    └─────────────────────────────────┘  │
│  └─────────────┘    └─────────────┘                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```
