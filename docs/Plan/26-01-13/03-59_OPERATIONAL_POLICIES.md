# Sigma9 운영 정책 (Operational Policies)

> **버전**: v1.0 (2026-01-07)  
> **목적**: 트레이딩 시스템 운영에 필요한 핵심 정책 정의 및 구현 접근법

---

## 1. 개요

본 문서는 Sigma9 트레이딩 시스템에 적용해야 할 5가지 핵심 운영 정책을 정의합니다.
각 정책에 대해 **적용 가능 여부**, **현재 구현 상태**, **구현 접근법**을 분석합니다.

| 정책 도메인 | 적용 가능 | 현재 상태 | 우선순위 |
|------------|----------|----------|----------|
| 1. 시간/순서/재처리 | ✅ 가능 | ⚠️ 부분 구현 | **P1** |
| 2. 감사/추적 | ✅ 가능 | ❌ 미구현 | P2 |
| 3. 리스크/킬스위치 | ✅ 가능 | ✅ 구현됨 | P3 |
| 4. 장애 모드 정의 | ✅ 가능 | ❌ 미구현 | P1 |
| 5. 권한/보안 | ✅ 가능 | ⚠️ 부분 구현 | P5 |

---

## 2. 시간/순서/재처리 정책

### 2.1 적용 가능 여부: ✅ 적용 가능

트레이딩 시스템에서 이벤트 시간 관리는 필수적입니다. 특히:
- 틱 데이터의 **이벤트 타임 vs 수신 타임** 구분
- 중복 데이터 처리 (Idempotency)
- WebSocket 재연결 시 **순서 보장**

### 2.2 현재 구현 상태: ⚠️ 부분 구현

| 항목 | 상태 | 위치 |
|------|------|------|
| 이벤트 타임 | ⚠️ 수신 타임만 사용 | `seismograph.py` → `TickData.timestamp` |
| 중복 처리 | ❌ 미구현 | - |
| 순서 보장 | ⚠️ WebSocket 단일 연결에 의존 | `polygon_client.py` |

**현재 문제점**:
```python
# seismograph.py - 수신 시 timestamp 설정
tick = TickData(
    ticker=ticker,
    price=price,
    timestamp=timestamp,  # ← Polygon API 제공 시간 (event time) 사용 중
    ...
)
```
그러나 **지연 도착, 순서 역전, 중복 메시지** 처리 로직이 없음.

### 2.3 구현 접근법

#### Phase 1: 이벤트 타임 vs 수신 타임 분리

```python
# 제안: TickData 확장
@dataclass
class TickData:
    ticker: str
    price: float
    event_time: datetime    # 거래소 체결 시간 (Polygon t 필드)
    receive_time: datetime  # 시스템 수신 시간 (now())
    sequence_num: int       # Polygon sequence number (있을 경우)
```

**구현 위치**: `backend/strategies/seismograph.py` → `TickData` 클래스

#### Phase 2: Idempotency (중복 처리)

```python
# 제안: 중복 체크용 Bloom Filter 또는 Set
class TickDeduplicator:
    def __init__(self, window_seconds: int = 60):
        self._seen: Dict[str, Set[Tuple[int, float]]] = {}  # ticker -> (timestamp, price)
    
    def is_duplicate(self, tick: TickData) -> bool:
        key = (tick.event_time.timestamp(), tick.price)
        if key in self._seen.get(tick.ticker, set()):
            return True
        self._seen.setdefault(tick.ticker, set()).add(key)
        return False
```

**구현 위치**: `backend/core/tick_dedup.py` (신규)

#### Phase 3: 순서 보장 범위 정의

| 보장 수준 | 설명 | 트레이드오프 |
|----------|------|-------------|
| **Best-effort** (현재) | 도착 순서대로 처리 | 빠르지만 비정확 |
| **Per-ticker ordered** | 종목별 시퀀스 보장 | 약간의 지연 |
| **Global ordered** | 전체 시퀀스 보장 | 높은 지연 |

**권장**: Per-ticker ordered (종목별 60초 윈도우 내 정렬)

---

## 3. 감사/추적 (Auditability)

### 3.1 적용 가능 여부: ✅ 적용 가능 (필수)

트레이딩 시스템의 **재현 가능성**과 **사후 분석**을 위해 필수.

### 3.2 현재 구현 상태: ❌ 미구현

| 항목 | 상태 | 필요성 |
|------|------|--------|
| 주문 의사결정 로그 | ❌ | 진입/청산 이유 추적 |
| 파라미터 스냅샷 | ❌ | 설정 변경 이력 |
| 전략 상태 덤프 | ❌ | 디버깅 및 재현 |
| 시장 데이터 기록 | ⚠️ DB에 바 저장 | 틱 레벨 미저장 |

### 3.3 구현 접근법

#### 3.3.1 주문 의사결정 로그

```python
# 제안: Trade Decision 구조체
@dataclass
class TradeDecision:
    timestamp: datetime
    symbol: str
    action: Literal["ENTER", "EXIT", "HOLD", "SKIP"]
    reason: str                          # "TightRange + OBVDiv detected"
    scores: Dict[str, float]             # {"score_v3": 85.2, "ignition": 72.0}
    market_snapshot: Dict[str, Any]      # 의사결정 당시 시장 상태
    strategy_state: Dict[str, Any]       # 전략 내부 상태
    executed: bool = False
    order_id: Optional[str] = None
```

**구현 위치**: `backend/core/audit/decision_logger.py` (신규)

#### 3.3.2 파라미터 스냅샷

```python
# 서버 시작 시 설정 저장
def snapshot_config(config: dict, reason: str = "startup") -> str:
    """
    Returns:
        snapshot_id: UUID로 식별되는 스냅샷 ID
    """
    snapshot = {
        "id": str(uuid4()),
        "timestamp": datetime.now().isoformat(),
        "reason": reason,
        "config": config,
        "git_commit": get_git_commit_hash(),  # 코드 버전
    }
    save_json(f"data/audit/config_{snapshot['id']}.json", snapshot)
    return snapshot["id"]
```

**저장 위치**: `data/audit/` 디렉터리

#### 3.3.3 재현 가능성

| 구성 요소 | 저장 대상 | 포맷 |
|----------|----------|------|
| 입력 데이터 | 틱 스트림 | Parquet (압축) |
| 의사결정 | TradeDecision | JSON Lines |
| 설정 | 파라미터 스냅샷 | JSON |
| 코드 버전 | Git commit hash | - |

**리플레이 모드**: 저장된 데이터로 동일 결과 재현 가능하도록 설계

---

## 4. 리스크/킬스위치

### 4.1 적용 가능 여부: ✅ 적용 가능 (구현됨)

### 4.2 현재 구현 상태: ✅ 구현됨

`backend/core/risk_manager.py`에 다음 기능 구현:

| 기능 | 상태 | 메서드 |
|------|------|--------|
| 일일 손실 제한 | ✅ | `check_daily_limit()` |
| 주간 손실 제한 | ✅ | `check_weekly_limit()` |
| 최대 포지션 수 | ✅ | `can_open_position()` |
| 자동 Kill Switch | ✅ | `kill_switch()` |
| 수동 Kill Switch | ✅ | API `/kill-switch` |

### 4.3 개선 사항

#### 4.3.1 추가 권장 한도

| 한도 유형 | 현재 | 권장 추가 |
|----------|------|----------|
| 거래 횟수/일 | ✅ | - |
| 슬리피지 한도 | ❌ | 주문당 최대 슬리피지 % |
| 연속 손실 횟수 | ❌ | N회 연속 손실 시 휴식 |
| 시간대 제한 | ❌ | 개장 직후/마감 전 제한 |

#### 4.3.2 Kill Switch 강화

```python
# 현재
def kill_switch(self, reason: str = "Manual"):
    # 전 포지션 청산

# 제안: 단계별 Kill Switch
class KillSwitchLevel(Enum):
    SOFT = "soft"      # 신규 진입만 금지
    MEDIUM = "medium"  # 신규 + 기존 포지션 축소
    HARD = "hard"      # 전량 청산 + 거래 정지
```

---

## 5. 장애 모드 정의 (Failure Modes)

### 5.1 적용 가능 여부: ✅ 적용 가능 (필수)

실시간 트레이딩에서 장애 대응은 생존의 문제.

### 5.2 현재 구현 상태: ❌ 미구현

명시적인 장애 모드 정의 및 자동 대응 로직 없음.

### 5.3 구현 접근법

#### 5.3.1 장애 모드 테이블

| 장애 유형 | 감지 조건 | 대응 행동 | 복구 조건 |
|----------|----------|----------|----------|
| **데이터 지연** | 30초간 틱 없음 | SOFT_STOP → 신규 진입 금지 | 정상 틱 수신 시 |
| **거래소 연결 끊김** | WebSocket 3회 재연결 실패 | MEDIUM_STOP + 알림 | 수동 확인 후 |
| **체결 지연** | 주문 후 60초간 응답 없음 | 해당 종목 SKIP + 알림 | 응답 수신 시 |
| **API 한도 초과** | 429 에러 | 5분 대기 + 축소 운영 | 한도 리셋 시 |
| **브로커 연결 끊김** | IB TWS 연결 실패 | HARD_STOP | 수동 재시작 |

#### 5.3.2 구현 구조

```python
# 제안: backend/core/failure_modes.py
class FailureMode(Enum):
    DATA_DELAY = "data_delay"
    EXCHANGE_DISCONNECT = "exchange_disconnect"
    EXECUTION_DELAY = "execution_delay"
    RATE_LIMIT = "rate_limit"
    BROKER_DISCONNECT = "broker_disconnect"

class FailureHandler:
    def __init__(self, risk_manager: RiskManager):
        self.risk = risk_manager
        self._active_failures: Set[FailureMode] = set()
    
    def on_failure(self, mode: FailureMode):
        """장애 발생 시 호출"""
        self._active_failures.add(mode)
        action = FAILURE_ACTIONS[mode]
        if action == "SOFT_STOP":
            self.risk.disable_new_entries()
        elif action == "HARD_STOP":
            self.risk.kill_switch(f"Failure: {mode.value}")
    
    def on_recovery(self, mode: FailureMode):
        """복구 시 호출"""
        self._active_failures.discard(mode)
        if not self._active_failures:
            self.risk.enable_trading()
```

#### 5.3.3 대체 데이터 전략

| 상황 | 대체 데이터 소스 | 동작 모드 |
|------|-----------------|----------|
| Polygon 틱 지연 | Polygon REST Snapshot | 축소 운영 (30초 폴링) |
| Polygon 전체 장애 | 브로커 실시간 호가 | 보수적 운영 |
| 모든 데이터 불가 | - | 거래 중지 |

---

## 6. 권한/보안

### 6.1 적용 가능 여부: ✅ 적용 가능

### 6.2 현재 구현 상태: ⚠️ 부분 구현

| 항목 | 상태 | 위치 |
|------|------|------|
| API Key 분리 | ✅ | `.env` 파일 |
| 시크릿 암호화 | ❌ | 평문 저장 |
| 운영자 액션 로깅 | ❌ | 없음 |
| 권한 분리 | ❌ | 단일 사용자 |

### 6.3 구현 접근법

#### 6.3.1 키/시크릿 관리

**현재 문제**:
```
# .env (평문)
POLYGON_API_KEY=abc123...
IBKR_ACCOUNT=U12345...
```

**개선 방안**:

| 수준 | 방법 | 적용 대상 |
|------|------|----------|
| **Level 1** | `.env` + gitignore | 현재 (개발용) |
| **Level 2** | 환경 변수 주입 | Docker/프로덕션 |
| **Level 3** | Vault/KMS | 엔터프라이즈 |

**권장**: Level 2 (Docker Secrets 또는 환경 변수 주입)

#### 6.3.2 운영자 액션 로깅

```python
# 제안: 모든 수동 액션 로깅
@audit_log("operator_action")
def on_manual_kill_switch(operator_id: str, reason: str):
    """수동 Kill Switch 발동"""
    log_action({
        "action": "KILL_SWITCH",
        "operator": operator_id,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
        "positions_at_time": get_current_positions(),
    })
```

**로그 위치**: `data/audit/operator_actions.jsonl`

---

## 7. 구현 로드맵

### 7.1 우선순위 매트릭스

| 우선순위 | 정책 | 이유 | 예상 시간 |
|---------|------|------|----------|
| **P1** | 시간/순서 정책 | 데이터 정확도 (트레이딩 기반) | 4-6h |
| **P1** | 장애 모드 정의 | 운영 안정성 | 4-6h |
| **P2** | 감사/추적 | 사후 분석 필수 | 6-8h |
| **P3** | 리스크 강화 | 기존 기능 확장 | 2-3h |
| **P5** | 권한/보안 강화 | 장기 과제 | 2-4h |

### 7.2 구현 순서

```
Phase 1 (P1 필수): 시간/순서 정책 + 장애 모드
├── TickData 확장 (event_time, receive_time)
├── TickDeduplicator 구현
├── failure_modes.py 신규 생성
└── risk_manager.py 연동

Phase 2 (P2): 감사/추적
├── decision_logger.py 신규 생성
├── 파라미터 스냅샷
└── 리플레이 모드 설계

Phase 3 (P3): 리스크 강화
├── 슬리피지 한도 추가
├── 연속 손실 카운터
└── Kill Switch 레벨 분리

Phase 4 (P5 장기): 권한/보안
├── 시크릿 관리 개선
└── 운영자 로깅
```

---

## 8. 체크리스트

### 배포 전 필수 확인

- [ ] Kill Switch API 테스트 완료
- [ ] 장애 모드별 대응 로직 구현
- [ ] 의사결정 로깅 활성화
- [ ] 파라미터 스냅샷 저장 확인
- [ ] 브로커 연결 끊김 시 행동 확인
- [ ] `.env` 파일 gitignore 확인

### 운영 중 모니터링

- [ ] 일일 손익 한도 접근 알림
- [ ] 장애 발생 시 즉시 알림
- [ ] 주간 감사 로그 리뷰

---

*관련 문서: [REFACTORING.md](./REFACTORING.md), [risk_manager.py](../../backend/core/risk_manager.py)*
