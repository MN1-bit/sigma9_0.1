# ============================================================================
# Sigma9 Theme Manager
# ============================================================================
from enum import Enum
from typing import Dict, Any

try:
    from frontend.config.loader import load_settings, get_setting
except ImportError:
    # 'frontend' 패키지를 찾을 수 없는 경우 (예: frontend/main.py 직접 실행)
    # config 패키지가 sys.path에 있는지 확인
    from config.loader import load_settings, get_setting

class ThemeColors:
    """
    테마 색상 정의 (Dark/Light)
    """
    # -------------------------------------------------------------------------
    # Dark Theme Palette (Default)
    # -------------------------------------------------------------------------
    DARK = {
        "primary": "#2196F3",       # 주요 액션 (Connect 등)
        "success": "#4CAF50",       # 성공/매수/Start
        "warning": "#FF9800",       # 경고/Stop
        "danger":  "#f44336",       # 위험/매도/Kill
        "text":    "#FFFFFF",       # 기본 텍스트
        "text_secondary": "rgba(255, 255, 255, 0.6)", # 보조 텍스트
        "background": "#151520",    # 기본 배경 (Acrylic Tint)
        "surface": "rgba(255, 255, 255, 0.02)",       # 패널 배경 (더 투명하게)
        "border":  "rgba(255, 255, 255, 0.1)",        # 테두리
        "hover":   "rgba(255, 255, 255, 0.08)",       # 호버 효과
        "selection": "rgba(33, 150, 243, 0.3)",       # 선택됨
        "scrollbar": "rgba(255, 255, 255, 0.2)",      # 스크롤바
    }

    # -------------------------------------------------------------------------
    # Light Theme Palette (Optional)
    # -------------------------------------------------------------------------
    LIGHT = {
        "primary": "#1976D2",
        "success": "#388E3C",
        "warning": "#F57C00",
        "danger":  "#D32F2F",
        "text":    "#000000",
        "text_secondary": "rgba(0, 0, 0, 0.6)",
        "background": "#FFFFFF",
        "surface": "rgba(0, 0, 0, 0.05)",
        "border":  "rgba(0, 0, 0, 0.1)",
        "hover":   "rgba(0, 0, 0, 0.05)",
        "selection": "rgba(25, 118, 210, 0.2)",
        "scrollbar": "rgba(0, 0, 0, 0.2)",
    }

class ThemeManager:
    """
    설정을 기반으로 테마 색상과 스타일을 관리하는 싱글톤 클래스
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ThemeManager, cls).__new__(cls)
            cls._instance._init_theme()
        return cls._instance

    def _init_theme(self):
        """설정에서 테마 모드를 읽어 초기화"""
        self.mode = get_setting("gui.theme", "dark").lower()
        self.colors = ThemeColors.LIGHT if self.mode == "light" else ThemeColors.DARK
        
        
        # [REFAC] 폰트 설정 로드
        self.font_family = get_setting("gui.font_family", "Pretendard")
        self.font_size = get_setting("gui.font_size", 12)
        
        # Window & Acrylic Settings
        self.opacity = get_setting("gui.opacity", 1.0)
        self.acrylic_map_alpha = get_setting("gui.acrylic_map_alpha", 150)
        self.particle_alpha = get_setting("gui.particle_alpha", 1.0)
        self.background_effect = get_setting("gui.background_effect", "constellation")
        self.tint_color = get_setting("gui.tint_color", None)
        
        # Acrylic 틴트 컬러 (RGB Hex)
        # 설정된 tint_color가 있으면 우선 사용, 없으면 테마 기본값
        bg_color = self.tint_color.lstrip("#") if self.tint_color else self.colors["background"].lstrip("#")
        
        if len(bg_color) == 6:
            self.tint_r = int(bg_color[0:2], 16)
            self.tint_g = int(bg_color[2:4], 16)
            self.tint_b = int(bg_color[4:6], 16)
        else:
            # Fallback
            self.tint_r, self.tint_g, self.tint_b = (21, 21, 32)


    def reload(self):
        """설정을 다시 로드하고 테마 업데이트"""
        load_settings.cache_clear()
        self._init_theme()

    def get_color(self, key: str) -> str:
        """색상 코드 반환"""
        return self.colors.get(key, "#FF00FF") # 못 찾으면 핫핑크

    def get_stylesheet(self, component: str) -> str:
        """
        자주 사용되는 컴포넌트의 스타일시트 생성
        """
        c = self.colors
        # [REFAC] 공통 폰트 문자열 (버튼에만 적용하기 위해 여기서는 제거)
        # font_style = f"font-family: '{self.font_family}'; font-size: {self.font_size}pt;"
        
        if component == "panel":
            return f"""
                QFrame {{
                    background-color: {c['surface']}; 
                    border: 1px solid {c['border']};
                    border-radius: 10px;
                }}
            """
        elif component == "list":
            return f"""
                QListWidget {{
                    background-color: {c['surface']};
                    border: 1px solid {c['border']};
                    border-radius: 6px;
                    color: {c['text']};
                }}
                QListWidget::item {{
                    padding: 8px;
                    border-bottom: 1px solid {c['border']};
                }}
                QListWidget::item:selected {{
                    background-color: {c['hover']};
                }}
                QListWidget::item:hover {{
                    background-color: {c['selection']};
                }}
            """
        return ""

    def get_button_style(self, color_key: str = "surface") -> str:
        """
        버튼 스타일시트 생성 (Neutral Outline Style)
        
        Args:
            color_key (str): 테마 색상 키 ('primary', 'success', 'danger', 'surface' 등)
        """
        c = self.colors
        semantic_color = self.get_color(color_key) # 호버/보더용 의미 색상
        
        return f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {c['border']};
                border-radius: 6px;
                padding: 8px 16px;
                color: {c['text']};
                font-family: '{self.font_family}';
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
                color: {semantic_color};
                border: 1px solid {semantic_color};
            }}
            QPushButton:pressed {{
                opacity: 0.8;
                background-color: {c['selection']};
            }}
        """

# 전역 인스턴스
theme = ThemeManager()
