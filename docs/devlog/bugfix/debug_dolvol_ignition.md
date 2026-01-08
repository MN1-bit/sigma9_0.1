# Debugging: DolVol=0 & Ignition="-" Issue

## ✅ 해결 완료

### DolVol = 0 문제
**원인**: `frontend/services/backend_client.py`의 `WatchlistItem` dataclass에 `avg_volume` 필드가 없었음

**수정**:
```python
# backend_client.py - WatchlistItem
avg_volume: float = 0.0  # [4.A.4] DolVol 계산용

# from_dict()
avg_volume=data.get("avg_volume", 0)
```

---

### Ignition = "-" 문제
**원인**: `backend/server.py`의 `lifespan()`에서 `IgnitionMonitor` 초기화 누락

**수정**:
```python
# server.py - lifespan() 내
from backend.core.ignition_monitor import initialize_ignition_monitor
app_state.ignition_monitor = initialize_ignition_monitor(strategy, ws_manager)
```

---

### ⏳ Ignition = 0 (장외 시간)
**상태**: 정상 동작

Ignition Score는 **실시간 틱 데이터**를 기반으로 계산됩니다.
현재 미국 시장 장외 시간이므로 틱 데이터가 없어 Score = 0입니다.

**장중 테스트 필요** (미국 동부시간 9:30 AM ~ 4:00 PM)

---

## 수정된 파일
1. `frontend/services/backend_client.py` - WatchlistItem에 avg_volume 추가
2. `backend/api/routes.py` - WatchlistItem 모델에 avg_volume 추가
3. `backend/server.py` - AppState에 ignition_monitor 추가, lifespan()에서 초기화
