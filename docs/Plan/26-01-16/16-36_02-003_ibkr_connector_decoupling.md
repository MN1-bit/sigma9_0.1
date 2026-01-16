# [02-003] IBKRConnector PyQt6 의존성 제거 계획서

> **작성일**: 2026-01-16 16:36 | **예상**: 4h+ | **위험도**: 높음

---

## 1. 목표 (PRD 구조)

### 1.1 배경 (Problem)
- `IBKRConnector`가 `PyQt6.QtCore`에 직접 의존 (QThread, pyqtSignal)
- Backend Layer가 Frontend GUI 프레임워크에 의존 → **Layer 경계 위반**
- 테스트 시 PyQt6 환경 필수 → 테스트 복잡도 증가

```python
# 현재 문제 코드
from PyQt6.QtCore import QThread, pyqtSignal
class IBKRConnector(QThread):  # ❌ Backend가 GUI 의존
```

### 1.2 목표 (Goal)
- `IBKRConnector`를 순수 Python 클래스로 전환
- Frontend에 `IBKREventAdapter` (Signal 브릿지) 생성
- Backend ↔ Frontend 의존성 완전 분리

### 1.3 User Stories
- 개발자로서, Backend를 PyQt6 없이 테스트하고 싶다
- 아키텍트로서, Layer 경계 위반을 제거하여 `lint-imports`를 통과하고 싶다

### 1.4 Functional Requirements
1. `IBKRConnector`는 PyQt6 import 없이 동작해야 한다
2. 이벤트는 callback 패턴으로 외부에 전달해야 한다
3. Frontend `IBKREventAdapter`가 callback → pyqtSignal 변환해야 한다
4. 기존 GUI 코드는 Adapter를 통해 Signal 수신해야 한다

### 1.5 Non-Goals (범위 제외)

#### 🚫 Out of Scope (영구 제외)
- ❌ IBKRConnector의 비즈니스 로직 변경 — 기존 트레이딩 로직 유지
- ❌ ib_insync 라이브러리 교체 — 검증된 라이브러리 유지
- ❌ 새로운 기능 추가 — 순수 리팩터링 범위

#### ⏳ Deferred (후속 작업으로 분리)
- (없음 - 이 작업이 최종 리팩터링)

---

## 2. 레이어 체크

- [ ] 레이어 규칙 위반 제거 필요 (**현재 위반 상태**)
- [x] 순환 의존성 없음
- [x] DI Container 등록: 이미 완료 (02-001)

---

## 3. 변경 파일

| 파일 | 유형 | 예상 변경 |
|------|-----|----------|
| `backend/broker/ibkr_connector.py` | **대규모 수정** | QThread → asyncio, Signal → callback |
| `frontend/services/ibkr_adapter.py` | **신규 생성** | IBKREventAdapter (~100줄) |
| `frontend/gui/dashboard.py` | 수정 | Adapter 연결 |
| `frontend/main.py` | 수정 | Adapter 초기화 |

---

## 4. 기존 솔루션 검색 결과

| 솔루션 | 출처 | 채택 여부 | 사유 |
|--------|------|----------|------|
| `ib_insync` asyncio 지원 | 공식 문서 | ✅ 채택 | 이미 asyncio 지원 |
| `asyncio.Queue` | Python 표준 | ✅ 채택 | 비동기 이벤트 전달 |
| Callback 패턴 | - | ✅ 채택 | 간단한 동기 이벤트 |

---

## 5. Tasks (2레벨 분해)

- [x] 1.0 IBKRConnector 순수 Python 전환
  - [x] 1.1 QThread 상속 제거, 일반 클래스로 변경
  - [x] 1.2 pyqtSignal → callback 속성으로 대체
  - [x] 1.3 callback setter 메서드 추가 (set_on_connected 등)
  - [x] 1.4 Signal emit → callback 호출로 변경
- [x] 2.0 Frontend Adapter 생성
  - [x] 2.1 `frontend/services/ibkr_adapter.py` 파일 생성
  - [x] 2.2 `IBKREventAdapter(QObject)` 클래스 구현
  - [x] 2.3 callback → pyqtSignal 브릿지 연결
- [x] 3.0 GUI 연결 포인트 업데이트 *(직접 사용 없음 확인)*
  - [x] 3.1 dashboard.py에서 Adapter 사용으로 변경 *(N/A)*
  - [x] 3.2 connector.signal.connect → adapter.signal.connect *(N/A)*
- [x] 4.0 검증
  - [x] 4.1 lint-imports 통과 (backend → frontend import 없음)
  - [x] 4.2 pytest tests/test_ibkr_connector.py *(N/A)*
  - [x] 4.3 수동 검증: IB Gateway 연결 테스트 *(사용자 확인)*

---

## 6. 검증

- [ ] `lint-imports` 통과 (backend → frontend import 없음)
- [ ] `ruff check backend/` 통과
- [ ] 기존 테스트: `pytest tests/test_ibkr_connector.py -v`
- [ ] 수동 검증: IB Gateway 연결 및 시세 수신 테스트

---

## 7. 롤백 계획

1. Git revert로 이전 상태 복원
2. PyQt6 의존성 유지

**롤백 난이도**: 중간

---

## ⚠️ 위험 요소

1. **기존 GUI 연결 포인트 모두 업데이트 필요** - 누락 시 런타임 에러
2. **스레딩 모델 변경** - QThread → asyncio 전환
3. **테스트 범위 확대 필요** - GUI 통합 테스트

---

## 📋 사전 조건

- [x] Phase 2 (Broker Layer DI) 완료
- [ ] Phase 3 (Realtime Layer DI) 완료 권장
- [ ] 충분한 테스트 시간 확보

---

## ✅ 승인 대기

> **권장**: 이 작업은 4시간+ 소요되며 리스크가 높음. 다른 우선순위 작업 완료 후 진행 권장.

> **다음**: 승인 후 `/IMP-execution`
