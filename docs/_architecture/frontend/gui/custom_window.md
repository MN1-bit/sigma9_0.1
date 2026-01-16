# custom_window.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `frontend/gui/custom_window.py` |
| **역할** | Windows Acrylic/Mica 효과를 지원하는 프레임리스 커스텀 윈도우 |
| **라인 수** | 620 |
| **바이트** | 20,645 |

---

## 클래스

### Windows API 구조체

| 클래스 | 설명 |
|--------|------|
| `APPBARDATA` | Taskbar 정보 구조체 |
| `PWINDOWPOS` | 윈도우 위치 구조체 |
| `NCCALCSIZE_PARAMS` | Non-client 영역 계산 파라미터 |
| `Taskbar` | 태스크바 위치/자동숨김 감지 |

---

### `TitleBarButtonState` (Enum)

| 값 | 설명 |
|----|------|
| `NORMAL` | 기본 상태 |
| `HOVER` | 마우스 오버 |
| `PRESSED` | 클릭됨 |

---

### `TitleBarButton(QAbstractButton)`

> 타이틀바 버튼 (Minimize/Maximize/Close)

---

### `CustomBase`

> Acrylic/Mica 효과 기반 윈도우 베이스 클래스

#### 생성자 파라미터

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `use_mica` | `str` | `'false'`, `'true'`, `'if available'` |
| `theme` | `str` | `'auto'`, `'dark'`, `'light'` |
| `color` | `str` | 배경색 (RRGGBBAA) |

#### 주요 메서드

| 메서드 | 설명 |
|--------|------|
| `set_effect(enable)` | Acrylic/Mica 효과 활성화/비활성화 |
| `update_acrylic_color(color)` | 동적 Acrylic 색상 변경 |
| `nativeEvent(event_type, message)` | Windows 메시지 처리 (WM_NCCALCSIZE 등) |

---

### `CustomWindow(CustomBase, QMainWindow)`

> 프레임리스 Acrylic 윈도우 (QMainWindow 기반)

---

### `CustomAcrylicWindow(CustomWindow)`

> Sigma9Dashboard에서 상속하는 Final 윈도우 클래스

---

## 함수 (Standalone)

| 함수 | 설명 |
|------|------|
| `is_maximized(h_wnd)` | 최대화 상태 확인 |
| `get_monitor_info(h_wnd, dw_flags)` | 모니터 정보 조회 |
| `is_full_screen(h_wnd)` | 전체 화면 상태 확인 |
| `find_window(h_wnd)` | Qt 윈도우 검색 |
| `get_resize_border_thickness(h_wnd)` | 리사이즈 테두리 두께 |
| `is_system_dark_mode()` | 시스템 다크모드 확인 |
| `invert_color(color)` | 색상 반전 |

---

## 🔗 외부 연결 (Connections)

### Imports From

| 파일/모듈 | 가져오는 항목 |
|----------|--------------|
| `frontend/gui/window_effects.py` | `WindowsEffects` |
| `win32api`, `win32con` | Windows API |
| `ctypes` | Windows 구조체 정의 |

### Imported By

| 파일 | 사용 목적 |
|------|----------|
| `frontend/gui/__init__.py` | 패키지 export |
| `frontend/gui/dashboard.py` | 메인 윈도우 상속 |

---

## 외부 의존성

- `PyQt6` / `PySide6`
- `pywin32` (win32api, win32con)
- `ctypes` (Windows API)
