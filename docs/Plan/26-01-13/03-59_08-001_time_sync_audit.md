# 08-001: Time Synchronization & Audit System

**날짜**: 2026-01-08  
**우선순위**: P1 (핵심 기능)  
**상태**: 📋 계획 완료

---

## 1. 목표

### 1.1 GUI 시간 표시
- 백엔드 시간 (EST/EDT, 미국 동부)
- 프론트엔드 시간 (KST, 한국 표준시)
- 지연 시간 표시 (Event → Backend → Frontend)

### 1.2 백엔드 시간 처리
- 이벤트 타임 vs 수신 타임 분리
- 중복 처리 (Idempotency)
- 순서 보장 (100ms 허용)
- 감사/추적 로그 (무기한 보관)

---

## 2. 현황 분석

### 2.1 `datetime.now()` 사용 현황 (총 34건)

| 파일 | 라인 | 용도 | 수정 필요 |
|------|------|------|-----------|
| `realtime_scanner.py` | 324 | `discovered_at` | ✅ event_time으로 대체 |
| `ignition_monitor.py` | 276 | TickData 생성 | ✅ event_time 전파 |
| `websocket.py` | 245 | heartbeat 타임스탬프 | ✅ 서버 시간 전파 |
| `tick_broadcaster.py` | 120,166 | 내부 추적 | ⚠️ 유지 (시스템 시간) |
| `order_manager.py` | 347,368 | 체결/취소 시간 | ⚠️ 유지 (시스템 시간) |
| `risk_manager.py` | 393,489 | 킬 타임스탬프 | ⚠️ 유지 (시스템 시간) |
| `watchlist_store.py` | 207 | 저장 타임스탬프 | ⚠️ 유지 (시스템 시간) |
| 기타 (massive_client 등) | - | API 호출 날짜 계산 | ⚠️ 유지 |

### 2.2 이벤트 타임 현황

| 데이터 소스 | event_time 제공 | 현재 처리 |
|-------------|-----------------|-----------|
| Massive WebSocket T채널 | ✅ `t` (Unix ms) | `_parse_message`에서 `time` 필드로 변환 |
| Massive WebSocket AM채널 | ✅ `s` (Unix ms) | `_parse_message`에서 `time` 필드로 변환 |
| Gainers REST API | ✅ `lastUpdate` | 미사용 |

> **핵심 문제**: WebSocket에서 event_time을 추출하지만, 이후 전파 경로에서 `datetime.now()`로 덮어씀

---

## 3. Phase 구성

| Phase | 내용 | 파일 | 예상 공수 |
|-------|------|------|----------|
| 1 | GUI 시간 표시 패널 | `time_display_widget.py` [NEW] | 2h |
| 2 | 이벤트 타임 전파 | `tick.py`, `massive_ws_client.py` 수정 | 3h |
| 3 | 중복 처리 | `deduplicator.py` [NEW] | 2h |
| 4 | 순서 보장 | `event_sequencer.py` [NEW] | 3h |
| 5 | 감사 로그 | `audit_logger.py` [NEW] | 3h |

---

## 4. 상세 설계

### 4.1 Phase 1: GUI 시간 표시

#### [NEW] `frontend/gui/widgets/time_display_widget.py`

```python
class TimeDisplayWidget(QWidget):
    """
    시간 표시 위젯
    
    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    미국 거래소 시간과 한국 시간을 동시에 보여줍니다.
    데이터가 얼마나 늦게 도착하는지 지연 시간도 표시합니다.
    
    표시 예시:
      ┌─────────────────────────────────────────┐
      │ 🇺🇸 NYSE: 02:31:09 PM EST               │
      │ 🇰🇷 Local: 03:31:09 AM KST (+1d)        │
      │ ⏱ Latency: Event→BE 15ms | BE→FE 32ms │
      └─────────────────────────────────────────┘
    """
    
    # 시그널: 백엔드에서 시간 업데이트 수신 시
    time_updated = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._backend_time: Optional[datetime] = None
        self._local_time: datetime = datetime.now()
        self._latency_event_to_be: int = 0  # ms
        self._latency_be_to_fe: int = 0     # ms
        self._setup_ui()
        self._start_timer()
    
    def update_from_heartbeat(self, data: dict) -> None:
        """WebSocket heartbeat 메시지로 시간 업데이트"""
        # data = {"server_time_utc": "...", "event_time_utc": "...", "sent_at": ...}
        pass
```

#### [MODIFY] `frontend/gui/dashboard.py`
- 상단바에 `TimeDisplayWidget` 통합

#### [MODIFY] `backend/api/websocket.py` (Lines 239-246)
```diff
- "timestamp": datetime.now().isoformat()
+ "server_time_utc": datetime.now(timezone.utc).isoformat(),
+ "event_time_utc": event_time.isoformat() if event_time else None,
+ "sent_at": time.time_ns() // 1_000_000  # Unix ms for latency calc
```

---

### 4.2 Phase 2: 이벤트 타임 전파

#### [MODIFY] `backend/models/tick.py`

```diff
@dataclass
class TickData:
    price: float
    volume: int
-   timestamp: datetime
+   event_time: datetime      # 거래소 발생 시간 (source of truth)
+   receive_time: datetime    # 백엔드 수신 시간
    side: str = "B"
+   
+   @property
+   def timestamp(self) -> datetime:
+       """하위 호환성: 기존 코드에서 tick.timestamp 사용 시"""
+       return self.event_time
```

> **하위 호환성**: `timestamp` 프로퍼티로 기존 코드 유지

#### [MODIFY] `backend/data/massive_ws_client.py` (Lines 326-342)

```diff
elif ev == "T":
    tick = {
        "type": "tick",
        "ticker": data.get("sym"),
        "price": data.get("p"),
        "size": data.get("s"),
-       "time": data.get("t", 0) / 1000,
+       "event_time": data.get("t", 0) / 1000,  # Unix sec
+       "receive_time": time.time(),             # 수신 시점
        "conditions": data.get("c"),
    }
```

#### [MODIFY] `backend/core/ignition_monitor.py` (Line 276)

```diff
- timestamp=datetime.now()
+ event_time=datetime.fromtimestamp(tick_data["event_time"]),
+ receive_time=datetime.fromtimestamp(tick_data["receive_time"])
```

#### [MODIFY] `backend/core/realtime_scanner.py` (Line 324)

```diff
- "discovered_at": datetime.now().isoformat(),
+ "discovered_at": item.get("lastUpdated") or datetime.now().isoformat(),
```

---

### 4.3 Phase 3: 중복 처리

#### [NEW] `backend/core/deduplicator.py`

```python
class EventDeduplicator:
    """
    이벤트 중복 제거기 (60초 윈도우)
    
    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    같은 거래 이벤트가 네트워크 문제로 두 번 올 수 있습니다.
    이미 처리한 이벤트는 무시하여 중복 계산을 방지합니다.
    
    작동 방식:
      1. 이벤트마다 고유 ID 생성 (ticker + event_time + price + size)
      2. 60초 동안 ID 캐시
      3. 동일 ID 수신 시 무시
    """
    
    def __init__(self, window_seconds: int = 60):
        self._window = window_seconds
        self._seen: Dict[str, float] = {}  # event_id -> expire_time
        self._lock = threading.Lock()
    
    def is_duplicate(self, event_id: str) -> bool:
        """중복 여부 확인 (중복이면 True)"""
        now = time.time()
        with self._lock:
            self._cleanup(now)
            if event_id in self._seen:
                return True
            self._seen[event_id] = now + self._window
            return False
    
    @staticmethod
    def generate_event_id(ticker: str, event_time: float, price: float, size: int) -> str:
        """이벤트 고유 ID 생성"""
        return f"{ticker}:{event_time:.3f}:{price:.4f}:{size}"
```

---

### 4.4 Phase 4: 순서 보장

#### [NEW] `backend/core/event_sequencer.py`

```python
class EventSequencer:
    """
    이벤트 순서 재정렬기 (100ms 버퍼)
    
    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    네트워크 지연으로 이벤트가 뒤바뀐 순서로 도착할 수 있습니다.
    100ms 버퍼에 모아서 event_time 기준으로 정렬 후 처리합니다.
    
    작동 방식:
      buffer_ms=100 설정 시:
      ┌─────────────────────────────────────────┐
      │ 수신 순서: B(t=102) → A(t=100) → C(t=105) │
      │ 100ms 후 방출: A(t=100) → B(t=102) → C(t=105) │
      └─────────────────────────────────────────┘
    """
    
    def __init__(self, buffer_ms: int = 100, on_emit: Optional[Callable] = None):
        self._buffer_ms = buffer_ms
        self._on_emit = on_emit
        self._heap: List[Tuple[float, int, dict]] = []  # (event_time, seq, event)
        self._seq = 0
        self._lock = threading.Lock()
    
    async def push(self, event: dict) -> None:
        """이벤트 추가"""
        event_time = event.get("event_time", time.time())
        with self._lock:
            heapq.heappush(self._heap, (event_time, self._seq, event))
            self._seq += 1
        await self._try_emit()
    
    async def _try_emit(self) -> None:
        """버퍼 시간 초과 이벤트 방출"""
        cutoff = time.time() - (self._buffer_ms / 1000)
        with self._lock:
            while self._heap and self._heap[0][0] <= cutoff:
                _, _, event = heapq.heappop(self._heap)
                if self._on_emit:
                    await self._on_emit(event)
```

---

### 4.5 Phase 5: 감사 로그

#### [NEW] `backend/core/audit_logger.py`

```python
class AuditLogger:
    """
    의사결정 감사 로그
    
    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    모든 매매 의사결정을 기록합니다.
    나중에 "왜 이 시점에 매수했지?"를 추적할 수 있습니다.
    
    기록 항목:
      - 입력 데이터 스냅샷 (틱, 가격)
      - 계산된 신호 (score_v3, ignition)
      - 최종 결정 (BUY/SELL/HOLD)
      - 파라미터 버전
    
    저장 위치: data/audit/YYYY-MM-DD/decisions.jsonl
    """
    
    def __init__(self, base_path: Path = Path("data/audit")):
        self._base_path = base_path
        self._base_path.mkdir(parents=True, exist_ok=True)
    
    async def log_decision(
        self,
        ticker: str,
        decision: str,  # "BUY", "SELL", "HOLD"
        event_time: datetime,
        inputs: Dict[str, Any],
        signals: Dict[str, Any],
        params_version: str
    ) -> None:
        """의사결정 기록"""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_time": event_time.isoformat(),
            "ticker": ticker,
            "decision": decision,
            "inputs": inputs,
            "signals": signals,
            "params_version": params_version
        }
        
        # 일별 파일에 추가
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_file = self._base_path / date_str / "decisions.jsonl"
        log_file.parent.mkdir(exist_ok=True)
        
        async with aiofiles.open(log_file, "a") as f:
            await f.write(json.dumps(record) + "\n")
```

---

## 5. 수정 대상 파일 요약

| 파일 | 변경 유형 | Phase |
|------|----------|-------|
| `frontend/gui/widgets/time_display_widget.py` | NEW | 1 |
| `frontend/gui/dashboard.py` | MODIFY | 1 |
| `backend/api/websocket.py` | MODIFY | 1, 2 |
| `backend/models/tick.py` | MODIFY | 2 |
| `backend/data/massive_ws_client.py` | MODIFY | 2 |
| `backend/core/ignition_monitor.py` | MODIFY | 2 |
| `backend/core/realtime_scanner.py` | MODIFY | 2 |
| `backend/core/deduplicator.py` | NEW | 3 |
| `backend/core/event_sequencer.py` | NEW | 4 |
| `backend/core/audit_logger.py` | NEW | 5 |

---

## 6. 구현 순서

```
Phase 1 (GUI) → Phase 2 (이벤트 타임) → Phase 5 (감사) → Phase 3 (중복) → Phase 4 (순서)
```

> **이유**: 
> - Phase 1-2: 즉시 가시적인 효과 (시간 표시)
> - Phase 5: 디버깅 지원 (감사 로그)
> - Phase 3-4: 안정성 강화 (중복/순서)

---

## 7. DI Container 등록

> **@PROJECT_DNA.md 준수**: "신규 서비스는 `Container`에 등록 후 주입"

| 신규 서비스 | Container 프로바이더 |
|------------|---------------------|
| `EventDeduplicator` | `Factory` (상태 있음) |
| `EventSequencer` | `Factory` (상태 있음) |
| `AuditLogger` | `Singleton` (파일 핸들 공유) |
| `TimeDisplayWidget` | N/A (GUI 위젯) |

### [MODIFY] `backend/container.py`

```python
class Container(containers.DeclarativeContainer):
    # ... 기존 프로바이더 ...
    
    # [08-001] Time Sync 서비스
    event_deduplicator = providers.Factory(EventDeduplicator, window_seconds=60)
    event_sequencer = providers.Factory(EventSequencer, buffer_ms=100)
    audit_logger = providers.Singleton(AuditLogger)
```

---

## 8. Reference 문서 Sync

> **Development Workflow Step 4**: 핵심 참조 문서 동기화 필요 여부

| 문서 | 변경 필요 | 내용 |
|------|----------|------|
| `@PROJECT_DNA.md` | ❌ | 정책 변경 없음 |
| `.agent\Ref\archt.md` | ⚠️ 선택 | Section 3 데이터 파이프라인에 `event_time` 전파 설명 추가 가능 |
| `docs/Plan/MASTERPLAN.md` | ❌ | 아키텍처 변경 없음 |

---

## 9. 검증 계획

### 9.1 자동화 테스트

```powershell
# 기존 테스트 실행 (TickData 변경 영향 확인)
pytest tests/test_strategies.py -v

# 새 테스트 추가 후
pytest tests/test_time_sync.py -v
```

#### [NEW] `tests/test_time_sync.py`

```python
"""Phase 2-5 검증 테스트"""

def test_tick_data_backward_compatibility():
    """TickData.timestamp 프로퍼티 하위 호환성"""
    tick = TickData(
        price=10.0, volume=100,
        event_time=datetime(2026, 1, 8, 10, 0, 0),
        receive_time=datetime(2026, 1, 8, 10, 0, 0, 50000)  # +50ms
    )
    assert tick.timestamp == tick.event_time

def test_deduplicator():
    """중복 이벤트 필터링"""
    dedup = EventDeduplicator(window_seconds=1)
    event_id = "AAPL:1704700000.000:150.0000:100"
    assert dedup.is_duplicate(event_id) == False
    assert dedup.is_duplicate(event_id) == True

@pytest.mark.asyncio
async def test_event_sequencer():
    """이벤트 순서 재정렬"""
    results = []
    seq = EventSequencer(buffer_ms=50, on_emit=lambda e: results.append(e))
    await seq.push({"event_time": 1.02})  # 뒤늦게 도착
    await seq.push({"event_time": 1.00})  # 먼저 발생
    await asyncio.sleep(0.1)  # 버퍼 대기
    assert [r["event_time"] for r in results] == [1.00, 1.02]
```

### 7.2 수동 검증

1. **GUI 시간 표시 확인**
   - 백엔드 시작 → GUI 연결
   - 상단바에서 EST/KST 시간 및 Latency 표시 확인

2. **의사결정 재현 테스트**
   ```powershell
   # 감사 로그 확인
   Get-Content data/audit/2026-01-08/decisions.jsonl | ConvertFrom-Json | Select-Object -First 5
   ```

### 9.3 QA 체크 (필수)

```powershell
# Development Workflow Step 7: 코드 품질 검증
ruff format && ruff check .
lint-imports                    # 순환 의존성 검사
mypy backend/core/deduplicator.py backend/core/event_sequencer.py backend/core/audit_logger.py
```

---

## 8. 롤백 계획

### 8.1 TickData 변경 롤백
`timestamp` 프로퍼티가 하위 호환성을 보장하므로 롤백 최소화.

### 8.2 Git 복구
```bash
git revert HEAD~N  # Phase별 커밋 단위로 롤백 가능
```

---

## Appendix A: 관련 코드 참조

### A.1 Massive WebSocket 이벤트 타임 추출 위치
- [massive_ws_client.py#L291-L345](file:///d:/Codes/Sigma9-0.1/backend/data/massive_ws_client.py#L291-L345)

### A.2 기존 TickData 정의
- [tick.py#L26-L56](file:///d:/Codes/Sigma9-0.1/backend/models/tick.py#L26-L56)
