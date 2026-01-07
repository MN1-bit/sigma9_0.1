# 02-002: Tier1 Watchlist 실시간 change% 업데이트

## 문제 설명
Tier1 Watchlist의 `change%` 컬럼이 실시간으로 업데이트되지 않음.

## 근본 원인
현재 아키텍처는 **Tier2 종목만** T 채널(틱)을 구독하여 실시간 가격을 수신함.
Tier1 종목은 Gainers API 폴링(1초)에 의존하지만, 이는 **Top 21개 급등주만** 반환하므로 Watchlist 전체 종목을 커버하지 못함.

## 제안된 해결책: Massive A 채널 (1초봉) 구독

### 왜 A 채널인가?

| 채널 | 설명 | 초당 메시지 | 적합성 |
|------|------|-----------|--------|
| **T** | 틱 (매 체결) | 수십~수백/종목 | ⚠️ 부하 높음 |
| **AM** | 1분봉 | 1/분/종목 | ❌ 너무 느림 |
| **A** | **1초봉** | **1/초/종목** | ✅ 최적 |

Tier1 종목 50개 × 1메시지/초 = **50 메시지/초** (가벼움)

---

## 구현 계획

### Phase 1: SubscriptionManager 확장

#### [MODIFY] [subscription_manager.py](file:///d:/Codes/Sigma9-0.1/backend/core/subscription_manager.py)

**변경 1**: Tier1용 A 채널 구독 메서드 추가

```python
async def subscribe_tier1_second_bars(self, tickers: List[str]):
    """
    Tier1 종목 1초봉(A 채널) 구독
    
    change% 실시간 업데이트를 위해 모든 Tier1 종목에 1초봉 구독
    
    Args:
        tickers: Tier1 종목 목록
    """
    if not self.massive_ws or not self.massive_ws.is_connected:
        return
    
    from backend.data.massive_ws_client import Channel
    
    if not hasattr(self, '_second_bar_subscribed'):
        self._second_bar_subscribed: Set[str] = set()
    
    new_tickers = [t for t in tickers if t not in self._second_bar_subscribed]
    if new_tickers:
        await self.massive_ws.subscribe(new_tickers, Channel.A)
        self._second_bar_subscribed.update(new_tickers)
        logger.info(f"📋 Second bar (A) subscribed: {len(new_tickers)} tickers")
```

**변경 2**: `sync_watchlist()` 호출 시 A 채널 자동 구독

```python
async def sync_watchlist(self, watchlist: List[str]):
    # ... 기존 AM 채널 동기화 로직 ...
    
    # [NEW] Tier1 종목 A 채널 구독 (change% 실시간 업데이트)
    await self.subscribe_tier1_second_bars(list(watchlist_set))
```

---

### Phase 2: 1초봉 수신 및 가격 캐시 업데이트

#### [MODIFY] [massive_ws_client.py](file:///d:/Codes/Sigma9-0.1/backend/data/massive_ws_client.py)

**변경**: A 채널 메시지 파싱 추가 (이미 T, AM이 있으므로 A 추가)

```python
elif ev == "A":
    # Aggregate Second (1초봉)
    bar = {
        "type": "second_bar",
        "ticker": data.get("sym"),
        "timeframe": "1s",
        "time": data.get("s", 0) / 1000,
        "open": data.get("o"),
        "high": data.get("h"),
        "low": data.get("l"),
        "close": data.get("c"),
        "volume": data.get("v"),
        "vwap": data.get("a"),
    }
    
    if self.on_second_bar:
        self.on_second_bar(bar)
    
    return bar
```

---

### Phase 3: RealtimeScanner 가격 캐시 연동

#### [MODIFY] [realtime_scanner.py](file:///d:/Codes/Sigma9-0.1/backend/core/realtime_scanner.py)

**변경**: A 채널 콜백 등록 및 `_latest_prices` 업데이트

```python
# start() 메서드에서:
if massive_ws:
    massive_ws.on_second_bar = self._on_second_bar_received

def _on_second_bar_received(self, bar: dict):
    """1초봉 수신 시 가격 캐시 업데이트"""
    ticker = bar.get("ticker")
    price = bar.get("close", 0)
    volume = bar.get("volume", 0)
    
    if ticker and price > 0:
        self._latest_prices[ticker] = (price, volume)
```

이미 `_periodic_watchlist_broadcast()`에서 `_latest_prices`를 사용해 `change_pct`를 재계산하므로, 자동으로 GUI에 반영됨.

---

### Phase 4: Frontend 업데이트

> [!NOTE]
> Frontend 수정 불필요. 현재 `_update_watchlist_panel()`이 이미 `change_pct` 값을 수신하여 표시 중.

---

## 예상 효과

| 항목 | 수정 전 | 수정 후 |
|------|--------|--------|
| change% 업데이트 빈도 | Gainers에 있을 때만 (불확실) | **매 1초** |
| 커버리지 | Top 21 급등주만 | **Tier1 전체** |
| 추가 부하 | - | 50 메시지/초 (미미) |

---

## 검증 계획

### 자동 테스트
- 없음 (실시간 WebSocket 테스트는 Mocking 필요)

### 수동 테스트
1. 애플리케이션 실행: `python -m frontend.main`
2. 백엔드 연결 후 Watchlist에 종목이 표시될 때까지 대기
3. Tier1 종목의 `change%` 컬럼이 1초마다 변경되는지 확인
4. 로그에서 `📋 Second bar (A) subscribed` 메시지 확인

---

## 대안 고려사항

### 왜 T 채널(틱)을 사용하지 않는가?

T 채널은 매 체결마다 메시지가 발생하여:
- NVDA 같은 고거래량 종목: **초당 수백 틱**
- 50개 종목 × 100틱/초 = **5,000 메시지/초**

A 채널(1초봉)은 정확히 **50 메시지/초**로 99% 적은 부하.

### Gainers API만으로 충분하지 않은 이유

Gainers API는 **Top 21개 급등주만** 반환.
Watchlist에 추가된 후 순위가 떨어지면 price 업데이트가 중단됨.
