# 09-105: 출력점 마이그레이션 Devlog

> **작성일**: 2026-01-13
> **계획서**: [09-105_output_points.md](../../Plan/refactor/09-105_output_points.md)

## 진행 현황

| Step | 상태 | 시간 |
|------|------|------|
| Step 1: TickerInfoWindow 수정 | ✅ | 06:01 |
| Step 2: ChartPanel 수정 | ✅ | 06:02 |
| Step 3: Dashboard 연결 | ✅ | 06:02 |

---

## Step 1: TickerInfoWindow 수정

### 변경 사항
- `frontend/gui/ticker_info_window.py` (+23줄):
  - `TYPE_CHECKING` import 추가 (`DashboardState`)
  - `connect_to_state(state)` 메서드 추가
  - `_on_ticker_changed(ticker, source)` 메서드 추가

### 패턴
- `isVisible()` 체크로 창이 숨겨졌을 때 불필요한 로딩 방지

---

## Step 2: ChartPanel 수정

### 변경 사항
- `frontend/gui/panels/chart_panel.py` (+18줄):
  - `chart_load_requested = pyqtSignal(str, str)` 시그널 추가
  - `__init__`에 `state` 파라미터 추가
  - `_on_ticker_changed(ticker, source)` 메서드 추가

### 설계 결정
ChartPanel은 직접 차트 로딩을 수행하지 않고, `chart_load_requested` 시그널을 발행하여 Dashboard가 처리하도록 위임합니다. 이는 기존 Dashboard의 로딩 로직을 유지하면서 Event Bus를 통해 연결합니다.

---

## Step 3: Dashboard 연결

### 변경 사항
- `frontend/gui/dashboard.py` (+3줄):
  - `_show_ticker_info()`에서 TickerInfoWindow 초기화 후 `connect_to_state()` 호출

---

## 스파게티 방지 체크
- [x] 신규 메서드 ≤ 30개? ✅
- [x] Singleton get_*_instance() 미사용? ✅
- [x] DI Container 사용? ✅

## 검증
- ticker_info_window.py lint: ✅
- chart_panel.py lint: ✅
- dashboard.py: 기존 F401/F821 에러 존재 (이번 변경과 무관)
