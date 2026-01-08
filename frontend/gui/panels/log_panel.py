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
# ==============================================================================
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QTextEdit

if TYPE_CHECKING:
    from ..state.dashboard_state import DashboardState


class LogPanel(QFrame):
    """
    로그 콘솔 패널

    ═══════════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════════
    이건 프로그램이 하는 일을 실시간으로 보여주는 "게임 채팅창" 같은 거예요.

    예시:
    [12:30:05] [INFO] 서버에 연결되었습니다
    [12:30:10] [INFO] 스캔 완료: 15개 종목 발견
    [12:30:15] [WARN] 가격 데이터 지연

    새 메시지가 오면 자동으로 아래로 스크롤해요!
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

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """UI 구성"""
        c = self._theme.colors

        # 프레임 스타일
        self.setStyleSheet(self._theme.get_stylesheet("panel"))
        self.setFixedHeight(140)

        # 레이아웃
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # 제목 라벨
        title_label = QLabel("📝 Log")
        title_label.setStyleSheet(f"""
            color: {c["text_secondary"]}; 
            font-size: 12px; 
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        layout.addWidget(title_label)

        # 로그 텍스트 영역
        self._log_console = QTextEdit()
        self._log_console.setReadOnly(True)
        self._log_console.setStyleSheet(f"""
            QTextEdit {{
                background-color: {c["surface"]};
                border: 1px solid {c["border"]};
                border-radius: 6px;
                color: {c["primary"]};  /* 콘솔 텍스트는 primary 컬러 사용 */
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }}
        """)

        # 초기 메시지
        self._log_console.append("[INFO] Sigma9 Dashboard initialized")
        self._log_console.append(f"[INFO] Theme loaded: {self._theme.mode}")
        self._log_console.append("[INFO] Waiting for connection...")

        layout.addWidget(self._log_console)

    def _connect_signals(self) -> None:
        """DashboardState 시그널 연결"""
        if self._state:
            self._state.log_message.connect(self.log)

    def log(self, message: str) -> None:
        """
        로그 콘솔에 메시지 추가 (자동 스크롤)

        Args:
            message: 로그 메시지
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log_console.append(f"[{timestamp}] {message}")

        # 자동 스크롤 (맨 아래로)
        scrollbar = self._log_console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    @property
    def log_console(self) -> QTextEdit:
        """
        로그 콘솔 위젯 반환 (호환성용)

        NOTE: 기존 dashboard.py에서 self.log_console로 접근하던 코드와의 호환성
        """
        return self._log_console
