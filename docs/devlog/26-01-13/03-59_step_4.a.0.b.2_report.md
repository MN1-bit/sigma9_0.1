# Step 4.A.0.b.2: 전략 모듈 (Seismograph) 연결

> **작성일**: 2026-01-02  
> **버전**: 1.0

---

## 📋 개요

**SeismographStrategy.on_tick()** → **TickDispatcher** 연결

```
Massive T (틱) → TickDispatcher.dispatch()
                      │
                      ▼
              SeismographStrategy.on_tick()
                      │
                      ▼
              Ignition Score 실시간 계산
```

---

## ✅ 구현 완료

### 기존 메서드 확인

`SeismographStrategy.on_tick()` (lines 1198-1339) 이미 존재:
- 틱 버퍼에 데이터 저장
- Ignition Score 재계산
- Signal 반환 (BUY/HOLD/None)

### 수정된 파일

| 파일 | 변경 |
|------|------|
| `server.py` | `TickDispatcher` 생성 및 전략 콜백 등록 |
| `server.py` (AppState) | `tick_dispatcher` 필드 추가 |

---

## 🔗 연결 코드

```python
# server.py lifespan()
app_state.tick_dispatcher = TickDispatcher()

if app_state.strategy_loader:
    active_strategy = app_state.strategy_loader.get_active_strategy()
    if active_strategy and hasattr(active_strategy, 'on_tick'):
        def strategy_tick_handler(tick: dict):
            active_strategy.on_tick(
                ticker=tick.get("ticker"),
                price=tick.get("price"),
                volume=tick.get("size"),
                timestamp=tick.get("time")
            )
        app_state.tick_dispatcher.register("strategy", strategy_tick_handler)
```

---

## 🔗 다음 단계

- **4.A.0.b.3**: Trading Engine `on_tick` 연결
