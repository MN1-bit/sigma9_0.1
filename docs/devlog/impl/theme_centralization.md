# Theme Centralization Devlog

> **작성일**: 2026-01-10
> **계획서**: [Theme-01_centralization.md](../../Plan/refactor/Theme-01_centralization.md)

## 진행 현황

| Step | 상태 | 시간 |
|------|------|------|
| Phase 1: ThemeManager 확장 | ✅ | 02:28 |
| Phase 2: Color Migration | ✅ | 02:37 |
| Phase 3: GUI 실행 검증 | ✅ | 02:45 |

---

## Phase 1: ThemeManager 확장

### 변경 사항
- `frontend/gui/theme.py`: 180→370 lines
  - QObject 상속 + `theme_changed` Signal
  - 25+ 색상 토큰 (chart, tier, status)
  - 7개 컴포넌트 stylesheet 지원
  - `get_action_button_style()` 신규

### 신규 색상 토큰
```
chart_up, chart_down, chart_neutral
tier_zenV_high, tier_zenV_mid, tier_zenV_low
status_connected, status_disconnected, status_error
text_muted, surface_elevated
```

---

## Phase 2: Color Migration

### 수정 파일
| 파일 | 변경 내용 |
|------|----------|
| `watchlist_model.py` | chart_up/down/warning |
| `tier2_panel.py` | tier_zenV_*, danger, primary |

### 이미 호환 (수정 불필요)
- position_panel.py, oracle_panel.py, log_panel.py
- control_panel.py, dashboard.py, settings_dialog.py

---

## Phase 3: 검증

### 자동화
- ruff check: ✅
- lint-imports: ✅

### 수동 (GUI 실행)
- `python -m frontend` 실행: ✅
- Settings Dialog 정상: ✅

### 추가 작업
- `frontend/__main__.py` 생성 (패키지 실행 지원)

---

## Before/After 비교

| 항목 | Before | After |
|------|--------|-------|
| 하드코딩 색상 | 100+ | 0 (핵심 파일) |
| 색상 토큰 | 12개 | 25개 |
| Stylesheet 컴포넌트 | 2개 | 7개 |
| Hot Reload | ❌ | ✅ (Signal 준비) |

---

## 산출물

| 항목 | 경로 |
|------|------|
| 계획서 | `docs/Plan/refactor/Theme-01_centralization.md` |
| 워크플로우 | `.agent/workflows/Theme-policy.md` |
| ThemeManager | `frontend/gui/theme.py` |
| 패키지 진입점 | `frontend/__main__.py` |

---

## 향후 작업 (Optional)

- [ ] Settings Dialog에서 Font Family/Size 조정 UI 추가
- [ ] 각 위젯에서 `theme.theme_changed.connect()` 연결
- [ ] 테마 프리셋 시스템 (Neon, Pastel 등)
