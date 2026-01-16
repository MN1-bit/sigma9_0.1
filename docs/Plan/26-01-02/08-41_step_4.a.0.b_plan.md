# Step 4.A.0.b: Massive 틱 데이터 통합 계획

> **버전**: 1.1  
> **작성일**: 2026-01-02  
> **선행 조건**: Step 4.A.0 완료 (Massive WebSocket 기본 구현)

---

## 📋 개요

Massive WebSocket T (Trades) 채널을 시스템 전반에 통합:

```
Massive T Channel (틱)
       │
       ▼
┌──────────────────────────────────────────────────┐
│ 1. 전략 모듈 (Seismograph)                       │ → Ignition Score 실시간 계산
├──────────────────────────────────────────────────┤
│ 2. Trading Engine                                │ → 진입/청산 시그널 실행
├──────────────────────────────────────────────────┤
│ 3. TrailingStopManager                           │ → 손절/익절 체크
├──────────────────────────────────────────────────┤
│ 4. Tier 2 Hot Zone (GUI)                         │ → zenV/zenP, 실시간 가격
└──────────────────────────────────────────────────┘
```

---

## 🔧 구현 항목

### 4.A.0.b.1: TickDispatcher 생성 (중앙 배포자)

| 작업 | 파일 |
|------|------|
| 틱 데이터 중앙 배포 클래스 생성 | `backend/core/tick_dispatcher.py` [NEW] |

```python
class TickDispatcher:
    """틱 데이터를 여러 구독자에게 배포"""
    
    def __init__(self):
        self._subscribers = []  # 전략, 엔진, GUI 등
    
    def register(self, callback: Callable[[dict], None]):
        self._subscribers.append(callback)
    
    def dispatch(self, tick: dict):
        for subscriber in self._subscribers:
            subscriber(tick)
```

---

### 4.A.0.b.2: 전략 모듈 연결 (Seismograph)

| 작업 | 파일 |
|------|------|
| `on_tick()` 메서드 추가 | `strategies/seismograph.py` |
| Ignition Score 실시간 재계산 | `strategies/seismograph.py` |

```python
def on_tick(self, ticker: str, price: float, volume: int):
    """실시간 틱 수신 → Ignition Score 업데이트"""
    if ticker in self._watched_tickers:
        self._update_realtime_metrics(ticker, price, volume)
        self._recalculate_ignition(ticker)
```

---

### 4.A.0.b.3: Trading Engine 연결

| 작업 | 파일 |
|------|------|
| 틱 기반 진입/청산 체크 | `backend/core/trading_engine.py` |

```python
def on_tick(self, tick: dict):
    """실시간 틱 → 진입/청산 판단"""
    ticker = tick["ticker"]
    price = tick["price"]
    
    # 진입 조건 체크
    if self._check_entry_signal(ticker, price):
        self._execute_entry(ticker)
    
    # 청산 조건 체크
    if self._check_exit_signal(ticker, price):
        self._execute_exit(ticker)
```

---

### 4.A.0.b.4: Trailing Stop 연결

| 작업 | 파일 |
|------|------|
| TrailingStopManager 틱 연결 | `tick_dispatcher.py` |

---

### 4.A.0.b.5: Tier 2 GUI 연결

| 작업 | 파일 |
|------|------|
| `tick_received` Signal | `ws_adapter.py` |
| zenV/zenP 실시간 계산 | `dashboard.py` 또는 별도 모듈 |
| Tier 2 패널 가격 업데이트 | `dashboard.py` |

---

### 4.A.0.b.6: 구독 자동화

| 작업 | 파일 |
|------|------|
| Tier 2 종목 → T 채널 구독 | `subscription_manager.py` |
| 활성 주문 종목 → T 채널 구독 | `subscription_manager.py` |
| Ignition 모니터링 종목 → T 채널 구독 | `subscription_manager.py` |

---

## 📝 구현 순서

| # | 작업 | 예상 시간 |
|---|------|----------|
| 1 | `tick_dispatcher.py` 생성 | 30분 |
| 2 | `seismograph.py` on_tick 추가 | 45분 |
| 3 | `trading_engine.py` 틱 연결 | 45분 |
| 4 | `trailing_stop.py` 연결 | 15분 |
| 5 | `ws_adapter.py` + `dashboard.py` GUI 연결 | 30분 |
| 6 | `subscription_manager.py` 자동 구독 | 30분 |

**총 예상 시간**: 3~4시간

---

## ✅ 완료 조건

1. [ ] TickDispatcher가 모든 모듈에 틱 배포
2. [ ] Seismograph Ignition Score 실시간 업데이트
3. [ ] Trading Engine 틱 기반 진입/청산
4. [ ] Trailing Stop 실시간 작동
5. [ ] Tier 2 GUI 실시간 가격/zenV/zenP 표시
