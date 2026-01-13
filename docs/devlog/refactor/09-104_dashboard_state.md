# 09-104: DashboardState 확장 Devlog

> **작성일**: 2026-01-13
> **계획서**: [09-104_dashboard_state.md](../../Plan/refactor/09-104_dashboard_state.md)

## 진행 현황

| Step | 상태 | 시간 |
|------|------|------|
| Step 1: DashboardState 확장 | ✅ | 05:59 |

---

## Step 1: DashboardState에 Ticker Selection Event Bus 추가

### 변경 사항
- `frontend/gui/state/dashboard_state.py` (+55줄):
  - `ticker_changed = pyqtSignal(str, str)` 시그널 추가
  - `TickerSource` 내부 클래스 추가 (WATCHLIST, TIER2, SEARCH, ...)
  - `__init__`에 `ws_adapter` 파라미터 추가
  - `_current_ticker`, `_previous_ticker` 상태 필드 추가
  - `current_ticker` / `previous_ticker` 프로퍼티 추가
  - `select_ticker()` 메서드 추가 (Optimistic Update 패턴)
  - `_handle_active_ticker_changed()` 메서드 추가

### Optimistic Update 패턴
```
select_ticker("AAPL")
  → 1. 즉시 ticker_changed.emit() (UI 즉각 반응)
  → 2. ws.send(SET_ACTIVE_TICKER) (Backend 동기화)
```

### 스파게티 방지 체크
- [x] 신규 메서드 ≤ 30개? ✅
- [x] Singleton get_*_instance() 미사용? ✅
- [x] DI Container 사용? ✅ (ws_adapter 주입)

### 검증
- lint: ✅ `All checks passed!`
