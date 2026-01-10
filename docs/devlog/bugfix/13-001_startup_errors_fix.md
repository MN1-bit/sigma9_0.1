# [13-001] Startup Critical Issues Fix - Devlog

> **작성일**: 2026-01-10 07:03
> **관련 계획서**: [13-001_startup_errors_20260110.md](../../Plan/bugfix/13-001_startup_errors_20260110.md)

## 진행 현황

| Step | 상태 | 완료 시간 |
|------|------|----------|
| Step 1: get_active_strategy 수정 | ✅ 완료 | 07:01 |
| Step 2: load_watchlist 편의 함수 복원 | ✅ 완료 | 07:02 |
| Step 3: ChartPanel 시그널 수정 | ✅ 완료 | 07:02 |
| Step 4: 검증 | ✅ 완료 | 07:03 |

---

## Step 1: get_active_strategy 수정

### 변경 사항
- `backend/startup/realtime.py`: 
  - L163: `get_active_strategy()` → `get_strategy("seismograph") or load_strategy("seismograph")`

### 원인
- devlog 작성 시 존재하지 않는 메서드를 호출하는 코드 작성 (계획서에 없던 기능)
- StrategyLoader에 구현되지 않은 메서드

---

## Step 2: load_watchlist 편의 함수 복원

### 변경 사항
- `backend/data/watchlist_store.py`:
  - 파일 끝에 3개 편의 함수 추가: `load_watchlist()`, `save_watchlist()`, `merge_watchlist()`
  - Lazy init 패턴으로 `_default_store` 사용

### 원인
- 02-006_singleton_cleanup 리팩터링 시 삭제되었으나 호출부 마이그레이션 미완료

---

## Step 3: ChartPanel 시그널 수정

### 변경 사항
- `frontend/gui/panels/chart_panel.py`:
  - L49: `viewport_data_needed = pyqtSignal(str, str, int, int)` → `pyqtSignal(int, int)`

### 원인
- 05-003_dashboard_split_phase4 리팩터링 시 시그니처 불일치 발생
- PyQtGraphChartWidget은 2개 인자만 emit하는데 ChartPanel은 4개 기대

---

## 최종 검증 결과

| 검증 항목 | 결과 |
|----------|------|
| realtime.py import test | ✅ |
| watchlist_store.py import test | ✅ |
| chart_panel.py import test | ✅ |
| ruff check (E,F) | ✅ |

## 수정 파일 요약

| 파일 | 수정 내용 |
|------|----------|
| `backend/startup/realtime.py` | get_active_strategy 호출 수정 |
| `backend/data/watchlist_store.py` | 편의 함수 3개 복원 |
| `frontend/gui/panels/chart_panel.py` | 시그널 시그니처 수정 |
