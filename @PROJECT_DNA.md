<root_instruction>
  <critical_warning>
    YOU MUST READ THIS DOCUMENT BEFORE GENERATING ANY CODE.
    IGNORING THESE RULES WILL CAUSE SYSTEM CRASH.
  </critical_warning>

  <project_dna>
# 🧬 PROJECT_DNA.md — Σ-IX (Sigma-Nine)

> **For AI Agent (Google Antigravity)**  
> **Version**: 3.1 | **Last Updated**: 2026-01-08  
> **Philosophy**: "Detect the Accumulation, Strike the Ignition, Harvest the Surge."

---

## 🎯 Project Identity

| Field | Value |
|-------|-------|
| **Project Name** | Sigma9 (Σ-IX) |
| **Domain** | Automated US Microcap Stock Trading System |
| **Core Edge** | Volume-Price Divergence + Information Asymmetry Detection |
| **Language** | Python (Backend + Frontend) |
| **Primary Language** | Korean (code comments, docs) |

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    🇺🇸 AWS EC2 (us-east-1)                             │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                     Trading Engine Server                         │  │
│  │  Strategy Engine (Scanning + Trading) │ IBKR Gateway (TWS)        │  │
│  │  LLM Oracle          │ Risk Manager    │ FastAPI + WebSocket      │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                     ▲
                                     │ WebSocket (Data Push) / REST (Commands)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        🇰🇷 Local Client (Windows)                       │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  PyQt6 GUI Dashboard + pyqtgraph Charts                           │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
Sigma9-0.1/
├── backend/                          # ← AWS 배포 대상
│   ├── server.py                     # FastAPI 메인 서버 (~200줄)
│   ├── container.py                  # DI Container (dependency-injector)
│   ├── core/
│   │   ├── interfaces/               # 추상 인터페이스
│   │   │   └── scoring.py            # ScoringStrategy 인터페이스
│   │   ├── strategy_base.py          # 전략 추상 인터페이스
│   │   ├── strategy_loader.py        # 플러그인 동적 로더
│   │   ├── risk_manager.py           # 리스크 관리
│   │   └── double_tap.py             # 재진입 로직
│   ├── startup/                      # 서버 시작 로직 모듈화
│   │   ├── config.py, database.py, realtime.py, shutdown.py
│   ├── models/                       # 중앙 모델 저장소
│   │   ├── tick.py, watchlist.py, order.py, risk.py, backtest.py
│   ├── strategies/                   # 전략 플러그인 폴더
│   │   ├── seismograph/              # 메인 전략 (패키지)
│   │   │   ├── strategy.py           # SeismographStrategy
│   │   │   ├── signals/              # 시그널 계산 모듈
│   │   │   └── scoring/              # 점수 계산 (v1, v2, v3)
│   │   └── _template.py              # 신규 전략 템플릿
│   ├── broker/
│   │   └── ibkr_connector.py         # IBKR 연동 (ib_insync)
│   ├── llm/
│   │   └── oracle.py                 # LLM Intelligence Layer
│   └── api/
│       ├── routes/                   # REST API (12개 도메인 분할)
│       │   ├── status.py, control.py, watchlist.py ...
│       └── websocket.py              # WebSocket 핸들러
│
├── frontend/                         # ← Windows 로컬 유지
│   ├── main.py                       # PyQt6 진입점
│   ├── gui/
│   │   ├── dashboard.py              # 메인 대시보드
│   │   ├── panels/                   # 분리된 UI 패널
│   │   │   ├── watchlist_panel.py, tier2_panel.py, log_panel.py
│   │   ├── state/                    # 상태 관리
│   │   │   └── dashboard_state.py
│   │   └── chart/                    # pyqtgraph 차트
│   └── services/
│       ├── backend_client.py         # 어댑터 관리
│       ├── rest_adapter.py           # REST 클라이언트
│       └── ws_adapter.py             # WebSocket 클라이언트
│
├── docs/
│   └── context/                      # 📘 핵심 정책 문서
│       ├── ARCHITECTURE.md           # 시스템 아키텍처 → .agent/Ref/archt.md 참조
│       ├── REFACTORING.md            # 리팩터링 가이드
│       └── strategy/                 # 전략별 문서
│
└── tests/
    ├── test_strategies.py
    └── test_api.py
```

---

## 🛠️ Tech Stack

### Backend (AWS EC2)
| Component | Library | Purpose |
|-----------|---------|---------|
| API Server | `FastAPI` + `uvicorn` | REST + WebSocket |
| Broker | `ib_insync` | IBKR 연동, OCA 주문 |
| Data Analysis | `pandas` + `pandas_ta` | OBV, ATR, VWAP |
| LLM | `openai` / `anthropic` | 해설 및 분석 |
| Logging | `loguru` | 컬러 로깅 |
| Database | `SQLite` (WAL) | 메인 DB |
| ORM | `SQLAlchemy` + `Alembic` | 비동기 ORM + 마이그레이션 |
| Async | `asyncio` | 비동기 처리 |

### Frontend (Local Windows)
| Component | Library | Purpose |
|-----------|---------|---------|
| GUI | `PyQt6` + `qfluentwidgets` | 데스크탑 대시보드 (Glassmorphism) |
| Charts | `pyqtgraph` | 고성능 네이티브 차트 |
| HTTP | `httpx` | REST 클라이언트 |
| WebSocket | `websockets` | 실시간 데이터 수신 |
| Async | `qasync` | PyQt + asyncio 통합 |

---

## 🎨 Design System

| Feature | Spec |
|---------|------|
| **Theme** | Glassmorphism (Acrylic Effect) |
| **Library** | `PyQt-Fluent-Widgets` |
| **Policy** | Centralized Theme Management (No ad-hoc styling) |

---

## ⚙️ StrategyBase Interface

> **핵심 변경**: Scanning 로직이 Strategy Layer에 통합됨

### Scanning Layer (Phase 1 & 2)
| Method | Description |
|--------|-------------|
| `get_universe_filter()` | Universe 필터 조건 반환 (가격, 시가총액, Float 등) |
| `calculate_watchlist_score()` | 일봉 기반 Watchlist 점수 (예: Accumulation Score) |
| `calculate_trigger_score()` | 실시간 Trigger 점수 (예: Ignition Score) |
| `get_anti_trap_filter()` | Anti-Trap 필터 조건 반환 |

### Trading Layer
| Method | Description |
|--------|-------------|
| `initialize()` | 전략 초기화 |
| `on_tick()` | 실시간 틱 처리 → Signal |
| `on_bar()` | 분봉/일봉 처리 → Signal |
| `on_order_filled()` | 주문 체결 콜백 |

### Configuration Layer
| Method | Description |
|--------|-------------|
| `get_config()` | 전략 설정값 반환 |
| `set_config()` | 전략 설정값 변경 (런타임) |

---

## 🔌 API Endpoints

```
REST:
  GET  /api/watchlist          - Watchlist 조회
  GET  /api/positions          - 현재 포지션
  POST /api/kill-switch        - 긴급 정지
  POST /api/order              - 수동 주문
  GET  /api/strategies         - 전략 목록
  POST /api/strategies/{name}/load   - 전략 로드
  POST /api/strategies/{name}/reload - 전략 핫 리로드

WebSocket:
  WS /ws/market               - 실시간 시장 데이터
  WS /ws/trade                - 거래 이벤트 스트림
```

---

## 🧠 LLM Oracle (v2.0 = Read-Only)

| Method | Description | Permission |
|--------|-------------|------------|
| `explain_selection()` | 종목 선정 이유 해설 | 🟢 Read |
| `technical_analysis()` | 기술적 지표 해설 | 🟢 Read |
| `why_is_it_hot()` | 외부 API 기반 급등 이유 | 🟢 Read |
| `trade_journal_entry()` | 거래 사후 분석 | 🟢 Read |

> **Future Roadmap**: v3.0 (Suggest) → v4.0 (Adjust) → v5.0 (Execute)

---

## 🛡️ Risk Management

| Rule | Value |
|-------|-------|
| Max Position Size | Kelly × 0.5 (Half Kelly) |
| Max Concurrent Positions | 3 |
| Per-Trade Stop | -5% |
| Daily Loss Limit | -3% → 봇 자동 정지 |
| Weekly Loss Limit | -10% → 수동 리뷰 |

---

## 📌 Design Principles

1. **Backend/Frontend 분리**: AWS 마이그레이션 용이성 확보
2. **Strategy = Scanning + Trading**: 전략이 자체 스캐닝 로직 보유
3. **Strategy Pattern + Plugin Architecture**: 런타임 전략 교체 가능
4. **ABC 인터페이스**: `StrategyBase` 상속 필수
5. **Hot Reload**: 서버 재시작 없이 전략 파일 교체
6. **Server-Side OCA**: 모든 청산 로직은 서버에서 처리

---

## 🛣️ Development Process (Strict Mandate)

> **⚠️ CRITICAL**: All development MUST follow the granular steps defined in `docs/Plan/steps/development_steps.md`.

0. **🔴 Pre-Step Verification (신규 스탭 진입 전 반드시 확인)**:
   - **MUST READ** the following files before entering ANY new step:
     - `.agent/Ref/MPlan.md` — 전체 설계 및 아키텍처 확인
     - `docs/Plan/steps/development_steps.md` — 스탭 목록 및 진행 상황 확인
     - Previous step's devlog (`docs/devlog/step_X.Y_report.md`) — 이전 스탭 결과 확인
   - **Purpose**: 컨텍스트 연속성 보장, 중복 작업 방지, 일관성 유지
   - **Violation**: 이 단계를 생략하면 잘못된 구현 또는 설계 충돌 발생 가능

1. **Pre-Step Planning (In Korean)**:
   - **Before** writing any code for Step `X.Y`, you MUST write a detailed plan in `docs/Plan/steps/step_X.Y_plan.md`.
   - Language: Korean (한국어).
   - Content: Detailed logic, class design, file structure changes, and verification strategy.

2. **Step Execution**: 
   - Implement the step according to the plan.
   - Do not deviate without updating the plan.

3. **Post-Step Reporting (Devlog)**: 
   - **After** completing the step, you MUST create a log file in `docs/devlog/`.
   - File Naming: `step_X.Y_report.md`.
   - Content: What was implemented, obstacles faced, solution details, and verification results.
   - Do not proceed to next step without permission.

4. **Restriction**: You cannot proceed to Step `X.Y + 1` until the Devlog for Step `X.Y` is completed.

5. **Code Commentary (ELI5 Standard)**:
   - All Python code MUST include detailed comments explaining the logic.
   - **Target Audience**: Someone with ZERO coding knowledge (explain "what" and "why", not just "how").
   - **Requirement**: Break down complex logic into plain language sentences.

---

## 🔗 Key Files Reference

| File | Description |
|------|-------------|
| `.agent/Ref/archt.md` | 시스템 아키텍처 |
| `docs/context/REFACTORING.md` | 리팩터링 가이드 |
| `docs/context/strategy/seismograph.md` | Seismograph 전략 (Score V3 포함) |
| `docs/context/strategy/mep.md` | MEP 실행 프로토콜 |
| `docs/context/strategy/ignition.md` | Ignition Score |
| `backend/strategies/seismograph.py` | 메인 전략 구현 |

---

## 💻 Development Commands

### Running the Application

```bash
# Backend Server (FastAPI)
python -m backend
# API docs: http://localhost:8000/docs

# Frontend GUI (PyQt6)
python -m frontend
```

### Testing & Linting

```bash
# 필수 검증 (모든 PR 전 실행)
ruff format && ruff check .   # Lint + Format
mypy backend/                 # Type checking
lint-imports                  # 경계 위반 검사 (필수)
pydeps backend --show-cycles --no-output  # 순환 의존성 검사

# 테스트
pytest                        # Run all tests
```

### 리팩터링 도구 정책

> **참조**: `docs/context/REFACTORING.md` (상세 정책)

| 도구 | 버전 | 강제 조건 |
|------|------|-----------|
| `import-linter` | 설치됨 | `lint-imports` 실패 시 PR 머지 불가 |
| `pydeps` | 3.x | 순환 의존성 검출 시 리팩터링 필수 |
| `dependency-injector` | 4.x | 전역 싱글톤 사용 금지 |

### 코드 품질 기준

- **신규 파일**: ≤ 500 라인
- **신규 클래스**: ≤ 30 메서드
- **금지 패턴**: `get_*_instance()`, 전역 `_instance` 변수
- **DI 필수**: 신규 서비스는 `Container`에 등록 후 주입

---

## 📋 Coding Conventions

- **Language**: Python 3.10+
- **Type Hints**: 모든 함수에 타입 힌트 사용
- **Docstrings**: Google style
- **Async**: `asyncio` + `async/await` 패턴
- **Config**: YAML 파일 (`settings.yaml`)
- **Logging**: `loguru` + JSON Structured Logging
- **Database**: Async Session + Repository Pattern
- **Error Handling**: Global Exception Middleware
- **CI/CD**: GitHub Actions (Lint/Test on Push)

---

> **"Smart money leaves footprints. We just need to read them."**
  </project_dna>
</root_instruction>
