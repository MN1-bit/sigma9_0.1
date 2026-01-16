# 09-004 Settings Dialog UI 수정 Devlog

> **작성일**: 2026-01-10
> **계획서**: [09-004_settings_dialog_fixes.md](../../Plan/refactor/09-004_settings_dialog_fixes.md)

## 진행 현황

| Step | 설명 | 상태 | 시간 |
|------|------|------|------|
| Step 1-3 | 드래그/틴트/Non-Modal | ✅ | 12:15 |
| Step 4 | 추가 수정 (eventFilter) | ✅ | 12:21 |
| Step 5 | 기존 에러 수정 | ✅ | 12:24 |
| Step 6 | 전체 배경 드래그 | ✅ | 12:47 |
| Step 7 | Opacity Hot Reload | ✅ | 13:03 |
| Step 8 | 테마 중앙화 개선 | ✅ | 13:08 |
| Step 9 | IMP-verification | ✅ | 13:21 |

---

## Step 1-3: 코드 수정 (통합)

### 변경 사항

**`frontend/gui/settings_dialog.py`**:

1. **드래그 이동 지원**
   - `__init__`: `self._drag_pos = None` 추가
   - `mousePressEvent()`, `mouseMoveEvent()`, `mouseReleaseEvent()` 오버라이드 추가
   - Frameless 창에서 마우스 드래그로 위치 이동 가능

2. **배경 틴트 중립화**
   - 기존: `tint_hex = self.initial_tint_color` → 사용자 설정 tint
   - 변경: `neutral_tint = "181818CC"` → 고정 어두운 회색 (파란/남색 제거)

3. **Non-Modal 전환**
   - `self.setModal(False)` 추가
   - Settings 창 열린 상태에서 메인 창 조작 가능

### Diff 요약

```diff
+ self._drag_pos = None  # 드래그 위치 저장
+ self.setModal(False)   # Non-Modal
- tint_hex = self.initial_tint_color.lstrip("#")
- self.window_effects.add_acrylic_effect(self.winId(), f"{tint_hex}CC")
+ neutral_tint = "181818CC"
+ self.window_effects.add_acrylic_effect(self.winId(), neutral_tint)
+ def mousePressEvent(self, event): ...
+ def mouseMoveEvent(self, event): ...
+ def mouseReleaseEvent(self, event): ...
```

### 검증

- lint: ⚠️ 기존 에러 3건 (F401 unused import, E722 bare except) - 신규 코드 무관
- 추가 라인: +27줄 (드래그 핸들러 + 초기화)
- 파일 총 라인: ~939줄 (1000줄 제한 내)

---

## Step 4: 추가 수정 (12:21)

### 문제점
- 기존 마우스 이벤트 오버라이드 방식은 자식 위젯이 이벤트를 소비하여 빈 공간에서 드래그 불가
- 배경색 transparent 설정 누락

### 추가 변경

1. **eventFilter 방식으로 전환** - 타이틀바(`QFrame`)에만 드래그 적용
2. **타이틀바 QFrame 추가** - 드래그 가능한 영역 명시
3. **닫기 버튼(X) 추가** - Frameless 창용 닫기 UI
4. **QDialog 배경색 transparent 설정** - Acrylic 효과 표시

```python
# eventFilter 방식
def eventFilter(self, watched, event):
    if watched == self.title_bar:
        # 타이틀바에서만 드래그 처리
```

---

## Step 5: 기존 에러 수정 (12:24)

> `/IMP-execution` 4.1 기존 에러 분석 Sub-Phase 적용

### 발견된 기존 에러

```
frontend/gui/settings_dialog.py:22 - F401 `QGroupBox` import but unused
frontend/gui/settings_dialog.py:26 - F401 `QDoubleSpinBox` import but unused  
frontend/gui/settings_dialog.py:608 - E722 bare `except`
```

### 수정 내역

| 에러 | 라인 | 조치 |
|-----|------|------|
| F401 `QGroupBox` | 22 | import 제거 |
| F401 `QDoubleSpinBox` | 26 | import 제거 |
| E722 bare `except` | 608 | `except Exception:` 변경 |

### 검증

```bash
$ ruff check frontend/gui/settings_dialog.py
All checks passed!
```

## Step 6: 전체 배경 드래그 + 컨테이너 수정 (12:47)

### 문제점
- `WA_TranslucentBackground`로 인해 alpha=0 영역은 마우스 이벤트가 뒤 창으로 통과
- 마우스 커서가 뒤 창의 커서로 변경되는 현상

### 해결
1. **컨테이너 QFrame 추가** - `rgba(0, 0, 0, 0.01)` 배경으로 마우스 이벤트 캡처
2. **모든 자식에 이벤트 필터 재귀 설치** - `showEvent`에서 `installEventFilter`
3. **X 버튼 제거** - Save/Cancel로 충분

---

## Step 7: Opacity Hot Reload (13:03)

### 문제점
- Settings/Theme/Window Opacity 슬라이더가 Dialog 자체에 반영 안 됨

### 해결
```python
def _on_opacity_changed(self, value):
    self.setWindowOpacity(value / 100.0)  # Hot reload 추가
```

---

## Step 8: 테마 중앙화 개선 (13:08)

### 추가 사항
`ThemeManager`에 `apply_to_widget()` 메서드 추가하여 새 창 구현 시 opacity 일괄 적용 가능.

### 변경 파일

| 파일 | 변경 |
|-----|------|
| `theme.py` | `apply_to_widget(widget)` 메서드 추가 |
| `settings_dialog.py` | `theme.apply_to_widget(self)` 사용 |
| `dashboard.py` | 3곳에서 `theme.apply_to_widget(self)` 사용 |

```python
# 사용 예시
theme.apply_to_widget(self)  # opacity 자동 적용
```

---

## Step 9: IMP-verification 검증 (13:21)

> `/IMP-verification` 워크플로우 실행

| 항목 | 결과 | 비고 |
|------|------|------|
| ruff check | ✅ | settings_dialog.py, theme.py 통과 |
| 크기 제한 | ⚠️ | settings_dialog.py 884줄 (기존 파일, 500줄 초과) |
| theme.py 크기 | ✅ | 334줄 |
| 수동 검증 | ✅ | 드래그, Acrylic, Opacity hot reload 동작 확인 |
| DI 패턴 | ✅ | get_*_instance() 미사용 |

### 수동 검증 체크리스트

```
[x] 앱 실행 → Settings 버튼 클릭
[x] 전체 배경 영역 드래그로 창 이동
[x] Acrylic 투명 효과 표시
[x] Settings 열린 상태에서 메인 창 조작 가능
[x] Opacity 슬라이더 → Dialog 실시간 반영
[x] Save 버튼 → 설정 저장 정상
```

---

## 📚 생성된 레퍼런스 문서

- [`.agent/Ref/frameless_dialog_pattern.md`](../../../.agent/Ref/frameless_dialog_pattern.md) - Frameless Dialog 구현 패턴
