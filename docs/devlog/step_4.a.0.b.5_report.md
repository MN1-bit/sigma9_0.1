# Step 4.A.0.b.5: Tier 2 GUI 연결

> **작성일**: 2026-01-02  
> **버전**: 1.0

---

## 📋 개요

**tick_received** Signal → **Dashboard._on_tick_received()** 연결

```
Massive T (틱) → WsAdapter.tick_received
                      │
                      ▼
              BackendClient.tick_received
                      │
                      ▼
              Dashboard._on_tick_received()
                      │
                      ▼
              _price_cache 업데이트
```

---

## ✅ 구현 완료

### 수정된 파일

| 파일 | 변경 |
|------|------|
| `backend_client.py` | `tick_received` Signal 추가 및 연결 |
| `dashboard.py` | `_on_tick_received` 핸들러, `_price_cache` 추가 |

---

## 📝 TODO

- Tier 2 패널 구현 시 `_update_tier2_price()` 메서드 연결
- zenV/zenP 실시간 계산 및 표시

---

## 🔗 다음 단계

- **4.A.0.b.6**: 구독 자동화
