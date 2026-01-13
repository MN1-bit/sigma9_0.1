# 09-104: DashboardState 확장

> **작성일**: 2026-01-13 | **예상**: 45분  
> **상위 문서**: [09-009_ticker_selection_event_bus.md](./09-009_ticker_selection_event_bus.md)

---

## 목표

`DashboardState`에 Event Bus 기능 추가:
- `ticker_changed` 시그널
- `select_ticker()` 메서드 (Optimistic Update)
- `TickerSource` 상수

---

## 변경 파일

| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
| `frontend/gui/state/dashboard_state.py` | MODIFY | +40 |

---

## 구현 내용

```python
# frontend/gui/state/dashboard_state.py

from PyQt6.QtCore import QObject, pyqtSignal


class DashboardState(QObject):
    """Dashboard 중앙 상태 관리자"""
    
    # ═══════════════════════════════════════════════════════════════════
    # 📌 [09-009] Ticker Selection Event Bus
    # ═══════════════════════════════════════════════════════════════════
    
    # 티커 변경 시그널: (ticker, source)
    ticker_changed = pyqtSignal(str, str)
    
    class TickerSource:
        """티커 변경 출처 (디버깅/로깅용)"""
        WATCHLIST = "watchlist"
        TIER2 = "tier2"
        SEARCH = "search"
        CHART = "chart"
        EXTERNAL = "external"
        UNKNOWN = "unknown"
    
    def __init__(self, ws_adapter=None):
        super().__init__()
        self._ws = ws_adapter
        
        # 📌 [09-009] Ticker state
        self._current_ticker: str | None = None
        self._previous_ticker: str | None = None
    
    # ───────────────────────────────────────────────────────────────────
    # Ticker Selection Methods
    # ───────────────────────────────────────────────────────────────────
    
    @property
    def current_ticker(self) -> str | None:
        """현재 선택된 티커 (읽기 전용)"""
        return self._current_ticker
    
    def select_ticker(self, ticker: str, source: str = TickerSource.UNKNOWN) -> None:
        """
        티커 선택 (Optimistic Update 패턴)
        
        1. 즉시 로컬 상태 업데이트 → UI 즉각 반응
        2. Backend에 비동기 전송 → 상태 동기화
        
        Args:
            ticker: 선택할 티커 심볼
            source: 변경 출처 (TickerSource 참조)
        """
        if self._current_ticker == ticker:
            return  # 동일 티커면 무시
        
        self._previous_ticker = self._current_ticker
        self._current_ticker = ticker
        
        # 1. 📢 즉시 UI 업데이트 (Optimistic)
        self.ticker_changed.emit(ticker, source)
        
        # 2. 🌐 Backend 동기화 (비동기)
        if self._ws and hasattr(self._ws, 'send'):
            self._ws.send({
                "type": "SET_ACTIVE_TICKER",
                "ticker": ticker,
                "source": source
            })
    
    def _handle_active_ticker_changed(self, ticker: str, source: str) -> None:
        """
        Backend에서 ACTIVE_TICKER_CHANGED 수신 시 처리
        
        다른 클라이언트가 티커를 변경했을 때 동기화
        """
        if self._current_ticker != ticker:
            self._previous_ticker = self._current_ticker
            self._current_ticker = ticker
            self.ticker_changed.emit(ticker, source)
```

---

## WebSocket 메시지 처리 연결

`WSAdapter`에서 `ACTIVE_TICKER_CHANGED` 메시지 수신 시 `_handle_active_ticker_changed` 호출 필요:

```python
# ws_adapter.py 또는 dashboard.py에서
if msg.get("type") == "ACTIVE_TICKER_CHANGED":
    self._state._handle_active_ticker_changed(
        msg.get("ticker"), 
        msg.get("source")
    )
```

---

## 검증

- [ ] `DashboardState` 인스턴스화 성공
- [ ] `select_ticker("AAPL", TickerSource.WATCHLIST)` 호출 → 시그널 발행
- [ ] `ticker_changed` 시그널 연결 테스트

---

## 다음 단계

→ [09-105: 출력점 마이그레이션](./09-105_output_points.md)
