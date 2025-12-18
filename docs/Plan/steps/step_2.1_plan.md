# Step 2.1: IBKR Connector (Data Feed) 구현 계획

> **작성일**: 2025-12-18  
> **Phase**: 2 (Core Engine)  
> **목표**: IB Gateway를 통한 실시간 데이터 연동 구현

---

## 1. 배경 및 목적

`masterplan.md` 2.1절에 따라 Backend 브로커 연동 모듈을 구현한다.  
QS-Gen2-01 프로젝트의 `bridge.py`를 **최소한으로 참조**하여, Sigma9에 맞게 단순화된 `IBKRConnector`를 구현한다.

### 참조 코드에서 채택할 패턴
| 패턴 | 설명 | 채택 여부 |
|------|------|-----------|
| QThread 기반 비동기 | GUI 블로킹 방지 | ✅ 채택 |
| pyqtSignal 통신 | 스레드→GUI 이벤트 전달 | ✅ 채택 |
| `.env` 설정 로드 | 민감 정보 분리 | ✅ 채택 |
| Exponential Backoff | 재시도 안정성 | ✅ 채택 |
| VIX 선물 구독 | 복잡한 선물 계약 처리 | ❌ 제외 (향후) |
| 포지션/주문 조회 | OMS 기능 | ❌ 제외 (Step 3.1) |

### 제외 이유
- **최소 기능 먼저**: Step 2.1은 "연결 + 데이터 수신"에만 집중
- **점진적 확장**: OMS, VIX 선물 등은 후속 단계에서 추가

---

## 2. 필요 환경 변수

`docs/references/core/.env`에서 확인된 필수 변수:

```env
# IBKR 연결 설정
IB_HOST=127.0.0.1
IB_PORT=4002           # IB Gateway Paper Trading
IB_CLIENT_ID=1         # 고유 클라이언트 ID
IB_ACCOUNT=            # Paper Trading 계좌 (선택)
```

---

## 3. Proposed Changes

### 3.1 환경 설정

#### [NEW] [.env.example](file:///d:/Codes/Sigma9-0.1/.env.example)

프로젝트 루트에 환경 변수 템플릿 생성:
- `IB_HOST`, `IB_PORT`, `IB_CLIENT_ID`, `IB_ACCOUNT` 정의
- 주석으로 설정 가이드 포함

---

### 3.2 IBKR Connector 구현

#### [NEW] [ibkr_connector.py](file:///d:/Codes/Sigma9-0.1/backend/broker/ibkr_connector.py)

핵심 클래스 `IBKRConnector` 구현:

**클래스 구조**:
```
IBKRConnector(QThread)
├── Signals
│   ├── connected(bool)        # 연결 상태
│   ├── price_update(dict)     # 실시간 시세
│   ├── account_update(dict)   # 계좌 정보
│   └── error(str)             # 에러 메시지
│
├── Connection
│   ├── __init__()             # 설정 로드
│   ├── run()                  # 스레드 메인 루프
│   ├── stop()                 # 연결 중지
│   └── is_connected()         # 상태 확인
│
└── Market Data
    ├── subscribe_ticker(symbols)   # 시세 구독
    ├── unsubscribe_ticker(symbol)  # 구독 해제
    └── _on_price_update(ticker)    # 콜백 처리
```

**핵심 구현 사항**:
1. `.env`에서 연결 정보 로드 (`dotenv`)
2. `ib_insync.IB` 객체로 연결 관리
3. 연결 실패 시 최대 3회 재시도 (Exponential Backoff)
4. 실시간 시세는 `reqMktData()` + `updateEvent` 콜백

---

### 3.3 패키지 설정

#### [MODIFY] [__init__.py](file:///d:/Codes/Sigma9-0.1/backend/broker/__init__.py)

`IBKRConnector` 클래스 export 추가

---

## 4. Verification Plan

### 4.1 Syntax Check (자동)

```powershell
# Python 문법 검사
python -m py_compile backend/broker/ibkr_connector.py
```

이 명령이 에러 없이 통과해야 함.

---

### 4.2 Unit Test (자동) - 신규 작성

#### [NEW] `tests/test_ibkr_connector.py`

Mock 기반 단위 테스트:
- `test_init_loads_config`: `.env` 설정 로드 확인
- `test_signal_emission`: pyqtSignal 발생 확인
- `test_connection_retry`: 재시도 로직 검증

```powershell
# 테스트 실행
pytest tests/test_ibkr_connector.py -v
```

> **Note**: 실제 IB Gateway 연결 없이 Mock으로 테스트

---

### 4.3 Integration Test (수동 - 사용자 검증 필요)

> [!IMPORTANT]
> 이 테스트는 **IB Gateway가 실행 중이어야만** 가능합니다.

**사전 조건**:
1. IB Gateway 실행 (Paper Trading, 포트 4002)
2. `.env` 파일 설정 완료

**테스트 절차**:
```powershell
# 1. 연결 테스트 스크립트 실행
python backend/broker/ibkr_connector.py
```

**예상 출력** (IB Gateway 연결 시):
```
🔌 IBKR 연결 시도 중...
📡 연결 시도 1/3...
✅ IBKR 연결 성공! (포트: 4002)
📡 실시간 시세 구독: SPY (Extended Hours)
🔔 가격 수신: SPY $XXX.XX
```

**실패 시 예상 출력** (IB Gateway 미실행):
```
⚠️ 연결 실패: ...
⏳ 1초 후 재시도...
❌ 연결 오류: ...
```

---

## 5. 의존성

`requirements.txt`에 추가 필요:
```
ib_insync>=0.9.86
python-dotenv>=1.0.0
```

---

## 6. 위험 요소

| 위험 | 대응 |
|------|------|
| IB Gateway 미실행 시 테스트 불가 | Mock 테스트로 기본 검증 |
| Paper Trading 구독 제한 | 단일 티커(SPY)로 최소 테스트 |
| 네트워크 불안정 | Exponential Backoff 재시도 |

---

## 7. 다음 단계

Step 2.1 완료 후:
- **Step 2.2**: Seismograph Strategy Scanning 구현
- `IBKRConnector`에서 수신한 데이터를 전략에 전달하는 인터페이스 연결
