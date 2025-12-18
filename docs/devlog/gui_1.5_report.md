# GUI Development Report: v1.5 (Icon Integration & Taskbar Fix)
**Date:** 2025-12-18
**Author:** Assistant

## 1. 개요
본 리포트는 Sigma9 애플리케이션의 아이덴티티 강화를 위한 아이콘 적용 작업과 Windows 환경에서의 작업표시줄 아이콘 표출 문제 해결 과정을 기술합니다. 사용자 요청에 따라 맞춤형 아이콘(`ico01.ico`)을 GUI의 주요 포인트와 시스템 레벨에 통합했습니다.

## 2. 주요 변경 사항

### 2.1 애플리케이션 아이콘 통합
기존의 텍스트 기반 로고와 기본 번개(⚡) 이모지를 제거하고, 전용 아이콘 파일(`ico01.ico`)을 적용하여 전문적인 트레이딩 앱의 느낌을 강화했습니다.
- **Top Control Panel:** 좌측 상단의 ⚡ 이모지를 제거하고 아이콘 이미지와 텍스트("Sigma9") 조합으로 레이아웃 변경.
- **Icon Loading:** `frontend/gui/assets/` 경로에서 아이콘을 로드하며, 파일 누락 시 텍스트(⚡)로 폴백(Fallback)하도록 예외 처리.

### 2.2 Windows 작업표시줄 아이콘 분리 (Taskbar Icon Fix)
Python 서드파티 라이브러리(PyQt6 등)로 제작된 GUI 앱은 Windows 작업표시줄에서 Python 기본 아이콘으로 그룹화되는 문제가 있습니다. 이를 해결하여 Sigma9 전용 아이콘이 표시되도록 수정했습니다.

- **원인:** Windows는 프로세스 ID를 기준으로 아이콘을 그룹화하는데, Python 스크립트는 `python.exe` 호스트 프로세스로 실행되므로 기본 Python 아이콘을 사용함.
- **해결:** `ctypes` 라이브러리를 사용하여 **AppUserModelID (AUMID)**를 명시적으로 설정.
  - Windows 쉘(Shell)에 이 프로세스가 "Sigma9"이라는 고유한 애플리케이션임을 알림.
  - 코드: `ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('sigma9.trading.dashboard.v0.1')`
- **결과:** 작업표시줄에 실행 중인 Sigma9 앱이 Python 아이콘이 아닌 설정한 `settings.ico` (또는 `ico01.ico`)로 독립적으로 표시됨.

### 2.3 메인 윈도우 아이콘 설정
애플리케이션 최상위 윈도우(`QMainWindow`)에도 아이콘을 설정하여 타이틀바와 Alt+Tab 전환 시 로고가 노출되도록 했습니다.
- `main.py` 진입점에 `QApplication.setWindowIcon` 로직 추가.

## 3. 기술적 세부 사항
- **File:** 
  - `frontend/main.py`: AUMID 설정 및 앱 전역 아이콘 로드
  - `frontend/gui/control_panel.py`: 상단 패널 로고 UI 변경 (QIcon + QLabel Layout)
- **Library:** `ctypes` (Windows API 호출용), `PyQt6.QtGui.QIcon`

## 4. 검증
- **GUI 실행:** `python -m frontend.main` 명령으로 실행하여 로고 변경 확인.
- **작업표시줄:** 앱 실행 시 작업표시줄 아이콘이 Python 로고에서 Sigma9 전용 아이콘으로 변경됨을 확인.
