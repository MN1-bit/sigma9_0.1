# 📅 Step 1.1: Project Setup & Structure - 개발 계획서

> **작성일**: 2024-12-17  
> **목표**: Sigma9 프로젝트의 기본 폴더 구조를 생성하고, 개발 환경을 설정한다.

---

## 1. 개요 (Overview)

이 스텝은 Sigma9 프로젝트의 **기반 인프라**를 구축하는 단계이다. `masterplan.md` 12.1절에서 정의한 폴더 구조를 정확히 생성하고, Python 가상환경과 의존성 패키지를 설치한다.

**왜 필요한가?**
- 모든 후속 개발 스텝은 이 구조 위에서 진행됨
- Backend/Frontend 분리 구조가 초기부터 확립되어야 AWS 마이그레이션이 용이함
- 일관된 폴더 구조는 팀 협업과 코드 유지보수에 필수적

---

## 2. 상세 구현 계획 (Implementation Details)

### 2.1 폴더 구조 생성

`masterplan.md` 12.1절 기준 생성할 폴더:

```
Sigma9-0.1/
├── backend/                          # ← AWS로 배포
│   ├── server.py                     # FastAPI 메인 서버 (빈 스켈레톤)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── strategy_base.py          # (Step 1.2에서 구현)
│   │   ├── strategy_loader.py        # (Step 1.2에서 구현)
│   │   ├── engine.py                 # (Step 2.x에서 구현)
│   │   ├── risk_manager.py           # (Step 3.x에서 구현)
│   │   └── double_tap.py             # (Step 3.x에서 구현)
│   ├── strategies/
│   │   ├── __init__.py
│   │   └── _template.py              # 전략 템플릿 (빈 스켈레톤)
│   ├── broker/
│   │   ├── __init__.py
│   │   └── ibkr_connector.py         # (Step 2.1에서 구현)
│   ├── llm/
│   │   ├── __init__.py
│   │   └── oracle.py                 # (Step 4.1에서 구현)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py                 # (Step 5.x에서 구현)
│   │   └── websocket.py              # (Step 5.x에서 구현)
│   └── config/
│       └── settings.yaml             # 설정 파일 (기본값)
│
├── frontend/                         # ← 로컬 Windows 유지
│   ├── main.py                       # PyQt6 진입점 (빈 스켈레톤)
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── dashboard.py              # (Step 1.3에서 구현)
│   │   ├── chart_widget.py           # (Step 1.3에서 구현)
│   │   └── watchlist_widget.py       # (Step 1.3에서 구현)
│   ├── client/
│   │   ├── __init__.py
│   │   ├── api_client.py             # (Step 5.x에서 구현)
│   │   └── ws_client.py              # (Step 5.x에서 구현)
│   └── config/
│       └── settings.yaml             # 클라이언트 설정
│
└── tests/
    ├── __init__.py
    ├── test_strategies.py            # (Step 1.2에서 구현)
    └── test_api.py                   # (Step 5.x에서 구현)
```

### 2.2 requirements.txt 생성

`masterplan.md` 2절 Tech Stack 기준 패키지 목록:

**Backend:**
```
# API Server
fastapi>=0.109.0
uvicorn[standard]>=0.27.0

# Broker
ib_insync>=0.9.86

# Data Analysis
pandas>=2.2.0
pandas_ta>=0.3.14b

# LLM
openai>=1.10.0
anthropic>=0.18.0

# Logging
loguru>=0.7.2

# Database
sqlalchemy[asyncio]>=2.0.25
aiosqlite>=0.19.0
alembic>=1.13.0

# Validation
pydantic>=2.6.0
pydantic-settings>=2.1.0

# Config
pyyaml>=6.0.1
```

**Frontend:**
```
# GUI
PyQt6>=6.6.1
PyQt6-WebEngine>=6.6.0
qfluentwidgets>=1.4.0

# HTTP Client
httpx>=0.26.0

# WebSocket
websockets>=12.0

# Async Integration
qasync>=0.27.1
```

### 2.3 빈 스켈레톤 파일 내용

후속 스텝에서 구현될 파일들에 대해 placeholder 주석을 포함한 빈 파일 생성.

**예시 - `backend/server.py`:**
```python
"""
Sigma9 Backend Server - FastAPI 메인 진입점

이 파일은 AWS EC2에서 실행될 백엔드 서버의 진입점입니다.
실제 라우팅, WebSocket 핸들러는 api/ 폴더에서 import됩니다.

TODO (Step 5.x):
- FastAPI App 인스턴스 생성
- 라우터 등록
- 미들웨어 설정
"""
```

---

## 3. 검증 계획 (Verification Plan)

- [ ] 모든 폴더가 `masterplan.md` 12.1절과 일치하는지 확인
- [ ] `pip install -r requirements.txt` 성공 (에러 없이 설치 완료)
- [ ] `python backend/server.py` 실행 시 ImportError 없이 (빈 파일이므로 아무 동작 안 함)
- [ ] `python frontend/main.py` 실행 시 ImportError 없음

---

## 4. 예상 난관 (Risks)

| 난관 | 대비책 |
|------|--------|
| `qfluentwidgets` Windows 호환성 문제 | PyPI 버전 확인, 필요시 버전 고정 |
| `ib_insync` 설치 시 C 컴파일 필요할 수 있음 | wheel 패키지로 설치 시도 |
| PyQt6-WebEngine 대용량 패키지 | 별도 requirements-frontend.txt 분리 고려 |

---

## 5. 실행 계획 (Execution Order)

1. Git 저장소 초기화 확인 (`.git` 폴더 존재 여부)
2. 폴더 구조 생성 (backend/, frontend/, tests/)
3. 각 폴더에 `__init__.py` 생성
4. 스켈레톤 파일 생성 (`server.py`, `main.py`, etc.)
5. `requirements.txt` 생성
6. 가상환경 생성 및 패키지 설치
7. 검증 테스트 실행
