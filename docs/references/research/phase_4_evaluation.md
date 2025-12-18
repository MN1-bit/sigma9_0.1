# Phase 4 개발 단계 평가 (Phase 4 Development Steps Evaluation)

## 1. 개요 및 현재 상태

Phase 3 완료 시점에서 Sigma9 애플리케이션은 **모놀리식 데스크탑 애플리케이션 (Monolithic Desktop Application)** 형태로 작동하고 있습니다. Frontend의 `BackendClient`는 동일한 프로세스 내에서 `IBKRConnector`, `Scanner`, `Engine`과 같은 Backend 클래스들을 직접 import하여 제어합니다.

이는 로컬 테스트에는 적합하지만, **Phase 4**는 "지능(Intelligence)" (LLM)과 "신뢰성(Reliability)" (Logging)을 도입하고, **Phase 5** (AWS Migration)를 준비하는 것을 목표로 하고 있습니다.

## 2. Phase 4 전략적 분석

현재설정된 Phase 4 계획은 다음과 같습니다:
- **4.1**: LLM Oracle 통합
- **4.2**: 로깅 및 데이터 영속성 (Persistence)
- **4.3**: FastAPI 서버 및 API 계층
- **4.4**: GUI 패널 통합

### 논리적 간극 (Logic Gap): 구형 아키텍처 위에 기능 구축
만약 **FastAPI 서버(4.3)** 구축 *전에* **LLM(4.1)**과 **로깅(4.2)**을 먼저 구현한다면, 이 기능들은 모놀리식 구조에 강하게 결합된 형태로 만들이질 가능성이 높습니다. 이후 Step 4.3에서 모놀리식 구조를 Client-Server 구조로 분리할 때, 기껏 만들어둔 LLM 및 로깅 모듈을 네트워크 통신이나 격리된 서버 프로세스에서 작동하도록 리팩토링(재작업)해야 하는 상황이 발생합니다.

### 권장 사항: "아키텍처 우선 (Architecture First)" 접근
재작업을 최소화하기 위해, **Client-Server 아키텍처 분리 (FastAPI)**를 Phase 4의 **최우선 과제**로 삼아야 합니다. "두뇌(Backend)"가 "신체(Frontend)"에서 분리되고 나면, "지능(LLM)"을 추가하는 작업은 단순히 서버에 엔드포인트를 추가하는 깔끔한 작업이 됩니다.

## 3. 상세 권장 사항

### 3.1 단계 재배치 (Reordering Steps)
아키텍처 변환을 최우선으로 하도록 Phase 4 순서를 재배치할 것을 권장합니다.

*   **Step 4.1 (New)**: **FastAPI 서버 및 API 계층 (기존 4.3)**
    *   원격 접속이 가능한 Backend의 기틀을 마련합니다.
    *   **Phase 5.1** (Backend/Frontend 분리) 내용을 미리 흡수하여 수행합니다.
*   **Step 4.2 (New)**: **GUI 클라이언트 어댑터 (기존 4.4)**
    *   `BackendClient`를 `httpx` 및 `websockets`을 사용하도록 리팩토링합니다.
    *   `Connect`/`Disconnect` 기능이 실제로 별도 프로세스와 통신하는지 검증합니다.
*   **Step 4.3 (New)**: **로깅 및 영속성 (기존 4.2)**
    *   `loguru`와 SQLite를 *서버 측*에 구현합니다.
    *   WebSocket을 통해 로그를 Client로 스트리밍합니다 (이미 API 계획에 포함됨).
    *   서버가 분리되어 있을 때 "서버 저널(Server Journal)"을 설계하기 훨씬 수월합니다.
*   **Step 4.4 (New)**: **LLM Oracle 통합 (기존 4.1)**
    *   `/api/oracle` 엔드포인트를 추가합니다.
    *   전체 컨텍스트와 로그에 접근 권한이 있는 Server가 LLM에 질의를 수행합니다.
    *   Client는 결과를 받아 표시하기만 하면 됩니다.

### 3.2 누락된 구성 요소 (Missing Components)

1.  **작업 스케줄러 (Job Scheduler) - AWS 배포 시 필수**
    *   **배경**: 마스터플랜에는 "일일 설정(Daily Setup)" (스캐닝)이 언급되어 있습니다. AWS 환경에서는 GUI 연결 여부와 관계없이 오전 8:00 / 9:00에 이 작업이 자동으로 수행되어야 합니다.
    *   **조치**: Backend Server에 `APScheduler` 등을 구현하여 `run_scan()` 및 `update_market_data()`를 자동으로 실행하는 하위 태스크를 추가해야 합니다.

2.  **상태 동기화 (State Synchronization)**
    *   **배경**: GUI가 실행 중인 Server에 재접속할 때, *현재 상태* (진행 중인 주문, 보유 포지션, 최근 로그 등)를 다운로드해야 합니다.
    *   **조치**: Step 4.2 (GUI 어댑터)에 접속 시 "Sync State" 프로토콜 구현을 포함해야 합니다.

3.  **설정 관리 분리 (Config Management Split)**
    *   **배경**: `settings.yaml`은 "클라이언트 설정" (테마, IP 주소)과 "서버 설정" (API 키, 리스크 한도)으로 구분되어야 합니다.
    *   **조치**: Step 4.1에 "설정 분리(Split Configuration)" 작업을 포함해야 합니다.

## 4. 개정된 Phase 4 계획 (제안)

다음은 논의를 위한 제안된 구조입니다.

### Step 4.1: 아키텍처 전환 (Client-Server 분리)
- [ ] 4.1.1: **Refactor Config**: `settings.yaml`을 `server_config.yaml`과 `client_config.yaml`로 분리
- [ ] 4.1.2: **Server Core**: FastAPI를 사용하여 `backend/server.py` 생성
- [ ] 4.1.3: **API Endpoints**: `/api/status`, `/api/control`, `/ws/feed` 구현
- [ ] 4.1.4: **Job Scheduler**: 장 시작 시 자동 스캐닝을 위한 `APScheduler` 구현

### Step 4.2: Frontend 통합
- [ ] 4.2.1: **BackendClient Refactor**: 직접 import 구문을 `RestAdapter` 및 `WsAdapter`로 교체
- [ ] 4.2.2: **State Sync**: 접속 시 `sync_initial_state()` 로직 구현
- [ ] 4.2.3: **Verify Decoupling**: 로컬 Backend 코드 없이 Frontend가 독립 실행 가능한지 검증

### Step 4.3: 신뢰성 및 로깅 (Reliability & Logging)
- [ ] 4.3.1: **Structured Logging**: JSON 로테이션을 포함한 `loguru`를 서버에 설정
- [ ] 4.3.2: **Log Streaming**: WebSocket을 통해 `INFO` 레벨 이상의 로그를 Client 콘솔로 스트리밍
- [ ] 4.3.3: **Trade Journal DB**: 거래 내역을 SQLite에 영구 저장

### Step 4.4: 지능화 (LLM Intelligence)
- [ ] 4.4.1: **Oracle Service**: 서버 측에 `LLMOracle` 구현
- [ ] 4.4.2: **Analysis Endpoints**: `/api/oracle/analyze/{ticker}` 엔드포인트 구현
- [ ] 4.4.3: **GUI Display**: LLM 분석 결과를 툴팁이나 사이드 패널에 표시

## 5. 결론
현재 계획된 태스크들의 *내용*은 정확하지만 *순서*가 최적화되지 않았습니다. 아키텍처 분리(Architecture Split)를 가장 먼저 수행함으로써, 고급 기능(LLM, Logging)들이 최종 프로덕션 아키텍처 위에서 안정적으로 구축되도록 하여 미래의 "모놀리스 기술 부채(Monolith Debt)"를 방지해야 합니다.
