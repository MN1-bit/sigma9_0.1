# 09-103: WebSocket 핸들러 추가

> **작성일**: 2026-01-13 | **예상**: 30분  
> **상위 문서**: [09-009_ticker_selection_event_bus.md](./09-009_ticker_selection_event_bus.md)

---

## 목표

WebSocket에 `SET_ACTIVE_TICKER` 메시지 핸들러 추가  
변경 시 `ACTIVE_TICKER_CHANGED` 브로드캐스트

---

## 변경 파일

| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
| `backend/api/routes/websocket.py` | MODIFY | +30 |

---

## 구현 내용

### 1. 메시지 타입 추가

```python
# 새로운 메시지 타입
# Frontend → Backend
SET_ACTIVE_TICKER = {
    "type": "SET_ACTIVE_TICKER",
    "ticker": "AAPL",
    "source": "watchlist"  # 출처 추적용
}

# Backend → Frontend (브로드캐스트)
ACTIVE_TICKER_CHANGED = {
    "type": "ACTIVE_TICKER_CHANGED",
    "ticker": "AAPL",
    "source": "watchlist"
}
```

### 2. 핸들러 추가

```python
# backend/api/routes/websocket.py

async def handle_message(websocket: WebSocket, data: dict, ws_manager: WSManager):
    msg_type = data.get("type", "")
    
    # ... 기존 핸들러들 ...
    
    # 📌 NEW: SET_ACTIVE_TICKER [09-009]
    elif msg_type == "SET_ACTIVE_TICKER":
        await _handle_set_active_ticker(data, ws_manager)


async def _handle_set_active_ticker(data: dict, ws_manager: WSManager):
    """
    [09-009] 활성 티커 변경 요청 처리
    
    Frontend에서 티커 선택 → Backend TradingContext 업데이트 → 브로드캐스트
    """
    ticker = data.get("ticker")
    source = data.get("source", "unknown")
    
    if not ticker:
        logger.warning("[WS] SET_ACTIVE_TICKER: missing ticker")
        return
    
    # TradingContext 업데이트
    from backend.container import container
    trading_context = container.trading_context()
    changed = trading_context.set_active_ticker(ticker, source)
    
    if changed:
        # 모든 클라이언트에게 브로드캐스트
        await ws_manager.broadcast({
            "type": "ACTIVE_TICKER_CHANGED",
            "ticker": ticker,
            "source": source
        })
```

---

## 의존성

- `TradingContext` (09-101 완료 필요)
- DI Container 등록 (09-102 완료 필요)

---

## 검증

- [ ] WebSocket 연결 후 `SET_ACTIVE_TICKER` 메시지 전송
- [ ] 서버 로그에서 `[TradingContext] Active ticker changed` 확인
- [ ] 브로드캐스트 `ACTIVE_TICKER_CHANGED` 수신 확인

---

## 다음 단계

→ [09-104: DashboardState 확장](./09-104_dashboard_state.md)
