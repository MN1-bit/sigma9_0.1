# ==============================================================================
# watchlist_panel.py - Tier 1 Watchlist 패널
# ==============================================================================
# 📌 이 파일의 역할:
#    Sigma9 Dashboard의 Tier 1 Watchlist 테이블 + Tier 2 Hot Zone을 포함한
#    Left Panel 전체를 담당합니다.
#
# 📌 ELI5:
#    이건 "감시 목록" 패널이에요.
#    상단에는 뜨거운 종목들(Hot Zone), 하단에는 전체 감시 목록이 있어요.
# ==============================================================================
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableView,
    QPushButton,
    QHeaderView,
    QAbstractItemView,
)
from PyQt6.QtCore import Qt, pyqtSignal, QModelIndex, QTimer
from PyQt6.QtCore import QSortFilterProxyModel

from .tier2_panel import Tier2Panel

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QTableWidget
    from ..state.dashboard_state import DashboardState
    from ..watchlist_model import WatchlistModel


class WatchlistPanel(QFrame):
    """
    Tier 1 Watchlist + Tier 2 Hot Zone 통합 패널

    ═══════════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════════
    대시보드 왼쪽 전체를 차지하는 패널이에요.

    레이아웃:
    ┌─────────────────┐
    │  🔥 Hot Zone    │  ← Tier 2 테이블 (상단, 고정 높이 150px)
    │  [Tier 2 Table] │
    ├─────────────────┤
    │  📋 Watchlist   │  ← Tier 1 테이블 (하단, 확장)
    │  [Tier 1 Table] │
    └─────────────────┘

    Hot Zone: 특별 감시 대상 (Ignition Score 높음)
    Watchlist: 전체 감시 목록 (Scanner 결과)
    ═══════════════════════════════════════════════════════════════════════════
    """

    # 시그널
    tier1_row_clicked = pyqtSignal(QModelIndex)  # Watchlist 클릭
    tier2_row_clicked = pyqtSignal(int, int)  # Hot Zone 클릭 (row, col)
    refresh_score_clicked = pyqtSignal()  # Score V3 재계산 버튼 클릭

    def __init__(
        self,
        state: DashboardState | None = None,
        theme=None,
        watchlist_model: WatchlistModel | None = None,
        on_save_column_widths: Callable[[str, int, int], None] | None = None,
    ):
        """
        WatchlistPanel 초기화

        Args:
            state: DashboardState 인스턴스 (DI)
            theme: 테마 매니저 (기본값: 전역 theme 사용)
            watchlist_model: 외부에서 주입할 WatchlistModel
            on_save_column_widths: 컬럼 너비 저장 콜백
        """
        super().__init__()

        from ..theme import theme as global_theme

        self._theme = theme or global_theme
        self._state = state
        self._on_save_column_widths = on_save_column_widths

        # 위젯 참조
        self._tier2_panel: Tier2Panel | None = None
        self._watchlist_table: QTableView | None = None
        self._watchlist_model: WatchlistModel | None = watchlist_model
        self._watchlist_proxy: QSortFilterProxyModel | None = None

        # Score V3 UI
        self._score_updated_label: QLabel | None = None
        self._refresh_score_btn: QPushButton | None = None

        # 자동 갱신 타이머
        self._refresh_timer: QTimer | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI 구성"""
        c = self._theme.colors

        # 프레임 스타일
        self.setStyleSheet(self._theme.get_stylesheet("panel"))
        self.setMinimumWidth(280)
        self.setMaximumWidth(400)

        # 레이아웃
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # ═══════════════════════════════════════════════════════════════════
        # 1. Tier 2 Hot Zone (상단)
        # ═══════════════════════════════════════════════════════════════════
        self._tier2_panel = Tier2Panel(
            state=self._state,
            theme=self._theme,
            on_save_column_widths=self._on_save_column_widths,
        )
        self._tier2_panel.row_clicked.connect(self.tier2_row_clicked.emit)
        layout.addWidget(self._tier2_panel)

        # ═══════════════════════════════════════════════════════════════════
        # 2. Tier 1 Watchlist 헤더 (라벨 + 버튼 + 업데이트 시각)
        # ═══════════════════════════════════════════════════════════════════
        tier1_header = QHBoxLayout()
        tier1_header.setSpacing(8)

        tier1_label = QLabel("📋 Watchlist")
        tier1_label.setStyleSheet(f"""
            color: {c["text_secondary"]}; 
            font-size: 12px; 
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        tier1_header.addWidget(tier1_label)
        tier1_header.addStretch()

        # Score V3 Last Updated 라벨
        self._score_updated_label = QLabel("Score V3: --:--")
        self._score_updated_label.setStyleSheet(f"""
            color: {c["text_secondary"]};
            font-size: 9px;
            background: transparent;
            border: none;
        """)
        self._score_updated_label.setToolTip("마지막 Score V3 재계산 시각")
        tier1_header.addWidget(self._score_updated_label)

        # Score V3 Refresh 버튼
        self._refresh_score_btn = QPushButton("🔄")
        self._refresh_score_btn.setToolTip("Score V3 재계산 (Watchlist 전체 아님)")
        self._refresh_score_btn.setFixedSize(24, 24)
        self._refresh_score_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {c["border"]};
                border-radius: 4px;
                color: {c["text_secondary"]};
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {c["surface"]};
                border-color: {c["primary"]};
                color: {c["primary"]};
            }}
        """)
        self._refresh_score_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._refresh_score_btn.clicked.connect(self.refresh_score_clicked.emit)
        tier1_header.addWidget(self._refresh_score_btn)

        layout.addLayout(tier1_header)

        # ═══════════════════════════════════════════════════════════════════
        # 3. Tier 1 Watchlist 테이블
        # ═══════════════════════════════════════════════════════════════════
        self._setup_watchlist_table(layout)

    def _setup_watchlist_table(self, layout: QVBoxLayout) -> None:
        """Watchlist 테이블 설정"""
        c = self._theme.colors

        # Model 생성 (외부에서 주입받지 않은 경우)
        if self._watchlist_model is None:
            from ..watchlist_model import WatchlistModel

            self._watchlist_model = WatchlistModel()

        # Proxy 모델 (정렬 상태 유지)
        self._watchlist_proxy = QSortFilterProxyModel()
        self._watchlist_proxy.setSourceModel(self._watchlist_model)
        self._watchlist_proxy.setSortRole(Qt.ItemDataRole.UserRole)

        # 테이블 뷰
        self._watchlist_table = QTableView()
        self._watchlist_table.setModel(self._watchlist_proxy)
        self._watchlist_table.setSortingEnabled(True)

        # 선택 모드
        self._watchlist_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._watchlist_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )

        # 헤더 설정
        header = self._watchlist_table.horizontalHeader()
        header.setStretchLastSection(False)
        for i in range(5):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

        # 기본 컬럼 너비
        default_widths = [60, 55, 60, 45, 55]
        for i, width in enumerate(default_widths):
            self._watchlist_table.setColumnWidth(i, width)

        # 저장된 컬럼 너비 로드
        self._load_saved_column_widths()

        # 컬럼 너비 변경 시 저장
        header.sectionResized.connect(self._on_section_resized)

        # 행 높이
        self._watchlist_table.verticalHeader().setDefaultSectionSize(24)
        self._watchlist_table.verticalHeader().setVisible(False)

        # 스타일
        self._watchlist_table.setStyleSheet(f"""
            QTableView {{
                background-color: transparent;
                border: none;
                color: {c["text"]};
                font-size: 11px;
                gridline-color: {c["border"]};
            }}
            QTableView::item {{
                padding: 2px 4px;
            }}
            QTableView::item:selected {{
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

        # 클릭 시그널
        self._watchlist_table.clicked.connect(self.tier1_row_clicked.emit)

        layout.addWidget(self._watchlist_table)

    def _load_saved_column_widths(self) -> None:
        """저장된 컬럼 너비 로드"""
        try:
            from frontend.config.loader import load_settings

            saved = load_settings().get("tables", {}).get("tier1_column_widths", [])
            default_widths = [60, 55, 60, 45, 55]
            for i in range(1, min(5, len(saved))):
                width = saved[i] if saved[i] > 0 else default_widths[i]
                self._watchlist_table.setColumnWidth(i, width)
        except Exception:
            pass

    def _on_section_resized(self, index: int, old_size: int, new_size: int) -> None:
        """컬럼 너비 변경 시 저장"""
        if self._on_save_column_widths and index > 0:
            self._on_save_column_widths("tier1", index, new_size)

    # =========================================================================
    # 공개 API
    # =========================================================================

    @property
    def tier2_panel(self) -> Tier2Panel:
        """Tier 2 패널 반환"""
        return self._tier2_panel

    @property
    def watchlist_table(self) -> QTableView:
        """Watchlist 테이블 반환 (호환성)"""
        return self._watchlist_table

    @property
    def watchlist_model(self) -> WatchlistModel:
        """Watchlist 모델 반환"""
        return self._watchlist_model

    @property
    def watchlist_proxy(self) -> QSortFilterProxyModel:
        """Watchlist 프록시 모델 반환"""
        return self._watchlist_proxy

    @property
    def tier2_table(self) -> "QTableWidget":
        """Tier 2 테이블 반환 (호환성용)"""
        return self._tier2_panel.table

    def set_score_updated_time(self, timestamp: str) -> None:
        """Score V3 업데이트 시각 설정"""
        self._score_updated_label.setText(f"Score V3: {timestamp}")

    def set_refresh_button_enabled(self, enabled: bool) -> None:
        """Refresh 버튼 활성화/비활성화"""
        self._refresh_score_btn.setEnabled(enabled)

    def set_refresh_button_text(self, text: str) -> None:
        """Refresh 버튼 텍스트 변경"""
        self._refresh_score_btn.setText(text)

    def start_auto_refresh(self, interval_ms: int = 60000) -> None:
        """자동 갱신 시작 (기본 1분)"""
        if self._refresh_timer is None:
            self._refresh_timer = QTimer()
        self._refresh_timer.start(interval_ms)

    def stop_auto_refresh(self) -> None:
        """자동 갱신 중지"""
        if self._refresh_timer:
            self._refresh_timer.stop()
