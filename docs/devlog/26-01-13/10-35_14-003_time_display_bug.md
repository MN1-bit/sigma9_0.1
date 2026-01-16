# [14-003] US Eastern Time Display Bug - Devlog

> **작성일**: 2026-01-13 10:32
> **관련 계획서**: [14-003_search_time_history_bugs.md](../../Plan/bugfix/14-003_search_time_history_bugs.md)

## 진행 현황

| Step | 상태 | 완료 시간 |
|------|------|----------|
| Step 1: 원인 분석 | ✅ 완료 | 10:31 |
| Step 2: 핸들러 추가 | ✅ 완료 | 10:32 |
| Step 3: 검증 | ✅ 완료 | 10:33 |

---

## Step 1: 원인 분석

### 버그 원인

**문제**: `dashboard.py` Line 220에서 `heartbeat_received` 시그널을 `on_heartbeat_received`에 연결하지만, 해당 메서드가 **정의되어 있지 않음**.

```python
# dashboard.py:218-220
if hasattr(self.backend_client, "heartbeat_received"):
    self.backend_client.heartbeat_received.connect(self.on_heartbeat_received)
    # ❌ on_heartbeat_received 메서드가 없음!
```

### 데이터 흐름 분석

1. ✅ **Backend** (`server.py:211-215`): PING → `PONG:{server_time_utc, sent_at}` 응답
2. ✅ **ws_adapter.py** (Line 326-333): PONG 파싱 → `heartbeat_received.emit()`
3. ✅ **backend_client.py** (Line 188-190): 시그널 체인 연결됨
4. ✅ **dashboard.py** (Line 220): 시그널 연결 코드 존재
5. ❌ **Missing**: `on_heartbeat_received()` 메서드 누락
6. ⏳ **control_panel.py** (Line 330-341): `update_time()` 대기 중

---

## Step 2: 핸들러 추가

### 변경 사항

- `frontend/gui/dashboard.py`: `on_heartbeat_received` 메서드 추가 (Line 639-654)

```python
def on_heartbeat_received(self, data: dict) -> None:
    """
    [14-003 FIX] Heartbeat 수신 핸들러
    ...
    """
    self.control_panel.update_time(data)
```

---

## Step 3: 검증

### 자동 검증

| 검증 항목 | 결과 |
|----------|------|
| Import 테스트 | ✅ `on_heartbeat_received` 메서드 존재 확인 |
| lint-imports | ✅ (기존 경고와 무관) |

### 수동 테스트 필요

프론트엔드 재시작 후 다음 확인:
1. 백엔드 실행 중인지 확인
2. 프론트엔드 시작: `python -m frontend`
3. 🇺🇸 US 시간 라벨에 시간이 표시되는지 확인

---

## 요약

**Root Cause**: `dashboard.py`에서 `heartbeat_received` 시그널 연결만 있고, 핸들러 메서드가 누락됨

**Fix**: `on_heartbeat_received()` 핸들러 추가 → `control_panel.update_time()` 호출
