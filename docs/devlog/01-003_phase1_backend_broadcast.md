# Devlog 01-003: Watchlist Data Refresh Fix (Phase 1)

**작성일**: 2026-01-06  
**작업자**: AI Assistant  
**이슈**: `docs/Plan/bugfix/01-003_watchlist_data_refresh.md`

---

## Phase 1: Backend 주기적 브로드캐스트

### 변경 사항

#### `backend/core/realtime_scanner.py`

1. **`_latest_prices` 딕셔너리 추가**
   - ticker → (price, volume) 형태의 실시간 가격 캐시
   - `_poll_gainers()` 에서 Gainers API 응답마다 업데이트

2. **`_periodic_watchlist_broadcast()` 메서드 구현**
   - 1초마다 전체 Watchlist 로드
   - `_latest_prices` 캐시를 사용하여 `dollar_volume` 재계산 (Hydration)
   - WebSocket으로 hydrated된 Watchlist 브로드캐스트

3. **태스크 관리**
   - `start()`: `_broadcast_task` 시작
   - `stop()`: `_broadcast_task` 정상 종료

### 기술적 결정

- **Hydration 전략**: Watchlist 저장소의 데이터와 실시간 가격 캐시를 결합하여 항상 최신 `dollar_volume` 계산
- **로깅**: DEBUG 레벨로 주기적 브로드캐스트 상태 기록 (hydrated 종목 수 포함)

### 코드 변경

```python
# 1초마다 전체 Watchlist를 GUI에 브로드캐스트
async def _periodic_watchlist_broadcast(self) -> None:
    while self._running:
        await asyncio.sleep(1.0)
        
        watchlist = load_watchlist()
        
        # 실시간 가격/볼륨으로 dollar_volume 재계산 (Hydration)
        for item in watchlist:
            ticker = item.get("ticker")
            if ticker in self._latest_prices:
                price, volume = self._latest_prices[ticker]
                item["dollar_volume"] = price * volume
        
        await self.ws_manager.broadcast_watchlist(watchlist)
```

---

## 다음 단계

Phase 2: Frontend 경고 표시 구현
- `dashboard.py`의 `_update_watchlist_panel()`에서 데이터 누락 시 ⚠️ 아이콘 표시
