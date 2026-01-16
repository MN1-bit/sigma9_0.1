# [DOC-001] Chunk 4: 통합/단순화 기회 식별 Devlog

> **작성일**: 2026-01-17 05:03
> **계획서**: [DOC-001](../../Plan/26-01-17/04-31_DOC-001_full_architecture_document.md)

## 진행 현황

| Chunk | 상태 | 완료 시간 |
|-------|------|----------|
| Chunk 1 | ✅ 완료 | 04:42 |
| Chunk 2A | ✅ 완료 | 04:50 |
| Chunk 2B | ✅ 완료 | 04:55 |
| Chunk 3 | ✅ 완료 | 05:02 |
| Chunk 4 | ✅ 완료 | 05:08 |

---

## 유사 Dataflow 패턴 식별

### 패턴 1: Polling → Processing → Broadcast

| 컴포넌트 | 소스 | 처리 | 브로드캐스트 |
|----------|------|------|-------------|
| RealtimeScanner | Massive Gainers API (1초) | ScoringStrategy | WebSocket |
| IgnitionMonitor | Massive API (1초) | SeismographStrategy | WebSocket |

> **통합 기회**: 두 컴포넌트가 동일한 1초 폴링을 수행. 폴링 레이어 통합 가능?

### 패턴 2: Tick Distribution Chain

```
MassiveWebSocketClient
    ↓
TickBroadcaster → GUI (ConnectionManager)
    ↓
TickDispatcher → 내부 (Strategy, TrailingStop, DoubleTap)
```

> **평가**: 현재 구조 적절. TickBroadcaster와 TickDispatcher 역할 분리 유지.

### 패턴 3: Order Execution Chain

```
Signal → OrderManager → IBKRConnector
       ↓
   RiskManager (position sizing)
```

> **평가**: 현재 구조 적절.

---

## 통합 가능한 서비스 후보

### 🔍 후보 1: RealtimeScanner + IgnitionMonitor 폴링 통합

| 현재 | 제안 |
|------|------|
| RealtimeScanner: 1초 Gainers 폴링 | 공통 폴링 레이어 |
| IgnitionMonitor: 1초 폴링 | ↓ 이벤트 분배 |

**장점**: 네트워크 요청 절반 감소
**단점**: 결합도 증가, 복잡성 증가
**결정**: ⏳ **Deferred** (현재 동작 안정적, ROI 낮음)

### 🔍 후보 2: Scanner + RealtimeScanner 통합

| Scanner | RealtimeScanner |
|---------|-----------------|
| Pre-market 일괄 스캔 | Market Hours 실시간 스캔 |

**평가**: 역할 다름. **통합 불필요**.

### 🔍 후보 3: EventDeduplicator + EventSequencer

| EventDeduplicator | EventSequencer |
|-------------------|----------------|
| 중복 제거 | 순서 보장 |

**평가**: 보완적 기능. Container에서 별도 관리 유지. **통합 불필요**.

---

## 단순화 제안

### 제안 1: TickerInfoService 의존성 명시화

현재 `ticker_info_service`는 `massive_client`를 Container에서 직접 받지 않음.
→ Container 의존성 명시화로 테스트 용이성 증가 가능.

### 제안 2: BackendClient 싱글톤 → Container 전환

Frontend의 `BackendClient`는 Singleton 패턴 사용 중.
→ Backend처럼 DI 패턴 적용 시 테스트 용이성 증가.

**결정**: ⏳ **Deferred** (Frontend는 PyQt 특성상 Singleton 유지)

---

## 결론

| 항목 | 결과 |
|------|------|
| 즉시 통합 필요 | **없음** |
| Deferred 후보 | 2개 (폴링 통합, BackendClient DI) |
| 구조 유지 | 대부분 현재 구조 적절 |

---

## 다음 단계

→ **Chunk 5A**: Full_Architecture.md 구조 + 콘텐츠 병합
