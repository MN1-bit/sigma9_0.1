# 02-003: IgnitionMonitor 싱글톤 완전 제거 계획서

> **작성일**: 2026-01-08 15:22  
> **우선순위**: 2 (DI Container 후속) | **예상 소요**: 1-2h | **위험도**: 낮음

---

## 1. 목표

[02-002 RealtimeScanner 싱글톤 제거](./02-002_singleton_removal.md) 후속 작업으로, `ignition_monitor.py`의 레거시 싱글톤을 완전 제거합니다.

1. `routes/ignition.py`의 레거시 싱글톤 사용을 Container로 마이그레이션
2. **레거시 싱글톤 코드 완전 제거** (`_monitor_instance`, `get_ignition_monitor()`, `initialize_ignition_monitor()`)
3. REFACTORING.md 정책 준수

### 해결할 문제점

| 문제 | 위치 | 심각도 |
|------|------|--------|
| 레거시 함수 사용 | `routes/ignition.py:33,71,93` | 중간 |
| 레거시 싱글톤 코드 잔존 (40줄) | `ignition_monitor.py:447-506` | 중간 |
| REFACTORING.md 정책 위반 | "금지 패턴: get_*_instance()" | 낮음 |

---

## 2. 영향 분석

### 2.1 변경 대상 파일

| 파일 | 변경 유형 | 변경 내용 |
|------|----------|----------|
| [ignition.py](file:///d:/Codes/Sigma9-0.1/backend/api/routes/ignition.py) | 수정 | 3곳 Container 마이그레이션 |
| [ignition_monitor.py](file:///d:/Codes/Sigma9-0.1/backend/core/ignition_monitor.py#L447-506) | 삭제 | 레거시 싱글톤 코드 40줄 제거 |
| [realtime.py](file:///d:/Codes/Sigma9-0.1/backend/startup/realtime.py) | 수정 | 직접 클래스 생성으로 변경 |

### 2.2 레거시 함수 사용처

```
routes/ignition.py:33  → get_ignition_monitor()
routes/ignition.py:71  → get_ignition_monitor()
routes/ignition.py:93  → get_ignition_monitor()
startup/realtime.py:59 → initialize_ignition_monitor as init_monitor
```

### 2.3 순환 의존성

- ✅ 순환 의존성 없음 (`container.py`에 이미 `ignition_monitor` 등록됨)

---

## 3. 실행 계획

### Step 1: `routes/ignition.py` Container 마이그레이션

**파일**: `backend/api/routes/ignition.py`

```python
# 변경 전 (3곳 모두)
from backend.core.ignition_monitor import get_ignition_monitor
monitor = get_ignition_monitor()

# 변경 후
from backend.container import container
monitor = container.ignition_monitor()
```

---

### Step 2: `startup/realtime.py` 수정

**파일**: `backend/startup/realtime.py`

```python
# 변경 전 (Line 58-60)
from backend.core.ignition_monitor import (
    initialize_ignition_monitor as init_monitor,
)
...
monitor = init_monitor(strategy, ws_manager)

# 변경 후
from backend.core.ignition_monitor import IgnitionMonitor
...
monitor = IgnitionMonitor(strategy, ws_manager, poll_interval=1.0)
```

---

### Step 3: `ignition_monitor.py` 레거시 코드 삭제

**파일**: `backend/core/ignition_monitor.py`

**삭제할 라인**: 447-506 (약 60줄)

- 헤더 주석 (Line 447-462)
- `import warnings` (Line 464)
- `_monitor_instance` 전역 변수 (Line 466)
- `get_ignition_monitor()` 함수 (Line 469-486)
- `initialize_ignition_monitor()` 함수 (Line 489-506)

---

## 4. 검증 계획

### 4.1 자동화 검증

```bash
# 1. 레거시 함수 참조 없음 확인
Select-String -Path "backend\**\*.py" -Pattern "get_ignition_monitor|initialize_ignition_monitor|_monitor_instance" -Recurse

# 2. Lint 검사
ruff check backend/core/ignition_monitor.py backend/api/routes/ignition.py backend/startup/realtime.py

# 3. Import 테스트
python -c "from backend.api.routes.ignition import router; print('✅ OK')"
python -c "from backend.core.ignition_monitor import IgnitionMonitor; print('✅ OK')"
```

### 4.2 수동 테스트

1. **백엔드 시작 테스트**: `python -m backend`
2. **Ignition 엔드포인트 테스트**:
   ```bash
   curl http://localhost:8000/ignition/scores
   ```

---

## 5. 롤백 계획

```bash
git checkout -- backend/core/ignition_monitor.py
git checkout -- backend/api/routes/ignition.py
git checkout -- backend/startup/realtime.py
```

---

## 6. 후속 작업 (참고)

이번 계획서 완료 후 고려할 추가 작업:

| 우선순위 | 작업 | 비고 |
|---------|------|------|
| 낮음 | `watchlist_store.py` → Container 등록 | 내부 사용 패턴 변경 필요 |
| 낮음 | `symbol_mapper.py` → Container 등록 | 내부 사용 패턴 |
| **중간** | **05-001 Phase 3 (dashboard.py 분리)** | **별도 계획서 필요** |

### 05-001 Phase 3 요약 (dashboard.py ≤500줄 목표)

현재 상태:
- `dashboard.py`: 2,362줄 (Phase 2 완료 후)
- 목표: ≤500줄

미완료 항목:
1. P2-3: `Tier2Item`, `NumericTableWidgetItem` 중복 클래스 제거
2. ChartPanel 분리
3. RightPanel 분리
4. 기타 이벤트 핸들러 모듈화

