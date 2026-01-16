# 09-009: Ticker Selection Event Bus 중앙화 리팩토링

> **Status**: 📋 Planning (문서화 단계)  
> **Created**: 2026-01-13  
> **Author**: AI Assistant

---

## 1. 문제 정의

### 현재 상태 (As-Is)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          dashboard.py (2200+ lines)                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   [진입점들] ─────────────────┬──────────────────► [출력점들]            │
│                               │                                          │
│   • Watchlist 클릭 ──────────►│                                          │
│   • Tier2 Hot Zone 클릭 ─────►│──► _load_chart_for_ticker() ─► Chart    │
│   • (미래: 검색창)            │                                          │
│   • (미래: 즐겨찾기)          │                  ─► TickerInfoWindow?    │
│   • (미래: 알림 클릭)         │                  ─► (미래: 뉴스패널)     │
│                               │                  ─► (미래: 재무패널)     │
│                               │                  ─► (미래: L2 오더북)    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 문제점

| 문제 | 설명 |
|------|------|
| **스파게티 연결** | 각 진입점마다 모든 출력점에 개별 연결 필요 (N×M 복잡도) |
| **중복 코드** | `_on_watchlist_table_clicked`, `_on_tier2_table_clicked` 등에서 동일한 로직 반복 |
| **확장성 부족** | 새 진입점/출력점 추가 시 dashboard.py 수정 필수 |
| **테스트 어려움** | ticker 선택 로직이 UI 코드에 강결합 |
| **상태 불일치** | `_current_chart_ticker` vs `_state.current_chart_ticker` 이중 관리 |

---

## 2. 목표 상태 (To-Be)

### Event Bus 기반 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│   [진입점들]              [Event Bus]              [출력점들]            │
│                                                                          │
│   Watchlist ──────┐                        ┌────► ChartWidget           │
│   Tier2 Panel ────┤                        │                             │
│   SearchBar ──────┼──► DashboardState ─────┼────► TickerInfoWindow      │
│   Favorites ──────┤    .current_ticker     │                             │
│   AlertClick ─────┘    (Single Source)     ├────► NewsPanel             │
│                              │              │                             │
│                              ▼              ├────► FinancialsPanel       │
│                     ticker_changed         │                             │
│                       (Signal)  ───────────┴────► L2OrderBook           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 핵심 원칙

1. **Single Source of Truth**: `DashboardState.current_ticker`가 유일한 진실
2. **Pub/Sub 패턴**: 진입점은 상태만 변경, 출력점은 시그널만 구독
3. **느슨한 결합**: 진입점과 출력점이 서로를 알 필요 없음
4. **O(N+M) 복잡도**: 진입점 N개, 출력점 M개 → 연결 수 = N+M (not N×M)

---

## 3. 설계 상세

### 3.1 DashboardState 확장

```python
# frontend/gui/state/dashboard_state.py

class DashboardState(QObject):
    """Dashboard 중앙 상태 관리자"""
    
    # ═══════════════════════════════════════════════════════════════════
    # 📌 Ticker Selection Event Bus
    # ═══════════════════════════════════════════════════════════════════
    
    # 현재 선택된 티커가 변경될 때 (진입점 무관하게 단일 시그널)
    ticker_changed = pyqtSignal(str, str)  # (ticker, source)
    
    # source 상수 정의 (디버깅/로깅용)
    class TickerSource:
        WATCHLIST = "watchlist"
        TIER2 = "tier2"
        SEARCH = "search"
        FAVORITES = "favorites"
        ALERT = "alert"
        EXTERNAL = "external"  # API 등 외부 요청
    
    def __init__(self):
        super().__init__()
        self._current_ticker: str | None = None
        self._previous_ticker: str | None = None  # 히스토리용
    
    @property
    def current_ticker(self) -> str | None:
        """현재 선택된 티커 (읽기 전용)"""
        return self._current_ticker
    
    def select_ticker(self, ticker: str, source: str = "unknown") -> None:
        """
        티커 선택 (유일한 진입점)
        
        모든 UI 컴포넌트는 이 메서드를 통해서만 티커를 변경해야 합니다.
        """
        if self._current_ticker == ticker:
            return  # 동일 티커면 무시 (불필요한 업데이트 방지)
        
        self._previous_ticker = self._current_ticker
        self._current_ticker = ticker
        
        # 📢 단일 시그널 발행 → 모든 구독자에게 전파
        self.ticker_changed.emit(ticker, source)
```

### 3.2 진입점 리팩토링

```python
# 변경 전 (현재)
def _on_watchlist_table_clicked(self, proxy_index):
    ticker = self._get_ticker_from_index(proxy_index)
    self._current_selected_ticker = ticker  # ❌ 자체 상태
    self._load_chart_for_ticker(ticker)     # ❌ 직접 호출

# 변경 후
def _on_watchlist_table_clicked(self, proxy_index):
    ticker = self._get_ticker_from_index(proxy_index)
    self._state.select_ticker(ticker, DashboardState.TickerSource.WATCHLIST)
    # 끝! 나머지는 Event Bus가 처리
```

### 3.3 출력점 구독 패턴

```python
# ChartPanel (구독자 예시)
class ChartPanel(QWidget):
    def __init__(self, state: DashboardState):
        super().__init__()
        self._state = state
        
        # 📌 Event Bus 구독
        self._state.ticker_changed.connect(self._on_ticker_changed)
    
    def _on_ticker_changed(self, ticker: str, source: str):
        """티커 변경 시 차트 업데이트"""
        self.load_chart(ticker)


# TickerInfoWindow (구독자 예시)
class TickerInfoWindow(QDialog):
    def connect_to_state(self, state: DashboardState):
        """DashboardState와 연결 (lazy connection)"""
        state.ticker_changed.connect(self._on_ticker_changed)
    
    def _on_ticker_changed(self, ticker: str, source: str):
        """티커 변경 시 정보 업데이트 (visible 상태일 때만)"""
        if self.isVisible():
            self.load_ticker(ticker)
```

---

## 4. 마이그레이션 전략

### Phase 1: 인프라 구축 (Breaking 없음)

| 단계 | 작업 | 파일 |
|------|------|------|
| 1.1 | `DashboardState`에 `ticker_changed` 시그널 추가 | `dashboard_state.py` |
| 1.2 | `select_ticker()` 메서드 추가 | `dashboard_state.py` |
| 1.3 | `TickerSource` 상수 클래스 추가 | `dashboard_state.py` |

### Phase 2: 출력점 마이그레이션

| 단계 | 작업 | 파일 |
|------|------|------|
| 2.1 | `TickerInfoWindow`에 `connect_to_state()` 추가 | `ticker_info_window.py` |
| 2.2 | Dashboard에서 연결 코드 추가 | `dashboard.py` |
| 2.3 | (향후) `ChartPanel`에 구독 로직 추가 | `chart_panel.py` |

### Phase 3: 진입점 마이그레이션

| 단계 | 작업 | 파일 |
|------|------|------|
| 3.1 | `_on_watchlist_table_clicked` → `select_ticker()` 호출로 변경 | `dashboard.py` |
| 3.2 | `_on_tier2_table_clicked` → `select_ticker()` 호출로 변경 | `dashboard.py` |
| 3.3 | `_current_selected_ticker` 제거 (중복 상태) | `dashboard.py` |
| 3.4 | `_current_chart_ticker` → `_state.current_ticker` 통합 | `dashboard.py` |

### Phase 4: 정리

| 단계 | 작업 | 파일 |
|------|------|------|
| 4.1 | `_load_chart_for_ticker()` 제거 (ChartPanel 내부로 이동) | `dashboard.py` |
| 4.2 | 중복 상태 변수 정리 | `dashboard.py` |
| 4.3 | 문서 업데이트 | KI 아티팩트 |

---

## 5. 확장 시나리오

### 5.1 새 진입점 추가 예시: SearchBar

```python
# frontend/gui/widgets/search_bar.py (신규)
class TickerSearchBar(QLineEdit):
    def __init__(self, state: DashboardState):
        self._state = state
        self.returnPressed.connect(self._on_search)
    
    def _on_search(self):
        ticker = self.text().upper().strip()
        if ticker:
            self._state.select_ticker(ticker, DashboardState.TickerSource.SEARCH)
```

**추가 작업**: SearchBar 위젯 생성 + Dashboard에 배치 (출력점 수정 불필요!)

### 5.2 새 출력점 추가 예시: NewsPanel

```python
# frontend/gui/panels/news_panel.py (신규)
class NewsPanel(QWidget):
    def __init__(self, state: DashboardState):
        self._state = state
        self._state.ticker_changed.connect(self._on_ticker_changed)
    
    def _on_ticker_changed(self, ticker: str, source: str):
        self.load_news_for(ticker)
```

**추가 작업**: NewsPanel 위젯 생성 + Dashboard에 배치 (진입점 수정 불필요!)

---

## 6. 복잡도 비교

| 시나리오 | 현재 (N×M) | 리팩토링 후 (N+M) |
|----------|------------|-------------------|
| 진입점 3개, 출력점 2개 | 6 연결 | 5 연결 |
| 진입점 5개, 출력점 5개 | 25 연결 | 10 연결 |
| 진입점 10개, 출력점 10개 | 100 연결 | 20 연결 |

---

## 7. 고려사항

### 7.1 Source 파라미터 활용

```python
def _on_ticker_changed(self, ticker: str, source: str):
    # 특정 source에서만 동작하는 로직
    if source == DashboardState.TickerSource.ALERT:
        self._highlight_alert_ticker(ticker)
    
    # 모든 source에서 동작하는 공통 로직
    self.load_data(ticker)
```

### 7.2 히스토리 기능 (Optional)

```python
class DashboardState(QObject):
    def __init__(self):
        self._ticker_history: list[str] = []
        self._history_max = 20
    
    def select_ticker(self, ticker: str, source: str):
        # ... 기존 로직 ...
        self._ticker_history.append(ticker)
        if len(self._ticker_history) > self._history_max:
            self._ticker_history.pop(0)
    
    def go_back(self) -> str | None:
        """이전 티커로 돌아가기"""
        if len(self._ticker_history) >= 2:
            self._ticker_history.pop()  # 현재 제거
            return self._ticker_history[-1]
        return None
```

### 7.3 Debouncing (Optional)

빠른 연속 클릭 시 불필요한 업데이트 방지:

```python
def select_ticker(self, ticker: str, source: str):
    # 100ms 이내 동일 티커 재선택 무시
    if self._debounce_timer.isActive() and ticker == self._pending_ticker:
        return
    
    self._pending_ticker = ticker
    self._pending_source = source
    self._debounce_timer.start(100)

def _emit_ticker_changed(self):
    if self._pending_ticker:
        self.ticker_changed.emit(self._pending_ticker, self._pending_source)
```

---

## 8. 예상 작업량

| Phase | 예상 시간 | 난이도 | Breaking Change |
|-------|----------|--------|-----------------|
| Phase 1 | 30분 | ⭐ | ❌ |
| Phase 2 | 1시간 | ⭐⭐ | ❌ |
| Phase 3 | 2시간 | ⭐⭐⭐ | ⚠️ (내부 리팩토링) |
| Phase 4 | 1시간 | ⭐⭐ | ❌ |

**총 예상**: 4-5시간 (테스트 포함)

---

## 9. 신규 위젯: TickerSearchBar

### 9.1 개요

Top Panel (ControlPanel)에 추가할 **통합 티커 검색/선택 위젯**입니다.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ [Sigma9 Logo]  [Connect]  [Start Engine]  | [TickerSearchBar] | [Time] [⚙] │
└─────────────────────────────────────────────────────────────────────────────┘
                                                    ▲
                                                    │
                            ┌───────────────────────┴───────────────────────┐
                            │                                               │
                            │   ┌─────────────────────────────────────────┐ │
                            │   │ 🔍 AAPL • Apple Inc.                ▼ │ │
                            │   └─────────────────────────────────────────┘ │
                            │                                               │
                            │   [드롭다운 메뉴]                             │
                            │   ┌─────────────────────────────────────────┐ │
                            │   │ 📌 Recent                               │ │
                            │   │   ├── AAPL • Apple Inc.                │ │
                            │   │   ├── TSLA • Tesla Inc.                │ │
                            │   │   └── MSFT • Microsoft Corporation     │ │
                            │   │─────────────────────────────────────────│ │
                            │   │ 🔤 Suggestions (typing "AA")            │ │
                            │   │   ├── AAPL • Apple Inc.                │ │
                            │   │   ├── AAL  • American Airlines Group   │ │
                            │   │   ├── AACG • ATA Creativity Global     │ │
                            │   │   └── AAP  • Advance Auto Parts        │ │
                            │   └─────────────────────────────────────────┘ │
                            │                                               │
                            └───────────────────────────────────────────────┘
```

### 9.2 기능 요구사항

| 기능 | 설명 |
|------|------|
| **현재 티커 표시** | `DashboardState.current_ticker` 실시간 반영 |
| **수동 입력** | 티커 직접 입력 후 Enter → 선택 |
| **최근 조회 히스토리** | 최근 N개 (default: 10) 티커 드롭다운 |
| **자동완성** | 입력 중 prefix 매칭 티커 + 기업명 표시 |
| **키보드 네비게이션** | ↑↓ 로 선택, Enter로 확정, Esc로 닫기 |

### 9.3 설계

```python
# frontend/gui/widgets/ticker_search_bar.py

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QListWidget, 
    QListWidgetItem, QFrame, QLabel, QVBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

class TickerSearchBar(QWidget):
    """
    통합 티커 검색/선택 위젯
    
    Features:
    - 현재 티커 표시
    - 수동 입력 + 자동완성
    - 최근 히스토리 드롭다운
    """
    
    ticker_selected = pyqtSignal(str)  # 티커 선택 시 → DashboardState.select_ticker()
    
    def __init__(self, state: "DashboardState", parent=None):
        super().__init__(parent)
        self._state = state
        self._ticker_data: dict[str, str] = {}  # {"AAPL": "Apple Inc.", ...}
        self._recent_history: list[str] = []
        self._max_history = 10
        
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 검색 아이콘
        self.search_icon = QLabel("🔍")
        layout.addWidget(self.search_icon)
        
        # 입력 필드 (editable combobox-like)
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Search ticker...")
        self.input_field.setMinimumWidth(180)
        layout.addWidget(self.input_field)
        
        # 드롭다운 버튼
        self.dropdown_btn = QPushButton("▼")
        self.dropdown_btn.setFixedWidth(24)
        layout.addWidget(self.dropdown_btn)
        
        # 드롭다운 팝업 (QFrame으로 구현)
        self._init_dropdown_popup()
    
    def _init_dropdown_popup(self):
        """드롭다운 팝업 초기화"""
        self.popup = QFrame(self, Qt.WindowType.Popup)
        self.popup.setFrameShape(QFrame.Shape.StyledPanel)
        self.popup.hide()
        
        popup_layout = QVBoxLayout(self.popup)
        
        # Recent 섹션
        self.recent_label = QLabel("📌 Recent")
        popup_layout.addWidget(self.recent_label)
        
        self.recent_list = QListWidget()
        self.recent_list.setMaximumHeight(100)
        popup_layout.addWidget(self.recent_list)
        
        # Suggestions 섹션
        self.suggestions_label = QLabel("🔤 Suggestions")
        popup_layout.addWidget(self.suggestions_label)
        
        self.suggestions_list = QListWidget()
        self.suggestions_list.setMaximumHeight(150)
        popup_layout.addWidget(self.suggestions_list)
    
    def _connect_signals(self):
        # 텍스트 변경 → 자동완성
        self.input_field.textChanged.connect(self._on_text_changed)
        
        # Enter 키 → 선택
        self.input_field.returnPressed.connect(self._on_enter_pressed)
        
        # 드롭다운 버튼 → 팝업 토글
        self.dropdown_btn.clicked.connect(self._toggle_popup)
        
        # 리스트 클릭 → 선택
        self.recent_list.itemClicked.connect(self._on_item_clicked)
        self.suggestions_list.itemClicked.connect(self._on_item_clicked)
        
        # DashboardState.ticker_changed 구독
        self._state.ticker_changed.connect(self._on_ticker_changed)
    
    def _on_text_changed(self, text: str):
        """입력 중 자동완성 업데이트"""
        if not text:
            self.suggestions_list.clear()
            return
        
        prefix = text.upper()
        matches = [
            (ticker, name) 
            for ticker, name in self._ticker_data.items()
            if ticker.startswith(prefix) or prefix in name.upper()
        ][:10]  # 최대 10개
        
        self.suggestions_list.clear()
        for ticker, name in matches:
            item = QListWidgetItem(f"{ticker} • {name}")
            item.setData(Qt.ItemDataRole.UserRole, ticker)
            self.suggestions_list.addItem(item)
        
        if matches:
            self._show_popup()
    
    def _on_enter_pressed(self):
        """Enter 키로 선택"""
        ticker = self.input_field.text().upper().strip()
        if ticker:
            self._select_ticker(ticker)
    
    def _on_item_clicked(self, item: QListWidgetItem):
        """드롭다운 항목 클릭"""
        ticker = item.data(Qt.ItemDataRole.UserRole)
        self._select_ticker(ticker)
    
    def _select_ticker(self, ticker: str):
        """티커 선택 (Event Bus로 전파)"""
        self.ticker_selected.emit(ticker)
        self._add_to_history(ticker)
        self._update_display(ticker)
        self.popup.hide()
    
    def _add_to_history(self, ticker: str):
        """히스토리에 추가"""
        if ticker in self._recent_history:
            self._recent_history.remove(ticker)
        self._recent_history.insert(0, ticker)
        self._recent_history = self._recent_history[:self._max_history]
        self._update_recent_list()
    
    def _update_recent_list(self):
        """최근 히스토리 리스트 업데이트"""
        self.recent_list.clear()
        for ticker in self._recent_history:
            name = self._ticker_data.get(ticker, "")
            item = QListWidgetItem(f"{ticker} • {name}")
            item.setData(Qt.ItemDataRole.UserRole, ticker)
            self.recent_list.addItem(item)
    
    def _update_display(self, ticker: str):
        """현재 티커 표시 업데이트"""
        name = self._ticker_data.get(ticker, "")
        display = f"{ticker} • {name}" if name else ticker
        self.input_field.setText(display)
    
    def _on_ticker_changed(self, ticker: str, source: str):
        """DashboardState.ticker_changed 시그널 핸들러"""
        self._update_display(ticker)
        self._add_to_history(ticker)
    
    # ───────────────────────────────────────────────────────────────────
    # Public API
    # ───────────────────────────────────────────────────────────────────
    
    def set_ticker_data(self, data: dict[str, str]):
        """
        티커 데이터 설정 (자동완성용)
        
        Args:
            data: {"AAPL": "Apple Inc.", "MSFT": "Microsoft Corporation", ...}
        """
        self._ticker_data = data
    
    def get_recent_history(self) -> list[str]:
        """최근 히스토리 반환"""
        return self._recent_history.copy()
```

### 9.4 데이터 소스: 티커 목록

자동완성에 사용할 티커 + 기업명 데이터:

```python
# backend/data/ticker_list.py

class TickerListService:
    """티커 목록 서비스 (자동완성용)"""
    
    async def get_all_tickers(self) -> dict[str, str]:
        """
        전체 티커 목록 조회
        
        Returns:
            {"AAPL": "Apple Inc.", "MSFT": "Microsoft Corporation", ...}
        """
        # Option 1: Massive API
        # Option 2: 로컬 캐시 (JSON/SQLite)
        # Option 3: 하드코딩된 Top 5000
        pass
```

**권장 접근법:**
1. 앱 시작 시 Massive API에서 전체 티커 목록 가져오기
2. SQLite에 캐싱 (만료: 24시간)
3. Frontend에 WebSocket으로 전달 또는 REST로 로드

### 9.5 ControlPanel 통합

```python
# frontend/gui/control_panel.py (수정)

class ControlPanel(QFrame):
    def _init_ui(self):
        # ... 기존 코드 ...
        
        # 로고 뒤에 추가
        layout.addWidget(logo_container)
        
        layout.addWidget(self._create_separator())
        
        # 📌 NEW: Ticker Search Bar [09-009]
        self.ticker_search = TickerSearchBar(state=self._state)
        self.ticker_search.ticker_selected.connect(self._on_ticker_search_selected)
        layout.addWidget(self.ticker_search)
        
        layout.addStretch(1)
        
        # ... 나머지 코드 ...
    
    def _on_ticker_search_selected(self, ticker: str):
        """TickerSearchBar에서 티커 선택"""
        self._state.select_ticker(ticker, TickerSource.SEARCH)
```

### 9.6 구현 Phase

| 단계 | 작업 | 파일 |
|------|------|------|
| 9.1 | `TickerListService` 생성 (Backend) | `backend/data/ticker_list.py` |
| 9.2 | `TickerSearchBar` 위젯 생성 | `frontend/gui/widgets/ticker_search_bar.py` |
| 9.3 | `ControlPanel`에 통합 | `frontend/gui/control_panel.py` |
| 9.4 | 앱 시작 시 티커 목록 로드 | `frontend/main.py` |
| 9.5 | 히스토리 저장/복원 (localStorage) | `frontend/services/local_storage.py` |

### 9.7 UI 스타일

```python
# 테마와 일관된 스타일
SEARCH_BAR_STYLE = f"""
    QLineEdit {{
        background-color: {theme.get_color("surface")};
        border: 1px solid {theme.get_color("border")};
        border-radius: 4px;
        color: {theme.get_color("text")};
        padding: 4px 8px;
        font-size: 12px;
    }}
    QLineEdit:focus {{
        border-color: {theme.get_color("primary")};
    }}
    
    QListWidget {{
        background-color: {theme.get_color("background")};
        border: 1px solid {theme.get_color("border")};
        border-radius: 4px;
        color: {theme.get_color("text")};
    }}
    QListWidget::item:hover {{
        background-color: {theme.get_color("surface")};
    }}
    QListWidget::item:selected {{
        background-color: {theme.get_color("primary")};
    }}
"""
```

---

## 10. 아키텍처 결정: Frontend vs Backend 관리

### 10.1 문제 제기

> "선택된 티커로 수동주문을 넣거나, Backend 코드(Ticker Info 조회 등)를 구동해야 한다면?"

이 경우 **Frontend에서만 상태를 관리하면 문제**가 발생합니다:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 현재: Frontend-only 상태 관리                                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Frontend                              Backend                          │
│   ┌─────────────────────┐               ┌─────────────────────┐         │
│   │ current_ticker=AAPL │──── API ────► │ ??? (모름)          │         │
│   │ (상태 있음)          │     호출      │ (stateless)         │         │
│   └─────────────────────┘               └─────────────────────┘         │
│                                                                          │
│   ❌ 문제: Backend가 "현재 선택된 티커"를 모름                          │
│   ❌ 매번 API 호출 시 ticker를 파라미터로 전달해야 함                    │
│   ❌ Backend에서 자발적으로 "선택된 티커"에 대한 작업 불가               │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 10.2 옵션 비교

#### Option A: Frontend as Source of Truth (현재 설계)

```python
# Frontend
class DashboardState:
    current_ticker: str  # ← 유일한 진실

# Backend API 호출 시
response = backend.get_ticker_info(ticker=state.current_ticker)  # 매번 전달
response = backend.place_order(ticker=state.current_ticker, ...)
```

| 장점 | 단점 |
|------|------|
| 단순함 | Backend가 context를 모름 |
| 네트워크 오버헤드 적음 | 모든 API에 ticker 파라미터 필수 |
| Frontend만 수정 | Multi-client 시나리오 불가능 |

**적합한 경우**: 단일 클라이언트, UI 상태만 관리

---

#### Option B: Backend as Source of Truth (권장)

```python
# Backend
class TradingContext:
    active_ticker: str  # ← 유일한 진실
    
# Frontend → Backend (WebSocket)
ws.send({"type": "SET_ACTIVE_TICKER", "ticker": "AAPL"})

# Backend → Frontend (브로드캐스트)
ws.broadcast({"type": "ACTIVE_TICKER_CHANGED", "ticker": "AAPL"})

# Backend 내부에서 context 활용
order_service.place_order(ctx.active_ticker, ...)  # 파라미터 불필요
ticker_info_service.get_info(ctx.active_ticker)
```

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Backend as Source of Truth                                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Frontend                              Backend                          │
│   ┌─────────────────────┐               ┌─────────────────────┐         │
│   │ UI: AAPL selected   │◄── sync ────► │ TradingContext      │         │
│   │ (mirror)            │               │   active_ticker=AAPL│         │
│   └─────────────────────┘               │   (Source of Truth) │         │
│         │                               └─────────────────────┘         │
│         │ click                                    │                     │
│         ▼                                          ▼                     │
│   SET_ACTIVE_TICKER ─────────────────────► update + broadcast            │
│                                                    │                     │
│                                          ┌────────┴────────┐            │
│                                          ▼                 ▼            │
│                                     TickerInfo        OrderService      │
│                                     (자동 연동)        (context 활용)    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

| 장점 | 단점 |
|------|------|
| Backend 서비스들이 context 공유 | WebSocket 의존성 증가 |
| Multi-client 지원 (여러 GUI) | 초기 구현 복잡도 |
| API 파라미터 단순화 | 상태 동기화 로직 필요 |
| Backend initiated actions 가능 | |

**적합한 경우**: 트레이딩 시스템, Backend 로직과 연동 필요

---

#### Option C: Hybrid - 계층별 분리

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Hybrid: 관심사별 분리                                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌─── UI Layer (Frontend) ───┐    ┌─── Domain Layer (Backend) ───┐    │
│   │                            │    │                               │    │
│   │  selected_row: int         │    │  TradingContext:              │    │
│   │  highlighted_ticker: str   │    │    active_ticker: str         │    │
│   │  (순수 UI 상태)            │    │    position_ticker: str       │    │
│   │                            │    │    (비즈니스 상태)             │    │
│   └────────────┬───────────────┘    └───────────────┬───────────────┘    │
│                │                                     │                   │
│                └──────────── sync ───────────────────┘                   │
│                                                                          │
│   📌 규칙:                                                               │
│   - UI 상태 (row highlight, scroll position): Frontend 관리             │
│   - 비즈니스 상태 (주문 대상, 분석 대상): Backend 관리                    │
│   - WebSocket으로 양방향 동기화                                          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### 10.3 Sigma9 권장 아키텍처: Option B (Backend as SoT)

**이유:**

1. **수동 주문**: Backend의 `OrderService`가 `active_ticker`를 알아야 함
2. **Ticker Info**: Backend의 `TickerInfoService`가 이미 존재
3. **전략 실행**: Backend 전략 엔진이 현재 티커 context 필요
4. **멀티 클라이언트**: 향후 모바일/웹 클라이언트 확장 가능성

---

### 10.4 구현 설계

#### Backend 변경

```python
# backend/core/trading_context.py (신규)

class TradingContext:
    """
    트레이딩 세션의 공유 콘텍스트
    
    모든 Backend 서비스가 참조하는 "현재 상태"
    """
    
    def __init__(self):
        self._active_ticker: str | None = None
        self._subscribers: list[Callable] = []
    
    @property
    def active_ticker(self) -> str | None:
        return self._active_ticker
    
    def set_active_ticker(self, ticker: str, source: str = "unknown") -> None:
        """
        활성 티커 변경 (유일한 진입점)
        
        변경 시 모든 구독자에게 알림
        """
        if self._active_ticker == ticker:
            return
        
        self._active_ticker = ticker
        
        # 내부 구독자 알림 (Backend 서비스들)
        for callback in self._subscribers:
            callback(ticker, source)
    
    def subscribe(self, callback: Callable[[str, str], None]) -> None:
        """Backend 서비스들이 티커 변경을 구독"""
        self._subscribers.append(callback)


# backend/container.py (DI 컨테이너에 추가)
trading_context = TradingContext()
```

#### WebSocket 프로토콜 확장

```python
# 새로운 메시지 타입

# Frontend → Backend
{
    "type": "SET_ACTIVE_TICKER",
    "ticker": "AAPL",
    "source": "watchlist"  # 진입점 추적용
}

# Backend → Frontend (브로드캐스트)
{
    "type": "ACTIVE_TICKER_CHANGED",
    "ticker": "AAPL",
    "source": "watchlist"
}
```

#### Frontend 변경

```python
# frontend/gui/state/dashboard_state.py

class DashboardState(QObject):
    ticker_changed = pyqtSignal(str, str)  # (ticker, source)
    
    def __init__(self, ws_adapter: WSAdapter):
        self._ws = ws_adapter
        self._current_ticker: str | None = None
        
        # Backend로부터 ticker 변경 알림 수신
        self._ws.on_message.connect(self._handle_ws_message)
    
    def select_ticker(self, ticker: str, source: str) -> None:
        """
        티커 선택 → Backend에 전송
        
        실제 상태 변경은 Backend 응답(ACTIVE_TICKER_CHANGED) 수신 시
        """
        self._ws.send({
            "type": "SET_ACTIVE_TICKER",
            "ticker": ticker,
            "source": source
        })
    
    def _handle_ws_message(self, msg: dict) -> None:
        if msg.get("type") == "ACTIVE_TICKER_CHANGED":
            ticker = msg["ticker"]
            source = msg.get("source", "backend")
            
            self._current_ticker = ticker
            self.ticker_changed.emit(ticker, source)  # UI 업데이트
```

---

### 10.5 데이터 흐름 예시

#### 예시 1: Watchlist에서 티커 선택

```
1. User clicks AAPL in Watchlist
2. Frontend: DashboardState.select_ticker("AAPL", "watchlist")
3. Frontend → Backend: {"type": "SET_ACTIVE_TICKER", "ticker": "AAPL"}
4. Backend: TradingContext.set_active_ticker("AAPL")
5. Backend: 내부 서비스들에게 알림 (TickerInfoService 등)
6. Backend → Frontend: {"type": "ACTIVE_TICKER_CHANGED", "ticker": "AAPL"}
7. Frontend: DashboardState._current_ticker = "AAPL"
8. Frontend: ticker_changed.emit("AAPL", "watchlist")
9. UI Updates: Chart, TickerInfoWindow, etc.
```

#### 예시 2: Backend에서 주문 실행

```python
# Backend: OrderService
def execute_buy(self, quantity: int, price: float):
    ticker = self._trading_context.active_ticker  # ← context에서 가져옴
    if not ticker:
        raise ValueError("No active ticker selected")
    
    return self._broker.buy(ticker, quantity, price)
```

---

### 10.6 마이그레이션 확장 (Phase 5 추가)

| Phase | 작업 | 위치 |
|-------|------|------|
| **5.1** | `TradingContext` 클래스 생성 | `backend/core/` |
| **5.2** | WebSocket 핸들러에 `SET_ACTIVE_TICKER` 추가 | `backend/api/` |
| **5.3** | `DashboardState`에서 WebSocket 연동 | `frontend/gui/state/` |
| **5.4** | 기존 서비스들이 `TradingContext` 구독하도록 수정 | `backend/services/` |

---

### 10.7 결정 Matrix

| 기능 | Frontend 관리 | Backend 관리 (권장) |
|------|--------------|-------------------|
| UI highlight | ✅ | - |
| Chart 로드 | ✅ (local trigger) | ✅ (sync) |
| Ticker Info 조회 | ❌ (매번 param) | ✅ (context) |
| 수동 주문 | ❌ (매번 param) | ✅ (context) |
| 전략 실행 | ❌ | ✅ (context) |
| Multi-client | ❌ | ✅ |
| Offline 동작 | ✅ | ❌ |

---

## 11. 레이턴시 대응: Optimistic Update 패턴

### 11.1 문제: 한국 ↔ AWS US-East 레이턴시

| 구간 | 예상 RTT |
|------|----------|
| 한국 → AWS US-East (Virginia) | **150-250ms** |
| 한국 → AWS Seoul | 5-15ms |

**Backend as SoT만 사용 시**: 클릭 후 UI 반응까지 ~250ms (체감됨)

### 11.2 해결: Optimistic Update

```python
# frontend/gui/state/dashboard_state.py

def select_ticker(self, ticker: str, source: str) -> None:
    """
    티커 선택 (Optimistic Update 패턴)
    
    1. 즉시 로컬 상태 업데이트 (0ms) → UI 즉각 반응
    2. Backend에 비동기 전송 (250ms) → 확인용
    """
    if self._current_ticker == ticker:
        return
    
    # 1. 즉시 로컬 업데이트 (Optimistic)
    self._current_ticker = ticker
    self.ticker_changed.emit(ticker, source)  # ← UI 즉각 반응
    
    # 2. Backend 동기화 (비동기, fire-and-forget)
    if self._ws and self._ws.is_connected():
        self._ws.send({
            "type": "SET_ACTIVE_TICKER",
            "ticker": ticker,
            "source": source
        })
```

### 11.3 결과

| 항목 | 순수 Backend SoT | Optimistic Update |
|------|:---------------:|:-----------------:|
| UI 반응 속도 | 250ms | **0ms** |
| Backend 동기화 | ✅ | ✅ (비동기) |
| 일관성 | 강함 (동기) | 결과적 일관성 |

---

## 12. DI Container 등록

### 12.1 Backend 변경

```python
# backend/container.py

@staticmethod
def _create_trading_context():
    """
    TradingContext 생성 팩토리
    
    📌 [09-009] 활성 티커 컨텍스트 관리
    📌 모든 Backend 서비스가 공유하는 "현재 상태"
    """
    from backend.core.trading_context import TradingContext
    return TradingContext()

# TradingContext: 트레이딩 컨텍스트 (Singleton)
trading_context = providers.Singleton(_create_trading_context)
```

### 12.2 등록되는 항목

```
Container (기존)
├── config
├── ws_manager
├── Data Layer
│   ├── massive_client
│   ├── parquet_manager
│   ├── data_repository
│   └── database
├── Strategy Layer
│   ├── watchlist_store
│   ├── ticker_info_service
│   ├── symbol_mapper
│   └── scoring_strategy
├── Core Layer
│   ├── realtime_scanner
│   ├── ignition_monitor
│   ├── audit_logger
│   ├── event_deduplicator
│   └── event_sequencer
│
└── 📌 NEW: trading_context  ← 추가됨
```

---

## 13. 최종 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│   Frontend (Local, Korea)               Backend (AWS US-East)           │
│                                                                          │
│   ┌─────────────────────┐               ┌─────────────────────┐         │
│   │ DashboardState      │               │ TradingContext      │ ← DI    │
│   │   _current_ticker   │◄───sync────►  │   _active_ticker    │         │
│   │   (Optimistic)      │   WebSocket   │   (Source of Truth) │         │
│   └─────────────────────┘               └─────────────────────┘         │
│         │                                        │                       │
│         │ 즉시 (0ms)                             │ 구독자 알림           │
│         ▼                                        ├─→ TickerInfoService  │
│   ticker_changed                                 ├─→ OrderService       │
│   (PyQt Signal)                                  └─→ StrategyEngine     │
│         │                                                                │
│   ┌─────┼─────┐                                                          │
│   ▼     ▼     ▼                                                          │
│ Chart  Info  News                                                        │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 14. 구현 Phase 정리

### Phase 1: Backend 인프라 (Breaking 없음)

| 단계 | 작업 | 파일 |
|------|------|------|
| 1.1 | `TradingContext` 클래스 생성 | `backend/core/trading_context.py` |
| 1.2 | DI Container에 등록 | `backend/container.py` |
| 1.3 | WebSocket 핸들러 추가 (`SET_ACTIVE_TICKER`) | `backend/api/websocket.py` |

### Phase 2: Frontend Event Bus

| 단계 | 작업 | 파일 |
|------|------|------|
| 2.1 | `DashboardState`에 `ticker_changed` 시그널 추가 | `dashboard_state.py` |
| 2.2 | `select_ticker()` 메서드 (Optimistic Update) | `dashboard_state.py` |
| 2.3 | WebSocket 메시지 핸들링 | `dashboard_state.py` |

### Phase 3: 출력점 마이그레이션

| 단계 | 작업 | 파일 |
|------|------|------|
| 3.1 | `TickerInfoWindow`에 시그널 연결 | `ticker_info_window.py` |
| 3.2 | `ChartPanel`에 시그널 연결 | `chart_panel.py` |
| 3.3 | Dashboard에서 연결 코드 추가 | `dashboard.py` |

### Phase 4: 진입점 마이그레이션

| 단계 | 작업 | 파일 |
|------|------|------|
| 4.1 | `_on_watchlist_table_clicked` → `select_ticker()` | `dashboard.py` |
| 4.2 | `_on_tier2_table_clicked` → `select_ticker()` | `dashboard.py` |
| 4.3 | 중복 상태 변수 제거 | `dashboard.py` |

### Phase 5: Backend 서비스 연동

| 단계 | 작업 | 파일 |
|------|------|------|
| 5.1 | `TickerInfoService`가 `TradingContext` 구독 | `ticker_info_service.py` |
| 5.2 | `OrderService`가 `TradingContext` 활용 | `order_service.py` |
| 5.3 | 전략 엔진 연동 (향후) | `strategy_engine.py` |

---

## 15. 결론

### 최종 결정

| 항목 | 선택 |
|------|------|
| **Source of Truth** | Backend (`TradingContext`) |
| **레이턴시 대응** | Optimistic Update (Frontend 즉시 반응) |
| **DI 등록** | `trading_context` 추가 |
| **WebSocket 프로토콜** | `SET_ACTIVE_TICKER`, `ACTIVE_TICKER_CHANGED` |

### 핵심 변경

1. **Backend**: `TradingContext` 클래스 생성 및 DI 등록
2. **Frontend**: `DashboardState.select_ticker()` + Optimistic Update
3. **진입점**: `_state.select_ticker(ticker, source)` 호출만
4. **출력점**: `_state.ticker_changed.connect(handler)` 구독만
5. **중복 상태 제거**: `_current_selected_ticker`, `_current_chart_ticker` → 통합

### 기대 효과

- ✅ **확장성**: 새 진입점/출력점 추가 시 다른 컴포넌트 수정 불필요
- ✅ **유지보수성**: ticker 선택 로직이 한 곳에 집중
- ✅ **Backend 연동**: OrderService, StrategyEngine이 context 공유
- ✅ **레이턴시 해결**: UI 즉각 반응 (0ms)
- ✅ **테스트 용이성**: TradingContext, DashboardState 단위 테스트 가능

### 예상 작업량

| Phase | 예상 시간 | 난이도 |
|-------|----------|--------|
| Phase 1 (Backend 인프라) | 2시간 | ⭐⭐ |
| Phase 2 (Frontend Event Bus) | 1시간 | ⭐⭐ |
| Phase 3 (출력점) | 1시간 | ⭐ |
| Phase 4 (진입점) | 1시간 | ⭐ |
| Phase 5 (Backend 서비스) | 2시간 | ⭐⭐ |

**총 예상**: 7-8시간 (테스트 포함)

---

> **📋 Status**: 계획 완료. 사용자 승인 후 구현 진행.
