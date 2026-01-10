# ============================================================================
# Sigma9 Theme Manager
# ============================================================================
# [REFAC] Theme-01: Complete Theme Centralization
# - QObject 상속 + theme_changed Signal 추가 (Hot Reload 지원)
# - 추가 색상 토큰 (chart, tier, status)
# - 확장된 get_stylesheet() 메서드
# ============================================================================

from typing import Optional

try:
    from PySide6.QtCore import QObject, Signal
except ImportError:
    from PyQt6.QtCore import QObject, pyqtSignal as Signal

try:
    from frontend.config.loader import load_settings, get_setting
except ImportError:
    from config.loader import load_settings, get_setting


class ThemeColors:
    """
    테마 색상 정의 (Dark/Light)

    [ELI5] 모든 UI 색상을 한 곳에서 관리.
    새 색상이 필요하면 여기에 추가하고, theme.get_color("key")로 사용.
    """

    # -------------------------------------------------------------------------
    # Dark Theme Palette (Default)
    # -------------------------------------------------------------------------
    DARK = {
        # Semantic Colors (의미 색상)
        "primary": "#2196F3",  # 주요 액션 (Connect 등)
        "success": "#4CAF50",  # 성공/매수/Start
        "warning": "#FF9800",  # 경고/Stop
        "danger": "#f44336",  # 위험/매도/Kill
        # Text Colors
        "text": "#FFFFFF",
        "text_secondary": "rgba(255, 255, 255, 0.6)",
        "text_muted": "rgba(255, 255, 255, 0.4)",
        # Surface Colors (배경/패널)
        "background": "#151520",
        "surface": "rgba(255, 255, 255, 0.02)",
        "surface_elevated": "rgba(255, 255, 255, 0.05)",
        # Interactive States
        "border": "rgba(255, 255, 255, 0.1)",
        "hover": "rgba(255, 255, 255, 0.08)",
        "selection": "rgba(33, 150, 243, 0.3)",
        "scrollbar": "rgba(255, 255, 255, 0.2)",
        # Chart Colors (차트 전용)
        "chart_up": "#22c55e",  # 상승 (Green)
        "chart_down": "#ef4444",  # 하락 (Red)
        "chart_neutral": "#9e9e9e",  # 중립 (Gray)
        # Tier Colors (Watchlist/Tier2 전용)
        "tier_zenV_high": "#ff9800",  # ZenV > 3.0 (Orange)
        "tier_zenV_mid": "#4caf50",  # ZenV 1.5-3.0 (Green)
        "tier_zenV_low": "#9e9e9e",  # ZenV < 1.5 (Gray)
        # Status Colors
        "status_connected": "#4CAF50",
        "status_disconnected": "#888888",
        "status_error": "#F44336",
    }

    # -------------------------------------------------------------------------
    # Light Theme Palette
    # -------------------------------------------------------------------------
    LIGHT = {
        "primary": "#1976D2",
        "success": "#388E3C",
        "warning": "#F57C00",
        "danger": "#D32F2F",
        "text": "#000000",
        "text_secondary": "rgba(0, 0, 0, 0.6)",
        "text_muted": "rgba(0, 0, 0, 0.4)",
        "background": "#FFFFFF",
        "surface": "rgba(0, 0, 0, 0.05)",
        "surface_elevated": "rgba(0, 0, 0, 0.08)",
        "border": "rgba(0, 0, 0, 0.1)",
        "hover": "rgba(0, 0, 0, 0.05)",
        "selection": "rgba(25, 118, 210, 0.2)",
        "scrollbar": "rgba(0, 0, 0, 0.2)",
        "chart_up": "#16a34a",
        "chart_down": "#dc2626",
        "chart_neutral": "#6b7280",
        "tier_zenV_high": "#ea580c",
        "tier_zenV_mid": "#16a34a",
        "tier_zenV_low": "#6b7280",
        "status_connected": "#388E3C",
        "status_disconnected": "#666666",
        "status_error": "#D32F2F",
    }


class ThemeManager(QObject):
    """
    설정을 기반으로 테마 색상과 스타일을 관리하는 싱글톤 클래스

    [ELI5] 앱 전체의 "옷장" 역할.
    모든 위젯이 여기서 색상/스타일을 가져가므로,
    이 클래스만 바꾸면 전체 앱 테마가 바뀜.

    Usage:
        from .theme import theme
        btn.setStyleSheet(theme.get_button_style("primary"))
        label_color = theme.get_color("text_secondary")
    """

    # [REFAC] Hot Reload Signal
    # 위젯에서 theme.theme_changed.connect(self._refresh_styles)로 연결
    theme_changed = Signal()

    _instance: Optional["ThemeManager"] = None

    def __new__(cls):
        if cls._instance is None:
            # QObject.__init__은 __new__ 이후 별도 호출 필요
            cls._instance = super(ThemeManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
        self._init_theme()

    def _init_theme(self):
        """설정에서 테마 모드를 읽어 초기화"""
        self.mode = get_setting("gui.theme", "dark").lower()
        self.colors = ThemeColors.LIGHT if self.mode == "light" else ThemeColors.DARK

        # 폰트 설정
        self.font_family = get_setting("gui.font_family", "Pretendard")
        self.font_size = get_setting("gui.font_size", 12)

        # Window & Acrylic Settings
        self.opacity = get_setting("gui.opacity", 1.0)
        self.acrylic_map_alpha = get_setting("gui.acrylic_map_alpha", 150)
        self.particle_alpha = get_setting("gui.particle_alpha", 1.0)
        self.background_effect = get_setting("gui.background_effect", "constellation")
        self.tint_color = get_setting("gui.tint_color", None)

        # Acrylic 틴트 컬러 (RGB)
        bg_color = (
            self.tint_color.lstrip("#")
            if self.tint_color
            else self.colors["background"].lstrip("#")
        )

        if len(bg_color) == 6:
            self.tint_r = int(bg_color[0:2], 16)
            self.tint_g = int(bg_color[2:4], 16)
            self.tint_b = int(bg_color[4:6], 16)
        else:
            self.tint_r, self.tint_g, self.tint_b = (21, 21, 32)

    def reload(self):
        """설정을 다시 로드하고 테마 업데이트, Signal emit"""
        load_settings.cache_clear()
        self._init_theme()
        self.theme_changed.emit()

    def get_color(self, key: str) -> str:
        """색상 코드 반환"""
        return self.colors.get(key, "#FF00FF")  # Fallback: 핫핑크

    # =========================================================================
    # Stylesheet Generators
    # =========================================================================

    def get_stylesheet(self, component: str) -> str:
        """
        자주 사용되는 컴포넌트의 스타일시트 생성

        Supported components:
            - panel: QFrame 패널
            - list: QListWidget
            - combobox: QComboBox
            - input: QLineEdit, QSpinBox 등
            - tab: QTabWidget
            - separator: 구분선 QFrame
            - label_section: 섹션 제목 QLabel
        """
        c = self.colors
        font = f"font-family: '{self.font_family}'; font-size: {self.font_size}pt;"

        if component == "panel":
            return f"""
                QFrame {{
                    background-color: {c["surface"]}; 
                    border: 1px solid {c["border"]};
                    border-radius: 10px;
                }}
            """

        elif component == "list":
            return f"""
                QListWidget {{
                    background-color: {c["surface"]};
                    border: 1px solid {c["border"]};
                    border-radius: 6px;
                    color: {c["text"]};
                    {font}
                }}
                QListWidget::item {{
                    padding: 8px;
                    border-bottom: 1px solid {c["border"]};
                }}
                QListWidget::item:selected {{
                    background-color: {c["hover"]};
                }}
                QListWidget::item:hover {{
                    background-color: {c["selection"]};
                }}
            """

        elif component == "combobox":
            return f"""
                QComboBox {{
                    background: {c["surface"]};
                    border: 1px solid {c["border"]};
                    border-radius: 4px;
                    padding: 6px;
                    color: {c["text"]};
                    {font}
                }}
                QComboBox:hover {{
                    border: 1px solid {c["primary"]};
                }}
                QComboBox QAbstractItemView {{
                    background: {c["background"]};
                    border: 1px solid {c["border"]};
                    color: {c["text"]};
                    selection-background-color: {c["primary"]};
                }}
            """

        elif component == "input":
            return f"""
                background: rgba(0,0,0,0.3);
                color: {c["text"]};
                border: 1px solid {c["border"]};
                border-radius: 4px;
                padding: 4px 8px;
                {font}
            """

        elif component == "tab":
            return f"""
                QTabWidget::pane {{ 
                    border: 1px solid {c["border"]}; 
                    border-radius: 6px;
                    background: rgba(0,0,0,0.2);
                }}
                QTabBar::tab {{
                    background: {c["surface"]};
                    color: {c["text"]};
                    padding: 8px 16px;
                    margin: 2px;
                    border-radius: 4px;
                }}
                QTabBar::tab:selected {{
                    background: {c["primary"]};
                }}
                QTabBar::tab:hover:!selected {{
                    background: {c["hover"]};
                }}
            """

        elif component == "separator":
            return f"background-color: {c['border']};"

        elif component == "label_section":
            return f"color: {c['primary']}; font-weight: bold; font-size: 12px;"

        return ""

    def get_button_style(self, color_key: str = "surface") -> str:
        """
        버튼 스타일시트 생성 (Neutral Outline Style)

        Args:
            color_key: 테마 색상 키 ('primary', 'success', 'danger' 등)
        """
        c = self.colors
        semantic_color = self.get_color(color_key)

        return f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {c["border"]};
                border-radius: 6px;
                padding: 8px 16px;
                color: {c["text"]};
                font-family: '{self.font_family}';
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {c["hover"]};
                color: {semantic_color};
                border: 1px solid {semantic_color};
            }}
            QPushButton:pressed {{
                opacity: 0.8;
                background-color: {c["selection"]};
            }}
            QPushButton:disabled {{
                background: rgba(100, 100, 100, 0.3);
                color: #666;
                border: 1px solid #666;
            }}
        """

    def get_action_button_style(self, color_key: str) -> str:
        """
        액션 버튼 스타일 (Start/Stop/Test 등)

        [ELI5] 테두리 + 배경색이 있는 강조 버튼용
        """
        color = self.get_color(color_key)

        return f"""
            QPushButton {{
                background: rgba({self._hex_to_rgb(color)}, 0.3);
                color: {color};
                border: 1px solid {color};
                border-radius: 4px;
                padding: 6px 12px;
                font-family: '{self.font_family}';
            }}
            QPushButton:hover {{
                background: rgba({self._hex_to_rgb(color)}, 0.5);
            }}
            QPushButton:disabled {{
                background: rgba(100, 100, 100, 0.3);
                color: #666;
                border: 1px solid #666;
            }}
        """

    def _hex_to_rgb(self, hex_color: str) -> str:
        """#RRGGBB -> 'R, G, B' 문자열 변환 (rgba용)"""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) != 6:
            return "255, 0, 255"  # Fallback
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"{r}, {g}, {b}"


# 전역 인스턴스
theme = ThemeManager()
