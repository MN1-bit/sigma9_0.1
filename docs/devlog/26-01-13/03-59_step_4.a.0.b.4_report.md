# Step 4.A.0.b.4: Trailing Stop 연결

> **작성일**: 2026-01-02  
> **버전**: 1.0

---

## 📋 개요

**TrailingStopManager.on_price_update()** → **TickDispatcher** 연결

```
Massive T (틱) → TickDispatcher.dispatch()
                      │
                      ▼
         TrailingStopManager.on_price_update()
                      │
                      ▼
         ACTIVATED / TRIGGERED 이벤트
```

---

## ✅ 구현 완료

### 기존 메서드 확인

`TrailingStopManager.on_price_update(symbol, current_price)` (lines 170-229):
- PENDING → ACTIVE (활성화)
- 최고가 갱신 → stop_price 업데이트
- 가격 < stop_price → TRIGGERED

### 수정된 파일

| 파일 | 변경 |
|------|------|
| `server.py` | TrailingStopManager 초기화 + TickDispatcher 등록 |

---

## 🔗 다음 단계

- **4.A.0.b.5**: Tier 2 GUI 연결
