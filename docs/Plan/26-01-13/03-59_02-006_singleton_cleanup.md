# 02-006: 전체 싱글톤 패턴 정리 계획서

> **작성일**: 2026-01-10 05:25  
> **우선순위**: 2 (DI Container 후속) | **예상 소요**: 2h | **위험도**: 낮음

---

## 1. 목표

프로젝트 전체 싱글톤 패턴 현황 파악 및 정리.  
`@PROJECT_DNA.md` 금지 정책: `get_*_instance()`, 전역 `_instance` 변수

---

## 2. 현황 분석

### 2.1 발견된 싱글톤 패턴

| 파일 | 패턴 | 현재 상태 | 조치 필요 |
|------|------|----------|----------|
| `backend/data/watchlist_store.py` | `_store_instance` + `get_watchlist_store()` | ⚠️ DeprecationWarning 추가됨 | 레거시 코드 제거 |
| `backend/data/watchlist_store.py` | `WatchlistWriter._instance` (내부 클래스) | 📌 스레드 관리 목적 | 유지 (내부용) |
| `backend/data/symbol_mapper.py` | `_mapper_instance` + `get_symbol_mapper()` | ⚠️ DeprecationWarning 추가됨 | 레거시 코드 제거 |
| `frontend/services/backend_client.py` | `BackendClient._instance` + `instance()` | 📋 대기 | Frontend DI 도입 필요 |
| `frontend/gui/theme.py` | `ThemeManager._instance` | 📌 전역 테마 관리 | 현행 유지 (Frontend 정책) |

### 2.2 이미 DI Container에 등록된 모듈

| 모듈 | Container Provider | 상태 |
|------|-------------------|------|
| `WatchlistStore` | `container.watchlist_store()` | ✅ 등록됨 |
| `SymbolMapper` | `container.symbol_mapper()` | ✅ 등록됨 |
| `RealtimeScanner` | `container.realtime_scanner()` | ✅ 싱글톤 제거 완료 (02-002) |
| `IgnitionMonitor` | `container.ignition_monitor()` | ✅ 싱글톤 제거 완료 (02-003) |

### 2.3 기존 계획서 현황

| 계획서 | 대상 | 상태 |
|--------|------|------|
| [02-004](file:///d:/Codes/Sigma9-0.1/docs/Plan/refactor/02-004_watchlist_store_singleton.md) | `WatchlistStore` | 📌 DeprecationWarning만 추가, 레거시 제거 미완료 |
| [02-005](file:///d:/Codes/Sigma9-0.1/docs/Plan/refactor/02-005_symbol_mapper_singleton.md) | `SymbolMapper` | 📌 DeprecationWarning만 추가, 레거시 제거 미완료 |

---

## 3. 영향 분석

### 3.1 Backend 모듈 (`watchlist_store.py`, `symbol_mapper.py`)

#### 변경 대상 파일

| 파일 | 변경 유형 | 변경 내용 |
|------|----------|----------|
| [watchlist_store.py](file:///d:/Codes/Sigma9-0.1/backend/data/watchlist_store.py) | 수정 | 레거시 `_store_instance`, `get_watchlist_store()`, 편의 함수 제거 |
| [symbol_mapper.py](file:///d:/Codes/Sigma9-0.1/backend/data/symbol_mapper.py) | 수정 | 레거시 `_mapper_instance`, `get_symbol_mapper()`, 편의 함수 제거 |

#### 레거시 함수 사용처 검색 결과

```
watchlist_store.py:
  - save_watchlist(), load_watchlist(), merge_watchlist() → 내부 편의 함수 (get_watchlist_store() 호출)
  
symbol_mapper.py:
  - MASSIVE_TO_IBKR(), IBKR_TO_MASSIVE() → 내부 편의 함수 (get_symbol_mapper() 호출)
```

> **참고**: Container 등록 후 외부 호출자는 이미 마이그레이션됨. 내부 편의 함수만 정리 대상.

### 3.2 Frontend 모듈 (`backend_client.py`, `theme.py`)

> [!IMPORTANT]
> Frontend 모듈은 별도 DI 아키텍처 검토 필요. 현재는 PyQt 기반 싱글톤 패턴 유지.

| 모듈 | 분석 결과 |
|------|----------|
| `BackendClient` | PyQt QObject 상속, Signal 사용. 전역 instance() 패턴 유지 중. Frontend DI Container 부재로 현행 유지 권장. |
| `ThemeManager` | 전역 테마 관리자. 앱 전체에서 단일 인스턴스 필요. 현행 유지. |

### 3.3 `WatchlistWriter` 내부 클래스

```python
# backend/data/watchlist_store.py L59-76
class WatchlistWriter:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
```

> [!NOTE]
> `WatchlistWriter`는 파일 I/O 전담 스레드 관리를 위한 내부 클래스.  
> Race Condition 방지 목적으로 싱글톤 패턴이 필요함. **유지**.

---

## 4. 실행 계획

### Phase 1: Backend 레거시 싱글톤 제거

#### Step 1: `watchlist_store.py` 레거시 코드 제거

**제거 대상 (L388-425):**
```python
# 싱글톤 인스턴스 (삭제)
_store_instance: Optional[WatchlistStore] = None

def get_watchlist_store() -> WatchlistStore:  # 삭제
    ...

# 편의 함수 (삭제)
def save_watchlist(watchlist: List[Dict[str, Any]]) -> Path:  # 삭제
def load_watchlist() -> List[Dict[str, Any]]:  # 삭제
def merge_watchlist(...) -> List[Dict[str, Any]]:  # 삭제
```

**사전 확인**: 편의 함수 외부 사용처 없음 확인 필요 (`grep_search`)

#### Step 2: `symbol_mapper.py` 레거시 코드 제거

**제거 대상 (L230-262):**
```python
# 싱글톤 인스턴스 (삭제)
_mapper_instance: Optional[SymbolMapper] = None

def get_symbol_mapper() -> SymbolMapper:  # 삭제
    ...

# 편의 함수 (삭제)
def MASSIVE_TO_IBKR(symbol: str) -> Optional[str]:  # 삭제
def IBKR_TO_MASSIVE(symbol: str) -> Optional[str]:  # 삭제
```

**사전 확인**: 편의 함수 외부 사용처 없음 확인 필요 (`grep_search`)

### Phase 2: Frontend 싱글톤 검토 (별도 계획 필요)

> [!WARNING]
> Frontend DI Container가 없으므로 현재 단계에서는 **현행 유지**.  
> 향후 Frontend 아키텍처 리팩터링 시 별도 계획서 작성.

---

## 5. 검증 계획

### 5.1 자동화 검증

```bash
# 1. Lint 검사
ruff check backend/data/watchlist_store.py backend/data/symbol_mapper.py

# 2. Import 검사
lint-imports

# 3. 모듈 로드 테스트
python -c "from backend.data.watchlist_store import WatchlistStore; print('✅ WatchlistStore OK')"
python -c "from backend.data.symbol_mapper import SymbolMapper; print('✅ SymbolMapper OK')"
python -c "from backend.container import container; print(container.watchlist_store()); print(container.symbol_mapper())"

# 4. 레거시 함수 사용처 확인 (제거 전 필수)
# 아래 검색 결과가 대상 파일 내부만 나와야 함
# grep "get_watchlist_store\|save_watchlist\|load_watchlist\|merge_watchlist" --include="*.py"
# grep "get_symbol_mapper\|MASSIVE_TO_IBKR\|IBKR_TO_MASSIVE" --include="*.py"
```

### 5.2 수동 검증

- [ ] Backend 서버 정상 기동 확인: `python -m backend`
- [ ] Scanner 실행 테스트 (Watchlist 저장/로드 확인)

---

## 6. 롤백 계획

```bash
git checkout -- backend/data/watchlist_store.py backend/data/symbol_mapper.py
```

---

## 7. 범위 외 항목 (Future Work)

| 항목 | 이유 | 향후 계획 |
|------|------|----------|
| `BackendClient._instance` | Frontend DI Container 부재 | Frontend 아키텍처 리팩터링 시 검토 |
| `ThemeManager._instance` | 전역 테마 관리 필요 | 현행 유지 |
| `WatchlistWriter._instance` | 스레드 안전성 보장 | 현행 유지 (내부 클래스) |

---

## 8. 요약

| 대상 | 조치 | 우선순위 |
|------|------|----------|
| `watchlist_store.py` 레거시 | 제거 | 🔴 높음 |
| `symbol_mapper.py` 레거시 | 제거 | 🔴 높음 |
| `BackendClient` | 현행 유지 | ⚪ 범위 외 |
| `ThemeManager` | 현행 유지 | ⚪ 범위 외 |
| `WatchlistWriter` | 현행 유지 | ⚪ 범위 외 |
