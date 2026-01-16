# Phase 4.A.0: 실시간 데이터 파이프라인 구현

> **작성일**: 2026-01-02  
> **버전**: 1.0

---

## 📋 개요

**IBKR Tick → Massive WebSocket**으로 실시간 데이터 소스 전환.

Massive.com (구 Polygon.io)은 REST API뿐만 아니라 **WebSocket 스트리밍**을 지원하므로,
IBKR의 틱 구독 기능을 Massive WebSocket으로 완전 대체함.

---

## ✅ 구현 완료

### 신규 파일

| 파일 | 설명 |
|------|------|
| `backend/data/massive_ws_client.py` | Massive WebSocket 연결/인증/구독 |
| `backend/core/tick_broadcaster.py` | Massive → GUI WebSocket 브로드캐스트 |
| `backend/core/subscription_manager.py` | Watchlist ↔ 구독 동기화 |

### 수정된 파일

| 파일 | 변경 |
|------|------|
| `backend/server.py` | Massive WS 초기화 (AppState + lifespan) |
| `backend/api/websocket.py` | `BAR` MessageType 추가 |
| `frontend/services/ws_adapter.py` | `bar_received` Signal |
| `frontend/services/backend_client.py` | `bar_received` 연결 |
| `frontend/gui/chart/pyqtgraph_chart.py` | `update_realtime_bar()` |
| `frontend/gui/chart/candlestick_item.py` | `update_bar()`, `add_bar()` |
| `frontend/gui/dashboard.py` | `_on_bar_received` 핸들러 |

### 삭제된 파일/코드

| 항목 | 이유 |
|------|------|
| `backend/core/tick_aggregator.py` | Massive AM 채널이 1분봉 제공 |
| `IBKRConnector.price_update` Signal | Massive T 채널로 대체 |
| `IBKRConnector.subscribe_ticker()` | Massive WebSocket으로 대체 |
| `IBKRConnector.unsubscribe_ticker()` | 위와 동일 |
| `IBKRConnector._on_price_update()` | 위와 동일 |

---

## 🔧 Massive WebSocket 채널

| 채널 | 데이터 | 용도 |
|------|--------|------|
| `AM.*` | 1분봉 (Aggregate Minute) | 차트 실시간 갱신 |
| `T.*` | 틱 (Trades) | Trailing Stop, 가격 모니터링 |

---

## 📊 아키텍처

```
Massive WebSocket (wss://socket.massive.com/stocks)
       │
       │ AM.AAPL, T.AAPL, ...
       ▼
MassiveWebSocketClient (backend/data/)
       │
       │ on_bar / on_tick
       ▼
TickBroadcaster (backend/core/)
       │
       │ asyncio broadcast
       ▼
ConnectionManager.broadcast_bar() (backend/api/)
       │
       │ GUI WebSocket
       ▼
WsAdapter.bar_received (frontend/services/)
       │
       │ PyQt Signal
       ▼
Dashboard._on_bar_received → Chart.update_realtime_bar()
```

---

## 🧪 테스트

1. `.env` 설정:
```
MASSIVE_WS_ENABLED=true
MASSIVE_API_KEY=your_key
```

2. 서버 시작 후 로그 확인:
```
📡 Massive WebSocket initializing...
✅ Massive WebSocket connected
```

3. 장중 차트 실시간 갱신 확인

---

## 📝 IBKR 역할 변경

| 기능 | Before | After |
|------|--------|-------|
| 실시간 시세 | IBKR `price_update` | **Massive T 채널** |
| 1분봉 | IBKR → `tick_aggregator` | **Massive AM 채널** |
| 주문 실행 | IBKR `place_order` | IBKR (유지) |
| 포지션 조회 | IBKR `get_positions` | IBKR (유지) |

**IBKR는 이제 주문 실행 전용** (시세는 Massive 담당)
