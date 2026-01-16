# 09-105: 출력점 마이그레이션

> **작성일**: 2026-01-13 | **예상**: 1시간  
> **상위 문서**: [09-009_ticker_selection_event_bus.md](./09-009_ticker_selection_event_bus.md)

---

## 목표

티커 변경 시 자동 업데이트되어야 하는 UI 컴포넌트들을 Event Bus에 연결

---

## 변경 파일

| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
| `frontend/gui/ticker_info_window.py` | MODIFY | +10 |
| `frontend/gui/panels/chart_panel.py` | MODIFY | +15 |
| `frontend/gui/dashboard.py` | MODIFY | +20 |

---

## 구현 내용

### 1. TickerInfoWindow

```python
# frontend/gui/ticker_info_window.py

class TickerInfoWindow(QDialog):
    
    # 📌 [09-009] DashboardState와 연결
    def connect_to_state(self, state: "DashboardState") -> None:
        """
        DashboardState의 ticker_changed 시그널 구독
        
        창이 열려있을 때만 티커 정보 자동 업데이트
        """
        state.ticker_changed.connect(self._on_ticker_changed)
    
    def _on_ticker_changed(self, ticker: str, source: str) -> None:
        """
        [09-009] 티커 변경 시 자동 업데이트
        
        창이 visible 상태일 때만 새 티커 정보 로드
        """
        if self.isVisible():
            self.load_ticker(ticker)
```

### 2. ChartPanel

```python
# frontend/gui/panels/chart_panel.py

class ChartPanel(QWidget):
    
    def __init__(self, state: "DashboardState", parent=None):
        super().__init__(parent)
        self._state = state
        
        # 📌 [09-009] Event Bus 구독
        self._state.ticker_changed.connect(self._on_ticker_changed)
    
    def _on_ticker_changed(self, ticker: str, source: str) -> None:
        """
        [09-009] 티커 변경 시 차트 자동 로드
        """
        self.load_chart(ticker)
```

### 3. Dashboard에서 연결

```python
# frontend/gui/dashboard.py

def _init_components(self):
    # ... 기존 코드 ...
    
    # 📌 [09-009] TickerInfoWindow Event Bus 연결
    if self._ticker_info_window is None:
        self._ticker_info_window = TickerInfoWindow()
    self._ticker_info_window.connect_to_state(self._state)
```

또는 lazy initialization 시:

```python
def _show_ticker_info(self, ticker: str = None):
    # Lazy initialization
    if self._ticker_info_window is None:
        self._ticker_info_window = TickerInfoWindow()
        # 📌 [09-009] Event Bus 연결
        self._ticker_info_window.connect_to_state(self._state)
    
    # 최초 로드는 명시적으로 (아직 시그널 발행 전)
    target_ticker = ticker or self._state.current_ticker
    if target_ticker:
        self._ticker_info_window.load_ticker(target_ticker)
    
    self._ticker_info_window.show()
```

---

## 주의사항

1. **ChartPanel**: `_state.ticker_changed.connect()` 연결 시점
   - `__init__`에서 연결하면 DashboardState가 먼저 생성되어야 함
   - 동적 연결도 가능

2. **TickerInfoWindow**: 창이 닫혀있을 때는 업데이트 불필요
   - `isVisible()` 체크로 최적화

---

## 검증

- [ ] Watchlist 클릭 → TickerInfoWindow (열려있을 때) 자동 업데이트
- [ ] Watchlist 클릭 → 차트 자동 로드
- [ ] 여러 출력점이 동시에 업데이트되는지 확인

---

## 다음 단계

→ [09-106: 진입점 마이그레이션](./09-106_entry_points.md)
