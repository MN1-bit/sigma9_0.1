# 09-106: 진입점 마이그레이션

> **작성일**: 2026-01-13 | **예상**: 45분  
> **상위 문서**: [09-009_ticker_selection_event_bus.md](./09-009_ticker_selection_event_bus.md)

---

## 목표

티커를 선택할 수 있는 모든 진입점을 `DashboardState.select_ticker()` 호출로 통일

---

## 변경 파일

| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
| `frontend/gui/dashboard.py` | MODIFY | +30 |

---

## 현재 코드 vs 변경 후

### 1. Watchlist 클릭

```python
# ❌ 변경 전 (현재)
def _on_watchlist_table_clicked(self, proxy_index):
    ticker = self._get_ticker_from_index(proxy_index)
    self._current_selected_ticker = ticker  # 자체 상태 관리
    self._load_chart_for_ticker(ticker)     # 직접 호출

# ✅ 변경 후
def _on_watchlist_table_clicked(self, proxy_index):
    source_index = self.watchlist_proxy.mapToSource(proxy_index)
    ticker_index = self.watchlist_model.index(source_index.row(), 0)
    ticker = self.watchlist_model.data(ticker_index)
    
    if ticker:
        self.log(f"[ACTION] Watchlist selected: {ticker}")
        # 📌 [09-009] Event Bus로 통합
        self._state.select_ticker(ticker, DashboardState.TickerSource.WATCHLIST)
```

### 2. Tier2 Hot Zone 클릭

```python
# ❌ 변경 전 (현재)
def _on_tier2_item_clicked(self, ticker: str):
    self._current_selected_ticker = ticker
    self._load_chart_for_ticker(ticker)

# ✅ 변경 후
def _on_tier2_item_clicked(self, ticker: str):
    self.log(f"[ACTION] Tier2 selected: {ticker}")
    # 📌 [09-009] Event Bus로 통합
    self._state.select_ticker(ticker, DashboardState.TickerSource.TIER2)
```

---

## 제거해야 할 중복 상태

### 1단계: 주석 처리 (안전)

```python
# dashboard.py

def __init__(self):
    # ...
    # 📌 [09-009] 아래 변수들은 _state.current_ticker로 대체됨
    # self._current_selected_ticker: str | None = None
    # self._current_chart_ticker: str | None = None
```

### 2단계: 참조 검색 및 수정

```bash
# 프로젝트에서 참조 검색
grep -rn "_current_selected_ticker" frontend/
grep -rn "_current_chart_ticker" frontend/
```

### 3단계: 대체

| 기존 참조 | 대체 |
|----------|------|
| `self._current_selected_ticker` | `self._state.current_ticker` |
| `self._current_chart_ticker` | `self._state.current_ticker` |

---

## 주의사항

1. **_load_chart_for_ticker() 제거 여부**:
   - 09-105에서 ChartPanel이 `ticker_changed` 구독하면, 직접 호출 불필요
   - 하지만 점진적 마이그레이션을 위해 당장은 유지 가능

2. **로그 메시지 유지**:
   - `[ACTION]` 로그는 그대로 유지하여 디버깅 편의성 확보

---

## 검증

- [ ] Watchlist 클릭 → `select_ticker()` 호출 → 차트/Info 업데이트
- [ ] Tier2 클릭 → `select_ticker()` 호출 → 차트/Info 업데이트
- [ ] 로그에서 `[TradingContext]` 메시지 확인 (Backend 동기화)

---

## 다음 단계

→ [09-107: TickerSearchBar 위젯](./09-107_ticker_search_bar.md)
