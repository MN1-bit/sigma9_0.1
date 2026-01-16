# requirements.txt

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `requirements.txt` |
| **역할** | Python 패키지 의존성 목록 (Backend + Frontend 통합) |
| **라인 수** | 84 |

## 의존성 분류

### Backend Dependencies

#### API Server
| 패키지 | 버전 | 설명 |
|--------|------|------|
| `fastapi` | ≥0.109.0 | REST API 프레임워크 |
| `uvicorn[standard]` | ≥0.27.0 | ASGI 서버 |

#### Broker (IBKR)
| 패키지 | 버전 | 설명 |
|--------|------|------|
| `ib_insync` | ≥0.9.86 | Interactive Brokers 연동 |

#### Data Analysis
| 패키지 | 버전 | 설명 |
|--------|------|------|
| `pandas` | ≥2.2.0 | 데이터 분석 |
| `pandas_ta` | ≥0.3.14b | 기술적 분석 지표 |

#### LLM Integration
| 패키지 | 버전 | 설명 |
|--------|------|------|
| `openai` | ≥1.10.0 | OpenAI API |
| `anthropic` | ≥0.18.0 | Anthropic API |

#### Database
| 패키지 | 버전 | 설명 |
|--------|------|------|
| `sqlalchemy[asyncio]` | ≥2.0.25 | ORM (비동기) |
| `aiosqlite` | ≥0.19.0 | 비동기 SQLite |
| `aiolimiter` | ≥1.1.0 | Rate Limiting |
| `alembic` | ≥1.13.0 | DB 마이그레이션 |

#### Scheduler & Config
| 패키지 | 버전 | 설명 |
|--------|------|------|
| `apscheduler` | ≥3.10.0 | Job 스케줄러 |
| `pydantic` | ≥2.6.0 | 데이터 검증 |
| `pydantic-settings` | ≥2.1.0 | 설정 관리 |
| `pyyaml` | ≥6.0.1 | YAML 파싱 |
| `loguru` | ≥0.7.2 | 로깅 |

---

### Frontend Dependencies

#### GUI
| 패키지 | 버전 | 설명 |
|--------|------|------|
| `PyQt6` | ≥6.6.1 | GUI 프레임워크 |
| `PyQt6-WebEngine` | ≥6.6.0 | 웹 엔진 |
| `PyQt-Fluent-Widgets` | ≥1.4.0 | Fluent Design 위젯 |

#### Network
| 패키지 | 버전 | 설명 |
|--------|------|------|
| `httpx` | ≥0.26.0 | HTTP 클라이언트 |
| `websockets` | ≥12.0 | WebSocket 클라이언트 |
| `qasync` | ≥0.27.1 | PyQt + asyncio 통합 |

---

### Development Dependencies

| 패키지 | 버전 | 설명 |
|--------|------|------|
| `pytest` | ≥8.0.0 | 테스트 프레임워크 |
| `pytest-asyncio` | ≥0.23.0 | 비동기 테스트 |
| `mypy` | ≥1.8.0 | 타입 체크 |
| `ruff` | ≥0.1.14 | 린팅 |

## 🔗 연결

### 설치 명령
```bash
pip install -r requirements.txt
```

### 참조
| 문서 | 설명 |
|------|------|
| `masterplan.md` 2절 | Tech Stack 기준 |
