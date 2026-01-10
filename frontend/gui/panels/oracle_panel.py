# ==============================================================================
# oracle_panel.py - Oracle (LLM 분석) 패널
# ==============================================================================
# 📌 이 파일의 역할:
#    Sigma9 Dashboard의 Oracle (LLM 분석 요청) 패널입니다.
#    AI에게 종목 분석을 요청하고 결과를 표시합니다.
#
# 📌 ELI5:
#    AI한테 "이 주식 왜 떴어?" "이 회사 분석해줘" 하고
#    물어보는 버튼들이 있는 패널이에요.
# ==============================================================================
from __future__ import annotations

from PyQt6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal


class OraclePanel(QFrame):
    """
    Oracle (LLM 분석) 패널

    ═══════════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════════
    이건 "AI 질문 창"이에요.

    버튼을 누르면 AI(LLM)에게 분석을 요청합니다:
    - Why? 버튼: "왜 이 주식에 신호가 떴어?"
    - Fundamental 버튼: "이 회사 기본 분석해줘"
    - Reflection 버튼: "지금까지 거래 복기해줘"

    결과는 아래 텍스트 영역에 표시됩니다.
    ═══════════════════════════════════════════════════════════════════════════
    """

    # =========================================================================
    # 시그널 (Signal) - 버튼 클릭 시 발생
    # =========================================================================
    why_clicked = pyqtSignal()
    fundamental_clicked = pyqtSignal()
    reflection_clicked = pyqtSignal()

    def __init__(self, theme=None):
        """
        Oracle 패널 초기화

        Args:
            theme: 테마 매니저 (기본값: 전역 theme 사용)
        """
        super().__init__()

        from ..theme import theme as global_theme

        self._theme = theme or global_theme

        # UI 요소들
        self._why_btn: QPushButton | None = None
        self._fundamental_btn: QPushButton | None = None
        self._reflection_btn: QPushButton | None = None
        self._result: QTextEdit | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """UI 구성"""
        c = self._theme.colors

        # 레이아웃
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(4)

        # 제목
        title_label = QLabel("🔮 Oracle")
        title_label.setStyleSheet(f"""
            color: {c["text_secondary"]}; 
            font-size: 12px; 
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        layout.addWidget(title_label)

        # Oracle 프레임
        oracle_frame = QFrame()
        oracle_frame.setStyleSheet(f"""
            background-color: {c["surface"]};
            border: 1px solid {c["border"]};
            border-radius: 8px;
        """)
        oracle_layout = QVBoxLayout(oracle_frame)
        oracle_layout.setContentsMargins(8, 8, 8, 8)
        oracle_layout.setSpacing(6)

        # 분석 버튼들
        self._why_btn = QPushButton("❓ Why?")
        self._why_btn.setToolTip("선택된 종목이 왜 신호를 발생했는지 분석")
        self._why_btn.setStyleSheet(self._get_btn_style())
        self._why_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._why_btn.clicked.connect(self.why_clicked.emit)
        oracle_layout.addWidget(self._why_btn)

        self._fundamental_btn = QPushButton("📊 Fundamental")
        self._fundamental_btn.setToolTip("종목 펀더멘털 분석")
        self._fundamental_btn.setStyleSheet(self._get_btn_style())
        self._fundamental_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._fundamental_btn.clicked.connect(self.fundamental_clicked.emit)
        oracle_layout.addWidget(self._fundamental_btn)

        self._reflection_btn = QPushButton("💭 Reflection")
        self._reflection_btn.setToolTip("거래 복기 및 교훈 분석")
        self._reflection_btn.setStyleSheet(self._get_btn_style())
        self._reflection_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reflection_btn.clicked.connect(self.reflection_clicked.emit)
        oracle_layout.addWidget(self._reflection_btn)

        # 결과 표시 영역
        self._result = QTextEdit()
        self._result.setReadOnly(True)
        self._result.setPlaceholderText("Select a stock and click a button...")
        self._result.setStyleSheet(f"""
            QTextEdit {{
                background-color: rgba(0,0,0,0.3);
                border: 1px solid {c["border"]};
                border-radius: 4px;
                color: {c["text"]};
                font-size: 11px;
            }}
        """)
        self._result.setMaximumHeight(100)
        oracle_layout.addWidget(self._result)

        layout.addWidget(oracle_frame)

    def _get_btn_style(self) -> str:
        """
        버튼 스타일

        기본 테마와 통일된 투명 배경 스타일
        """
        c = self._theme.colors
        return f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {c["border"]};
                border-radius: 4px;
                color: {c["text"]};
                padding: 6px 12px;
                font-size: 11px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {c["surface"]};
            }}
        """

    # =========================================================================
    # 속성 접근자 (Compatibility)
    # =========================================================================
    @property
    def oracle_why_btn(self) -> QPushButton:
        """Why? 버튼"""
        return self._why_btn

    @property
    def oracle_fundamental_btn(self) -> QPushButton:
        """Fundamental 버튼"""
        return self._fundamental_btn

    @property
    def oracle_reflection_btn(self) -> QPushButton:
        """Reflection 버튼"""
        return self._reflection_btn

    @property
    def oracle_result(self) -> QTextEdit:
        """결과 텍스트 영역"""
        return self._result

    # =========================================================================
    # 편의 메서드
    # =========================================================================
    def set_result(self, text: str) -> None:
        """Oracle 결과 텍스트 설정"""
        self._result.setPlainText(text)

    def clear_result(self) -> None:
        """결과 영역 초기화"""
        self._result.clear()
        self._result.setPlaceholderText("Select a stock and click a button...")
