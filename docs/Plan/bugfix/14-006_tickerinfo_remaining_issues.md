# 14-006: TickerInfoWindow 잔여 이슈 분석

> **작성일**: 2026-01-13
> **관련 구현**: 14-004 (TickerInfo UI 레이아웃 통합 개선)

## 개요

14-004 구현 후 남은 UI 이슈들을 문서화합니다.

---

## 이슈 1: 창 재오픈 시 투명도 문제

### 현상
- TickerInfoWindow를 닫았다가 다시 열면 창이 **너무 투명**해지는 문제
- 첫 번째 오픈 시에는 정상적으로 표시됨

### 분석 필요 사항
1. `showEvent()`에서 `setWindowOpacity(theme.opacity)` 호출 확인
2. `theme.opacity` 값이 재오픈 시 변경되는지 확인
3. Acrylic 효과 (`WindowsEffects.add_acrylic_effect`) 상태 확인
4. 다른 창(SettingsDialog 등)에서 동일 문제 발생 여부

### 의심 원인
- Acrylic 효과와 `setWindowOpacity()` 중복 적용 가능성
- `hideEvent()` 또는 `closeEvent()`에서 상태 변경 가능성
- 테마 변경 시그널이 `showEvent()` 전에 발생하여 값 충돌

### 관련 코드
```python
# frontend/gui/ticker_info_window.py
def showEvent(self, event) -> None:
    super().showEvent(event)
    logger.debug(f"[showEvent] Setting opacity to theme.opacity={theme.opacity}")
    self.setWindowOpacity(theme.opacity)
    # ...
```

---

## 이슈 2: Profile 박스 Dynamic Height 미작동

### 현상
- Profile 섹션(Column 1)의 `DetailTable` 내용물 길이에 따라 박스 높이가 자동 조절되지 않음
- SIC 설명 등 긴 텍스트가 잘리거나 빈 공간이 남음

### 적용된 수정 (미완료)
```python
# DetailTable._setup_ui
self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

# DetailTable.set_data
val_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
val_label.setMinimumHeight(0)
self._grid.setRowStretch(row, 0)
```

### 분석 필요 사항
1. 부모 `QFrame`의 `QVBoxLayout`에서 stretch 정책 확인
2. `QScrollArea` 래핑 후 `minimumSizeHint()` 동작 확인
3. Column 고정 너비(`setFixedWidth(200)`)가 높이 계산에 영향 주는지
4. `setWordWrap(True)` 후 레이아웃 재계산 필요 여부

### 의심 원인
- `QScrollArea`가 내부 위젯의 높이를 강제로 고정할 수 있음
- Column 1의 `setFixedWidth(200)`로 인해 너비 기반 높이 계산 실패
- Qt의 레이아웃 시스템에서 `wordWrap` + `SizePolicy.Minimum` 조합 문제

### 시도해볼 접근법
1. `DetailTable`에 `setMinimumHeight(0)` + `setMaximumHeight(QWIDGETSIZE_MAX)` 적용
2. Column 1 프레임에 `setSizePolicy(Fixed, Preferred)` 적용
3. `adjustSize()` 또는 `updateGeometry()` 호출로 강제 레이아웃 재계산
4. `QScrollArea` 내부가 아닌 외부에 Column 1 배치

---

## 우선순위

| 이슈 | 심각도 | 난이도 |
|------|--------|--------|
| 투명도 문제 | 중간 | 낮음 |
| Dynamic Height | 낮음 | 높음 |

---

## 참고

- 14-003: Opacity 버그 수정 (re-open 시 theme.opacity로 재설정)
- 14-004: UI 레이아웃 통합 개선
