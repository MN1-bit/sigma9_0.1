# Step 08-001: Time Synchronization & Audit System

**Date**: 2026-01-08  
**Status**: 🔄 진행 중 (E⏱ 일시 비활성화)  
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

## 2026-01-08 추가 작업

### Phase 6: E⏱/B⏱ 분리 및 UI 개선

| File | Change |
|------|--------|
| `frontend/gui/widgets/time_display_widget.py` | B⏱/E⏱ 레이턴시 분리 표시 (수직 배치), `_event_latency_ms` 추가, `_last_event_time` 추적 |
| `frontend/gui/dashboard.py` | 로그 콘솔 다이나믹 스크롤 (맨 아래일 때만 자동 스크롤) |
| `frontend/services/ws_adapter.py` | `_event_latency_ms` 필드 처리 추가 |
| `backend/api/websocket.py` | `broadcast_watchlist`에 `event_latency_ms` 파라미터 추가 |
| `backend/core/realtime_scanner.py` | `_api_latency_ms` 저장 및 브로드캐스트 전달, `_last_poll_timestamp_ms` 추가 |
| `backend/data/massive_client.py` | `updated` 타임스탬프 추출 시도 (비활성화됨) |

### 레이턴시 정의

```
이벤트 발생 ──E⏱──> 백엔드 수신 ──B⏱──> 프론트엔드 수신
   (event_time)      (sent_at)         (now)

B⏱ = now - sent_at       (네트워크 지연)
E⏱ = sent_at - event_time (데이터 처리 지연) ← 현재 비활성화
```

### E⏱ 비활성화 사유

Massive API의 `updated` 타임스탬프 분석 결과:
- `updated = 1767834000000000000` (나노초)
- 밀리초 변환: `1767834000000` ms
- 해당 시점: **2026년 2월 7일** (약 1달 미래!)

> **TODO**: Massive API 문서 확인 후 올바른 타임스탬프 필드 사용

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

### 3. 로그 다이나믹 스크롤

```python
# dashboard.py - log() 메서드
at_bottom = scrollbar.value() >= scrollbar.maximum() - 20
# ... 로그 추가 ...
if at_bottom:
    scrollbar.setValue(scrollbar.maximum())
```

사용자가 스크롤을 올려 이전 로그를 보고 있을 때 강제 스크롤 방지.

### 4. E⏱/B⏱ 수직 배치

```
┌─────────────────────────────────────┐
│ 🇺🇸 00:46:08 EST  ←stretch→   B⏱32ms │
│ 🇰🇷 14:46:08 KST  ←stretch→   E⏱--ms │
└─────────────────────────────────────┘
```

---

## Verification Results

### 최종 검증 결과 (2026-01-08)

| 검증 항목 | 결과 |
|----------|------|
| ruff format | ✅ 118 files reformatted |
| ruff check (변경 파일) | ✅ All checks passed |
| 신규 파일 ≤ 500 라인 | ✅ time_display_widget.py: 224줄 |
| Singleton 미사용 | ✅ 신규 코드에 없음 |
| 수동 테스트 | ✅ B⏱ 표시, E⏱ --ms, 다이나믹 스크롤 |

### QA Checks

```powershell
ruff format  # 118 files reformatted
ruff check backend/api/websocket.py frontend/gui/widgets/time_display_widget.py frontend/services/ws_adapter.py
# All checks passed!
```

### 알려진 이슈

- `realtime_scanner.py`, `massive_client.py`에 기존 E402 (module level import) 경고 있음
- 해당 파일들은 기존 코드로, 별도 리팩터링 필요

---

## Next Steps

1. ~~**E⏱/B⏱ 분리 표시**~~ ✅ 완료 (E⏱ 비활성화)
2. **Massive API 문서 확인**: `updated` 필드 의미 파악
3. **E⏱ 재활성화**: 올바른 타임스탬프 사용

---

## Files Created/Modified

**Created (9 files)**:
- `frontend/gui/widgets/time_display_widget.py`
- `frontend/gui/widgets/__init__.py`
- `backend/core/audit_logger.py`
- `backend/core/deduplicator.py`
- `backend/core/event_sequencer.py`
- `tests/test_time_sync.py`

**Modified (10 files)**:
- `backend/models/tick.py`
- `backend/server.py`
- `backend/container.py`
- `backend/strategies/seismograph/strategy.py`
- `backend/api/websocket.py`
- `backend/core/realtime_scanner.py`
- `backend/data/massive_client.py`
- `frontend/gui/control_panel.py`
- `frontend/gui/dashboard.py`
- `frontend/services/ws_adapter.py`
- `frontend/services/backend_client.py`

