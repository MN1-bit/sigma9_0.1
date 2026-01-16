# 14-002: Info Panel 레이아웃 재설계 Devlog

> **작성일**: 2026-01-13
> **계획서**: [14-002_info_panel_layout_redesign.md](../../Plan/bugfix/14-002_info_panel_layout_redesign.md)

## 진행 현황

| Step | 상태 | 시간 |
|------|------|------|
| Step 1: Header 리팩토링 | ✅ | 09:10 |
| Step 2: 3-Column 레이아웃 | ✅ | 09:12 |
| Step 3: Column 1 프로필 | ✅ | 09:12 |
| Step 4: Column 2 QTabWidget | ✅ | 09:12 |
| Step 5: Column 3 뉴스 | ✅ | 09:12 |
| _update_ui 데이터 바인딩 | ✅ | 09:14 |

---

## 변경 사항 요약

### `frontend/gui/ticker_info_window.py`

1. **QTabWidget import 추가** (PySide6 & PyQt6)

2. **`_setup_ui()` 리팩토링**
   - 기존 카드 그리드 제거
   - 새 헤더 + 3-Column 본문 호출

3. **새 메서드 추가**
   - `_setup_header_v2()`: 거래소, 가격, 등락, 시총 표시
   - `_setup_3column_body()`: 3-Column 레이아웃 (200px / stretch / 220px)
   - `_create_column1_profile()`: 회사 설명 + Profile 테이블
   - `_create_column2_tabs()`: QTabWidget (재무/배당/공시/유동성)
   - `_create_column3_news()`: Related + News

4. **`_update_ui()` 리팩토링**
   - 새 헤더 라벨에 데이터 바인딩 (`_exchange_label`, `_price_label`, `_change_label`, `_mcap_label`)
   - 프로필 설명 라벨 바인딩 (`_desc_label`)
   - 배당 정보 → `_dividends_table`
   - Float + Short 정보 → `_float_table`
   - 기존 카드 참조 제거 (`_dividends_card`, `_splits_card`, 등)

5. **Unused import 제거**
   - QScrollArea, QGridLayout (ruff --fix)

---

## 검증 결과

| 항목 | 결과 |
|------|------|
| ruff check | ✅ All checks passed |

---

## 다음 단계

수동 테스트:
1. Info 창 열기 → 3-Column 레이아웃 확인
2. 탭 전환 (재무/배당/공시/유동성)
3. 헤더에 가격/등락/시총 표시 확인
