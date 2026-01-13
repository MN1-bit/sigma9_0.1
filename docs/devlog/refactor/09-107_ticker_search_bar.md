# 09-107: TickerSearchBar 위젯 Devlog

> **작성일**: 2026-01-13
> **계획서**: [09-107_ticker_search_bar.md](../../Plan/refactor/09-107_ticker_search_bar.md)

## 진행 현황

| Step | 상태 | 시간 |
|------|------|------|
| Step 1: TickerSearchBar 위젯 생성 | ✅ | 06:11 |
| Step 2: ControlPanel 통합 | ✅ | 06:12 |
| Step 3: Dashboard 연결 | ✅ | 06:13 |

---

## Step 1: TickerSearchBar 위젯 생성

### 변경 사항
- **NEW** `frontend/gui/widgets/ticker_search_bar.py` (196줄):
  - `TickerSearchBar(QWidget)` 클래스
  - Editable `QComboBox` + `QCompleter` 자동완성
  - `ticker_selected(str)` 시그널
  - 최근 히스토리 드롭다운 (최대 10개)

### Public API
```python
set_ticker_data({"AAPL": "Apple Inc.", ...})  # 자동완성 데이터
set_current_ticker("AAPL")                     # 현재 표시
on_ticker_changed(ticker, source)               # Event Bus 연동
```

---

## Step 2: ControlPanel 통합

### 변경 사항
- `frontend/gui/control_panel.py` (+8줄):
  - `TickerSearchBar` import 추가
  - `ticker_search_selected = pyqtSignal(str)` 추가
  - `self.ticker_search = TickerSearchBar()` 인스턴스 생성
  - 로고 옆에 배치

---

## Step 3: Dashboard 연결

### 변경 사항
- `frontend/gui/dashboard.py` (+12줄):
  - `ticker_search_selected` 시그널 → `_on_ticker_search_selected` 연결
  - `_state.ticker_changed` → `ticker_search.on_ticker_changed` 연결
  - `_on_ticker_search_selected()` 핸들러 추가

### 데이터 흐름
```
SearchBar 입력 → ticker_selected.emit()
  → control_panel.ticker_search_selected
    → dashboard._on_ticker_search_selected()
      → _state.select_ticker(ticker, SEARCH)
        → ticker_changed.emit()
          → 차트/Info 업데이트
          → SearchBar 히스토리 추가
```

---

## 스파게티 방지 체크
- [x] 신규 파일 ≤ 1000줄? ✅ (196줄)
- [x] 신규 클래스 ≤ 30 메서드? ✅ (10 메서드)
- [x] Singleton get_*_instance() 미사용? ✅
- [x] DI Container 사용? ✅

## 검증
- ticker_search_bar.py lint: ✅
- control_panel.py lint: ✅
- dashboard.py: 기존 에러만 (이번 변경과 무관)
