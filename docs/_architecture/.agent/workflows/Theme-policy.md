# Theme-policy.md

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `.agent/workflows/Theme-policy.md` |
| **역할** | GUI 테마 중앙화 정책 |
| **라인 수** | 83 |

## 필수 Import
```python
from ..theme import theme
from ..window_effects import WindowsEffects  # Popup용
```

## 색상 사용 규칙

### ❌ 금지
```python
label.setStyleSheet("color: #2196F3;")
```

### ✅ 필수
```python
label.setStyleSheet(f"color: {theme.get_color('primary')};")
```

## 색상 토큰
| 토큰 | 용도 |
|------|------|
| `primary` | 주요 액션, 링크 |
| `success` | 성공, 매수, 상승 |
| `danger` | 위험, 매도, 하락 |
| `text/text_secondary` | 텍스트 |
| `background/surface` | 배경 |

## 체크리스트
- [ ] `from ..theme import theme` import
- [ ] 하드코딩된 `#XXXXXX` 없음
- [ ] `ruff check` 통과
