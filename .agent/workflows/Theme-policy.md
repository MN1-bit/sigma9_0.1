---
description: 새 GUI 요소 작성 시 테마 중앙화 정책
---

# Theme-policy

> **전제**: 신규 GUI 위젯/패널/팝업 작성 시 적용

## 1. 필수 Import

```python
from ..theme import theme
from ..window_effects import WindowsEffects  # Popup/Window용
```

## 2. 색상 사용 규칙

### ❌ 금지
```python
label.setStyleSheet("color: #2196F3;")
```

### ✅ 필수
```python
label.setStyleSheet(f"color: {theme.get_color('primary')};")
```

## 3. 참조 가능 vs 신규 작성

| 요소 | 재사용 ✅ | 신규 ❌ |
|------|----------|---------|
| 색상 | `theme.get_color()` | 커스텀 토큰 |
| 패널/입력/콤보 | `theme.get_stylesheet()` | 테이블/트리뷰 |
| 버튼 | `theme.get_button_style()` | 토글/아이콘 버튼 |
| Acrylic | `WindowsEffects` | - |
| 폰트 | `theme.font_family/size` | - |
| 레이아웃 | - | 항상 신규 |

## 4. 색상 토큰 목록

| 토큰 | 용도 |
|------|------|
| `primary` | 주요 액션, 링크 |
| `success` | 성공, 매수, 상승 |
| `warning` | 경고, 주의 |
| `danger` | 위험, 매도, 하락 |
| `text/text_secondary/text_muted` | 텍스트 |
| `background/surface/surface_elevated` | 배경 |
| `chart_up/chart_down` | 차트 |
| `tier_zenV_high/mid/low` | Tier 레벨 |

## 5. Stylesheet 생성

```python
frame.setStyleSheet(theme.get_stylesheet("panel"))
combo.setStyleSheet(theme.get_stylesheet("combobox"))
btn.setStyleSheet(theme.get_button_style("primary"))
action_btn.setStyleSheet(theme.get_action_button_style("success"))
```

**지원 컴포넌트**: `panel`, `list`, `combobox`, `input`, `tab`, `separator`, `label_section`

## 6. Popup/Window 생성

```python
class MyPopup(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Acrylic 효과
        self.window_effects = WindowsEffects()
        tint = f"{theme.tint_r:02X}{theme.tint_g:02X}{theme.tint_b:02X}CC"
        self.window_effects.add_acrylic_effect(self.winId(), tint)
```

## 7. 체크리스트

- [ ] `from ..theme import theme` import
- [ ] 하드코딩된 `#XXXXXX` 없음
- [ ] `ruff check` 통과
