# ==============================================================================
# log_panel.py - 로그 콘솔 패널
# ==============================================================================
# 📌 이 파일의 역할:
#    Sigma9 Dashboard의 로그 콘솔 패널입니다.
#    시스템 이벤트, 경고, 에러 메시지를 표시합니다.
#
# 📌 ELI5:
#    프로그램이 하는 일을 실시간으로 보여주는 "일기장"이에요.
#    연결됨, 스캔 완료, 에러 등을 시간과 함께 기록합니다.
#
# 📌 기능:
#    - 자동 스크롤: 맨 아래에 있으면 자동 스크롤, 위로 스크롤하면 고정
#    - Go to Recent 버튼: 클릭 시 맨 아래로 이동 + 자동 스크롤 활성화
# ==============================================================================
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QPushButton,
)
from PyQt6.QtCore import Qt

if TYPE_CHECKING:
    from ..state.dashboard_state import DashboardState


class LogPanel(QFrame):
    """
    로그 콘솔 패널 (자동 스크롤 제어 기능 포함)

    ═══════════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════════
    이건 프로그램이 하는 일을 실시간으로 보여주는 "게임 채팅창" 같은 거예요.

    - 맨 아래에 있으면 새 메시지가 올 때 자동으로 스크롤
    - 위로 스크롤해서 과거 로그를 보면 자동 스크롤 멈춤
    - "Go to Recent" 버튼을 누르면 맨 아래로 이동하고 자동 스크롤 다시 활성화
    ═══════════════════════════════════════════════════════════════════════════
    """

    def __init__(self, state: DashboardState | None = None, theme=None):
        """
        로그 패널 초기화

        Args:
            state: DashboardState 인스턴스 (DI)
            theme: 테마 매니저 (기본값: 전역 theme 사용)
        """
        super().__init__()

        from ..theme import theme as global_theme

        self._theme = theme or global_theme
        self._state = state

        # 자동 스크롤 상태
        self._auto_scroll = True

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """UI 구성"""
        c = self._theme.colors

        # 프레임 스타일
        self.setStyleSheet(self._theme.get_stylesheet("panel"))
        self.setFixedHeight(160)  # 버튼 공간으로 약간 키움

        # 레이아웃
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 헤더 (제목 + Go to Recent 버튼)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        # 제목 라벨
        title_label = QLabel("📝 Log")
        title_label.setStyleSheet(f"""
            color: {c["text_secondary"]}; 
            font-size: 12px; 
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        header_layout.addWidget(title_label)

        header_layout.addStretch(1)

        # Go to Recent 버튼 (처음엔 숨김)
        self._goto_recent_btn = QPushButton("⬇ Go to Recent")
        self._goto_recent_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._goto_recent_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c["primary"]};
                color: {c["background"]};
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {c["success"]};
            }}
        """)
        self._goto_recent_btn.clicked.connect(self._on_goto_recent)
        self._goto_recent_btn.hide()  # 처음엔 숨김
        header_layout.addWidget(self._goto_recent_btn)

        layout.addLayout(header_layout)

        # 로그 텍스트 영역
        self._log_console = QTextEdit()
        self._log_console.setReadOnly(True)
        self._log_console.setStyleSheet(f"""
            QTextEdit {{
                background-color: {c["surface"]};
                border: 1px solid {c["border"]};
                border-radius: 6px;
                color: {c["primary"]};
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }}
        """)

        # 스크롤바 이벤트 연결 (사용자가 스크롤하면 자동 스크롤 비활성화)
        self._log_console.verticalScrollBar().valueChanged.connect(
            self._on_scroll_changed
        )

        # 초기 메시지
        self._log_console.append("[INFO] Sigma9 Dashboard initialized")
        self._log_console.append(f"[INFO] Theme loaded: {self._theme.mode}")
        self._log_console.append("[INFO] Waiting for connection...")

        layout.addWidget(self._log_console)

    def _connect_signals(self) -> None:
        """DashboardState 시그널 연결"""
        if self._state:
            self._state.log_message.connect(self.log)

    def _on_scroll_changed(self, value: int) -> None:
        """
        스크롤 위치 변경 시 호출

        맨 아래에 있으면 자동 스크롤 활성화, 아니면 비활성화
        """
        scrollbar = self._log_console.verticalScrollBar()
        max_value = scrollbar.maximum()

        # 맨 아래 근처(10px 이내)이면 자동 스크롤 활성화
        if value >= max_value - 10:
            self._auto_scroll = True
            self._goto_recent_btn.hide()
        else:
            self._auto_scroll = False
            self._goto_recent_btn.show()

    def _on_goto_recent(self) -> None:
        """Go to Recent 버튼 클릭: 맨 아래로 이동 + 자동 스크롤 활성화"""
        scrollbar = self._log_console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        self._auto_scroll = True
        self._goto_recent_btn.hide()

    def log(self, message: str) -> None:
        """
        로그 콘솔에 메시지 추가

        자동 스크롤이 활성화된 경우에만 맨 아래로 스크롤

        Args:
            message: 로그 메시지
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log_console.append(f"[{timestamp}] {message}")

        # 자동 스크롤 활성화 상태일 때만 맨 아래로 이동
        if self._auto_scroll:
            scrollbar = self._log_console.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    @property
    def log_console(self) -> QTextEdit:
        """
        로그 콘솔 위젯 반환 (호환성용)

        NOTE: 기존 dashboard.py에서 self.log_console로 접근하던 코드와의 호환성
        """
        return self._log_console
