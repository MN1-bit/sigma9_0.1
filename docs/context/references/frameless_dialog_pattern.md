# Frameless Dialog with Acrylic Effect Pattern

> **작성일**: 2026-01-10
> **출처**: 09-004 Settings Dialog UI 수정

---

## 문제 요약

PyQt6에서 Frameless + Acrylic 효과 + 드래그 가능 Dialog 구현 시 여러 함정 존재.

---

## 문제 1: 마우스 이벤트가 뒤 창으로 통과

### 증상
- `WA_TranslucentBackground` 설정 시 배경 클릭이 뒤 창으로 통과
- 마우스 커서가 뒤 창의 커서로 변경 (예: I-beam)
- 드래그 불가능

### 원인
```python
self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
```
이 속성은 **alpha=0인 영역**의 마우스 이벤트를 창 뒤로 전달함.

### 해결
```python
# 컨테이너에 최소 alpha 값 부여 (0.01 = 거의 투명하지만 이벤트 캡처)
self.container = QFrame()
self.container.setStyleSheet("""
    #settingsContainer {
        background-color: rgba(0, 0, 0, 0.01);  # ← alpha > 0 필수!
        border-radius: 12px;
    }
""")
```

> ⚠️ **주의**: Qt 스타일시트에서 `rgba(0,0,0,1)` = 완전 불투명 (alpha 0-1 범위)

---

## 문제 2: 자식 위젯에서 드래그 불가

### 증상
- `mousePressEvent` 오버라이드해도 자식 위젯 위에서는 호출 안 됨
- 빈 공간에서만 드래그 가능

### 원인
- 자식 위젯(QTabWidget, QFrame 등)이 마우스 이벤트를 먼저 소비

### 해결
```python
def _install_drag_filter_recursive(self, widget):
    """모든 자식 위젯에 이벤트 필터 재귀 설치"""
    widget.installEventFilter(self)
    for child in widget.findChildren(QWidget):
        child.installEventFilter(self)

def showEvent(self, event):
    super().showEvent(event)
    if not hasattr(self, '_drag_filter_installed'):
        self._install_drag_filter_recursive(self)
        self._drag_filter_installed = True

def eventFilter(self, watched, event):
    """전체 배경에서 드래그 가능 (인터랙티브 위젯 제외)"""
    if event.type() == QEvent.Type.MouseButtonPress:
        if event.button() == Qt.MouseButton.LeftButton:
            if not self._is_interactive_widget(watched):
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                return False  # 이벤트 계속 전파
    
    elif event.type() == QEvent.Type.MouseMove:
        if self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            return True  # 이벤트 소비
    
    elif event.type() == QEvent.Type.MouseButtonRelease:
        self._drag_pos = None
    
    return super().eventFilter(watched, event)
```

---

## 문제 3: 인터랙티브 위젯에서 드래그 방지

### 해결
```python
def _is_interactive_widget(self, widget) -> bool:
    """드래그 제외 대상 위젯 판별"""
    interactive_types = (
        QPushButton, QComboBox, QSpinBox, QLineEdit,
        QCheckBox, QRadioButton, QSlider, QTabBar, QTimeEdit,
        QScrollBar, QProgressBar
    )
    check_widget = widget
    while check_widget is not None:
        if isinstance(check_widget, interactive_types):
            return True
        if check_widget == self:
            break
        check_widget = check_widget.parent()
    return False
```

---

## 문제 4: Opacity 설정 미적용

### 증상
- Theme 탭의 Window Opacity 슬라이더가 Dialog에 반영 안 됨

### 해결 (테마 중앙화 사용)
```python
from .theme import theme

def __init__(self, ...):
    # ... 생략 ...
    # 테마 중앙화 - opacity 자동 적용
    theme.apply_to_widget(self)
    # Hot reload 연결 (선택)
    theme.theme_changed.connect(lambda: theme.apply_to_widget(self))

def _on_opacity_changed(self, value):
    # Hot reload: 슬라이더 변경 시 즉시 적용
    self.setWindowOpacity(value / 100.0)
    self.sig_settings_changed.emit({"opacity": value / 100.0})
```

---

## 전체 구현 체크리스트

| # | 항목 | 구현 |
|---|------|------|
| 1 | Frameless 설정 | `setWindowFlags(Qt.WindowType.FramelessWindowHint \| Qt.WindowType.Dialog)` |
| 2 | 투명 배경 허용 | `setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)` |
| 3 | 마우스 캡처 컨테이너 | `rgba(0, 0, 0, 0.01)` 배경 QFrame |
| 4 | Acrylic 효과 | `WindowsEffects.add_acrylic_effect()` |
| 5 | 드래그 필터 설치 | `showEvent`에서 재귀 `installEventFilter` |
| 6 | 인터랙티브 위젯 제외 | `_is_interactive_widget()` 체크 |
| 7 | **Opacity 적용** | **`theme.apply_to_widget(self)`** |
| 8 | Non-Modal | `setModal(False)` |

---

## 참고 파일

- `frontend/gui/settings_dialog.py` - 실제 구현 예시
- `frontend/gui/window_effects.py` - Windows Acrylic API 래퍼
- `frontend/gui/theme.py` - `apply_to_widget()` 메서드
