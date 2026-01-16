# 10-001: Complete GUI Theme Centralization

GUI 테마를 완전 중앙화하여 Settings 창에서 모든 테마 요소를 제어.

---

## Current State Analysis

### ✅ Centralized (Working)
| Item | Location |
|------|----------|
| Color Palettes | `theme.py` (Dark/Light 12색) |
| Theme Mode | Settings → Dark/Light 라디오 |
| Acrylic Settings | Settings → Opacity, Alpha, Tint |
| Background Effect | Settings → 9개 효과 |

### ❌ NOT Centralized
| Issue | Count |
|-------|-------|
| Hardcoded Hex Colors | 100+ |
| Inline `setStyleSheet()` | 50+ |
| `theme` Import 누락 | 11/15 파일 |
| Font 설정 미적용 | 다수 |

---

## Decisions Made

- **색상 커스터마이징**: 프리셋 테마 (Dark/Light/Neon 등)
- **마이그레이션**: 전체 파일 일괄 처리
- **폰트**: 중앙화 포함

---

## Proposed Changes

### Phase 1: ThemeManager 확장
**[MODIFY] `frontend/gui/theme.py`**
- 추가 색상 토큰 (`chart_up`, `chart_down`, `tier1_zenV_high` 등)
- `get_stylesheet()` 확장: `button`, `combobox`, `input`, `table`, `slider`
- `theme_changed` Signal 추가 (핫 리로드용)
- QObject 상속 추가

### Phase 2: Hardcoded Color Migration

| File | 수정량 |
|------|--------|
| `settings_dialog.py` | ~40 |
| `control_panel.py` | ~15 |
| `tier2_panel.py` | ~10 |
| `position_panel.py` | ~8 |
| `oracle_panel.py` | ~6 |
| `watchlist_panel.py` | ~5 |
| `log_panel.py` | ~4 |
| `chart_panel.py` | ~3 |
| `watchlist_model.py` | ~2 |

### Phase 3: Settings Dialog 확장
**[MODIFY] `settings_dialog.py` `_create_theme_tab()`**
- Font Family Dropdown (Pretendard, Inter, Roboto)
- Font Size Spinner (10-16px)
- Theme Preset 선택

### Phase 4: Hot Reload
- 각 위젯에서 `theme.theme_changed.connect(self._refresh_styles)` 연결

---

## Verification Plan

```bash
ruff format --check frontend/gui/
ruff check frontend/gui/
lint-imports
pydeps frontend/gui --only frontend/gui --show-cycles --no-output
```

**수동 검증**:
1. Backend/Frontend 시작
2. Settings → Theme → Dark/Light 전환 확인
3. 모든 패널 색상 즉시 반영 확인

---

## Estimated Effort

| Phase | 예상 시간 |
|-------|----------|
| ThemeManager 확장 | 30분 |
| Settings Dialog 확장 | 45분 |
| Color Migration | 1-2시간 |
| Hot Reload | 1시간 |
| 검증 | 30분 |

**총 예상: 3-5시간**
