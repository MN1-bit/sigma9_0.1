# Settings Dialog UI 수정

> **상태**: 📋 **구현 계획**
> **작성일**: 2026-01-10
> **예상 작업 시간**: 1.5h
> **레이어**: Frontend

---

## 1. 목표

`SettingsDialog` UI 버그 3건 수정:

1. **드래그 위치 변경 불가** - Frameless 창 이동 지원
2. **배경색 파란/남색 틴트** - Acrylic tint_color 중립화
3. **기존 GUI 조작 통제** - 모달 → Non-Modal 전환

---

## 2. 레이어 체크

- [x] 레이어 규칙 위반 없음 (Frontend 단독)
- [x] 순환 의존성 없음
- [x] DI Container 등록 필요: **아니오**

---

## 3. 기존 솔루션 검색 결과

| 솔루션 | 출처 | 채택 여부 | 사유 |
|--------|------|----------|------|
| `FramelessWindow` (qframelesswindow) | PyPI | ❌ 미채택 | 외부 의존성 추가 불필요 |
| PyQt 내장 `mousePressEvent`/`mouseMoveEvent` | Qt Docs | ✅ 채택 | 표준 패턴, 의존성 없음 |

> 검색 완료: 간단한 마우스 이벤트 오버라이드로 충분

---

## 4. 문제 분석

### 4.1 드래그 불가

**원인**: [settings_dialog.py#L114](file:///d:/Codes/Sigma9-0.1/frontend/gui/settings_dialog.py#L114)
```python
self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
```
- `FramelessWindowHint`로 타이틀바 제거 → 기본 드래그 핸들러 비활성화
- 커스텀 타이틀 영역에 마우스 이벤트 핸들러 부재

**해결**: `mousePressEvent`/`mouseMoveEvent` 오버라이드 추가

### 4.2 배경 틴트

**원인**: [settings_dialog.py#L122-123](file:///d:/Codes/Sigma9-0.1/frontend/gui/settings_dialog.py#L122-L123)
```python
tint_hex = self.initial_tint_color.lstrip("#")
self.window_effects.add_acrylic_effect(self.winId(), f"{tint_hex}CC")
```
- 사용자 설정 `tint_color` (기본값: 테마 tint) → 파란/남색 계열 가능
- Acrylic 효과에 해당 tint 적용 → 배경색 편향

**해결**: 중립 tint (어두운 회색 `#1a1a1a` 또는 `#181818`) 고정 적용

### 4.3 모달 통제

**원인**: Dashboard에서 `exec()` 호출 시 기본 모달 동작
```python
# 예상 호출 패턴 (dashboard.py)
dialog.exec()  # 블로킹 모달
```

**해결**: 
- `setModal(False)` 명시
- 호출부에서 `show()` 사용 or `exec()` 유지 (사용자 선택)

---

## 5. 변경 파일

| 파일 | 유형 | 설명 | 예상 라인 |
|------|------|------|----------|
| `frontend/gui/settings_dialog.py` | MODIFY | 드래그 + 틴트 + 모달 수정 | +40 |

---

## 6. 실행 단계

### Step 1: 드래그 이동 지원 (0.5h)

**변경 위치**: `SettingsDialog` 클래스

```python
def __init__(self, parent=None, current_settings=None):
    super().__init__(parent)
    # ... 기존 코드 ...
    self._drag_pos = None  # [NEW] 드래그 위치 저장

def mousePressEvent(self, event):
    """Frameless 창 드래그 시작"""
    if event.button() == Qt.MouseButton.LeftButton:
        self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        event.accept()

def mouseMoveEvent(self, event):
    """Frameless 창 드래그 이동"""
    if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
        self.move(event.globalPosition().toPoint() - self._drag_pos)
        event.accept()

def mouseReleaseEvent(self, event):
    """드래그 종료"""
    self._drag_pos = None
```

---

### Step 2: 배경 틴트 중립화 (0.3h)

**변경 위치**: `__init__` 메서드 내 Acrylic 적용부

```diff
- tint_hex = self.initial_tint_color.lstrip("#")
- self.window_effects.add_acrylic_effect(self.winId(), f"{tint_hex}CC")
+ # 중립 어두운 회색 틴트 (테마 독립)
+ neutral_tint = "181818CC"  # Dark gray + CC alpha
+ self.window_effects.add_acrylic_effect(self.winId(), neutral_tint)
```

---

### Step 3: Non-Modal 전환 (0.3h)

**변경 위치**: `__init__` 메서드

```python
def __init__(self, parent=None, current_settings=None):
    super().__init__(parent)
    # ... 기존 코드 ...
    self.setModal(False)  # [NEW] Non-Modal 설정
```

**호출부 검토**: Dashboard에서 `exec()` → `show()` 전환 필요 시 추가 수정

---

### Step 4: 검증 (0.4h)

| # | 항목 | 예상 결과 |
|---|------|----------|
| 1 | 창 드래그 | 타이틀 영역 드래그로 창 이동 가능 |
| 2 | 배경색 | 중립 어두운 회색 (파란 틴트 제거) |
| 3 | GUI 조작 | Settings 창 열린 상태에서 메인 창 조작 가능 |
| 4 | 기존 기능 | 모든 탭 설정 저장/로드 정상 작동 |

---

## 7. 검증 계획

### 수동 검증
```
1. 앱 실행 → Settings 버튼 클릭
2. Settings 창 타이틀 영역 드래그 → 창 이동 확인
3. 배경색 시각적 확인 (파란 틴트 없음)
4. Settings 열린 상태에서 메인 창 조작 시도
5. Save 버튼 → 설정 저장 확인
```

### 자동 검증
```bash
# lint 체크
python -m ruff check frontend/gui/settings_dialog.py --fix
```

---

## 8. 다음 단계

- [ ] `/IMP-execution`
- [ ] 완료 후 09-005 진행 (Chart Theme Settings)
