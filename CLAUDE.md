# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 필수 참조 문서

**작업 시작 전 반드시 읽어야 할 문서:**
- `docs/Plan/masterplan.md` - 전체 시스템 설계 문서 (상세 아키텍처, 전략 로직, API 스펙)
- `@PROJECT_DNA.md` - 프로젝트 핵심 원칙 및 개발 프로세스

## Project Overview

**Sigma9 (Σ-IX)** is an automated US microcap stock trading system with volume-price divergence detection. The architecture separates Backend (FastAPI, designed for AWS EC2) from Frontend (PyQt6, local Windows client).

**Philosophy**: "Detect the Accumulation, Strike the Ignition, Harvest the Surge."

## Development Commands

### Running the Application

```bash
# Backend Server (FastAPI)
python -m backend
# API docs: http://localhost:8000/docs

# Frontend GUI (PyQt6)
python -m frontend
```

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_strategies.py -v

# Run specific test function
pytest tests/test_strategies.py -v -k "test_signal"

# Async tests are auto-configured (asyncio_mode = auto)
```

### Linting and Type Checking

```bash
# Linting
ruff check .

# Type checking
mypy .
```

### Dependencies

```bash
pip install -r requirements.txt
```

## Architecture

### Client-Server Split

```
Backend (AWS EC2)              Frontend (Local Windows)
FastAPI + uvicorn              PyQt6 + qfluentwidgets
    ↑                                ↓
    └──── WebSocket/REST ────────────┘
```

### Backend Structure (`backend/`)

| Directory | Purpose |
|-----------|---------|
| `server.py` | FastAPI app entry, lifespan management |
| `core/` | Strategy engine, risk management, tick processing |
| `strategies/` | Plugin folder for trading strategies (e.g., `seismograph.py`) |
| `broker/` | IBKR connector (order execution only) |
| `data/` | Database, Massive.com WebSocket/REST clients |
| `llm/` | LLM Oracle (read-only analyst, multi-provider) |
| `api/` | REST routes, WebSocket handlers |

### Frontend Structure (`frontend/`)

| Directory | Purpose |
|-----------|---------|
| `main.py` | PyQt6 entry point |
| `gui/` | Dashboard, charts (pyqtgraph), control panel |
| `gui/chart/` | Candlestick rendering, chart data management |
| `services/` | REST/WebSocket adapters for backend communication |

### Key Patterns

**Strategy Plugin System**: Strategies inherit from `StrategyBase` (ABC). Placed in `backend/strategies/`, automatically discovered and hot-reloadable.

**Real-time Data Pipeline**:
```
Massive WebSocket → MassiveWebSocketClient → TickBroadcaster → TickDispatcher
                                                    ↓                ↓
                                              GUI WebSocket    Strategy.on_tick()
```

**Three-Phase Trading Cycle** (상세: masterplan.md Section 3-5):
1. **Phase 1 (Setup)**: Universe Filter → Accumulation 4단계 탐지 → Watchlist 50 선정
   - Stage 1: Volume Dry-out → Stage 2: OBV Divergence → Stage 3: Accumulation Bar → Stage 4: Tight Range (VCP)
2. **Phase 2 (Trigger)**: Ignition Score ≥70 + Anti-Trap Filter 통과 시 진입
   - Tick Velocity (8×), Volume Burst (6×), Price Break, Buy Pressure
3. **Phase 3 (Harvest)**: Server-Side OCA (Stop Loss, Time Stop, Trailing) + Double Tap 재진입

### Data Sources

| Source | Role |
|--------|------|
| Massive.com REST | Universe data, historical OHLCV |
| Massive.com WebSocket | Real-time AM (1-min bars), T (ticks) |
| IBKR | Order execution only (not for market data) |

### Tiered Watchlist System (masterplan.md Section 7.4)

| Tier | 갱신 주기 | 데이터 소스 | 용도 |
|------|----------|------------|------|
| Tier 1 (Watchlist) | 1분/5분 | AM 채널 | 일반 모니터링 |
| Tier 2 (Hot Zone) | 1초 | T 채널 (틱) | 폭발 임박 종목 집중 감시 |

## Development Workflow

**Mandatory Process** (from @PROJECT_DNA.md):

1. **Pre-Step Verification**: Read `masterplan.md`, previous devlog, and step plan before starting
2. **Pre-Step Planning**: Create `docs/Plan/steps/step_X.Y_plan.md` (in Korean) before coding
3. **Step Execution**: Implement according to plan
4. **Post-Step Reporting**: Create `docs/devlog/step_X.Y_report.md` after completion
5. **Do not proceed** to next step without completing devlog

### Code Commentary Standard

All Python code must include ELI5-level comments explaining the "what" and "why" for someone with zero coding knowledge.

## Configuration

### Backend (`backend/config/settings.yaml`)
- Server settings (host, port, debug)
- IBKR connection settings
- Risk management parameters
- Logging configuration
- Market data settings

### Frontend (`frontend/config/settings.yaml`)
- Backend connection (host, port)
- GUI theme settings (dark, acrylic effects)
- Chart defaults

### Environment Variables
- `MASSIVE_API_KEY`: Massive.com API key
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`: LLM providers
- `MASSIVE_WS_ENABLED`: Enable WebSocket streaming ("true"/"false")

## Key Files Reference

| File | Description |
|------|-------------|
| `docs/Plan/masterplan.md` | **핵심 설계 문서** - 전략 상세, API 스펙, 리스크 관리, GUI 레이아웃 |
| `@PROJECT_DNA.md` | 프로젝트 정체성, 개발 프로세스, 코딩 컨벤션 |
| `docs/architecture/data_flow.md` | 데이터 파이프라인 다이어그램 (Mermaid) |
| `docs/Plan/steps/` | 단계별 구현 계획 문서 |
| `docs/devlog/` | 단계별 구현 완료 보고서 |
| `backend/core/strategy_base.py` | Strategy ABC interface (Signal, StrategyBase) |
| `backend/strategies/seismograph.py` | 메인 전략 (Accumulation + Ignition Detection) |
| `backend/core/strategy_loader.py` | Plugin loader with hot reload |

### masterplan.md 주요 섹션

| 섹션 | 내용 |
|------|------|
| Section 3 | Phase 1: Accumulation Detection (매집 4단계, 우선순위 로직) |
| Section 4 | Phase 2: Ignition Trigger (Tick Velocity, Volume Burst, Anti-Trap) |
| Section 5 | Phase 3: Harvest (OCA Orders, Trailing Stop, Double Tap) |
| Section 6 | Architecture (Class Diagram, Execution Flow, Deployment) |
| Section 7 | GUI Dashboard (Layout, Chart Features, Tiered Watchlist) |
| Section 8 | LLM Oracle (Multi-Model, v2.0 Read-Only → v5.0 Roadmap) |
| Section 11 | Risk Management (Kelly Criterion, Loss Limits, Kill Switch) |
| Section 13 | Modular Strategy Architecture (Plugin System) |

## Coding Conventions

- Python 3.10+
- Type hints on all functions
- Google-style docstrings
- Async pattern: `asyncio` + `async/await`
- ORM: SQLAlchemy 2.0 async with Repository pattern
- Logging: `loguru` with JSON structured output
- Primary language for docs/comments: Korean
