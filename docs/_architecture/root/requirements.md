# requirements.txt

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `requirements.txt` |
| **역할** | Python 패키지 의존성 목록 |
| **라인 수** | 84 |

## 의존성 구조

### Backend Dependencies

| 카테고리 | 패키지 | 버전 |
|----------|--------|------|
| **API Server** | `fastapi` | ≥0.109.0 |
| | `uvicorn[standard]` | ≥0.27.0 |
| **Broker** | `ib_insync` | ≥0.9.86 |
| **Data Analysis** | `pandas` | ≥2.2.0 |
| | `pandas_ta` | ≥0.3.14b |
| **LLM** | `openai` | ≥1.10.0 |
| | `anthropic` | ≥0.18.0 |
| **Logging** | `loguru` | ≥0.7.2 |
| **Database** | `sqlalchemy[asyncio]` | ≥2.0.25 |
| | `aiosqlite` | ≥0.19.0 |
| | `alembic` | ≥1.13.0 |
| **Scheduler** | `apscheduler` | ≥3.10.0 |
| **Validation** | `pydantic` | ≥2.6.0 |
| | `pydantic-settings` | ≥2.1.0 |
| **Config** | `pyyaml` | ≥6.0.1 |

### Frontend Dependencies

| 카테고리 | 패키지 | 버전 |
|----------|--------|------|
| **GUI** | `PyQt6` | ≥6.6.1 |
| | `PyQt6-WebEngine` | ≥6.6.0 |
| | `PyQt-Fluent-Widgets` | ≥1.4.0 |
| **HTTP** | `httpx` | ≥0.26.0 |
| **WebSocket** | `websockets` | ≥12.0 |
| **Async** | `qasync` | ≥0.27.1 |

### Development Dependencies

| 카테고리 | 패키지 | 버전 |
|----------|--------|------|
| **Testing** | `pytest` | ≥8.0.0 |
| | `pytest-asyncio` | ≥0.23.0 |
| **Type Check** | `mypy` | ≥1.8.0 |
| **Linting** | `ruff` | ≥0.1.14 |

## 설치 방법
```bash
pip install -r requirements.txt
```
