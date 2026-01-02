# MEP v3.2 — Microstructure Execution Protocol

---

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

## 3. 세션 프로토콜 (Session Protocol)

### 3.1 세션 정의

| Session | 시간 (ET) | 설명 |
|---------|-----------|------|
| **PRE_EARLY** | 04:00-07:00 | 프리마켓 초반, 유동성 매우 낮음 |
| **PRE_LATE** | 07:00-09:30 | 프리마켓 후반, 뉴스 반응 |
| **REG_EARLY** | 09:30-10:30 | 정규장 오픈, 변동성 높음 |
| **REG_MID** | 10:30-14:00 | 정규장 중반, 안정적 유동성 |
| **REG_LATE** | 14:00-16:00 | 정규장 후반, 포지션 정리 |
| **POST_EARLY** | 16:00-18:00 | 에프터 초반, 실적 반응 |
| **POST_LATE** | 18:00-20:00 | 에프터 후반, 유동성 급감 |

### 3.2 Session Multiplier (예산 승수)

| Session | Multiplier |
|---------|------------|
| PRE_EARLY | 0.5 |
| PRE_LATE | 0.8 |
| REG | 1.0 |
| POST_EARLY | 0.6 |
| POST_LATE | 0.3 |

### 3.3 4차원 버킷 시스템

$$
Bucket(s,t) = (Stock\_Tier, Session, Time\_Bucket, VIX\_Regime)
$$

#### Stock Tier

| Tier | 시가총액 |
|------|---------|
| MEGA | >$200B |
| LARGE | $10B-$200B |
| MID | $2B-$10B |
| SMALL | <$2B |

#### VIX Regime

| Regime | VIX 범위 |
|--------|---------|
| low | < 15 |
| normal | 15-25 |
| high | 25-35 |
| extreme | ≥ 35 |

### 3.4 Session-Specific Level Sets

| Session | 레벨 후보 |
|---------|----------|
| PRE | PDC, PDH, PDL, ATR_Upper, ATR_Lower, Rolling_PMH |
| REG | PMH, PDH, PDL, VWAP, HOD, LOD |
| POST | HOD, LOD, VWAP, PDC, AH_High, AH_Low |

#### ATR Bands

$$
ATR\_Upper = PDC + k \times ATR_{14}
$$
$$
ATR\_Lower = PDC - k \times ATR_{14}
$$

| Session | k |
|---------|---|
| PRE_EARLY | 0.5 |
| PRE_LATE | 0.75 |
| REG | 1.0 |
| POST_EARLY | 0.75 |
| POST_LATE | 0.5 |

#### Rolling PMH

$$
Rolling\_PMH(t) = \max\{P(\tau) : \tau \in [PRE\_OPEN, t]\}
$$

### 3.5 Session-Aware Hold Duration

$$
HoldDuration = BaseDuration \times SessionFactor \times TierFactor
$$

| Session | SessionFactor |
|---------|---------------|
| PRE_EARLY | 4.0 |
| PRE_LATE | 2.5 |
| REG | 1.0 |
| POST_EARLY | 2.0 |
| POST_LATE | 5.0 |

| Tier | TierFactor |
|------|------------|
| MEGA | 1.0 |
| LARGE | 1.0 |
| MID | 1.5 |
| SMALL | 2.0 |

### 3.6 Session-Aware Gates

#### Activity Gate

$$
TickCount_{1m} \geq N_{min}(session)
$$

| Session | N_min |
|---------|-------|
| PRE_EARLY | 5 |
| PRE_LATE | 15 |
| REG | 50 |
| POST_EARLY | 15 |
| POST_LATE | 5 |

#### Liquidity Gate

$$
\overline{Volume}_{10min} \geq V_{min}(session)
$$

| Session | V_min |
|---------|-------|
| PRE_EARLY | 5,000 |
| PRE_LATE | 10,000 |
| REG | 50,000 |
| POST_EARLY | 10,000 |
| POST_LATE | 3,000 |

### 3.7 Session End Exit

$$
SESSION\_END = t \geq session_{end} - 5min
$$

PRE, POST 세션 종료 5분 전 자동 청산

### 3.8 Trailing Stop (세션 적응)

$$
TrailingStop = Entry - k \times ATR_{session}
$$

| Session | k |
|---------|---|
| PRE | 1.5 |
| REG | 1.0 |
| POST | 2.0 |

---

## 4. 시스템 설정 (Configuration)

### 4.1 파라미터 분류

| 구분 | 설명 | 예시 |
|------|------|------|
| **고정 (Hard Gate)** | 절대 넘으면 안 되는 임계값. 상수로 고정. | 스프레드 상위 5% 이상이면 무조건 진입 금지 |
| **유동 (Soft/Rank)** | 상대적 순위로 판단. 상수 없음. | 상위 K개만 관심, TopH만 보유 |
| **운영 파라미터** | 리소스/용량 제한. 운영 상황에 따라 조정. | 최대 동시보유 수, 예산 상한 |

### 4.2 파라미터 상세

| 구분 | 항목 |
|------|------|
| **고정(상수 임계)** | $q^{self}_{spread} \ge 0.95$ (비용 폭탄), $O_s(t) \in TopY$ (나쁜 과열) |
| **유동(무상수)** | rank/TopK/예산/이벤트/Market Permission |
| **운영 파라미터** | $N$(스캔대상수), $K$(관심종목수), $H$(보유종목수), $M_{max}$(최대예산), $X$(체결품질예산), $Y$(리스크예산), $L_{tf}$(TF지속조건), $EmergencyThresh$(긴급전환임계) |

---

## 5. 구현 아키텍처 (Implementation)

### 5.1 데이터 파이프라인

```
Data → Normalize → Score → State → Order
```

**흐름 설명:**
1. **Data**: 원시 데이터 수집
2. **Normalize**: 표준화 (분위수/랭크 변환)
3. **Score**: 각종 점수 계산
4. **State**: 상태머신 상태 전이
5. **Order**: 주문 실행

### 5.2 모듈별 역할

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

### 5.3 상태 흐름

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

## 6. SCAN: 유니버스 → 후보군

### 6.1 표준화 규칙 (Session-Aware)

#### Self-Quantile (세션 분리)

각 종목의 원시 지표는 **종목/세션/버킷별** 경험분포로 분위수화:

$$
q^{self,session}_{x,s}(t)=F_{x,s,session,b(t)}(x_s(t))
$$

#### Cross-Section Rank (세션 범위)

**동일 세션 활성 종목** 내에서만 절대 수준 비교:

$$
r^{xs,session}_{x}(s,t)=rank_{j\in U^{session}(t)}(x_j(t))
$$

> **Session-Scoped Universe**: 해당 세션에서 최소 유동성 조건을 충족하는 종목만 포함

### 6.2 입력 신호 (1m 봉 기반 피처)

| 카테고리 | 피처 | 계산 방식 |
|----------|------|----------|
| 관심/유동성 | $vol_{1m}$ | 1m 봉 거래량 |
| 과열/변동 | $range_{1m}$ | (High - Low) / Open |
| 체결 가속 | $tick\_intensity_{1m}$ | 1m 내 체결 건수 |
| 압력/불균형 | $ofi_{1m}$ | 1m 내 OFI 누적 |
| 비용(핵심) | $spread_{1m}$ | 1m 평균 스프레드 |
| 레벨 이벤트 | Touch/Hold/Fail + ActiveLevel | 레벨 상호작용 |

### 6.3 핵심 스코어 (Session-Aware)

#### Ready(임박 강도)

$$
R_s^{session}(t)=rank_{session}(q^{self,session}_{ofi,s}(t)) + rank_{session}(q^{self,session}_{tick,s}(t)) + rank_{session}(q^{self,session}_{vol\_accel,s}(t))
$$

#### Cost(거래 불리)

$$
C_s^{session}(t)= rank_{session}(q^{self,session}_{spread,s}(t)) + rank_{session}(r^{xs,session}_{spread}(s,t)) + rank_{session}(q^{self,session}_{range,s}(t)) + rank_{session}(r^{xs,session}_{range}(s,t))
$$

#### Tradeability(먹힘 가능성)

$$
T_s^{session}(t)=R_s^{session}(t)-C_s^{session}(t)
$$

### 6.4 SCAN 스코어 (Session-Scoped)

$$
S^{scan,session}_s(t)=rank_{session}(r^{xs,session}_{vol}(s,t)) - rank_{session}(r^{xs,session}_{spread}(s,t))
$$

$$
\mathcal{C}(t)=TopN(S^{scan,session}(t))
$$

### 6.5 Empty Bar Gate

$$
empty\_bar\_ratio_{10} < 0.7
$$

최근 10봉 중 빈 봉(거래 없는 봉) 비율이 70% 이상이면 SCAN 제외

---

## 7. MACRO PERMISSION: 셋업 권한부여(5m)

### 7.1 MacroScore (Session-Aware)

$$
MacroScore_s^{session}(t)=rank_{session}(q^{self,session}_{rvol,5m})+rank_{session}(q^{self,session}_{trend,5m})+rank_{session}(q^{self,session}_{level\_event,5m})
$$

$$
\mathcal{M}(t)=TopK(MacroScore^{session}(t))
$$

### 7.2 Market Permission + Dispersion Budget (Session-Aware)

v3.2는 세션별 예산 승수를 적용하여 Extended Hours 적응:

#### Market Cost/Heat 분위수 (Session-Scoped)

$$
Spread^{mkt,session}(t)=median_{s\in U^{session}(t)}(spread_s(t))
$$
$$
q^{mkt,session}_{spread}(t)=F_{Spread^{mkt},session,b(t)}(Spread^{mkt,session}(t))
$$

range도 동일 ($q^{mkt,session}_{range}$).

#### Dispersion 분위수

$$
D(t)=IQR(\{T_s^{session}(t)\}_{s\in U^{session}(t)})
$$
$$
q_D(t)=F_{D,session,b(t)}(D(t))
$$

### 7.3 동적 진입 예산 M(t) (Session-Aware)

$$
M(t)=\Big\lfloor M_{max}\cdot SessionMultiplier \cdot (1-q^{mkt,session}_{spread}(t))\cdot (1-q^{mkt,session}_{range}(t))\cdot q_D(t)\Big\rfloor
$$

*   장이 비싸고/과열이면 → M 감소
*   엣지가 납작하면 → M 감소 (무엣지 자동 휴식)
*   Extended Hours면 → SessionMultiplier로 추가 감소

> **예산이 0으로 수렴**하게 만드는 방식 + **세션 적응**

---

## 8. PRIME: 임박 모드

### 8.1 PRIME 집합

$$
\mathcal{P}(t)=TopK(R^{session}(t))
$$

Persist(상대적 지속성)로 prime 유지/해제.

### 8.2 Hard Gates (Session-Aware)

#### Gate #1 비용 폭탄 (Session-Relative)

$$
q^{self,session}_{spread,s}(t)\ge 0.95 \Rightarrow \text{진입 금지}
$$

#### Gate #2 Smart Overheat (Session-Aware)

**"Flow가 없는 공허한 급등"**만 차단:

$$
O_s^{session}(t) = rank_{session}(q^{self,session}_{range,s}(t)) - rank_{session}(q^{self,session}_{vol,s}(t)) - rank_{session}(q^{self,session}_{ofi,s}(t))
$$

$$
O_s^{session}(t) \in TopY(RiskBudget, session) \Rightarrow \text{진입 금지}
$$

#### Gate #3 Activity Gate

$$
TickCount_{1m}(s,t) \geq N_{min}(session) \Rightarrow \text{통과}
$$

#### Gate #4 Liquidity Gate

$$
\overline{Volume}_{10min}(s,t) \geq V_{min}(session) \Rightarrow \text{통과}
$$

> 변동성은 1등인데, 거래량과 OFI는 꼴등 = **나쁜 과열(Bad Volatility)**
> 최소 체결 건수/거래량 미달 = **진입 불가**

---

## 9. TF SELECT: 타임프레임 선택

### 9.1 대상

$$
\mathcal{M}(t)\cap\mathcal{P}(t)
$$

### 9.2 타임프레임 레이어 (Dual-Mode)

| 레이어 | 용도 | TF |
|--------|------|-----|
| Setup | 권한부여 | 5m (Bar Mode) |
| Execution | 진입/관리 | TF-Adaptive (Bar Mode) |
| Micro | 체결 정밀도 | tick (Tick Mode, ENTRY/INPOS에서만) |

### 9.3 TF 후보 (v3.2 확대)

$$
T_{exec}=\{1m,2m,3m,5m,10m,15m\}
$$

#### Session별 TF 제약

| Session | 허용 TF | 최적 TF |
|---------|---------|---------|
| PRE_EARLY | {5m, 10m, 15m} | 10m |
| PRE_LATE | {3m, 5m, 10m} | 5m |
| REG_EARLY | {1m, 2m, 3m, 5m} | 1-2m |
| REG_MID | {1m, 2m, 3m, 5m} | 2-3m |
| REG_LATE | {2m, 3m, 5m} | 3-5m |
| POST_EARLY | {3m, 5m, 10m} | 5m |
| POST_LATE | {5m, 10m, 15m} | 10m |

### 9.4 TFScore (Session-Aware)

$$
TFScore(s,t,\tau,session)=S(s,t,\tau)-C(s,t,\tau)-N(s,t,\tau)+SessionBonus(\tau,session)
$$

$$
SessionBonus(\tau, session) = \begin{cases}
+1 & \text{if } \tau \in T_{optimal}(session) \\
0 & \text{if } \tau \in T_{allowed}(session) \\
-\infty & \text{if } \tau \notin T_{allowed}(session)
\end{cases}
$$

$$
tf^{cand}_{exec}(s,t)=\arg\max_{\tau\in T_{allowed}(session)} TFScore(s,t,\tau,session)
$$

### 9.5 Persist 기반 TF 전환 (Session-Aware)

$$
tf_{exec}(s,t)=
\begin{cases}
tf^{cand}(s,t) & \text{if } R_s^{session}(t) \ge R_{emergency}(session) \text{ (Emergency)} \\
tf^{cand}(s,t) & \text{if } tf^{cand} \text{ wins for } L_{tf}(session) \text{ consecutive} \\
tf_{exec}(s,t-1) & \text{otherwise}
\end{cases}
$$

| Session | $R_{emergency}$ | $L_{tf}$ |
|---------|-----------------|----------|
| PRE | 0.95 | 3 bars |
| REG | 0.99 | 5 bars |
| POST | 0.95 | 3 bars |

> Extended Hours에서는 더 민첩하게 반응 (임계 낮춤, 지속 조건 완화)

---

## 10. ENTRY/BUY: 진입 (Hold + FlowConfirm + 예산)

### 10.1 Level 시스템 (Session-Specific)

#### 레벨 후보 (세션별)

| Session | 레벨 후보 |
|---------|----------|
| PRE | PDC, PDH, PDL, ATR_Upper, ATR_Lower, Rolling_PMH |
| REG | PMH, PDH, PDL, VWAP, HOD, LOD |
| POST | HOD, LOD, VWAP, PDC, AH_High, AH_Low |

#### LevelScore (Session-Aware)

| 요소 | 설명 |
|------|------|
| Reaction(L) | Touch 이후 유리방향 확장 |
| FlowConfirm(L) | Touch 구간에서 OFI/틱/거래대금 동반 |
| Fail(L) | Fail 이벤트 빈도/최근성 |
| Fatigue(L) | 최근 Touch 반복 횟수 (감점) |

$$
LevelScore(L,session)=rank_{session}(Reaction_L)+rank_{session}(FlowConfirm_L)-rank_{session}(Fail_L)-rank_{session}(Fatigue_L)+Recency\_Bonus(L)
$$

$$
ActiveLevel(s,t,session)=\arg\max_{L \in L(session)} LevelScore(L,session)
$$

### 10.2 게이트 통과 집합

$$
\mathcal{E}(t)=\{s\in\mathcal{P}(t)\cap\mathcal{M}(t): Touch_{L}(t)=1,\ GatesOK\}
$$

(GatesOK: Spread + Overheat + Activity + Liquidity 게이트 모두 통과)

### 10.3 FlowConfirm (Session-Aware)

$$
FC_s^{session}(t)=rank_{session}(q^{self,session}_{ofi,s}(t)) + rank_{session}(q^{self,session}_{tick,s}(t)) + rank_{session}(q^{self,session}_{vol,s}(t))
$$

### 10.4 최종 진입 집합 (예산 기반)

$$
\mathcal{B}(t)=TopM(T^{session}(t))\cap TopX(FC^{session}(t))\cap \mathcal{E}(t)
$$

*   $M=M(t)$ (Session-Aware 동적 예산)
*   $X$: 동시 체결 품질 예산

### 10.5 PreTrigger Zone (Tick Mode 활성화)

$$
PreTrigger: \quad P(t) \geq L \times (1 - \epsilon)
$$

$\epsilon = 0.002$ (0.2%)

레벨 0.2% 이내 진입 시 **Bar Mode → Tick Mode 전환**

### 10.6 BUY 트리거 (Tick Mode)

$$
Hold_L(t)=\mathbf{1}\{P(\tau)>L,\ \forall \tau \in [t, t + HoldDuration]\}=1 \Rightarrow BUY
$$

### 10.7 포지션 사이징

#### Tradeability 기반 softmax 분배

$$
w_s(t)=\frac{\exp(\alpha \cdot z(T_s^{session}(t)))}{\sum_{j\in \mathcal{B}(t)}\exp(\alpha \cdot z(T_j^{session}(t)))}
$$

#### 비용 기반 소프트 사이즈 컷

$$
size_s \propto w_s(t)\cdot (1-q^{self,session}_{spread,s}(t))\cdot (1-O_s^{session}(t))
$$

---

## 11. INPOS/EXIT: 보유 및 청산

### 11.1 기본 보유(랭크 유지)

$$
s\in TopH(T(t)) \Rightarrow Hold
$$

### 11.2 SELL-FAIL (레벨 실패 + T 붕괴)

$$
Fail_L(t)=\mathbf{1}\{P(t)<L \wedge P(t+1s)<L\}=1
$$
$$
Fail_L(t)=1\ \wedge\ rank(T_s(t))\downarrow \Rightarrow SELL
$$

### 11.3 SELL-END (TopH 이탈)

$$
s\notin TopH(T(t)) \Rightarrow SELL
$$

### 11.4 SELL-FT (Follow-through 붕괴)

진입 이후 강도/확장이 유지되지 않으면 청산:

$$
\Delta R_s(t)=R_s(t)-R_s(t_{entry})
$$
$$
FT_s(t)=rank(\Delta R_s(t)) + rank(\text{post-entry expansion})
$$
$$
s\notin TopY(FT(t)) \Rightarrow SELL
$$

---

## 12. 백테스트/실전 주의사항 (Cautions)

### 12.1 미래 정보 누수 방지

- 분위수/랭크 계산은 **반드시 온라인(롤링) 방식**으로
- 미래 데이터가 과거 계산에 유입되면 백테스트 결과가 과대평가됨

### 12.2 레벨 정의 시점 고정

- **PMH(Pre-Market High)**: 장전 거래 기준, 정규장 시작 전에 확정
- **PDH(Previous Day High)**: 전일 종가 기준
- **VWAP**: 당일 누적으로 실시간 계산

### 12.3 체결 가정

- 최소한의 **fill/slippage 가정** 포함 필수
- 안 넣으면 Gate/Cost가 과소평가되어 실전과 괴리 발생

### 12.4 생존편향 주의

- 유니버스 정의 시 **상장폐지/합병 종목** 포함 여부 확인
- 현재 기준 유니버스만 사용하면 과거 실패 종목이 빠져 과대평가
