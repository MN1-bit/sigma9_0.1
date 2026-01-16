# Backend Overview

> 📍 **Location**: `backend/`  
> **Role**: AWS EC2에 배포되는 서버 레이어 - FastAPI 기반 REST/WebSocket API 및 트레이딩 엔진

---

## 하위 모듈

| 모듈 | 파일 수 | 설명 |
|------|---------|------|
| [core/](./core/_overview.md) | 26 | 핵심 비즈니스 로직 |
| [api/](./api/_overview.md) | 17 | REST/WebSocket API |
| [models/](./models/_overview.md) | 8 | 데이터 모델 |
| [strategies/](./strategies/_overview.md) | - | 전략 플러그인 |
| [broker/](./broker/_overview.md) | 2 | IBKR 연동 |
| [startup/](./startup/_overview.md) | 5 | 서버 시작 모듈 |
| [llm/](./llm/_overview.md) | 2 | LLM Oracle |

---

## 진입점 파일

| 파일 | 역할 |
|------|------|
| `server.py` | FastAPI 메인 서버 |
| `container.py` | DI Container (dependency-injector) |
| `__main__.py` | 모듈 실행 진입점 |
