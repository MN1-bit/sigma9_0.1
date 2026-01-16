# [02-004] Realtime Services Container 통합 계획서

> **작성일**: 2026-01-16 16:40 | **예상**: 2h

---

## 1. 목표 (PRD 구조)

### 1.1 배경 (Problem)
- 02-001.5, 02-002에서 Container에 서비스를 등록했으나, `backend/startup/realtime.py`는 여전히 직접 인스턴스화 사용
- Container 등록과 실제 사용 코드가 분리되어 **불일치** 발생
- 서버 lifespan에서 Container를 활용하지 않음

### 1.2 목표 (Goal)
- `backend/startup/realtime.py`가 Container에서 서비스를 가져오도록 수정
- 수동 인스턴스화 코드 제거
- Container 기반 의존성 주입 완성

### 1.3 User Stories
- 개발자로서, 모든 서비스가 Container에서 일관되게 제공되어 테스트가 쉬웠으면 좋겠다
- 아키텍트로서, DI 패턴이 실제로 사용되는 것을 보고 싶다

### 1.4 Functional Requirements
1. `initialize_massive_websocket()`에서 `container.massive_ws()` 사용
2. `initialize_realtime_scanner()`에서 `container.realtime_scanner()` 사용
3. `initialize_ignition_monitor()`에서 `container.ignition_monitor()` 사용
4. `TickDispatcher`, `TickBroadcaster`, `SubscriptionManager`도 Container에서 획득

### 1.5 Non-Goals (범위 제외)

#### 🚫 Out of Scope (영구 제외)
- ❌ `RealtimeServicesResult` 클래스 구조 변경 — 기존 API 호환성 유지
- ❌ 새로운 서비스 추가 — 순수 통합 작업
- ❌ 초기화 순서 변경 — 기존 순서 안정적

#### ⏳ Deferred (후속 작업으로 분리)
- (없음 - 이 작업이 최종 통합)

---

## 2. 선행 의존성

| 계획서 | 상태 | 필수 여부 |
|--------|------|----------|
| 02-001.5 MassiveWebSocketClient DI | 필수 | ✅ |
| 02-002 Realtime Layer DI | 필수 | ✅ |

> **중요**: 02-001.5, 02-002 완료 후에만 진행 가능

---

## 3. 레이어 체크

- [x] 레이어 규칙 위반 없음 (startup → container 참조)
- [x] 순환 의존성 없음
- [x] DI Container 사용: **예**

---

## 4. 변경 파일

| 파일 | 유형 | 예상 변경 |
|------|-----|----------|
| `backend/startup/realtime.py` | 수정 | Container 사용으로 전환 (~50줄 변경) |

---

## 5. 해결되는 Non-Goals

이 계획서 완료 시 다음 Non-Goals가 해결됩니다:

| 원본 계획서 | Non-Goal | 해결 여부 |
|-------------|----------|----------|
| 02-001.5 | `backend/startup/realtime.py` 수정 | ✅ 해결 |
| 02-001.5 | 기존 서버 lifespan 코드 변경 | ✅ 해결 |
| 02-002 | 기존 인스턴스화 코드 수정 | ✅ 해결 |
| 02-002 | 서버 lifespan 코드 수정 | ✅ 해결 |

---

## 6. Tasks (2레벨 분해)

- [x] 1.0 `initialize_massive_websocket()` Container 통합
  - [x] 1.1 `MassiveWebSocketClient()` → `container.massive_ws()` 변경
  - [x] 1.2 `TickDispatcher()` → `container.tick_dispatcher()` 변경
  - [x] 1.3 `SubscriptionManager()` → `container.subscription_manager()` 변경
  - [x] 1.4 `TickBroadcaster()` → `container.tick_broadcaster()` 호출로 변경
- [x] 2.0 `initialize_realtime_scanner()` Container 통합
  - [x] 2.1 `massive_client`, `data_repository`, `scoring_strategy` → Container에서 획득
- [x] 3.0 `initialize_ignition_monitor()` Container 통합
  - [x] 3.1 `IgnitionMonitor()` → `container.ignition_monitor()` 변경
- [x] 4.0 검증
  - [x] 4.1 `ruff check backend/startup/realtime.py` 통과
  - [ ] 4.2 서버 시작 테스트 (선택적)

---

## 7. 검증

- [x] `ruff check backend/startup/` 통과 ✅
- [ ] 서버 시작 테스트 (선택적):
  ```bash
  cd d:\Codes\Sigma9-0.1
  python -m backend.server
  # 로그에서 서비스 초기화 확인
  ```

---

## 8. 롤백 계획

Git revert로 이전 상태 복원 → 수동 인스턴스화 유지

---

## ✅ 승인 대기

> **다음**: 02-001.5, 02-002 완료 후 `/IMP-execution`

---

## 📋 후속 작업

> **이후**: 02-004 완료 후 → **[02-003] IBKRConnector PyQt6 의존성 제거** 진행
