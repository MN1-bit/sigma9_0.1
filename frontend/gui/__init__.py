# ============================================================================
# Frontend GUI Package
# ============================================================================
# 이 패키지는 PyQt6 기반의 GUI 컴포넌트들을 담당합니다.
#
# 📦 포함 모듈:
#   - dashboard.py: 메인 대시보드 윈도우 (Sigma9Dashboard)
#   - custom_window.py: Acrylic 프레임리스 윈도우
#   - window_effects.py: Windows DWM API 래퍼
#   - particle_effects.py: 트레이딩 파티클 이펙트
#   - chart_widget.py: TradingView Lightweight Charts 위젯 (추후)
#   - watchlist_widget.py: Watchlist 패널 위젯 (추후)
#
# 🎨 디자인 원칙:
#   - Glassmorphism / Acrylic Effect 스타일
#   - 5-Panel 레이아웃 (Top, Left, Center, Right, Bottom)
# ============================================================================

"""
Sigma9 GUI Package

PyQt6 기반의 GUI 컴포넌트들을 포함하는 패키지입니다.
"""

from .dashboard import Sigma9Dashboard
from .custom_window import CustomWindow
from .particle_effects import ParticleSystem

__all__ = [
    "Sigma9Dashboard",
    "CustomWindow",
    "ParticleSystem",
]

