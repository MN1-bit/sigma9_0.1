# @PROJECT_DNA.md

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `@PROJECT_DNA.md` |
| **역할** | AI 에이전트용 프로젝트 핵심 정보 문서 (루트 레벨) |
| **라인 수** | 341 |

## 문서 구조

### 1. Project Identity
| 항목 | 값 |
|------|---|
| **프로젝트명** | Sigma9 (Σ-IX) |
| **도메인** | 미국 마이크로캡 자동 트레이딩 시스템 |
| **Core Edge** | Volume-Price Divergence + Information Asymmetry Detection |
| **주요 언어** | Python (Backend + Frontend) |

### 2. Architecture Overview
- AWS EC2 (us-east-1): Trading Engine Server
- Local Windows: PyQt6 GUI Dashboard

### 3. Tech Stack
| 영역 | 핵심 라이브러리 |
|------|---------------|
| Backend | FastAPI, ib_insync, pandas, loguru, SQLAlchemy |
| Frontend | PyQt6, qfluentwidgets, pyqtgraph, httpx, qasync |

### 4. StrategyBase Interface
- Scanning Layer: `get_universe_filter()`, `calculate_watchlist_score()`
- Trading Layer: `initialize()`, `on_tick()`, `on_bar()`
- Configuration Layer: `get_config()`, `set_config()`

### 5. Risk Management
| 규칙 | 값 |
|------|---|
| Max Position Size | Kelly × 0.5 |
| Max Positions | 3 |
| Daily Loss Limit | -3% → 자동 정지 |
| Weekly Loss Limit | -10% |

### 6. Development Process
- Pre-Step Planning → Step Execution → Post-Step Reporting

## 🔗 외부 연결 (Connections)

### Referenced By
| 파일 | 사용 목적 |
|------|----------|
| AI Agent | 프로젝트 컨텍스트 이해 |
| 개발자 | 프로젝트 개요 파악 |
