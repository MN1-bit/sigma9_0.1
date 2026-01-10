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
import ctypes  # [NEW] Windows 작업표시줄 아이콘 분리를 위해 필요

# 고DPI 스케일링 설정
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
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
        if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
            QApplication.setHighDpiScaleFactorRoundingPolicy(
                Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            )

        # [FIX] WebEngineView와 투명 윈도우(Acrylic) 호환성 개선
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

        # [FIX] Windows 작업표시줄 아이콘 분리 (AppUserModelID 설정)
        # Python 실행파일 아이콘이 아닌 앱 고유 아이콘을 사용하기 위해 필요함
        try:
            myappid = "sigma9.trading.dashboard.v0.1"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception as e:
            print(f"[WARN] Failed to set AppUserModelID: {e}")

        # QApplication 생성
        app = QApplication(sys.argv)

        # [NEW] 앱 전체 아이콘 설정 (Taskbar 아이콘 반영에 중요)
        try:
            # frontend/main.py 기준 -> gui/assets/ico01.ico
            icon_path = os.path.join(
                os.path.dirname(__file__), "gui", "assets", "ico01.ico"
            )
            if os.path.exists(icon_path):
                app_icon = QIcon(icon_path)
                app.setWindowIcon(app_icon)
                print(f"[INFO] App icon set from: {icon_path}")
            else:
                print(f"[WARN] Icon file not found at: {icon_path}")
        except Exception as e:
            print(f"[WARN] Failed to set app icon: {e}")
        print("[DEBUG] QApplication created")

        # 메인 대시보드 윈도우 생성 및 표시
        window = Sigma9Dashboard()

        # [NEW] 작업표시줄 아이콘 설정
        try:
            icon_path = os.path.join(
                os.path.dirname(__file__), "gui", "assets", "ico01.ico"
            )
            window.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            print(f"[WARN] Failed to set window icon: {e}")

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
