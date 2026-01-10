# ==============================================================================
# position_panel.py - 포지션 & P&L 패널
# ==============================================================================
# 📌 이 파일의 역할:
#    Sigma9 Dashboard의 포지션 및 손익 표시 패널입니다.
#    현재 보유 중인 포지션과 오늘의 P&L을 표시합니다.
#
# 📌 ELI5:
#    내가 지금 어떤 주식을 얼마나 들고 있는지,
#    그리고 오늘 얼마 벌었는지/잃었는지 보여주는 패널이에요.
# ==============================================================================
from __future__ import annotations

from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel,
    QListWidget,
)


class PositionPanel(QFrame):
    """
    포지션 & P&L 패널

    ═══════════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════════
    이건 "내 주식 현황판"이에요.

    - Today's P&L: 오늘 벌거나 잃은 금액 (초록색 = 이익, 빨간색 = 손실)
    - Active Positions: 현재 들고 있는 주식들 목록

    예를 들어:
    - AAPL: 10 shares (+$50.00)
    - TSLA: 5 shares (-$20.00)
    ═══════════════════════════════════════════════════════════════════════════
    """

    def __init__(self, theme=None):
        """
        포지션 패널 초기화

        Args:
            theme: 테마 매니저 (기본값: 전역 theme 사용)
        """
        super().__init__()

        from ..theme import theme as global_theme

        self._theme = theme or global_theme

        # UI 요소들
        self._pnl_value: QLabel | None = None
        self._positions_list: QListWidget | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI 구성"""
        c = self._theme.colors

        # 레이아웃
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(4)

        # 제목
        title_label = QLabel("💰 Positions & P&L")
        title_label.setStyleSheet(f"""
            color: {c["text_secondary"]}; 
            font-size: 12px; 
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        layout.addWidget(title_label)

        # P&L 요약 프레임
        pnl_frame = QFrame()
        pnl_frame.setStyleSheet(f"""
            background-color: {c["surface"]};
            border: 1px solid {c["success"]};
            border-radius: 8px;
        """)
        pnl_layout = QVBoxLayout(pnl_frame)
        pnl_layout.setContentsMargins(8, 8, 8, 8)

        pnl_label = QLabel("Today's P&L")
        pnl_label.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: 11px; background: transparent; border: none;"
        )
        pnl_layout.addWidget(pnl_label)

        # P&L 값 (초록색 = 이익, 빨간색 = 손실)
        self._pnl_value = QLabel("+ $0.00")
        self._pnl_value.setStyleSheet(f"""
            color: {c["success"]}; 
            font-size: 20px; 
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        pnl_layout.addWidget(self._pnl_value)

        layout.addWidget(pnl_frame)

        # 포지션 리스트 라벨
        positions_label = QLabel("Active Positions")
        positions_label.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: 11px; background: transparent; border: none;"
        )
        layout.addWidget(positions_label)

        # 포지션 리스트
        self._positions_list = QListWidget()
        styles = self._theme.get_stylesheet("list")
        styles += "QListWidget { background-color: transparent; max-height: 80px; }"
        self._positions_list.setStyleSheet(styles)
        self._positions_list.setMaximumHeight(80)
        self._positions_list.addItem("No active positions")
        layout.addWidget(self._positions_list)

    # =========================================================================
    # 속성 접근자 (Compatibility)
    # =========================================================================
    @property
    def pnl_value(self) -> QLabel:
        """P&L 값 라벨"""
        return self._pnl_value

    @property
    def positions_list(self) -> QListWidget:
        """포지션 리스트"""
        return self._positions_list

    # =========================================================================
    # 편의 메서드
    # =========================================================================
    def set_pnl(self, amount: float) -> None:
        """
        P&L 값 설정

        Args:
            amount: 손익 금액 (양수 = 이익, 음수 = 손실)
        """
        c = self._theme.colors
        sign = "+" if amount >= 0 else ""
        color = c["success"] if amount >= 0 else c["danger"]

        self._pnl_value.setText(f"{sign} ${amount:.2f}")
        self._pnl_value.setStyleSheet(f"""
            color: {color}; 
            font-size: 20px; 
            font-weight: bold;
            background: transparent;
            border: none;
        """)

    def add_position(self, ticker: str, qty: int, pnl: float) -> None:
        """
        포지션 추가

        Args:
            ticker: 종목 코드
            qty: 수량
            pnl: 손익
        """
        # 첫 번째 항목이 "No active positions"이면 제거
        if self._positions_list.count() == 1:
            first_item = self._positions_list.item(0)
            if first_item and first_item.text() == "No active positions":
                self._positions_list.takeItem(0)

        sign = "+" if pnl >= 0 else ""
        self._positions_list.addItem(f"{ticker}: {qty} shares ({sign}${pnl:.2f})")

    def clear_positions(self) -> None:
        """모든 포지션 제거"""
        self._positions_list.clear()
        self._positions_list.addItem("No active positions")
