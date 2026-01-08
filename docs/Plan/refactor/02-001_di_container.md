# DI Container 도입 리팩터링 계획서

> **작성일**: 2026-01-08 00:29
> **우선순위**: 2 | **예상 소요**: 3-4h | **위험도**: 낮음
> **선행 조건**: 01-001 인터페이스 추출 완료

## 1. 목표

- Singleton Anti-Pattern 제거
- `dependency-injector` 라이브러리를 사용한 DI Container 도입
- 테스트 용이성 확보 (Mock 주입 가능)
- 전역 상태 오염 방지

### 현재 문제점 (Singleton Anti-Pattern)

| 모듈 | 패턴 | 문제점 |
|------|------|--------|
| `realtime_scanner.py` | `_scanner_instance` | 테스트 어려움, 상태 오염 |
| `ignition_monitor.py` | `get_ignition_monitor()` | 의존성 주입 불가 |
| `backend_client.py` | `BackendClient.instance()` | 멀티 인스턴스 테스트 불가 |

## 2. 영향 분석

### 변경 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `backend/container.py` | 🆕 신규 | DI Container 정의 |
| `backend/server.py` | 📝 수정 | Container 초기화 |
| `backend/core/realtime_scanner.py` | 📝 수정 | Singleton 제거, DI 수용 |
| `backend/core/ignition_monitor.py` | 📝 수정 | Singleton 제거, DI 수용 |
| `backend/api/routes.py` | 📝 수정 | Container에서 의존성 주입 |

### 영향받는 모듈

- `backend/` 전체 - Container 의존성 추가
- `tests/` - Mock 주입 패턴 변경

### 의존 관계

```
Container
├── ScoringStrategy (인터페이스) → SeismographStrategy (구현체)
├── RealtimeScanner
├── IgnitionMonitor
├── MassiveClient
└── WatchlistStore
```

## 3. 실행 계획

### Step 1: dependency-injector 설치 확인

```bash
pip show dependency-injector || pip install dependency-injector
```

### Step 2: Container 정의

```python
# backend/container.py
from dependency_injector import containers, providers
from backend.core.interfaces.scoring import ScoringStrategy
from backend.strategies.seismograph import SeismographStrategy
from backend.core.realtime_scanner import RealtimeScanner
from backend.core.ignition_monitor import IgnitionMonitor
from backend.data.massive_client import MassiveClient

class Container(containers.DeclarativeContainer):
    """Sigma9 DI Container"""
    
    config = providers.Configuration()
    
    # Data Layer
    massive_client = providers.Singleton(MassiveClient)
    
    # Strategy Layer (인터페이스 → 구현체)
    scoring_strategy = providers.Singleton(
        SeismographStrategy,
        # 필요한 의존성 주입
    )
    
    # Core Layer
    realtime_scanner = providers.Singleton(
        RealtimeScanner,
        massive_client=massive_client,
        scoring_strategy=scoring_strategy,
    )
    
    ignition_monitor = providers.Singleton(
        IgnitionMonitor,
        scanner=realtime_scanner,
    )
```

### Step 3: Singleton 패턴 제거

각 모듈에서 `_instance` 변수와 `get_*_instance()` 함수 제거:

```python
# Before
_scanner_instance = None
def get_realtime_scanner():
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = RealtimeScanner()
    return _scanner_instance

# After
class RealtimeScanner:
    def __init__(self, massive_client, scoring_strategy):
        self._client = massive_client
        self._strategy = scoring_strategy
```

### Step 4: server.py에서 Container 초기화

```python
# backend/server.py
from backend.container import Container

container = Container()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Container 초기화
    container.wire(modules=[__name__, "backend.api.routes"])
    yield
    # Cleanup
```

### Step 5: routes.py에서 의존성 주입

```python
# backend/api/routes.py
from dependency_injector.wiring import inject, Provide
from backend.container import Container

@router.get("/watchlist")
@inject
async def get_watchlist(
    scanner: RealtimeScanner = Depends(Provide[Container.realtime_scanner])
):
    return scanner.get_watchlist()
```

## 4. 검증 계획

### 자동화 테스트

```bash
# 1. Import 경계 검증
lint-imports

# 2. 기존 테스트 실행
pytest tests/ -v

# 3. mypy 타입 체크
mypy backend/container.py backend/server.py
```

### 수동 테스트

- [ ] Backend 서버 정상 시작: `python -m backend`
- [ ] API `/status` 엔드포인트 응답 확인
- [ ] Watchlist 데이터 정상 수신 확인
- [ ] Frontend 연결 후 실시간 데이터 동작 확인

## 5. 롤백 계획

```bash
# 문제 발생 시 롤백
git checkout HEAD -- backend/server.py
git checkout HEAD -- backend/core/realtime_scanner.py
git checkout HEAD -- backend/core/ignition_monitor.py
git checkout HEAD -- backend/api/routes.py
rm backend/container.py
```

---

**참조 문서**:
- [REFACTORING.md](./REFACTORING.md) - 섹션 6. Dependency Injection 패턴
- [dependency-injector 공식 문서](https://python-dependency-injector.ets-labs.org/)
