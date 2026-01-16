# 14-006 TickerInfo 잔여 이슈 Devlog

> **작성일**: 2026-01-14
> **계획서**: [link](../../Plan/impl/14-006_tickerinfo_remaining_issues_plan.md)

## 진행 현황

| Step | 상태 | 시간 |
|------|------|------|
| Step 1 | ✅ | 11:00 |
| Step 2 | ✅ | 11:05 |

---

## Step 1: 투명도 문제 수정

### 변경 사항
- `frontend/gui/ticker_info_window.py`: `showEvent`에서 Acrylic 효과 재적용 추가

### 검증
- ruff check: ✅ All checks passed!
- GUI 테스트: ✅ 창 재오픈 시 투명도 정상

---

## Step 2: Profile 전체 Dynamic Height 수정

### 변경 사항 (1차 시도 → 미작동)
- `val_label`에 `setSizePolicy(Minimum)`, `updateGeometry()` 추가

### 변경 사항 (2차 시도 → 성공!)
- `frontend/gui/ticker_info_window.py` - `DetailTable.set_data`:
  - `key_label.setFixedWidth(50)` - 키 라벨 고정 너비
  - `val_label.setMaximumWidth(110)` - wordWrap 시 height-for-width 작동
  - `Qt.AlignmentFlag.AlignTop` - 멀티라인 시 상단 정렬

### 핵심 원인
- Qt에서 `wordWrap`이 작동하려면 **고정 너비**가 필요 (height-for-width 메커니즘)
- `QScrollArea` 내부에서는 `setFixedWidth` 또는 `setMaximumWidth` 필수

### 검증
- ruff check: ✅ All checks passed!
- GUI 테스트: ✅ SIC, 주소, 회사명 등 긴 텍스트 자동 줄바꿈 확인
