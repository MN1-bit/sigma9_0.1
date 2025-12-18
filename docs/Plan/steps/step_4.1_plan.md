# Step 4.1: Architecture Transition (Client-Server Split) 구현 계획

> **작성일**: 2025-12-18  
> **Phase**: 4 (Intelligence & Refinement)  
> **목표**: Backend/Frontend 완전 분리 + 독립 실행 가능한 서버 구축

---

## 1. 배경 및 목적

### 📌 Strategic Shift: "Architecture First"

현재 Sigma9의 `BackendClient`는 직접 Python import 방식으로 백엔드 모듈(`IBKRConnector`, `Scanner` 등)을 사용하고 있다. 이는 로컬 개발에는 편리하지만 **AWS 배포 시 GUI와 Backend가 같은 머신에서 실행되어야 하는 제약**이 있다.

이 단계에서는:
1. **Config 분리**: `settings.yaml` → `server_config.yaml` + `client_config.yaml`
2. **Server 독립화**: FastAPI 서버가 GUI 없이도 단독 실행 가능
3. **API 완성**: 모든 제어/모니터링 기능을 REST/WebSocket으로 노출
4. **스케줄러 도입**: `APScheduler`로 장 시작 시 자동 스캔 실행

---

## 2. 현재 구조 분석

### 2.1 문제점

| 영역 | 현재 상태 | 문제점 |
|------|----------|--------|
| **Config** | `backend/config/settings.yaml` 통합 | Server/Client 분리 안 됨 |
| **BackendClient** | 직접 `import IBKRConnector` | Python 프로세스 공유 필요 |
| **API 엔드포인트** | `/api/status`, `/api/control` 미완성 | 실제 엔진 연동 안 됨 |
| **스케줄러** | 없음 | 수동 스캔만 가능 |

### 2.2 현재 파일 구조

```
backend/
├── server.py                 # FastAPI 메인 (기본 구조만)
├── config/
│   └── settings.yaml         # 통합 설정 (분리 필요)
├── api/
│   ├── routes.py             # REST API (미완성)
│   └── websocket.py          # WebSocket (기본 구조만)
└── core/                     # 엔진 로직

frontend/
├── services/
│   └── backend_client.py     # 직접 import 방식 (HTTP 전환 필요)
└── gui/
```

---

## 3. Proposed Changes

### 3.1 Config 분리

#### [NEW] `backend/config/server_config.yaml`

서버 전용 설정. GUI에 노출되지 않는 민감 정보 포함.

```yaml
# 서버 네트워크 설정
server:
  host: "0.0.0.0"
  port: 8000
  debug: false

# IBKR 연결 설정
ibkr:
  host: "127.0.0.1"
  port: 7497
  client_id: 1

# 데이터베이스 설정
database:
  type: "sqlite"
  path: "data/sigma9.db"

# Polygon API 설정
polygon:
  enabled: true
  rate_limit: 5

# 스케줄러 설정 (신규)
scheduler:
  enabled: true
  timezone: "America/New_York"
  market_open_scan: true           # 장 시작 시 자동 스캔
  market_open_offset_minutes: 15   # 장 시작 15분 후 실행
```

---

#### [NEW] `frontend/config/client_config.yaml`

클라이언트 전용 설정. 서버 접속 정보만 포함.

```yaml
# 서버 연결 설정
server:
  host: "localhost"                # AWS 배포 시 EC2 IP로 변경
  port: 8000
  ws_path: "/ws/feed"
  api_path: "/api"

# 연결 설정
connection:
  auto_connect: true               # GUI 시작 시 자동 연결
  reconnect_interval: 5            # 재연결 시도 간격 (초)
  timeout: 30                      # 연결 타임아웃 (초)

# GUI 설정
gui:
  theme: "dark"
  window_opacity: 0.95
```

---

### 3.2 Server Core 완성

#### [MODIFY] `backend/server.py`

| 변경 사항 | 설명 |
|----------|------|
| Config 로더 | `server_config.yaml` 로드 로직 추가 |
| Lifespan 완성 | 시작 시 DB 초기화, IBKR 연결, 스케줄러 시작 |
| 의존성 주입 | Engine, RiskManager 등을 FastAPI dependency로 관리 |

```python
# 핵심 변경 사항
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Sigma9 Server Starting...")
    
    # 1. Config 로드
    config = load_server_config()
    app.state.config = config
    
    # 2. Database 초기화
    app.state.db = init_database(config.database)
    
    # 3. IBKR 연결 (Optional: 설정에 따라)
    if config.ibkr.auto_connect:
        app.state.ibkr = await connect_ibkr(config.ibkr)
    
    # 4. APScheduler 시작
    if config.scheduler.enabled:
        app.state.scheduler = setup_scheduler(config.scheduler)
        app.state.scheduler.start()
    
    yield
    
    # Shutdown
    if app.state.scheduler:
        app.state.scheduler.shutdown()
    logger.info("🛑 Server Shut Down.")
```

---

#### [NEW] `backend/core/scheduler.py`

APScheduler 통합 모듈.

```python
class TradingScheduler:
    """
    거래 스케줄링 담당
    - 장 시작 전 Watchlist 스캔
    - 정기 데이터 업데이트
    """
    
    def __init__(self, config, scanner_func, db):
        self.scheduler = AsyncIOScheduler(timezone=config.timezone)
        self.config = config
        self.scanner_func = scanner_func
        self.db = db
        
    def setup_market_jobs(self):
        """미국 시장 스케줄 설정"""
        # 장 시작 15분 후 스캔
        self.scheduler.add_job(
            self._run_market_open_scan,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour=9, minute=45,  # ET 9:30 + 15분
                timezone='America/New_York'
            ),
            id='market_open_scan'
        )
        
    async def _run_market_open_scan(self):
        """장 시작 자동 스캔"""
        logger.info("📊 Running scheduled market open scan...")
        await self.scanner_func(self.db)
```

---

### 3.3 API 엔드포인트 완성

#### [MODIFY] `backend/api/routes.py`

| Endpoint | Method | 설명 | 현재 상태 |
|----------|--------|------|----------|
| `/api/status` | GET | 서버/엔진/IBKR 상태 | 🟡 Stub → 실제 연동 |
| `/api/control` | POST | start/stop/kill 명령 | 🟡 Stub → 실제 연동 |
| `/api/engine/start` | POST | 트레이딩 엔진 시작 | 🔴 신규 |
| `/api/engine/stop` | POST | 트레이딩 엔진 종료 | 🔴 신규 |
| `/api/watchlist` | GET | 현재 Watchlist 조회 | 🔴 신규 |
| `/api/positions` | GET | 현재 포지션 조회 | 🔴 신규 |
| `/api/kill-switch` | POST | 긴급 정지 | 🔴 신규 |

```python
# 예시: /api/status 실제 구현
@router.get("/status")
async def get_status(request: Request):
    engine = request.app.state.engine
    ibkr = request.app.state.ibkr
    
    return {
        "server": "running",
        "engine": engine.status if engine else "not_initialized",
        "ibkr": "connected" if ibkr and ibkr.is_connected() else "disconnected",
        "uptime": get_uptime(),
        "active_positions": engine.position_count if engine else 0
    }
```

---

#### [MODIFY] `backend/api/websocket.py`

WebSocket 메시지 타입 정의 및 브로드캐스트 구현.

| Message Type | 방향 | 설명 |
|-------------|------|------|
| `market_data` | Server → Client | 실시간 가격 데이터 |
| `trade_event` | Server → Client | 거래 이벤트 (Fill, Cancel 등) |
| `watchlist_update` | Server → Client | Watchlist 변경 알림 |
| `log` | Server → Client | 서버 로그 스트리밍 |
| `status_update` | Server → Client | 상태 변경 알림 |

---

### 3.4 Server 독립 실행 검증

#### [NEW] `backend/__main__.py`

서버 직접 실행 진입점.

```python
"""
Sigma9 Backend Server
독립 실행: python -m backend
"""
import uvicorn
from backend.server import app
from backend.core.config_loader import load_server_config

def main():
    config = load_server_config()
    uvicorn.run(
        "backend.server:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.debug
    )

if __name__ == "__main__":
    main()
```

---

## 4. 변경 파일 요약

| 상태 | 파일 | 설명 |
|------|------|------|
| 🆕 NEW | `backend/config/server_config.yaml` | 서버 전용 설정 |
| 🆕 NEW | `frontend/config/client_config.yaml` | 클라이언트 전용 설정 |
| 🆕 NEW | `backend/core/scheduler.py` | APScheduler 통합 |
| 🆕 NEW | `backend/core/config_loader.py` | YAML 설정 로더 |
| 🆕 NEW | `backend/__main__.py` | 서버 독립 실행 진입점 |
| ✏️ MODIFY | `backend/server.py` | Lifespan 완성, DI 구조 |
| ✏️ MODIFY | `backend/api/routes.py` | 실제 API 엔드포인트 구현 |
| ✏️ MODIFY | `backend/api/websocket.py` | 메시지 타입 정의 |
| ⏳ DEFER | `frontend/services/backend_client.py` | Step 4.2에서 HTTP 방식으로 전환 |

---

## 5. 의존성 추가

`requirements.txt`에 추가:

```txt
apscheduler>=3.10.0       # Job Scheduler
pyyaml>=6.0               # YAML Config Loader (기존에 있으면 생략)
pydantic-settings>=2.0    # Settings 관리
```

---

## 6. Verification Plan

### 6.1 자동화 테스트

#### [NEW] `tests/test_server.py`

```powershell
# 서버 API 테스트
pytest tests/test_server.py -v
```

테스트 항목:
- `/api/status` 엔드포인트 응답 검증
- `/api/control` 명령 처리 검증
- WebSocket 연결 및 메시지 수신 검증

---

### 6.2 수동 검증

#### Step 1: 서버 독립 실행 테스트

```powershell
# 터미널 1: 서버 실행
cd D:\Codes\Sigma9-0.1
python -m backend

# 예상 출력:
# 🚀 Sigma9 Server Starting...
# INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### Step 2: API 엔드포인트 테스트

```powershell
# 터미널 2: API 호출
curl http://localhost:8000/api/status

# 예상 응답:
# {"server": "running", "engine": "stopped", "ibkr": "disconnected", ...}
```

#### Step 3: GUI 없이 서버만 실행 확인

서버가 `ImportError` 없이 독립 실행되는지 확인:
- PyQt6 import 없음
- frontend 모듈 의존성 없음

---

## 7. 다음 단계 (Step 4.2)

이 단계 완료 후 **Step 4.2: Frontend Integration (Client Adapter)**에서:
- `BackendClient` → HTTP/WebSocket 방식으로 전환
- `RestAdapter`, `WsAdapter` 클래스 구현
- GUI와 원격 서버 연결 검증

---

## 8. 위험 요소 및 대응

| 위험 | 확률 | 대응 |
|------|------|------|
| IBKR 연결 실패 시 서버 크래시 | 중 | Optional 연결로 처리, 에러 핸들링 강화 |
| Config 마이그레이션 중 설정 누락 | 저 | 기존 `settings.yaml`과 1:1 매핑 검증 |
| APScheduler 타임존 이슈 | 저 | `America/New_York` 명시적 설정 |

---

> **"Architecture First"**: 기능 추가 전 구조를 바로잡아 기술 부채 방지
