# Step 4.A.0.b.1: TickDispatcher 생성

> **작성일**: 2026-01-02  
> **버전**: 1.0

---

## 📋 개요

**TickDispatcher** 생성 - 틱 데이터 중앙 배포자

```
Massive T (틱) → TickBroadcaster._on_tick()
                      │
                      ▼
               TickDispatcher.dispatch()
                      │
    ┌─────────────────┼─────────────────┐
    ▼                 ▼                 ▼
Strategy        TradingEngine     TrailingStop
(on_tick)         (on_tick)     (on_price_update)
```

---

## ✅ 구현 완료

### 신규 파일

| 파일 | 설명 |
|------|------|
| `backend/core/tick_dispatcher.py` | 틱 중앙 배포자 |

**주요 메서드:**
- `register(name, callback, tickers)` - 구독자 등록 (종목 필터 지원)
- `unregister(name)` - 구독 해제
- `dispatch(tick)` - 모든 구독자에게 틱 배포
- `update_filter(name, tickers)` - 종목 필터 업데이트

### 수정된 파일

| 파일 | 변경 |
|------|------|
| `tick_broadcaster.py` | `tick_dispatcher` 파라미터 추가, `dispatch()` 호출 |

---

## 🔗 다음 단계

- **4.A.0.b.2**: 전략 모듈 (Seismograph) `on_tick` 연결
