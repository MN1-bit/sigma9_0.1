# Step 4.A.0.b.3: Trading Engine 연결

> **작성일**: 2026-01-02  
> **버전**: 1.0

---

## ⏭️ SKIP

**TradingEngine 클래스가 아직 구현되지 않음.**

현재 아키텍처:
- 전략 (Seismograph)에서 BUY Signal 생성
- OrderManager가 직접 주문 실행

TradingEngine은 Phase 5 (실거래 통합) 단계에서 구현 예정.

---

## 📝 TODO (Phase 5)

1. `backend/core/trading_engine.py` 생성
2. 전략 Signal → 주문 실행 중개
3. TickDispatcher 연결
