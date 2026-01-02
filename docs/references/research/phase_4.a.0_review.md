# Phase 4.A.0 실시간 데이터 파이프라인 검토

> **작성일**: 2026-01-02  
> **버전**: 1.0

---

## 🔴 CRITICAL: 치명적 결함

### 1. listen() 루프 미실행

**문제**: `MassiveWebSocketClient.listen()`이 호출되지 않음

```python
# server.py - 현재 코드
async def start_massive_streaming():
    if await app_state.massive_ws.connect():
        logger.info("✅ Connected")
        # listen()이 호출되지 않음!
```

**영향**: 
- WebSocket 연결 성공해도 메시지 수신 안됨
- on_bar/on_tick 콜백이 절대 호출되지 않음
- **전체 데이터 파이프라인 작동 불가**

**수정 필요**:
```python
async def start_massive_streaming():
    if await app_state.massive_ws.connect():
        async for _ in app_state.massive_ws.listen():
            pass  # 콜백이 데이터 처리
```

---

## 🟡 MINOR: 경미한 결함

### 2. backend_client.py 문자열 깨짐

**위치**: Line 104-105

```python
bar_received = pyqtSignal(dict)  # Phase 4.A.0: {"
": str, "timeframe": str, "bar": dict}
```

**수정**: 한 줄로 정리 필요

---

### 3. AppState.trailing_stop 미선언

**문제**: server.py에서 `app_state.trailing_stop` 할당하지만 AppState 클래스에 필드 없음

**수정**: AppState에 `self.trailing_stop = None` 추가

---

### 4. 초기 구독 트리거 없음

**문제**: connect() 후 subscribe() 호출 없음

**현재 흐름**:
1. connect() ✅
2. listen() 시작 (수정 후)
3. subscribe() 호출 ❌ - 구독 없이 listen

**수정**: 
- Watchlist 로드 시 자동 구독
- 또는 connect 직후 sync_watchlist() 호출

---

### 5. TickDispatcher TYPE_CHECKING 누락

**위치**: tick_broadcaster.py Line 36-38

```python
if TYPE_CHECKING:
    from backend.data.massive_ws_client import MassiveWebSocketClient
    from backend.api.websocket import ConnectionManager
    # TickDispatcher import 누락
```

---

## ✅ 정상 동작 확인된 부분

| 컴포넌트 | 상태 |
|----------|------|
| MassiveWebSocketClient 구조 | ✅ |
| TickDispatcher 등록/배포 | ✅ |
| TickBroadcaster 콜백 체인 | ✅ |
| SubscriptionManager T채널 | ✅ |
| GUI tick_received 연결 | ✅ |

---

## 📝 수정 우선순위

1. **[P0] listen() 루프 추가** - 없으면 작동 안함
2. **[P1] 초기 구독 로직 추가**
3. **[P2] backend_client.py 문자열 수정**
4. **[P2] AppState 필드 추가**
5. **[P3] TYPE_CHECKING 정리**
