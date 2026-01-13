# 09-107: TickerSearchBar 위젯

> **작성일**: 2026-01-13 | **예상**: 1.5시간  
> **상위 문서**: [09-009_ticker_selection_event_bus.md](./09-009_ticker_selection_event_bus.md)

---

## 목표

Top Panel에 티커 검색/선택 위젯 추가:
- 현재 티커 표시
- 수동 입력 + 자동완성
- 최근 히스토리 드롭다운

---

## 변경 파일

| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
| `frontend/gui/widgets/ticker_search_bar.py` | **NEW** | ~200 |
| `frontend/gui/control_panel.py` | MODIFY | +20 |

---

## 구현 내용

### 1. TickerSearchBar 위젯

```python
# frontend/gui/widgets/ticker_search_bar.py

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QComboBox, QLabel, QCompleter
)
from PyQt6.QtCore import Qt, pyqtSignal, QStringListModel
from ..theme import theme


class TickerSearchBar(QWidget):
    """
    통합 티커 검색/선택 위젯
    
    Features:
    - 현재 티커 표시 (AAPL • Apple Inc.)
    - 수동 입력 + 자동완성
    - 최근 히스토리 드롭다운
    """
    
    ticker_selected = pyqtSignal(str)  # 티커 선택 시 발행
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ticker_data: dict[str, str] = {}  # {ticker: name}
        self._recent_history: list[str] = []
        self._max_history = 10
        
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # 검색 아이콘
        self.search_icon = QLabel("🔍")
        self.search_icon.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(self.search_icon)
        
        # Editable ComboBox
        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.setMinimumWidth(180)
        self.combo.setPlaceholderText("Search ticker...")
        self.combo.setStyleSheet(self._get_style())
        
        # QCompleter 설정
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchStartsWith)
        self.combo.setCompleter(self.completer)
        
        layout.addWidget(self.combo)
    
    def _get_style(self) -> str:
        return f"""
            QComboBox {{
                background-color: {theme.get_color("surface")};
                border: 1px solid {theme.get_color("border")};
                border-radius: 4px;
                color: {theme.get_color("text")};
                padding: 4px 8px;
                font-size: 12px;
            }}
            QComboBox:focus {{
                border-color: {theme.get_color("primary")};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme.get_color("background")};
                color: {theme.get_color("text")};
                selection-background-color: {theme.get_color("primary")};
            }}
        """
    
    def _connect_signals(self):
        # Enter 키 또는 항목 선택 시
        self.combo.lineEdit().returnPressed.connect(self._on_enter)
        self.combo.activated.connect(self._on_item_selected)
    
    def _on_enter(self):
        """Enter 키로 선택"""
        text = self.combo.currentText().upper().strip()
        # "AAPL • Apple Inc." 형식에서 티커만 추출
        if " • " in text:
            ticker = text.split(" • ")[0]
        else:
            ticker = text
        
        if ticker:
            self._add_to_history(ticker)
            self.ticker_selected.emit(ticker)
    
    def _on_item_selected(self, index: int):
        """드롭다운 항목 선택"""
        text = self.combo.currentText()
        if " • " in text:
            ticker = text.split(" • ")[0]
        else:
            ticker = text
        
        if ticker:
            self._add_to_history(ticker)
            self.ticker_selected.emit(ticker)
    
    def _add_to_history(self, ticker: str):
        """히스토리에 추가"""
        if ticker in self._recent_history:
            self._recent_history.remove(ticker)
        self._recent_history.insert(0, ticker)
        self._recent_history = self._recent_history[:self._max_history]
        self._update_combo_items()
    
    def _update_combo_items(self):
        """ComboBox 항목 업데이트"""
        self.combo.clear()
        for ticker in self._recent_history:
            name = self._ticker_data.get(ticker, "")
            display = f"{ticker} • {name}" if name else ticker
            self.combo.addItem(display)
    
    # ───────────────────────────────────────────────────────────────────
    # Public API
    # ───────────────────────────────────────────────────────────────────
    
    def set_ticker_data(self, data: dict[str, str]):
        """
        자동완성용 티커 데이터 설정
        
        Args:
            data: {"AAPL": "Apple Inc.", "MSFT": "Microsoft", ...}
        """
        self._ticker_data = data
        # QCompleter 모델 업데이트
        items = [f"{t} • {n}" for t, n in data.items()]
        model = QStringListModel(items)
        self.completer.setModel(model)
    
    def set_current_ticker(self, ticker: str):
        """현재 티커 표시 업데이트"""
        name = self._ticker_data.get(ticker, "")
        display = f"{ticker} • {name}" if name else ticker
        self.combo.setCurrentText(display)
    
    def on_ticker_changed(self, ticker: str, source: str):
        """DashboardState.ticker_changed 시그널 핸들러"""
        self.set_current_ticker(ticker)
        self._add_to_history(ticker)
```

### 2. ControlPanel 통합

```python
# frontend/gui/control_panel.py

from .widgets.ticker_search_bar import TickerSearchBar

class ControlPanel(QFrame):
    
    # 시그널 추가
    ticker_search_selected = pyqtSignal(str)
    
    def _init_ui(self):
        # ... 로고 뒤에 추가 ...
        
        layout.addWidget(logo_container)
        layout.addWidget(self._create_separator())
        
        # 📌 [09-009] Ticker Search Bar
        self.ticker_search = TickerSearchBar()
        self.ticker_search.ticker_selected.connect(self.ticker_search_selected.emit)
        layout.addWidget(self.ticker_search)
        
        layout.addStretch(1)
        # ... 나머지 버튼들 ...
```

### 3. Dashboard에서 연결

```python
# dashboard.py

def _init_ui(self):
    # ControlPanel ticker_search 연결
    self.control_panel.ticker_search_selected.connect(self._on_ticker_search_selected)
    
    # DashboardState 연결
    self._state.ticker_changed.connect(self.control_panel.ticker_search.on_ticker_changed)

def _on_ticker_search_selected(self, ticker: str):
    """TickerSearchBar에서 티커 선택"""
    self._state.select_ticker(ticker, DashboardState.TickerSource.SEARCH)
```

---

## 티커 데이터 로드 (선택사항)

앱 시작 시 티커 목록을 로드하여 자동완성 활성화:

```python
# 방법 1: 하드코딩된 주요 티커
TOP_TICKERS = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc.",
    # ...
}
self.control_panel.ticker_search.set_ticker_data(TOP_TICKERS)

# 방법 2: Backend API에서 로드 (향후)
# tickers = await backend.get_all_tickers()
# self.control_panel.ticker_search.set_ticker_data(tickers)
```

---

## 검증

- [ ] TickerSearchBar 렌더링 확인
- [ ] 타이핑 → 자동완성 동작
- [ ] Enter 키 → 티커 선택 → 차트/Info 업데이트
- [ ] 히스토리 드롭다운 동작

---

## 다음 단계

→ [09-108: 정리 및 검증](./09-108_cleanup.md)
