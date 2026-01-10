# ==============================================================================
# tier2_panel.py - Tier 2 Hot Zone 패널
# ==============================================================================
# 📌 이 파일의 역할:
#    Sigma9 Dashboard의 Tier 2 Hot Zone 테이블입니다.
#    Ignition Score가 높거나 특정 조건을 만족하는 종목이 승격되어 표시됩니다.
#
# 📌 ELI5:
#    "뜨거운 구역"에 올라온 종목들을 보여주는 테이블이에요.
#    점수가 높으면 자동으로 올라오고, 낮아지면 내려가요.
# ==============================================================================
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Callable

from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

if TYPE_CHECKING:
    from ..state.dashboard_state import DashboardState


# ==============================================================================
# Tier2Item: Hot Zone 종목 데이터 모델
# ==============================================================================
@dataclass
class Tier2Item:
    """
    Tier 2 Hot Zone 종목 데이터 모델

    ELI5: Hot Zone(뜨거운 구역)에 올라온 종목의 정보를 담는 상자예요.
    가격, 등락율, Z-Score, Ignition Score 등을 기록합니다.
    """

    ticker: str
    price: float = 0.0  # 실시간 가격
    change_pct: float = 0.0  # 등락율
    zenV: float = 0.0  # Z-score Volume
    zenP: float = 0.0  # Z-score Price
    ignition: float = 0.0  # Ignition Score
    signal: str = ""  # "🔥" (Divergence) 또는 "🎯" (Ignition>=70)
    last_update: datetime = None  # 마지막 틱 수신 시간

    def __post_init__(self):
        if self.last_update is None:
            self.last_update = datetime.now()


class NumericTableWidgetItem(QTableWidgetItem):
    """
    숫자 값으로 정렬되는 QTableWidgetItem

    ELI5: 일반 테이블 아이템은 "10"을 "2"보다 작다고 생각해요 (글자 순서로).
    이 클래스는 숫자로 비교해서 10 > 2가 되도록 해요.
    """

    def __init__(self, display_text: str, sort_value: float = 0.0):
        super().__init__(display_text)
        self._sort_value = sort_value
        # UserRole에도 저장 (하위 호환성)
        self.setData(Qt.ItemDataRole.UserRole, sort_value)

    def __lt__(self, other):
        """정렬 비교: 숫자 값으로 비교"""
        if isinstance(other, NumericTableWidgetItem):
            return self._sort_value < other._sort_value
        # 일반 QTableWidgetItem과 비교 시
        try:
            other_value = other.data(Qt.ItemDataRole.UserRole)
            if other_value is not None:
                return self._sort_value < float(other_value)
        except (TypeError, ValueError):
            pass
        return super().__lt__(other)


class Tier2Panel(QFrame):
    """
    Tier 2 Hot Zone 패널

    ═══════════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════════
    이건 "특별 감시 대상" 종목을 보여주는 테이블이에요.

    Ignition Score가 70 이상이거나, 특별한 신호(🔥 거래량 폭발 등)가 감지되면
    자동으로 이 테이블로 승격됩니다.

    컬럼 설명:
    - Ticker: 종목 코드 (AAPL, TSLA 등)
    - Price: 현재 가격
    - Chg%: 등락율
    - zenV: 거래량 Z-Score (높을수록 평소보다 거래량 많음)
    - zenP: 가격 변동 Z-Score
    - Ign: Ignition Score (폭발 임박 점수)
    - Sig: 시그널 (🔥 = 거래량 폭발, 🎯 = 타격 준비)
    ═══════════════════════════════════════════════════════════════════════════
    """

    # 시그널
    row_clicked = pyqtSignal(int, int)  # row, column

    def __init__(
        self,
        state: DashboardState | None = None,
        theme=None,
        on_save_column_widths: Callable[[str, int, int], None] | None = None,
    ):
        """
        Tier 2 패널 초기화

        Args:
            state: DashboardState 인스턴스 (DI)
            theme: 테마 매니저 (기본값: 전역 theme 사용)
            on_save_column_widths: 컬럼 너비 저장 콜백
        """
        super().__init__()

        from ..theme import theme as global_theme

        self._theme = theme or global_theme
        self._state = state
        self._on_save_column_widths = on_save_column_widths

        # 테이블 위젯
        self._table: QTableWidget | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI 구성"""
        c = self._theme.colors

        # 레이아웃
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(4)

        # 제목 라벨
        tier2_label = QLabel("🔥 Hot Zone")
        tier2_label.setStyleSheet(f"""
            color: {c["warning"]}; 
            font-size: 12px; 
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        layout.addWidget(tier2_label)

        # 테이블 생성
        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(
            ["Ticker", "Price", "Chg%", "zenV", "zenP", "Ign", "Sig"]
        )

        # 정렬 활성화
        self._table.setSortingEnabled(True)

        # 선택 모드
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

        # 헤더 설정
        header = self._table.horizontalHeader()
        header.setStretchLastSection(False)
        for i in range(7):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

        # 기본 컬럼 너비
        default_widths = [60, 60, 50, 45, 45, 40, 30]
        for i, width in enumerate(default_widths):
            self._table.setColumnWidth(i, width)

        # 저장된 컬럼 너비 로드
        self._load_saved_column_widths()

        # 컬럼 너비 변경 시 저장
        header.sectionResized.connect(self._on_section_resized)

        # 행 높이 및 고정 높이
        self._table.verticalHeader().setDefaultSectionSize(24)
        self._table.verticalHeader().setVisible(False)
        self._table.setMaximumHeight(150)

        # 스타일
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent;
                border: 1px solid {c["border"]};
                border-radius: 4px;
                color: {c["text"]};
                font-size: 11px;
                gridline-color: {c["border"]};
            }}
            QTableWidget::item {{
                padding: 2px 4px;
            }}
            QTableWidget::item:selected {{
                background-color: {c["primary"]};
                color: white;
            }}
            QHeaderView::section {{
                background-color: {c["surface"]};
                color: {c["text_secondary"]};
                border: 1px solid {c["border"]};
                padding: 4px;
                font-size: 10px;
                font-weight: bold;
            }}
        """)

        # 클릭 시그널 연결
        self._table.cellClicked.connect(self.row_clicked.emit)

        layout.addWidget(self._table)

    def _load_saved_column_widths(self) -> None:
        """저장된 컬럼 너비 로드"""
        try:
            from frontend.config.loader import load_settings

            saved = load_settings().get("tables", {}).get("tier2_column_widths", [])
            default_widths = [60, 60, 50, 45, 45, 40, 30]
            for i in range(1, min(7, len(saved))):
                width = saved[i] if saved[i] > 0 else default_widths[i]
                self._table.setColumnWidth(i, width)
        except Exception:
            pass  # 설정 로드 실패 시 기본값 사용

    def _on_section_resized(self, index: int, old_size: int, new_size: int) -> None:
        """컬럼 너비 변경 시 저장"""
        if self._on_save_column_widths and index > 0:
            self._on_save_column_widths("tier2", index, new_size)

    @property
    def table(self) -> QTableWidget:
        """테이블 위젯 반환 (호환성용)"""
        return self._table

    def set_row_data(self, row: int, item: Tier2Item) -> None:
        """
        행 데이터 설정

        Args:
            row: 행 인덱스
            item: Tier2Item 데이터
        """

        # Ticker
        self._table.setItem(row, 0, QTableWidgetItem(item.ticker))

        # Price
        price_text = f"${item.price:.2f}" if item.price > 0 else "-"
        price_item = NumericTableWidgetItem(price_text, item.price)
        self._table.setItem(row, 1, price_item)

        # Chg%
        sign = "+" if item.change_pct >= 0 else ""
        chg_item = NumericTableWidgetItem(
            f"{sign}{item.change_pct:.1f}%", item.change_pct
        )
        if item.change_pct >= 0:
            chg_item.setForeground(QColor(self._theme.get_color("success")))
        else:
            chg_item.setForeground(QColor(self._theme.get_color("danger")))
        self._table.setItem(row, 2, chg_item)

        # zenV
        zenV_text = f"{item.zenV:.1f}" if item.zenV != 0 else "-"
        zenV_item = NumericTableWidgetItem(zenV_text, item.zenV)
        # [REFAC] Theme-01: tier colors from theme
        if item.zenV >= 2.0:
            zenV_item.setForeground(QColor(self._theme.get_color("tier_zenV_high")))
        elif item.zenV >= 1.0:
            zenV_item.setForeground(QColor(self._theme.get_color("tier_zenV_mid")))
        else:
            zenV_item.setForeground(QColor(self._theme.get_color("tier_zenV_low")))
        self._table.setItem(row, 3, zenV_item)

        # zenP
        zenP_text = f"{item.zenP:.1f}" if item.zenP != 0 else "-"
        zenP_item = NumericTableWidgetItem(zenP_text, item.zenP)
        if item.zenP >= 2.0:
            zenP_item.setForeground(QColor(self._theme.get_color("tier_zenV_high")))
        elif item.zenP >= 1.0:
            zenP_item.setForeground(QColor(self._theme.get_color("tier_zenV_mid")))
        else:
            zenP_item.setForeground(QColor(self._theme.get_color("tier_zenV_low")))
        self._table.setItem(row, 4, zenP_item)

        # Ign
        if item.ignition > 0:
            ign_item = NumericTableWidgetItem(f"{int(item.ignition)}", item.ignition)
            if item.ignition >= 70:
                ign_item.setBackground(
                    QColor(self._theme.get_color("warning") + "50")
                )  # 50 = alpha hex
        else:
            ign_item = NumericTableWidgetItem("-", 0)
        self._table.setItem(row, 5, ign_item)

        # Signal
        sig_item = QTableWidgetItem(item.signal if item.signal else "")
        if item.signal == "🔥":
            sig_item.setForeground(QColor(self._theme.get_color("danger")))
        elif item.signal == "🎯":
            sig_item.setForeground(QColor(self._theme.get_color("primary")))
        self._table.setItem(row, 6, sig_item)

    def add_row(self, item: Tier2Item) -> int:
        """
        새 행 추가

        Args:
            item: Tier2Item 데이터

        Returns:
            추가된 행 인덱스
        """
        row = self._table.rowCount()
        self._table.insertRow(row)
        self.set_row_data(row, item)
        return row

    def remove_row_by_ticker(self, ticker: str) -> bool:
        """
        티커로 행 제거

        Args:
            ticker: 종목 코드

        Returns:
            제거 성공 여부
        """
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item and item.text() == ticker:
                self._table.removeRow(row)
                return True
        return False

    def get_row_by_ticker(self, ticker: str) -> int:
        """
        티커로 행 인덱스 조회

        Args:
            ticker: 종목 코드

        Returns:
            행 인덱스 (없으면 -1)
        """
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item and item.text() == ticker:
                return row
        return -1

    def clear(self) -> None:
        """모든 행 제거"""
        self._table.setRowCount(0)
