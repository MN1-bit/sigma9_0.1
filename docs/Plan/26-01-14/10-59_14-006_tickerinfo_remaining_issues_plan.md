# 14-006: TickerInfoWindow 잔여 이슈 수정 계획서

> **작성일**: 2026-01-14 | **예상**: 1h

## 1. 목표

1. **이슈 1**: 창 재오픈 시 투명도 문제 해결 (심각도 중간, 난이도 낮음)
2. **이슈 2**: Profile 박스 Dynamic Height 미작동 해결 (심각도 낮음, 난이도 높음)

---

## 2. 레이어 체크

- [x] 레이어 규칙 위반 없음 (frontend 내부 수정)
- [x] 순환 의존성 없음
- [x] DI Container 등록 필요: 아니오

---

## 3. 기존 솔루션 검색 결과

| 솔루션 | 출처 | 채택 여부 | 사유 |
|--------|------|----------|------|
| Qt 공식 문서 (wordWrap + sizeHint) | Qt 문서 | ✅ 참조 | `heightForWidth()` 기반 동적 높이 필요 |
| Acrylic 효과 + Opacity 중복 이슈 | Stack Overflow | ✅ 참조 | 이미 `showEvent`에서 재설정 중 |

---

## 4. 변경 파일

| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
| `frontend/gui/ticker_info_window.py` | MODIFY | +20 |

---

## 5. 실행 단계

### Step 1: 투명도 문제 진단 (이슈 1)

**현상 분석**:
- 현재 코드 (line 837): `showEvent`에서 `self.setWindowOpacity(theme.opacity)` 호출됨
- 현재 코드 (line 771): `_apply_theme`에서 동일 호출
- Acrylic 효과 tint: `181818CC` (alpha 204/255 = 80%)

**수정 방향**:
1. `_apply_theme`에서 `setWindowOpacity` 호출 시 로거 레벨 상세화
2. `showEvent` 직후 Acrylic 효과 재적용 (WA_WState_Created 상태 체크)
3. 테스트: 창 닫고 재오픈 시 투명도 동일한지 확인

**변경 내용**:
```python
# ticker_info_window.py - showEvent 수정
def showEvent(self, event) -> None:
    super().showEvent(event)
    # Opacity 재설정 (Acrylic 효과와 독립적으로 작동)
    logger.debug(f"[showEvent] Reapplying opacity: theme.opacity={theme.opacity}")
    self.setWindowOpacity(theme.opacity)
    
    # [14-006] Acrylic 효과 재적용 (재오픈 시 손실될 수 있음)
    if hasattr(self, '_window_effects'):
        self._window_effects.add_acrylic_effect(self.winId(), "181818CC")
    
    # ... 기존 코드
```

---

### Step 2: Profile 전체 Dynamic Height 수정 (이슈 2)

**현상 분석**:
- `DetailTable`의 `setSizePolicy(Preferred, Minimum)` 적용됨 (line 204)
- `val_label`에 `setWordWrap(True)`, `setSizePolicy(Expanding, Minimum)` 적용됨 (line 248-250)
- 문제: `QScrollArea` 내부에서 `widgetResizable=True`로 설정되어 있으나, 고정 너비(`setFixedWidth(200)`)가 wordWrap 높이 계산을 방해

**적용 범위**: Profile 영역 **모든 필드** (회사명, 본사 주소, SIC 설명 등)

**수정 방향**:
1. `DetailTable.set_data`에서 **모든 `val_label`**에 동적 높이 적용 + `updateGeometry()` 호출
2. `key_label`도 wordWrap 가능하게 수정 (긴 키 이름 대응)
3. `_create_column1_profile`에서 프레임/레이아웃 SizePolicy 조정
4. Column 1 고정 너비 내에서 텍스트 자동 줄바꿈 + 높이 확장

**변경 내용**:
```python
# DetailTable.set_data 수정 (전체 필드에 wordWrap 적용)
def set_data(self, data: list[tuple[str, str]]) -> None:
    # ... 기존 아이템 제거 ...
    
    for row, (key, value) in enumerate(data):
        key_label = QLabel(key)
        key_label.setStyleSheet(...)
        key_label.setWordWrap(True)  # [14-006] 키 라벨도 wordWrap
        
        val_label = QLabel(str(value) if value else "--")
        val_label.setStyleSheet(...)
        val_label.setWordWrap(True)
        # [14-006] 모든 필드에 동적 높이 적용
        val_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        val_label.setMinimumHeight(0)
        
        self._grid.addWidget(key_label, row, 0, Qt.AlignmentFlag.AlignTop)  # 상단 정렬
        self._grid.addWidget(val_label, row, 1, Qt.AlignmentFlag.AlignTop)
        self._grid.setRowStretch(row, 0)
    
    # [14-006] 레이아웃 재계산 강제 호출
    self.updateGeometry()
    self.adjustSize()
```

```python
# _create_column1_profile 수정
def _create_column1_profile(self) -> QFrame:
    frame = QFrame()
    # [14-006] 높이 자동 조절 활성화 (Fixed 너비, Preferred 높이)
    frame.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
    # ... 기존 코드 ...
    
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(8)
    
    # [14-006] Profile Table - stretch 없이 콘텐츠 높이에 맞춤
    self._profile_table = DetailTable("Profile")
    self._profile_table.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
    layout.addWidget(self._profile_table)
    # ... 기존 코드 ...
```

---

## 6. 검증

### 자동 검증

```bash
# 린트 검사
ruff check frontend/gui/ticker_info_window.py
lint-imports
```

### 수동 검증 (GUI 테스트)

1. **투명도 테스트**:
   - GUI 실행: `python -m frontend.main`
   - 아무 티커 선택 (e.g., AAPL)
   - Info 창 열기 → 창의 투명도 확인
   - Info 창 닫기 (X 버튼)
   - Info 창 다시 열기 → 투명도가 첫 번째와 동일한지 확인
   - **성공 기준**: 두 번째 오픈 시 투명도가 첫 번째와 동일

2. **Dynamic Height 테스트**:
   - 긴 SIC description이 있는 티커 검색 (e.g., AAPL, MSFT)
   - Profile 섹션의 "업종 (SIC)" 필드 확인
   - **성공 기준**: 텍스트가 잘리지 않고 박스 높이가 자동 조절됨

> ⚠️ **참고**: Dynamic Height 이슈는 Qt 레이아웃 시스템의 복잡성으로 인해 추가 조정이 필요할 수 있습니다. Step 2 완료 후 결과를 확인하고 필요시 추가 수정을 진행합니다.

---

## 7. 승인

**반드시** 사용자 승인 후 코드 작성.

---

**다음**: `/IMP-execution`
