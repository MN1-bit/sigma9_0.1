# MEP v3.2 — Overview

## 1. 철학 (Philosophy)

### 1.1 MEP란 무엇인가?

**MEP(Microstructure Execution Protocol)**는 단타 트레이딩을 위한 **상태머신 기반 실행 정책**입니다.

MEP는 "이 종목이 급등할 확률이 몇 %인가?"를 예측하는 시스템이 **아닙니다**.
대신, "지금 이 순간, 어떤 종목이 **가장 유리하게 거래될 수 있는가?**"를 판단하는 시스템입니다.

### 1.2 핵심 철학: Tradeability 우선

급등 예측보다 **거래 가능성(Tradeability)**을 우선합니다:

- 아무리 급등이 예상되어도, **스프레드가 너무 넓으면** 진입하지 않습니다
- 아무리 신호가 강해도, **거래량이 없으면** 진입하지 않습니다
- **"먹힐 수 있는 상황"**에서만 진입하고, 그렇지 않으면 쉽니다

### 1.3 v3.2 핵심 개념

#### Dual-Mode Architecture

의사결정과 실행을 분리하여 리소스 효율성과 실행 정밀도를 모두 확보:

| Mode | 사용 단계 | 데이터 |
|------|----------|--------|
| **Bar Mode** | SCAN → TF | 1m/5m 봉 |
| **Tick Mode** | ENTRY → EXIT | 실시간 tick |

#### Session-Aware Protocol

정규장뿐 아니라 프리마켓/에프터마켓에서도 동작하는 세션 적응형 시스템:

- **Session-Segmented Quantiles**: 세션별 독립 분위수 계산
- **Session Budget**: 세션별 예산 승수 적용
- **Session-Specific Levels**: 세션에 적합한 레벨 세트 사용

### 1.4 의사결정 구조

MEP의 모든 결정은 두 가지 레이어로 나뉩니다:

1. **Macro Permission (거시 허가)**: "오늘/지금 이 종목을 거래해도 되는가?"
2. **Micro Execution (미시 실행)**: "정확히 어느 가격, 어느 타이밍에 진입/청산하는가?"


---

## 2. 수식 및 설명 (Formulas)

### 2.1 목표 함수

$$
\max_{\pi}\ \mathbb{E}[PnL(\pi)]-\lambda\mathbb{E}[Cost(\pi)]-\mu\mathbb{E}[Risk(\pi)]
$$

**쉬운 설명:**
- **PnL(수익)은 최대화**하고
- **Cost(비용 = 스프레드, 슬리피지)는 최소화**하고
- **Risk(리스크 = 급락, 과열)는 최소화**합니다

λ와 μ는 비용과 리스크에 얼마나 민감하게 반응할지를 조절하는 가중치입니다.

### 2.2 의사결정 함수

$$
Decision = f(\text{Macro Permission}) \times g(\text{Micro Execution})
$$

**쉬운 설명:**
- **Macro Permission이 0이면** (= 거래 금지 상황) → 아무리 좋은 신호도 무시
- **Micro Execution이 0이면** (= 진입 타이밍 아님) → 대기
- **둘 다 1일 때만** 실제 진입이 발생

---

## 3. 시스템 설정 (Configuration)

### 3.1 파라미터 분류

| 구분 | 설명 | 예시 |
|------|------|------|
| **고정 (Hard Gate)** | 절대 넘으면 안 되는 임계값. 상수로 고정. | 스프레드 상위 5% 이상이면 무조건 진입 금지 |
| **유동 (Soft/Rank)** | 상대적 순위로 판단. 상수 없음. | 상위 K개만 관심, TopH만 보유 |
| **운영 파라미터** | 리소스/용량 제한. 운영 상황에 따라 조정. | 최대 동시보유 수, 예산 상한 |

### 3.2 파라미터 상세

| 구분 | 항목 |
|------|------|
| **고정(상수 임계)** | $q^{self}_{spread} \ge 0.95$ (비용 폭탄), $O_s(t) \in TopY$ (나쁜 과열) |
| **유동(무상수)** | rank/TopK/예산/이벤트/Market Permission |
| **운영 파라미터** | $N$(스캔대상수), $K$(관심종목수), $H$(보유종목수), $M_{max}$(최대예산), $X$(체결품질예산), $Y$(리스크예산), $L_{tf}$(TF지속조건), $EmergencyThresh$(긴급전환임계) |

---

## 4. 구현 아키텍처 (Implementation)

### 4.1 데이터 파이프라인

```
Data → Normalize → Score → State → Order
```

**흐름 설명:**
1. **Data**: 원시 데이터 수집
2. **Normalize**: 표준화 (분위수/랭크 변환)
3. **Score**: 각종 점수 계산
4. **State**: 상태머신 상태 전이
5. **Order**: 주문 실행

### 4.2 모듈별 역할

| 모듈 | 역할 | 상세 |
|------|------|------|
| **Ingestor** | 데이터 수집 | 1m/5m OHLC (Bar Mode), 체결/tick (Tick Mode) |
| **Feature Engine** | 피처 추출 | 거래량, 변동폭, 틱속도, OFI, 스프레드, 레벨이벤트 |
| **Normalizer** | 표준화 (SSOT) | $q^{self}$, $r^{xs}$, $q^{mkt}$, $q_D$ — 온라인 계산, 미래 누수 방지 |
| **Scoring** | 점수 계산 | Scan/Macro/R/C/T/TFScore/LevelScore/FC/FT/SmartOverheat |
| **State Machine** | 상태 전이 | SCAN → PERMIT → PRIME → TF → ENTRY → INPOS → EXIT |
| **Risk/Budget** | 리스크/예산 | M(t) 동적 예산, 포지션 사이징, 동시보유 제한 |
| **Execution** | 주문 실행 | 주문/체결/취소, 슬리피지 모델 |
| **Event Store** | 로그 저장 | 상태전이 "이유" 기록, 리플레이 가능 |

### 4.3 상태 흐름

```
SCAN → PERMIT → PRIME → TF → ENTRY → INPOS → EXIT
 ↑                                              ↓
 └──────────────────────────────────────────────┘
```

| 상태 | 설명 |
|------|------|
| SCAN | 전체 유니버스에서 후보군 선별 |
| PERMIT | Macro 권한 부여 (5분봉 기준) |
| PRIME | 임박 모드 진입 (실시간 모니터링) |
| TF | 최적 타임프레임 선택 |
| ENTRY | 진입 조건 충족 시 매수 |
| INPOS | 보유 중 (Hold 또는 Exit 판단) |
| EXIT | 청산 실행 후 SCAN으로 복귀 |

---

## 5. 백테스트/실전 주의사항 (Cautions)

### 5.1 미래 정보 누수 방지

- 분위수/랭크 계산은 **반드시 온라인(롤링) 방식**으로
- 미래 데이터가 과거 계산에 유입되면 백테스트 결과가 과대평가됨

### 5.2 레벨 정의 시점 고정

- **PMH(Pre-Market High)**: 장전 거래 기준, 정규장 시작 전에 확정
- **PDH(Previous Day High)**: 전일 종가 기준
- **VWAP**: 당일 누적으로 실시간 계산

### 5.3 체결 가정

- 최소한의 **fill/slippage 가정** 포함 필수
- 안 넣으면 Gate/Cost가 과소평가되어 실전과 괴리 발생

### 5.4 생존편향 주의

- 유니버스 정의 시 **상장폐지/합병 종목** 포함 여부 확인
- 현재 기준 유니버스만 사용하면 과거 실패 종목이 빠져 과대평가
