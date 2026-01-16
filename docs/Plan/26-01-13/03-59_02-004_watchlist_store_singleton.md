# 02-004: WatchlistStore 싱글톤 제거 계획서

> **작성일**: 2026-01-08 15:28  
> **우선순위**: 2 (DI Container 후속) | **예상 소요**: 30m | **위험도**: 낮음

---

## 1. 목표

`watchlist_store.py`의 레거시 싱글톤 패턴 제거 및 Container 등록.

1. `routes/scanner.py`의 레거시 싱글톤 사용을 Container로 마이그레이션
2. 내부 편의 함수는 유지 (하위 호환성)
3. Container에 WatchlistStore 등록

---

## 2. 영향 분석

### 2.1 변경 대상 파일

| 파일 | 변경 유형 | 변경 내용 |
|------|----------|----------|
| [container.py](file:///d:/Codes/Sigma9-0.1/backend/container.py) | 추가 | WatchlistStore provider 등록 |
| [scanner.py](file:///d:/Codes/Sigma9-0.1/backend/api/routes/scanner.py) | 수정 | Container 마이그레이션 |
| [watchlist_store.py](file:///d:/Codes/Sigma9-0.1/backend/data/watchlist_store.py) | 수정 | Deprecation Warning 추가 |

### 2.2 레거시 함수 사용처

```
routes/scanner.py:121,136 → get_watchlist_store()
watchlist_store.py:406,411,430 → 내부 편의함수 (유지)
```

---

## 3. 실행 계획

### Step 1: Container에 WatchlistStore 등록

**파일**: `backend/container.py`

```python
# 추가
watchlist_store = providers.Singleton(WatchlistStore)
```

### Step 2: `routes/scanner.py` Container 마이그레이션

```python
# 변경 전
from backend.data.watchlist_store import get_watchlist_store
store = get_watchlist_store()

# 변경 후
from backend.container import container
store = container.watchlist_store()
```

### Step 3: `get_watchlist_store()` Deprecation Warning 추가

```python
def get_watchlist_store() -> WatchlistStore:
    warnings.warn(
        "get_watchlist_store()는 deprecated입니다. "
        "container.watchlist_store() 사용을 권장합니다.",
        DeprecationWarning,
        stacklevel=2,
    )
    ...
```

---

## 4. 검증 계획

```bash
ruff check backend/container.py backend/api/routes/scanner.py backend/data/watchlist_store.py
python -c "from backend.api.routes.scanner import router; print('✅ OK')"
```

---

## 5. 롤백 계획

```bash
git checkout -- backend/container.py backend/api/routes/scanner.py backend/data/watchlist_store.py
```
