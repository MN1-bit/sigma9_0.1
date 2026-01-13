# ==============================================================================
# ticker_search_bar.py - 티커 검색/선택 위젯
# ==============================================================================
# 📌 [09-107] TickerSearchBar 위젯
#
# 역할:
#   - 현재 선택된 티커 표시 (AAPL • Apple Inc.)
#   - 수동 입력 + 자동완성
#   - 최근 히스토리 드롭다운
#
# 사용:
#   control_panel.ticker_search.set_ticker_data({"AAPL": "Apple Inc.", ...})
#   control_panel.ticker_search.set_current_ticker("AAPL")
# ==============================================================================

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal, QStringListModel
from PyQt6.QtWidgets import (
    QComboBox,
    QCompleter,
    QHBoxLayout,
    QLabel,
    QWidget,
)

if TYPE_CHECKING:
    pass

from ..theme import theme


class TickerSearchBar(QWidget):
    """
    통합 티커 검색/선택 위젯

    Features:
        - 현재 티커 표시 (AAPL • Apple Inc.)
        - 수동 입력 + 자동완성
        - 최근 히스토리 드롭다운

    Signals:
        ticker_selected(str): 티커 선택 시 발행
    """

    ticker_selected = pyqtSignal(str)  # 티커 선택 시 발행

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._ticker_data: dict[str, str] = {}  # {ticker: name}
        self._recent_history: list[str] = []
        self._max_history = 10

        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        """UI 초기화"""
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
        # ELI5: 타이핑하면 자동으로 추천 목록을 보여주는 기능
        self.completer = QCompleter()
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchFlag.MatchStartsWith)
        self.completer.setMaxVisibleItems(8)  # [14-001] 최대 8개 표시
        self.combo.setCompleter(self.completer)

        layout.addWidget(self.combo)

    def _get_style(self) -> str:
        """ComboBox 스타일 반환"""
        # [14-003 FIX] QAbstractItemView에 surface 색상 사용 (background는 투명도 문제)
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
                background-color: {theme.get_color("surface")};
                border: 1px solid {theme.get_color("border")};
                color: {theme.get_color("text")};
                selection-background-color: {theme.get_color("primary")};
            }}
        """

    def _connect_signals(self) -> None:
        """시그널 연결"""
        # Enter 키 또는 항목 선택 시
        self.combo.lineEdit().returnPressed.connect(self._on_enter)
        self.combo.activated.connect(self._on_item_selected)

    def _on_enter(self) -> None:
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

    def _on_item_selected(self, index: int) -> None:
        """드롭다운 항목 선택"""
        _ = index  # unused
        text = self.combo.currentText()
        if " • " in text:
            ticker = text.split(" • ")[0]
        else:
            ticker = text

        if ticker:
            self._add_to_history(ticker)
            self.ticker_selected.emit(ticker)

    def _add_to_history(self, ticker: str) -> None:
        """히스토리에 추가"""
        if ticker in self._recent_history:
            self._recent_history.remove(ticker)
        self._recent_history.insert(0, ticker)
        self._recent_history = self._recent_history[: self._max_history]
        self._update_combo_items()

    def _update_combo_items(self) -> None:
        """ComboBox 항목 업데이트"""
        self.combo.clear()
        for ticker in self._recent_history:
            name = self._ticker_data.get(ticker, "")
            display = f"{ticker} • {name}" if name else ticker
            self.combo.addItem(display)

    # =========================================================================
    # Public API
    # =========================================================================

    def set_ticker_data(self, data: dict[str, str]) -> None:
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

    def set_current_ticker(self, ticker: str) -> None:
        """현재 티커 표시 업데이트"""
        name = self._ticker_data.get(ticker, "")
        display = f"{ticker} • {name}" if name else ticker
        self.combo.setCurrentText(display)

    def on_ticker_changed(self, ticker: str, source: str) -> None:
        """
        DashboardState.ticker_changed 시그널 핸들러

        다른 곳에서 티커가 변경되면 SearchBar도 업데이트
        """
        _ = source  # unused
        self.set_current_ticker(ticker)
        self._add_to_history(ticker)
