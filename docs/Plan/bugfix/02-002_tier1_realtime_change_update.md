# 02-002: Tier1 Watchlist 실시간 change% 업데이트

## 문제 설명
Tier1 Watchlist의 `change%` 컬럼이 실시간으로 업데이트되지 않음.

## 근본 원인
`dashboard.py`의 `_on_tick_received()` 메서드에서 **Tier2 테이블만** 실시간 가격 업데이트를 수행함.
Tier1 Watchlist는 백엔드 브로드캐스트(1초 간격)에 의존하여 change%가 고정됨.

```python
# 현재 코드 (라인 1856~1868)
if hasattr(self, '_tier2_cache') and ticker in self._tier2_cache:
    self._tier2_cache[ticker].price = price
    # Tier2 테이블만 업데이트
```

## 제안된 해결책

### Phase 1: 가격 캐시 활용
1. `_on_tick_received()`에서 가격 캐시 업데이트 시, Tier1에도 해당 종목이 있는지 확인
2. `watchlist_model.update_price(ticker, new_price, new_change_pct)` 메서드 추가
3. `change_pct` 재계산: `(new_price - prev_close) / prev_close * 100`

### Phase 2: prev_close 저장
- `_watchlist_data` 캐시에 `prev_close` 필드 저장 (백엔드 브로드캐스트에서 수신)

---

## 수정 파일

### [MODIFY] [watchlist_model.py](file:///d:/Codes/Sigma9-0.1/frontend/gui/watchlist_model.py)

**추가**: `update_price()` 메서드
```python
def update_price(self, ticker: str, price: float, change_pct: float):
    """
    실시간 가격 및 change% 업데이트
    
    Args:
        ticker: 종목 코드
        price: 현재 가격
        change_pct: 등락율
    """
    if ticker not in self._ticker_to_row:
        return
    
    row = self._ticker_to_row[ticker]
    
    # Change % 컬럼 업데이트
    sign = "+" if change_pct >= 0 else ""
    change_item = QStandardItem(f"{sign}{change_pct:.1f}%")
    change_item.setData(change_pct, Qt.ItemDataRole.UserRole)
    if change_pct >= 0:
        change_item.setForeground(self._color_success)
    else:
        change_item.setForeground(self._color_danger)
    self.setItem(row, self.COL_CHANGE, change_item)
```

---

### [MODIFY] [dashboard.py](file:///d:/Codes/Sigma9-0.1/frontend/gui/dashboard.py)

**수정 1**: `_update_watchlist_panel()` (라인 1350~1393)
- `_prev_close_cache` 추가하여 prev_close 저장

```python
# _watchlist_data에 prev_close 추가 저장
if isinstance(item, WatchlistItem):
    prev_close = getattr(item, 'prev_close', 0) or getattr(item, 'last_close', 0)
else:
    prev_close = item.get("prev_close", 0) or item.get("last_close", 0)

self._watchlist_data[ticker] = {
    # ... 기존 필드 ...
    "prev_close": prev_close,
}
```

**수정 2**: `_on_tick_received()` (라인 1827~)
- Tier1 업데이트 로직 추가

```python
# [NEW] Tier1 Watchlist 실시간 업데이트
if hasattr(self, '_watchlist_data') and ticker in self._watchlist_data:
    data = self._watchlist_data[ticker]
    prev_close = data.get("prev_close", 0)
    if prev_close > 0:
        new_change_pct = (price - prev_close) / prev_close * 100
        self.watchlist_model.update_price(ticker, price, new_change_pct)
```

---

## 검증 계획

### 수동 테스트
1. 애플리케이션 실행: `python -m frontend.main`
2. 백엔드 연결 후 Watchlist에 종목이 표시될 때까지 대기
3. Watchlist에서 종목 선택 → 차트 로드
4. Tier2로 승격된 종목이 있다면, Tier1의 동일 종목 change%도 함께 업데이트되는지 확인
5. 확인 포인트: Tier1과 Tier2의 change%가 실시간으로 동기화됨

> [!NOTE]
> 이 기능은 Tier2에 승격된 종목에 대해 틱 구독이 활성화된 경우에만 동작합니다.
> Tier1 전용 종목은 여전히 1초 브로드캐스트에 의존합니다.
