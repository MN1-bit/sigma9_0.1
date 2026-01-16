# [02-002] Realtime Layer DI 통합 구현 계획서

> **작성일**: 2026-01-16 16:36 | **예상**: 1.5h

---

## 1. 목표 (PRD 구조)

### 1.1 배경 (Problem)
- Realtime Layer 3개 컴포넌트 (`TickDispatcher`, `TickBroadcaster`, `SubscriptionManager`)가 DI Container 외부에서 수동 인스턴스화됨
- 테스트 시 Mock 주입이 불편하고, 생명주기 관리가 분산됨

### 1.2 목표 (Goal)
- 3개 컴포넌트를 `container.py`에 Singleton Provider로 등록
- Container 수준에서 Mock override 가능하게 함

### 1.3 User Stories
- 개발자로서, Realtime 컴포넌트를 Container에서 가져와 일관된 방식으로 사용하고 싶다
- 테스터로서, Mock을 Container.override()로 주입하여 단위 테스트를 쉽게 작성하고 싶다

### 1.4 Functional Requirements
1. `container.tick_dispatcher()` 호출 시 TickDispatcher 인스턴스 반환
2. `container.subscription_manager()` 호출 시 SubscriptionManager 인스턴스 반환
3. `container.tick_broadcaster()` 호출 시 TickBroadcaster 인스턴스 반환

### 1.5 Non-Goals (범위 제외)

#### 🚫 Out of Scope (영구 제외)
- (없음 - 모든 관련 작업이 후속으로 분리됨)

#### ⏳ Deferred (후속 작업으로 분리)
- ✅ MassiveWebSocketClient의 Container 등록 → **[02-001.5]에서 해결**
- ⏳ 기존 인스턴스화 코드 수정 → **[02-004]에서 해결**
- ⏳ 서버 lifespan 코드 수정 → **[02-004]에서 해결**

---

## 2. 레이어 체크

- [x] 레이어 규칙 위반 없음 (core 레이어 내부)
- [x] 순환 의존성 없음
- [x] DI Container 등록 필요: **예**

---

## 3. 변경 파일

| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
| `backend/container.py` | 수정 | +55줄 |

---

## 4. 기존 솔루션 검색 결과

| 솔루션 | 출처 | 채택 여부 | 사유 |
|--------|------|----------|------|
| `dependency-injector` Singleton | 기존 container.py | ✅ 채택 | 프로젝트 표준 |
| 지연 import 패턴 | 기존 container.py | ✅ 채택 | 순환 참조 방지 |
| `Object(None)` + override | container.py `ws_manager` | ✅ 채택 | 외부 주입 객체 패턴 |

---

## 5. 의존성 분석 결과

> **선행 의존성**: [02-001.5] MassiveWebSocketClient DI 통합 (먼저 완료 필요)

| 컴포넌트 | 생성자 의존성 | Container 처리 방식 |
|----------|---------------|---------------------|
| `TickDispatcher` | 없음 | Singleton 바로 등록 |
| `SubscriptionManager` | `massive_ws` (Optional) | Singleton, `massive_ws`는 Container에서 주입 |
| `TickBroadcaster` | `massive_ws`, `ws_manager`, `tick_dispatcher` | Callable로 등록, 서버 시작 시 생성 |

> **핵심**: 02-001.5 완료 후 `massive_ws`가 Container에 있으므로, 모든 컴포넌트가 Container만으로 의존성 해결 가능

---

## 6. Tasks (2레벨 분해)

- [x] 1.0 container.py Realtime Layer Provider 추가
  - [x] 1.1 `massive_ws = providers.Object(None)` 추가 (외부 주입용) → **이미 02-001.5에서 Singleton으로 등록됨**
  - [x] 1.2 `_create_tick_dispatcher()` 팩토리 추가
  - [x] 1.3 `tick_dispatcher` Singleton Provider 선언
  - [x] 1.4 `_create_subscription_manager()` 팩토리 추가 (massive_ws=None)
  - [x] 1.5 `subscription_manager` Singleton Provider 선언
  - [x] 1.6 `_create_tick_broadcaster()` 팩토리 추가 (모든 의존성 주입)
  - [x] 1.7 `tick_broadcaster` Callable Provider 선언
- [x] 2.0 검증
  - [x] 2.1 `ruff check backend/container.py` 통과
  - [x] 2.2 Container 수동 테스트 (TickDispatcher, SubscriptionManager)

---

## 7. 검증

- [x] `ruff check backend/container.py` 통과 ✅
- [x] Container 수동 테스트 ✅
  ```bash
  # TickDispatcher (의존성 없음 - 바로 테스트 가능)
  python -c "from backend.container import container; print(container.tick_dispatcher())"
  # → <backend.core.tick_dispatcher.TickDispatcher object at ...>
  
  # SubscriptionManager (massive_ws=None으로 생성됨)
  python -c "from backend.container import container; print(container.subscription_manager())"
  # → <backend.core.subscription_manager.SubscriptionManager object at ...>
  ```

---

## 8. 롤백 계획

`container.py`의 Realtime Layer 섹션 삭제 → 기존 수동 인스턴스화 유지

---

## ⚠️ 주의사항

1. **`massive_ws` 주입 필요**: Container에 `massive_ws = Object(None)`으로 등록, 서버 lifespan에서 `container.massive_ws.override(actual_massive_ws)` 호출 필요
2. **`TickBroadcaster` 생성 시점**: `providers.Callable`로 등록하여 호출 시마다 새 인스턴스 생성 (서버 lifespan에서 1회 호출)
3. **Phase 3.5 선행 필요?**: `massive_ws`를 Container에 완전 등록하려면 별도 작업 필요

---

## ✅ 승인 대기

> **다음**: 승인 후 `/IMP-execution`
