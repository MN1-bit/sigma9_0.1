# 02-002: Tier1 Watchlist 실시간 change% 업데이트

> **작성일**: 2026-01-10 | **예상**: 2h

## 1. 목표

Tier1 Watchlist의 `change%` 컬럼이 실시간으로 업데이트되도록 개선.

### 문제 설명
- **현상**: Tier1 Watchlist의 `change%` 컬럼이 실시간 반영되지 않음
- **근본 원인**: 
  - Tier2 종목만 T 채널(틱) 구독
  - Tier1은 Gainers API 폴링(1초)에 의존하지만, **Top 21개 급등주만** 반환되므로 Tier1 전체 커버 불가

---

## 2. 제안된 해결책: A 채널(1초봉) 구독

| 채널 | 설명 | 초당 메시지 | 적합성 |
|------|------|-----------|--------|
| **T** | 틱 (매 체결) | 수십~수백/종목 | ⚠️ 부하 높음 |
| **AM** | 1분봉 | 1/분/종목 | ❌ 너무 느림 |
| **A** | **1초봉** | **1/초/종목** | ✅ 최적 |

Tier1 50개 × 1메시지/초 = **50 메시지/초** (가벼움)

---

## 3. 레이어 체크

- [ ] 레이어 규칙 위반 없음
- [ ] 순환 의존성 없음
- [ ] DI Container 등록 필요: 아니오 (기존 의존성 재사용)

---

## 4. 변경 파일

| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
| [massive_ws_client.py](file:///d:/Codes/Sigma9-0.1/backend/data/massive_ws_client.py) | MODIFY | +20줄 |
| [subscription_manager.py](file:///d:/Codes/Sigma9-0.1/backend/core/subscription_manager.py) | MODIFY | +25줄 |
| [realtime_scanner.py](file:///d:/Codes/Sigma9-0.1/backend/core/realtime_scanner.py) | MODIFY | +10줄 |

---

## 5. 실행 단계

### Step 1: A 채널 파싱 로직 추가

**파일**: `backend/data/massive_ws_client.py`

1. `on_second_bar` 콜백 속성 추가 (Line ~117)
2. `_parse_message()`에 A 채널 분기 추가 (Line ~340)
3. `_reconnect()`에 A 채널 복원 로직 추가 (Line ~362)

```python
# __init__에 추가
self.on_second_bar: Optional[Callable[[dict], None]] = None

# _parse_message에 A 채널 분기 추가
elif ev == "A":
    bar = {
        "type": "second_bar",
        "ticker": data.get("sym"),
        "timeframe": "1s",
        "time": data.get("s", 0) / 1000,
        "close": data.get("c"),
        "volume": data.get("v"),
    }
    if self.on_second_bar:
        self.on_second_bar(bar)
    return bar
```

---

### Step 2: SubscriptionManager Tier1 A 채널 구독

**파일**: `backend/core/subscription_manager.py`

1. `_second_bar_subscribed: Set[str]` 상태 추가
2. `subscribe_tier1_second_bars()` 메서드 추가
3. `sync_watchlist()`에서 자동 구독

```python
async def subscribe_tier1_second_bars(self, tickers: List[str]):
    """Tier1 종목 1초봉(A 채널) 구독"""
    from backend.data.massive_ws_client import Channel
    
    new_tickers = [t for t in tickers if t not in self._second_bar_subscribed]
    if new_tickers:
        await self.massive_ws.subscribe(new_tickers, Channel.A)
        self._second_bar_subscribed.update(new_tickers)
```

---

### Step 3: RealtimeScanner A 채널 콜백 연동

**파일**: `backend/core/realtime_scanner.py`

1. `start()` 메서드에서 A 채널 콜백 등록
2. `_on_second_bar_received()` 메서드 추가

```python
def _on_second_bar_received(self, bar: dict):
    """1초봉 수신 시 가격 캐시 업데이트"""
    ticker = bar.get("ticker")
    price = bar.get("close", 0)
    if ticker and price > 0:
        self._latest_prices[ticker] = (price, 0, int(time.time() * 1000))
```

---

## 6. 검증

### 수동 테스트
1. 서버 시작: `python -m backend`
2. 클라이언트 시작: `python -m frontend.main`
3. 확인:
   - [ ] 로그: `📡 Subscribed: A x N tickers`
   - [ ] Tier1 `change%` 1초마다 업데이트
   - [ ] Gainers 21위 밖 종목도 가격 반영

### 코드 검증
```bash
lint-imports
pydeps backend --only backend --show-cycles --no-output
```
