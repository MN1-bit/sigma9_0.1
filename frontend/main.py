# ============================================================================
# Sigma9 Frontend - PyQt6 GUI 진입점
# ============================================================================
# 📌 이 파일의 역할:
#   PyQt6 GUI 애플리케이션의 메인 진입점입니다.
#   Sigma9Dashboard 윈도우를 생성하고 표시합니다.
#
# 📌 실행 방법:
#   python frontend/main.py
#
# 📌 의존성:
#   - PyQt6
#   - pywin32 (Windows DWM API용)
# ============================================================================

"""
Sigma9 Frontend Application

PyQt6 기반의 데스크탑 트레이딩 대시보드 애플리케이션입니다.
Glassmorphism(Acrylic) 스타일의 모던한 UI를 제공합니다.
"""

import sys
import os

# 고DPI 스케일링 설정
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# gui 패키지에서 대시보드 import
from .gui.dashboard import Sigma9Dashboard


def main():
    """
    애플리케이션 메인 함수
    
    PyQt6 애플리케이션을 초기화하고 Sigma9Dashboard를 표시합니다.
    """
    print("[DEBUG] Starting main()")
    try:
        # 고DPI 정책 설정 (Qt 6.x)
        if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
            QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )
        
        # [FIX] WebEngineView와 투명 윈도우(Acrylic) 호환성 개선
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        
        # QApplication 생성
        app = QApplication(sys.argv)
        print("[DEBUG] QApplication created")
        
        # 메인 대시보드 윈도우 생성 및 표시
        window = Sigma9Dashboard()
        print("[DEBUG] Sigma9Dashboard window created")
        window.show()
        print("[DEBUG] Window shown, entering event loop")
        
        # 이벤트 루프 실행
        sys.exit(app.exec())
    except Exception as e:
        print(f"[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
