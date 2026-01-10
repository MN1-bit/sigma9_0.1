# 02-002: 레거시 싱글톤 완전 제거 및 Container 마이그레이션 계획서

> **작성일**: 2026-01-08 15:02  
> **우선순위**: 2 (DI Container 도입 후속) | **예상 소요**: 2-3h | **위험도**: 낮음

---

## 1. 목표

[02-001 DI Container 도입](file:///d:/Codes/Sigma9-0.1/docs/devlog/refactor/02-001_di_container.md)에서 **스킵된 Step 5**를 완료하여:

1. `routes/watchlist.py`의 레거시 싱글톤 사용을 Container로 마이그레이션
2. **레거시 싱글톤 코드 완전 제거** (`_scanner_instance`, `get_scanner_instance()`, `initialize_realtime_scanner()`, `get_realtime_scanner()`)
3. REFACTORING.md 정책 준수 (금지 패턴 제거)

### 해결할 문제점

| 문제 | 위치 | 심각도 |
|------|------|--------|
| `get_scanner_instance()` Deprecation Warning 누락 | `realtime_scanner.py:869` | 중간 |
| 레거시 함수 사용 | `routes/watchlist.py:64-66` | 중간 |
| 레거시 싱글톤 코드 잔존 (85줄) | `realtime_scanner.py:793-877` | 중간 |
| REFACTORING.md 정책 위반 | "금지 패턴: get_*_instance()" | 낮음 |

---

## 2. 영향 분석

### 2.1 변경 대상 파일

| 파일 | 변경 유형 | 변경 내용 |
|------|----------|----------|
| [realtime_scanner.py](file:///d:/Codes/Sigma9-0.1/backend/core/realtime_scanner.py#L793-877) | 삭제 | 레거시 싱글톤 코드 85줄 완전 제거 |
| [watchlist.py](file:///d:/Codes/Sigma9-0.1/backend/api/routes/watchlist.py#L64-66) | 수정 | Container 방식으로 마이그레이션 |

### 2.2 삭제 대상 코드 (realtime_scanner.py:793-877)

```python
# 삭제할 코드 목록
_scanner_instance: Optional[RealtimeScanner] = None  # Line 812

def get_realtime_scanner() -> Optional[RealtimeScanner]:  # Line 815-832
    ...

def initialize_realtime_scanner(...) -> RealtimeScanner:  # Line 835-866
    ...

def get_scanner_instance() -> Optional[RealtimeScanner]:  # Line 869-876
    ...
```

### 2.3 기타 레거시 싱글톤 (이번 범위 제외)

| 파일 | 패턴 | 비고 |
|------|------|------|
| `watchlist_store.py` | `_store_instance`, `get_watchlist_store()` | 내부 편의함수용 |
| `symbol_mapper.py` | `_mapper_instance`, `get_symbol_mapper()` | 내부 사용 |
| `ignition_monitor.py` | `_monitor_instance`, `get_ignition_monitor()` | ✅ Deprecation 있음 |

> **범위**: `realtime_scanner.py` 싱글톤 완전 제거 + `routes/watchlist.py` 마이그레이션

### 2.4 순환 의존성 현황

- ✅ 순환 의존성 없음 (`container.py`는 이미 모든 서비스 제공)

---

## 3. 실행 계획

### Step 1: `routes/watchlist.py` Container 마이그레이션

**파일**: `backend/api/routes/watchlist.py`

```python
# 변경 전 (Line 64-66)
from backend.core.realtime_scanner import get_scanner_instance
scanner = get_scanner_instance()

# 변경 후
from backend.container import container
scanner = container.realtime_scanner()
```

---

### Step 2: `realtime_scanner.py` 레거시 싱글톤 코드 완전 제거

**파일**: `backend/core/realtime_scanner.py`

**삭제할 라인**: 793-877 (약 85줄)

- 헤더 주석 (Line 793-808)
- `import warnings` (Line 810)
- `_scanner_instance` 전역 변수 (Line 812)
- `get_realtime_scanner()` 함수 (Line 815-832)
- `initialize_realtime_scanner()` 함수 (Line 835-866)
- `get_scanner_instance()` 함수 (Line 869-877)

---

### Step 3: 사용처 검증 및 정리

삭제 전 `_scanner_instance` 사용처 확인:

```bash
grep -rn "_scanner_instance\|get_scanner_instance\|get_realtime_scanner\|initialize_realtime_scanner" backend/
```

예상 결과:
- `routes/watchlist.py` (Step 1에서 수정 완료)
- `realtime_scanner.py` (Step 2에서 삭제)

---

## 4. 검증 계획

### 4.1 자동화 검증

```bash
# 1. 레거시 함수 참조 없음 확인
grep -rn "get_scanner_instance\|get_realtime_scanner\|initialize_realtime_scanner" backend/
# 예상: 결과 없음 (삭제 완료)

# 2. Lint 검사
ruff check backend/core/realtime_scanner.py backend/api/routes/watchlist.py

# 3. Import 테스트
python -c "from backend.api.routes.watchlist import router; print('✅ OK')"
python -c "from backend.core.realtime_scanner import RealtimeScanner; print('✅ OK')"
```

### 4.2 수동 테스트

1. **백엔드 시작 테스트**:
   ```bash
   python -m backend
   ```
   - ✅ 서버 정상 시작 확인
   - ✅ `📡 RealtimeScanner 시작` 로그 확인

2. **POST /watchlist/recalculate 엔드포인트 테스트**:
   ```bash
   curl -X POST http://localhost:8000/watchlist/recalculate
   ```
   - ✅ `{"status": "success", ...}` 응답 확인

---

## 5. 롤백 계획

변경이 간단하여 즉시 롤백 가능:

```bash
git checkout -- backend/core/realtime_scanner.py
git checkout -- backend/api/routes/watchlist.py
```

---

## 6. 후속 작업 (참고)

| 우선순위 | 작업 | 비고 |
|---------|------|------|
| 낮음 | `ignition_monitor.py` 싱글톤 제거 | 동일 패턴 |
| 낮음 | `watchlist_store.py` → Container 등록 | 내부 사용 패턴 변경 필요 |
| 중간 | 05-001 Phase 3 (dashboard.py 분리) | 별도 계획서 필요 |
