# [09-009] Ticker Selection Event Bus 구현 계획서

> **작성일**: 2026-01-13 | **예상**: 7-8h

## 1. 목표

### 1.1 Primary Goal
- **Ticker Selection Event Bus**: 티커 선택을 중앙화된 이벤트 버스로 통합
- **Source of Truth**: Backend `TradingContext`가 활성 티커 상태 관리
- **Optimistic Update**: Frontend 즉시 UI 반응 (0ms) + Backend 비동기 동기화

### 1.2 Secondary Goal
- **TickerSearchBar**: Top Panel에 티커 검색/자동완성 위젯 추가
- 현재 티커 표시 + 수동 입력 + 히스토리 드롭다운 + 자동완성

---

## 2. 레이어 체크

- [x] 레이어 규칙 위반 없음
  - `backend.core.trading_context` → Backend Core Layer (신규)
  - `backend.api.websocket` → API Layer에서 Core 호출 (허용)
  - `frontend.gui.widgets` → Frontend GUI (Backend와 분리)
- [x] 순환 의존성 없음
  - `TradingContext`는 독립 모듈, 다른 서비스 import 없음
- [x] DI Container 등록 필요: **예**
  - `trading_context = providers.Singleton(_create_trading_context)`

---

## 3. 기존 솔루션 검색 결과

| 솔루션 | 출처 | 채택 여부 | 사유 |
|--------|------|----------|------|
| PyQt6 `QComboBox` + `QCompleter` | Qt 공식 문서 | ✅ 채택 | 네이티브 자동완성 지원, 커스터마이징 용이 |
| Custom Autocomplete Widget | 직접 구현 | ❌ 미채택 | `QCompleter` 사용 시 불필요 |

**선택**: `QComboBox(editable=True)` + `QCompleter`로 자동완성 구현

---

## 4. 변경 파일

### 4.1 Backend (신규/수정)

| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
| `backend/core/trading_context.py` | **NEW** | ~80 |
| `backend/container.py` | MODIFY | +15 |
| `backend/api/routes/websocket.py` | MODIFY | +30 |

### 4.2 Frontend (신규/수정)

| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
| `frontend/gui/widgets/ticker_search_bar.py` | **NEW** | ~200 |
| `frontend/gui/state/dashboard_state.py` | MODIFY | +40 |
| `frontend/gui/control_panel.py` | MODIFY | +20 |
| `frontend/gui/dashboard.py` | MODIFY | +30 |
| `frontend/gui/panels/chart_panel.py` | MODIFY | +15 |
| `frontend/gui/ticker_info_window.py` | MODIFY | +10 |

---

## 5. 실행 단계

### Phase 1: Backend 인프라 (예상 2h)

#### Step 1.1: TradingContext 클래스 생성
```python
# backend/core/trading_context.py
class TradingContext:
    """활성 티커 컨텍스트 관리 (Source of Truth)"""
    
    def __init__(self):
        self._active_ticker: str | None = None
        self._subscribers: list[Callable] = []
    
    def set_active_ticker(self, ticker: str, source: str = "unknown"):
        if self._active_ticker == ticker:
            return
        self._active_ticker = ticker
        for callback in self._subscribers:
            callback(ticker, source)
    
    def subscribe(self, callback: Callable[[str, str], None]):
        self._subscribers.append(callback)
```

#### Step 1.2: DI Container 등록
```python
# backend/container.py
trading_context = providers.Singleton(_create_trading_context)
```

#### Step 1.3: WebSocket 핸들러 추가
```python
# backend/api/routes/websocket.py
# 새 메시지 타입: SET_ACTIVE_TICKER
# 응답: ACTIVE_TICKER_CHANGED 브로드캐스트
```

---

### Phase 2: Frontend Event Bus (예상 1h)

#### Step 2.1: DashboardState 확장
```python
# frontend/gui/state/dashboard_state.py
class DashboardState(QObject):
    ticker_changed = pyqtSignal(str, str)  # (ticker, source)
    
    class TickerSource:
        WATCHLIST = "watchlist"
        SEARCH = "search"
        # ...
    
    def select_ticker(self, ticker: str, source: str):
        # Optimistic Update: 즉시 로컬 + 비동기 Backend 동기화
        self._current_ticker = ticker
        self.ticker_changed.emit(ticker, source)
        if self._ws:
            self._ws.send({"type": "SET_ACTIVE_TICKER", ...})
```

---

### Phase 3: 출력점 마이그레이션 (예상 1h)

#### Step 3.1: TickerInfoWindow
```python
# ticker_info_window.py
def connect_to_state(self, state: DashboardState):
    state.ticker_changed.connect(self.on_ticker_changed)
```

#### Step 3.2: ChartPanel
```python
# chart_panel.py
state.ticker_changed.connect(self._on_ticker_changed)
```

---

### Phase 4: 진입점 마이그레이션 (예상 1h)

#### Step 4.1: Watchlist 클릭
```python
# dashboard.py: _on_watchlist_table_clicked
# 변경 전: self._current_selected_ticker = ticker
# 변경 후: self._state.select_ticker(ticker, TickerSource.WATCHLIST)
```

#### Step 4.2: Tier2 클릭
```python
# dashboard.py: _on_tier2_table_clicked
# 변경 후: self._state.select_ticker(ticker, TickerSource.TIER2)
```

#### Step 4.3: 중복 상태 제거
- `_current_selected_ticker` → 제거
- `_current_chart_ticker` → `_state.current_ticker`로 통합

---

### Phase 5: TickerSearchBar 위젯 (예상 2h)

#### Step 5.1: 위젯 생성
```python
# frontend/gui/widgets/ticker_search_bar.py
from PyQt6.QtWidgets import QComboBox, QCompleter

class TickerSearchBar(QWidget):
    ticker_selected = pyqtSignal(str)
    
    def _init_ui(self):
        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.completer = QCompleter(self._ticker_list)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.combo.setCompleter(self.completer)
```

#### Step 5.2: ControlPanel 통합
```python
# control_panel.py
self.ticker_search = TickerSearchBar(state=self._state)
layout.addWidget(self.ticker_search)
```

---

### Phase 6: Backend 서비스 연동 (Optional, 예상 1h)

#### Step 6.1: TickerInfoService 구독
```python
# ticker_info_service.py (향후)
def __init__(self, trading_context: TradingContext):
    trading_context.subscribe(self._on_ticker_changed)
```

---

## 6. 검증

### 자동 검증
- [ ] `ruff format --check .` 통과
- [ ] `ruff check .` 통과
- [ ] `lint-imports` 통과 (순환 의존성 없음)

### 수동 검증
- [ ] Watchlist 클릭 → 차트/Info 창 동시 업데이트
- [ ] TickerSearchBar 입력 → 자동완성 동작
- [ ] 히스토리 드롭다운 동작
- [ ] Backend 연동 시 WebSocket 메시지 확인

---

## 7. 의존성

| 의존 항목 | 상태 |
|----------|------|
| `DashboardState` | ✅ 존재 (`frontend/gui/state/`) |
| `WSAdapter` | ✅ 존재 (`frontend/services/`) |
| `WebSocket routes` | ✅ 존재 (`backend/api/routes/websocket.py`) |
| `container.py` | ✅ 존재 |

---

## 8. 리스크 및 대응

| 리스크 | 확률 | 대응 |
|--------|------|------|
| 기존 `_current_chart_ticker` 참조 누락 | 중 | grep 검색으로 모든 참조 확인 |
| WebSocket 메시지 형식 불일치 | 낮 | 기존 패턴 따름 (`type` + `data`) |
| QCompleter 성능 (대량 티커) | 낮 | 필터링 후 상위 10개만 표시 |

---

## 9. 관련 문서

- **설계 문서**: [09-009_ticker_selection_event_bus.md](../refactor/09-009_ticker_selection_event_bus.md)
- **아키텍처**: `.agent/Ref/archt.md`
- **리팩토링 정책**: `docs/Plan/refactor/REFACTORING.md`

---

> ⚠️ **주의**: 사용자 승인 후 `/IMP-execution` 워크플로우로 구현 진행
