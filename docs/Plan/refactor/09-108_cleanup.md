# 09-108: 정리 및 검증

> **작성일**: 2026-01-13 | **예상**: 30분  
> **상위 문서**: [09-009_ticker_selection_event_bus.md](./09-009_ticker_selection_event_bus.md)

---

## 목표

- 불필요한 중복 코드/상태 제거
- 전체 통합 검증
- 문서 업데이트

---

## 정리 작업

### 1. 중복 상태 변수 제거

```bash
# 참조 검색
grep -rn "_current_selected_ticker" frontend/
grep -rn "_current_chart_ticker" frontend/
```

| 변수 | 대체 | 파일 |
|------|------|------|
| `_current_selected_ticker` | `_state.current_ticker` | `dashboard.py` |
| `_current_chart_ticker` | `_state.current_ticker` | `dashboard.py` |

### 2. 불필요한 직접 호출 제거

```python
# 제거 대상 (Event Bus가 대체)
# self._load_chart_for_ticker(ticker)  # ChartPanel이 구독
# self._ticker_info_window.load_ticker(ticker)  # TickerInfoWindow가 구독
```

### 3. _load_chart_for_ticker() 메서드

- **당장 제거하지 않음**: 초기 로드나 수동 호출에 필요할 수 있음
- **Deprecated 표시**:

```python
def _load_chart_for_ticker(self, ticker: str):
    """
    @deprecated [09-009] Use _state.select_ticker() instead.
    ChartPanel now subscribes to ticker_changed signal.
    """
    self.log(f"[WARN] _load_chart_for_ticker called directly. Use select_ticker().")
    self._state.select_ticker(ticker, DashboardState.TickerSource.CHART)
```

---

## 통합 검증 체크리스트

### Backend

- [ ] `python -c "from backend.container import container; ctx = container.trading_context(); ctx.set_active_ticker('AAPL', 'test'); print(ctx.active_ticker)"`
- [ ] WebSocket 메시지 `SET_ACTIVE_TICKER` 처리 확인

### Frontend

- [ ] 앱 시작 → 정상 렌더링
- [ ] Watchlist 클릭 → 차트 업데이트 + Info 창 업데이트 (열려있을 때)
- [ ] Tier2 클릭 → 차트 업데이트
- [ ] TickerSearchBar 입력 → 차트 업데이트
- [ ] 여러 출력점 동시 업데이트 확인

### 코드 품질

- [ ] `ruff check frontend/ backend/`
- [ ] `ruff format --check frontend/ backend/`
- [ ] `lint-imports` 통과

---

## 문서 업데이트

### 1. 아키텍처 문서 반영

`.agent/Ref/archt.md` 업데이트:

```markdown
## 5. 아키텍처 패턴

### 5.3 Ticker Selection Event Bus [09-009]

\`\`\`
[진입점]              [Event Bus]              [출력점]
Watchlist ──────┐                      ┌────► ChartPanel
Tier2 ──────────┼──► DashboardState ───┼────► TickerInfoWindow
SearchBar ──────┘    (ticker_changed)  └────► (향후 추가)
                          │
                          ▼
                     TradingContext
                     (Backend SoT)
\`\`\`
```

### 2. KI 아티팩트 업데이트

`Frontend & UI Architecture` KI에 추가:
- Ticker Selection Event Bus 패턴 설명
- Optimistic Update 패턴 설명

---

## 완료 확인

- [ ] 모든 09-101 ~ 09-107 완료
- [ ] 통합 검증 통과
- [ ] 기존 기능 회귀 없음
- [ ] 코드 품질 검사 통과

---

## 향후 작업 (Optional)

| 작업 | 우선순위 | 설명 |
|------|----------|------|
| TickerInfoService 구독 | 낮음 | Backend에서 자동 푸시 |
| OrderService 연동 | 중간 | 주문 시 context.active_ticker 사용 |
| 티커 목록 API | 낮음 | 자동완성용 전체 티커 로드 |
| 히스토리 persistence | 낮음 | localStorage에 저장/복원 |

---

> ✅ **완료**: 09-009 Ticker Selection Event Bus 리팩토링 완료
