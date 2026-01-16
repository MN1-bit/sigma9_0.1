# [02-004] Realtime Services Container Integration

> **작성일**: 2026-01-17 04:43
> **계획서**: [16-40_02-004_realtime_services_container_integration.md](../../Plan/26-01-16/16-40_02-004_realtime_services_container_integration.md)

## 진행 현황

| Step | 상태 | 시간 |
|------|------|------|
| Step 1.0 | ✅ | 04:43-04:45 |
| Step 2.0 | ✅ | 04:45-04:46 |
| Step 3.0 | ✅ | 04:43-04:45 |
| Step 4.0 | ✅ | 04:46-04:47 |

---

## Step 1: initialize_massive_websocket() Container 통합

### 변경 사항
- `backend/startup/realtime.py`:
  - `container.ws_manager.override(ws_manager)` 추가
  - `container.tick_dispatcher()` 사용
  - `container.massive_ws()` 사용
  - `container.subscription_manager()` 사용
  - `container.tick_broadcaster()` 사용
  - `container.trailing_stop_manager()` 사용

---

## Step 2: initialize_realtime_scanner() Container 통합

### 변경 사항
- `backend/startup/realtime.py`:
  - `container.massive_client()` 사용
  - `container.data_repository()` 사용
  - `container.scoring_strategy()` 사용
  - `-15줄` 수동 인스턴스화 코드 제거

---

## Step 3: initialize_ignition_monitor() Container 통합

### 변경 사항
- `backend/startup/realtime.py`:
  - `container.ignition_monitor()` 사용
  - `-8줄` 수동 인스턴스화 코드 제거

---

## Step 4: 검증

### Lint
```bash
ruff check backend/startup/realtime.py
# All checks passed!
```

---

## 완료 확인

- [x] 계획서 체크박스 업데이트
- [x] Devlog 작성
- [x] 다음 단계: [02-003] IBKRConnector PyQt6 의존성 제거

---

## 검증 결과 (/IMP-verification)

| 항목 | 결과 |
|------|------|
| ruff check (수정 파일) | ✅ |
| ruff format | ✅ |
| DI 패턴 준수 | ✅ (금지 패턴 없음) |
| 크기 제한 | ⚠️ container.py 642줄 (DI 컨테이너 특성상 허용) |
| full_log_history 업데이트 | ✅ |

---

## [02-003.1] Lint Cleanup 결과

| 에러 유형 | Before | After | 해결 |
|-----------|--------|-------|------|
| E402 | 38 | 20 | -18 (from scripts/tests) |
| F401 | 18 | 7 | -11 |
| E722 | 14 | 0 | **-14 ✅** |
| F541 | 10 | 0 | **-10 ✅** |
| E741 | 5 | 4 | -1 |
| F821 | 4 | 0 | **-4 ✅** |
| F811 | 1 | 0 | **-1 ✅** |
| **Total** | **90** | **31** | **-59** |

### 수동 수정 파일
- `backend/core/tick_broadcaster.py` - F821 (TYPE_CHECKING 추가)
- `backend/core/backtest_engine.py` - E722
- `backend/core/backtest_report.py` - E722 x2
- `backend/core/risk_manager.py` - E722 x2
- `frontend/gui/dashboard.py` - F811, E722, F401 x3

### 스킵 사유
- **E402 (20)**: sys.path 조작 후 import (구조 변경 필요)
- **E741 (4)**: 변수명 `l` (low) - 금융 도메인 표준
- **F401 conditional (7)**: try/except PyQt6/PySide6 호환 import
