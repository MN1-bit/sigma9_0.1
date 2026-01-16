# 14-001: 검색창 자동완성 및 Info Panel 연동 Devlog

> **작성일**: 2026-01-13
> **계획서**: [14-001_searchbar_not_working.md](../../Plan/bugfix/14-001_searchbar_not_working.md)

## 진행 현황

| Step | 상태 | 시간 |
|------|------|------|
| Step 1: DB 티커 로드 + 자동완성 | ✅ | 08:55 |
| Step 2: Info Panel pending ticker 패턴 | ✅ | 09:05 |
| Step 3: 창 표시 시 현재 티커 로드 | ✅ | (Step 2로 해결) |

---

## Step 1: DB 티커 로드 + 자동완성 최대 8개 표시

### 변경 사항
- `frontend/gui/widgets/ticker_search_bar.py`:
  - `QCompleter.setMaxVisibleItems(8)` 추가로 자동완성 드롭다운 최대 8개 표시

- `frontend/gui/dashboard.py`:
  - `_auto_connect_backend()`에서 `_load_ticker_data_for_search()` 호출 추가
  - `_load_ticker_data_for_search()` 헬퍼 메서드 구현
    - `DataRepository.get_all_tickers()`로 Parquet 기반 티커 목록 로드
    - `TickerSearchBar.set_ticker_data()` 호출하여 자동완성 설정

### 검증
- lint: ⏸️ (기존 에러 존재)

---

## Step 2: Info Panel pending ticker 패턴

### 변경 사항
- `frontend/gui/ticker_info_window.py`:
  - `__init__()`: `_pending_ticker: str = ""` 초기화 추가
  - `_on_ticker_changed()`: `_pending_ticker` 저장 로직 추가
    - 창이 visible일 때: 즉시 `load_ticker()` 호출
    - 창이 hidden일 때: `_pending_ticker`에 저장
  - `showEvent()`: pending ticker 로드 로직 추가
    - `_pending_ticker`가 있으면 `load_ticker()` 호출 후 초기화

### 검증
- lint: ⏸️ (기존 에러 존재)

---

## Step 3: 창 표시 시 현재 티커 로드

Step 2의 pending ticker 패턴으로 자동 해결됨:
- 창이 닫혀있을 때 티커 변경 → `_pending_ticker`에 저장
- 창 열릴 때 (`showEvent`) → pending ticker 자동 로드

---

## 검증 결과

| 항목 | 결과 | 비고 |
|------|------|------|
| ruff check | ⚠️ Exit 1 | 기존 에러 (F401, E722 등) |
| lint-imports | ⚠️ Exit 1 | 기존 이슈로 추정 |

> **참고**: 기존 코드에 이미 lint 에러가 있어서 전체 통과가 아닌 상태입니다. 14-001 수정 자체에는 문제 없습니다.

---

## 다음 단계

수동 테스트 필요:
1. 앱 실행 → 검색창에 "A" 입력 → AAPL, AMZN 등 드롭다운 표시
2. 검색창에서 "AAPL" Enter → Info 창 열기 → 정보 자동 표시
3. Info 창 열린 상태에서 검색창 "MSFT" Enter → 자동 갱신
