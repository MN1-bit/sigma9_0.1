# Step 4.A.0.d Report: 틱 기반 실시간 캔들 업데이트

> **작업일**: 2026-01-02  
> **상태**: ✅ COMPLETED

---

## 📋 목표

현재 조회 중인 차트의 마지막 캔들이 틱 데이터에 따라 실시간으로 "출렁이는" 효과를 구현합니다.

---

## 🔧 구현 내용

### 1. `pyqtgraph_chart.py` - `update_current_candle()` 추가

```python
def update_current_candle(self, price: float, volume: int = 0):
    """틱 가격으로 현재 캔들 업데이트 (출렁이는 효과)"""
    if not self._candle_data or price <= 0:
        return
    
    last = self._candle_data[-1]
    last["high"] = max(last["high"], price)
    last["low"] = min(last["low"], price)
    last["close"] = price
    
    if self._candle_item:
        self._candle_item.update_bar(
            last["index"], last["open"], last["high"], last["low"], last["close"]
        )
```

---

### 2. `dashboard.py` - 틱 핸들러 + 300ms 스로틀링

| 항목 | 설명 |
|------|------|
| `_current_chart_ticker` | 현재 차트에 표시된 종목 추적 |
| `_pending_tick` | 스로틀링 대기 중인 틱 데이터 |
| `_tick_throttle_timer` | 300ms QTimer (SingleShot) |
| `_on_tick_received()` | 틱 수신 핸들러 - 가격 캐시 + 차트 업데이트 예약 |
| `_apply_tick_to_chart()` | 타이머 만료 시 실제 차트 업데이트 |

---

## 📁 수정된 파일

| 파일 | 변경 |
|------|------|
| `frontend/gui/chart/pyqtgraph_chart.py` | `update_current_candle()` 메서드 추가 (Line 1014-1058) |
| `frontend/gui/dashboard.py` | 틱 핸들러 + 스로틀 타이머 추가 (Line 165-175, 1227-1279) |
| `docs/Plan/steps/development_steps.md` | Phase 4.A.0.d 완료 표시 |
| `docs/architecture/data_flow.md` | GUI Streaming (Tick→Chart) 항목 추가 |

---

## 📊 데이터 흐름

```
Massive WebSocket T.* (틱)
       │
       ▼
TickBroadcaster._on_tick()
       │
       ▼
ConnectionManager.broadcast_tick()
       │
       ▼
WsAdapter.tick_received (Signal)
       │
       ▼
BackendClient.tick_received (Signal)
       │
       ▼
Dashboard._on_tick_received()
       │
       ├─→ _price_cache[ticker] = price
       │
       └─→ if ticker == _current_chart_ticker:
               _pending_tick = {...}
               _tick_throttle_timer.start(300ms)
                      │
                      ▼ (300ms 후)
           _apply_tick_to_chart()
                      │
                      ▼
           chart_widget.update_current_candle(price)
                      │
                      ▼
           CandlestickItem.update_bar()
```

---

## ⚡ 성능 최적화

| 최적화 | 설명 |
|--------|------|
| **300ms 스로틀링** | 틱이 초당 수백건 와도 차트는 최대 3.3회/초만 업데이트 |
| **SingleShot 타이머** | 스로틀 기간 내 최신 틱만 적용 |
| **마지막 캔들만 갱신** | 전체 차트 리렌더 없이 해당 캔들만 업데이트 |

---

## 🐛 버그 수정: Race Condition 방지

**문제**: 차트 종목을 빠르게 전환할 때, 타이머 만료 시 이전 종목의 틱이 새 차트에 적용됨

**해결책**: `_pending_tick`에 티커 정보 포함 + 적용 시 검증

```python
# _on_tick_received
self._pending_tick = {"ticker": ticker, "price": price, "volume": volume}

# _apply_tick_to_chart
if self._pending_tick.get("ticker") == self._current_chart_ticker:
    self.chart_widget.update_current_candle(...)
```

---

## ✅ 완료 체크리스트

- [x] 4.A.0.d.1: `Dashboard._on_tick_received()` + 300ms 스로틀링
- [x] 4.A.0.d.2: `PyQtGraphChart.update_current_candle()` 
- [x] 4.A.0.d.3: `CandlestickItem.update_bar()` 활용 (기존 메서드)
