# Step 08-001: Time Synchronization & Audit System

**Date**: 2026-01-08
**Status**: ✅ Completed
**Plan**: [08-001_time_sync_audit.md](../../Plan/refactor/08-001_time_sync_audit.md)

---

## Summary

이벤트 시간(Event Time)과 수신 시간(Receive Time)을 분리하고, 의사결정 감사 로깅 시스템을 구축했습니다.

---

## Changes Made

### Phase 1: GUI 시간 표시

| File | Change |
|------|--------|
| `frontend/gui/widgets/time_display_widget.py` | **NEW** - TimeDisplayWidget (US/KR 시간, 지연 시간 표시) |
| `frontend/gui/widgets/__init__.py` | **NEW** - widgets 패키지 초기화 |
| `frontend/gui/control_panel.py` | TimeDisplayWidget 통합 |
| `backend/server.py` | PONG heartbeat에 `server_time_utc`, `sent_at` 추가 |
| `frontend/services/ws_adapter.py` | `heartbeat_received` 시그널 추가 |
| `frontend/services/backend_client.py` | `heartbeat_received` 시그널 포워딩 |
| `frontend/gui/dashboard.py` | `on_heartbeat_received` 핸들러 추가 |

### Phase 2: 이벤트 타임 전파

| File | Change |
|------|--------|
| `backend/models/tick.py` | `timestamp` → `event_time` + `receive_time` 분리, 하위호환 프로퍼티 추가 |
| `backend/strategies/seismograph/strategy.py` | TickData 생성 시 `event_time=` 사용 |

### Phase 3-5: 이벤트 처리 & 감사

| File | Change |
|------|--------|
| `backend/core/audit_logger.py` | **NEW** - JSONL 의사결정 감사 로거 |
| `backend/core/deduplicator.py` | **NEW** - 시간 윈도우 기반 중복 제거 |
| `backend/core/event_sequencer.py` | **NEW** - 힙 기반 이벤트 순서 보장 |
| `backend/container.py` | 신규 서비스 DI 등록 |

### Tests

| File | Change |
|------|--------|
| `tests/test_time_sync.py` | **NEW** - TickData, Deduplicator, Sequencer 테스트 |

---

## Key Design Decisions

### 1. TickData 하위 호환성

```python
@dataclass
class TickData:
    event_time: datetime      # 거래소 체결 시간 (필수)
    receive_time: datetime    # 서버 수신 시간 (기본 now())
    
    @property
    def timestamp(self) -> datetime:
        return self.event_time  # 하위 호환!
```

기존 `tick.timestamp` 접근 코드가 자동으로 `event_time`을 사용합니다.

### 2. Heartbeat 시간 정보

```
PING → PONG:{"server_time_utc":"2026-01-08T10:30:00Z","sent_at":1736330000000}
```

GUI에서 `sent_at`과 현재 시간을 비교하여 지연 시간을 계산합니다.

### 3. Factory vs Singleton 선택

- `AuditLogger`: **Singleton** (파일 핸들 공유)
- `EventDeduplicator`: **Factory** (상태 있음, 컴포넌트별 인스턴스)
- `EventSequencer`: **Factory** (상태 있음, 컴포넌트별 인스턴스)

---

## Verification Results

### QA Checks

```powershell
ruff format  # 6 files reformatted
ruff check   # All checks passed (after --fix)
```

### Tests

```powershell
pytest tests/test_time_sync.py -v
# TestTickDataBackwardCompatibility: 4 passed
# TestEventDeduplicator: 5 passed
# TestEventSequencer: 3 passed
```

---

## Next Steps

1. **massive_ws_client.py 통합**: `_parse_message`에서 추출한 `time`을 TickData의 `event_time`으로 전파
2. **ignition_monitor.py 통합**: AuditLogger를 주입하여 의사결정 로깅
3. **GUI 수동 테스트**: TimeDisplayWidget 작동 확인

---

## Files Created/Modified

**Created (9 files)**:
- `frontend/gui/widgets/time_display_widget.py`
- `frontend/gui/widgets/__init__.py`
- `backend/core/audit_logger.py`
- `backend/core/deduplicator.py`
- `backend/core/event_sequencer.py`
- `tests/test_time_sync.py`

**Modified (7 files)**:
- `backend/models/tick.py`
- `backend/server.py`
- `backend/container.py`
- `backend/strategies/seismograph/strategy.py`
- `frontend/gui/control_panel.py`
- `frontend/gui/dashboard.py`
- `frontend/services/ws_adapter.py`
- `frontend/services/backend_client.py`
