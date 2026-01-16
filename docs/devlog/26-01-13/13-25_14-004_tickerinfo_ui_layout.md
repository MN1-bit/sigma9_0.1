# 14-004: TickerInfo UI 레이아웃 Devlog

> **작성일**: 2026-01-13 13:20
> **관련 계획서**: [14-004_tickerinfo_ui_layout.md](../../Plan/bugfix/14-004_tickerinfo_ui_layout.md)

## 진행 현황

| Step | 상태 | 완료 시간 |
|------|------|----------|
| Step 1 | ✅ 완료 | 13:20 |
| Step 2 | ✅ 완료 | 13:25 |
| Step 3 | ✅ 완료 | 13:28 |
| Step 4 | ✅ 완료 | 13:32 |

---

## Step 1: Related Tickers 레이아웃 개선

### 변경 사항

- `frontend/gui/ticker_info_window.py`:
  - **신규 클래스 `RelatedTickersGrid`**: 4열 그리드로 관련 종목 표시
    - `GRID_COLUMNS = 4`로 4열 고정
    - 각 티커는 클릭 가능한 스타일의 라벨로 표시
    - 최대 12개까지 표시
  - **`_create_column3_news()` 순서 변경**: News → Related (기존: Related → News)
  - **`_update_ui()` 연동**: `_related_grid.set_tickers()` 호출로 변경

### 검증 결과
- ruff check: ✅ All checks passed!

---

## Step 2: 창 크기 조절 및 스크롤 추가

### 변경 사항

- `_setup_ui()`:
  - **`QSizeGrip` 추가**: Frameless 창 우하단에 리사이즈 그립 배치
  - 투명 배경으로 자연스러운 UI

- `_setup_3column_body()`:
  - **`QScrollArea`로 3-column body 래핑**
  - 가로 스크롤 비활성화, 세로 스크롤 필요시만 표시
  - 스크롤바 스타일 커스터마이징 (8px width, 투명 배경)

### 검증 결과
- ruff check: ✅ All checks passed!

---

## Step 3: Profile 카드 동적 크기 적용

### 변경 사항

- `DetailTable.set_data()`:
  - **`val_label.setSizePolicy(Expanding, Minimum)`**: 콘텐츠에 맞게 높이 자동 조절
  - **`val_label.setMinimumHeight(0)`**: 최소 높이 제한 해제
  - **`self._grid.setRowStretch(row, 0)`**: 행 stretch 비활성화

### 검증 결과
- ruff check: ✅ All checks passed!

---

## Step 4: 미표시 데이터 UI 추가

### 변경 사항

- `_create_column2_tabs()`:
  - **`_splits_table` 추가** (Dividends 아래, Float 위)

- `_update_ui()`:
  - **Splits 데이터 바인딩**: `info.splits` → `_splits_table`
  - Split 정보: 날짜, 비율 (`split_from:split_to`)

### 검증 결과
- ruff check: ✅ All checks passed!

---

## 전체 검증 결과

- [x] `ruff check frontend/gui/ticker_info_window.py` 통과
- [ ] GUI 수동 테스트 (진행 예정)

---

## 다음 단계

`/IMP-verification` 워크플로우 실행
