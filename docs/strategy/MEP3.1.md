# MEP v3.1 최종 오버뷰 (SSOT + 수식)

## 0) v3.1 변경 요약 (v3.0 → v3.1)

v3.0 대비 v3.1은 “상수 임계 추가”가 아니라, **랭크/예산/이벤트의 확장**으로 안정성을 올립니다.

1.  **비용/유동성 절대성 보강**: self-quantile(자기 분포) + cross-sectional rank(유니버스 비교) 병행
2.  **Market Permission(장 컨디션)로 예산 스케일링**: 나쁜 날 자동으로 M(t)↓
3.  **Dispersion(엣지 벌어짐) 기반 예산 스케일링**: 무엣지 날 자동 휴식
4.  **TF-Adaptive Churn 억제 + Emergency Override**: 평소엔 빈번한 전환 억제, 초급등 시엔 즉시 전환
5.  **Smart Overheat (좋은 과열 vs 나쁜 과열)**: 단순 Range 차단 대신, Flow가 없는 변동성만 정밀 타격

---

## 1) 시스템 정체성 (변경 없음)

MEP v3.1은 “급등 확률 예측기”가 아니라, **거래 가능성(Tradeability)과 기대값(EV)**을 최대화하는 **상태머신 기반 실행 정책 (\pi)** 입니다.

$$
\max_{\pi}\ \mathbb{E}[PnL(\pi)]-\lambda\mathbb{E}[Cost(\pi)]-\mu\mathbb{E}[Risk(\pi)]
$$

핵심 요약:

$$
Decision = f(\text{Macro Permission}) \times g(\text{Micro Execution})
$$

---

## 2) 표준화 규칙 (v3.1 핵심: 2트랙 표준화)

### 2.1 시간대 버킷

시각 ($t$)는 버킷 ($b(t)$)로 묶습니다.

### 2.2 Self-Quantile (이상치 탐지)

각 종목의 원시 지표 ($x_s(t)$)는 종목/버킷별 경험분포로 분위수화합니다.

$$
q^{self}_{x,s}(t)=F_{x,s,b(t)}(x_s(t))
$$

### 2.3 Cross-Section Rank (절대 수준/거래성 비교)

같은 시점 ($t$)에서 유니버스 ($U(t)$) 내 절대 수준 비교를 위해 교차랭크를 둡니다.

$$
r^{xs}_{x}(s,t)=rank_{j\in U(t)}(x_j(t))
$$

> v3.0의 “상대화” 장점은 유지하면서, **‘원래부터 비싼/얇은 종목’이 정상처럼 보이는 문제**를 제거합니다.

---

## 3) 입력 신호 (대표 피처 세트)

모든 피처는 **($q^{self}$)** 또는 **($r^{xs}$)** 또는 둘의 결합으로 사용합니다.

*   관심/유동성: ($q^{self}_{vol}$), ($r^{xs}_{vol}$)
*   과열/변동: ($q^{self}_{range}$), ($r^{xs}_{range}$)
*   체결 가속: ($q^{self}_{tick}$)
*   압력/불균형: ($q^{self}_{ofid}$)
*   비용(핵심): ($q^{self}_{spread}$) + ($r^{xs}_{spread}$)
*   레벨 이벤트: Touch/Hold/Fail + ActiveLevel(자동선정)

---

## 4) 하드 게이트 (Smart Overheat 반영)

완전 무상수 TopK의 “나쁜 날에도 1등이 존재” 문제를 막기 위해, v3.1 기준 **폭탄 2개만 하드 차단**합니다. 상수 임계($\ge 0.95$) 중 과열 부분은 **구조적 리스크 랭크**로 업그레이드되었습니다.

**Gate #1 비용 폭탄**
$$
q^{self}_{spread,s}(t)\ge 0.95 \Rightarrow \text{진입 금지}
$$

**Gate #2 Smart Overheat (New)**
단순 Range가 높다고 자르지 않고, **"Flow가 없는 공허한 급등"**만 자릅니다.
$$
O_s(t) = rank(q^{self}_{range,s}(t)) - rank(q^{self}_{vol,s}(t)) - rank(q^{self}_{ofid,s}(t))
$$
$$
O_s(t) \in TopY(\text{RiskBudget}) \Rightarrow \text{진입 금지}
$$
> 의미: 변동성은 1등인데(High Rank), 거래량과 OFI는 꼴등(Low Rank)인 상태 = **나쁜 과열(Bad Volatility)**.

---

## 5) 타임프레임 설계 (v3.1: Churn 억제 + Emergency Override)

### 5.1 레이어

*   Setup(권한부여): 5m
*   Execution(진입/관리): TF-Adaptive
*   Micro(보조): 1s/tick 가능 시

### 5.2 TF 후보

$$
T_{exec}=\{15s,30s,1m,2m,3m,5m\}
$$

### 5.3 TFScore (기존 유지)

$$
TFScore(s,t,\tau)=S(s,t,\tau)-C(s,t,\tau)-N(s,t,\tau)
$$
$$
tf^{cand}_{exec}(s,t)=\arg\max_{\tau\in T_{exec}} TFScore(s,t,\tau)
$$

### 5.4 Persist 기반 TF 전환 (Emergency Override 추가)

“매 tick마다 argmax로 바꾸는 것”을 억제하되, **극단적 임박 시에는 즉시 전환**합니다.

$$
tf_{exec}(s,t)=
\begin{cases}
tf^{cand}(s,t) & \text{if } R_s(t) \ge 0.99 \text{ (Emergency: Immediate Switch)} \\
tf^{cand}(s,t) & \text{if } tf^{cand} \text{ wins for } L_{tf} \text{ consecutive} \\
tf_{exec}(s,t-1) & \text{otherwise}
\end{cases}
$$

> $R_s(t) \ge 0.99$: 초급등(Ignition) 상황에서는 안정성($L_{tf}$)보다 기민함이 우선입니다.

---

## 6) 핵심 스코어 (v3.1: Cost에 xs-rank 추가)

### 6.1 Ready(임박 강도)

$$
R_s(t)=rank(q^{self}_{ofid,s}(t)) + rank(q^{self}_{tick,s}(t))
$$

### 6.2 Cost(거래 불리) — v3.1 핵심 변경

비용은 “자기 기준 이상치” + “유니버스 절대 수준”을 함께 봅니다.

$$
C_s(t)= rank(q^{self}_{spread,s}(t)) + rank(r^{xs}_{spread}(s,t)) + rank(q^{self}_{range,s}(t)) + rank(r^{xs}_{range}(s,t))
$$
*(Note: Range 항목은 Smart Overheat 도입으로 Gate에서는 빠졌지만, Cost 페널티로는 여전히 유효합니다.)*

### 6.3 Tradeability(먹힘 가능성)

$$
T_s(t)=R_s(t)-C_s(t)
$$

---

## 7) Market Permission + Dispersion Budget (v3.1 핵심)

v3.1은 “거래 여부”를 임계로 끊기보다, **예산 M(t)를 자동으로 줄여서 사실상 거래를 멈추게** 합니다.

### 7.1 Market Cost/Heat 분위수

유니버스 집계 비용/과열 지표(예: 스프레드 중앙값, 레인지 중앙값)를 만들고 버킷별 분위수화합니다.

$$
Spread^{mkt}(t)=median_{s\in U(t)}(spread_s(t))
$$
$$
q^{mkt}_{spread}(t)=F_{Spread^{mkt},b(t)}(Spread^{mkt}(t))
$$
range도 동일 ($q^{mkt}_{range}$).

### 7.2 Dispersion(엣지 벌어짐) 분위수

Tradeability 분포가 얼마나 벌어져 있는지(IQR 등)로 측정합니다.

$$
D(t)=IQR(\{T_s(t)\}_{s\in U(t)})
$$
$$
q_D(t)=F_{D,b(t)}(D(t))
$$

### 7.3 동적 진입 예산 M(t)

$$
M(t)=\Big\lfloor M_{max}\cdot (1-q^{mkt}_{spread}(t))\cdot (1-q^{mkt}_{range}(t))\cdot q_D(t)\Big\rfloor
$$

*   장이 비싸고/과열이면 ($(1-q^{mkt})$) 항으로 M 감소
*   엣지가 납작하면 ($q_D$)로 M 감소(무엣지 자동 휴식)

> “상수 임계로 거래 금지”가 아니라, **예산이 0으로 수렴**하게 만드는 방식이라 v3 철학과 정합적입니다.

---

## 8) 상태머신 (v3.1 운영 순서)

### 8.1 SCAN: 유니버스 → 후보군

SCAN 점수도 비용 절대성을 반영 가능합니다(권장).

$$
S^{scan}_s(t)=rank(r^{xs}_{vol}(s,t)) - rank(r^{xs}_{spread}(s,t))
$$
$$
\mathcal{C}(t)=TopN(S^{scan}(t))
$$

### 8.2 MACRO PERMISSION: 셋업 권한부여(5m)

$$
MacroScore_s(t)=rank(q^{self}_{rvol,5m})+rank(q^{self}_{trend,5m})+rank(q^{self}_{level\_event,5m})
$$
$$
\mathcal{M}(t)=TopK(MacroScore(t))
$$

### 8.3 PRIME: 임박 모드

$$
\mathcal{P}(t)=TopK(R(t))
$$
Persist(상대적 지속성)로 prime 유지/해제.

### 8.4 TF SELECT

대상: $\mathcal{M}(t)\cap\mathcal{P}(t)$
선택: $tf_{exec}(s,t)$ (Persist + Emergency Override 반영)

---

## 9) Level 시스템 (ActiveLevel)

### 9.1 레벨 후보

$$L \in \{PMH, PDH, VWAP\}$$

### 9.2 LevelScore(오늘 먹히는 레벨 자동선정)

각 레벨 ($L$)에 대해 “반응/플로우 확인/실패/피로도”를 랭크로 합성합니다.

*   Reaction(L): Touch 이후 유리방향 확장(상대)
*   FlowConfirm(L): Touch 구간에서 OFI/틱/거래대금 동반
*   Fail(L): Fail 이벤트 빈도/최근성
*   Fatigue(L): 최근 Touch 반복 횟수(많을수록 감점)

$$
LevelScore(L)=rank(Reaction_L)+rank(FlowConfirm_L)-rank(Fail_L)-rank(Fatigue_L)
$$
$$
ActiveLevel(s,t)=\arg\max_{L} LevelScore(L)
$$
*(단순화된 등가중 모델 사용)*

---

## 10) BUY (v3.1: Hold + FlowConfirm TopX + 예산 M(t))

### 10.1 게이트 통과 집합

$$
\mathcal{E}(t)=\{s\in\mathcal{P}(t)\cap\mathcal{M}(t): Touch_{L}(t)=1,\ GatesOK\}
$$
(여기서 GatesOK는 $q^{self}_{spread} < 0.95$ AND $O_s(t) \notin TopY(Risk)$)

### 10.2 FlowConfirm(진짜 Hold인지 확인)

$$
FC_s(t)=rank(q^{self}_{ofid,s}(t)) + rank(q^{self}_{tick,s}(t)) + rank(q^{self}_{vol,s}(t))
$$

### 10.3 최종 진입 집합 (예산 기반)

$$
\mathcal{B}(t)=TopM(T(t))\cap TopX(FC(t))\cap \mathcal{E}(t)
$$
여기서 $M=M(t)$ (동적 예산), $X$는 동시 체결 품질 예산.

### 10.4 BUY 트리거(예시, 1s 기준)

$$
Hold_L(t)=\mathbf{1}\{P(t)>L \wedge P(t+1s)>L\}=1 \Rightarrow BUY
$$

---

## 11) 보유/청산 (v3.1: Follow-through 붕괴 추가)

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

진입 이후 강도/확장이 유지되지 않으면 청산합니다(개념적으로 $\Delta$랭크 기반).

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

## 12) 포지션 사이징 (v3.1 권장: 임계 없이 분배)

### 12.1 Tradeability 기반 softmax 분배

$$
w_s(t)=\frac{\exp(\alpha \cdot z(T_s(t)))}{\sum_{j\in \mathcal{B}(t)}\exp(\alpha \cdot z(T_j(t)))}
$$

### 12.2 비용 기반 소프트 사이즈 컷(하드게이트 아래에서도 자동 감쇄)

$$
size_s \propto w_s(t)\cdot (1-q^{self}_{spread,s}(t))\cdot (1-O_s(t))
$$

---

## 13) 무엇이 고정이고 무엇이 유동인가 (v3.1 최종)

*   **고정(상수 임계)**:
    1.  $q^{self}_{spread} \ge 0.95$ (비용 폭탄)
    2.  $O_s(t) \in TopY(\text{RiskBudget})$ (나쁜 과열)
*   **유동(무상수 판단)**: 나머지 전부 rank/TopK/예산/이벤트/Market Permission
*   **운영 파라미터(리소스)**: ($N, K, H, M_{max}, X, Y, L_{tf}, \text{EmergencyThresh}$)

---

## 14) 모듈 경계 SSOT (Data → Normalize → Score → State → Order)

1.  **Ingestor**: 1s OHLC / prints / (옵션)L2
2.  **Feature Engine**: vol/range/tick/ofi/spread/level events
3.  **Normalizer(SSOT)**: ($q^{self}$), ($r^{xs}$), ($q^{mkt}$), ($q_D$) (온라인/누수 방지)
4.  **Scoring**: Scan/Macro/R/C/T/TFScore/LevelScore/FC/FT/SmartOverheat($O_s$)
5.  **State Machine**: SCAN→PERMIT→PRIME→TF(Override)→ENTRY→INPOS→EXIT
6.  **Risk/Budget**: **M(t)** 동적 예산, 사이징, 동시보유 제한
7.  **Execution**: 주문/체결/취소/슬리피지 모델
8.  **Event Store/Replay**: 상태전이 “이유” 로그 저장

---

## 15) 백테스트/실전 필수 주의

*   분위수/랭크 계산은 **미래 누수 금지(온라인/롤링)**
*   PMH/PDH/VWAP의 **정의 시점 고정**(특히 PMH)
*   최소한의 **fill/slippage 가정**을 포함(안 넣으면 게이트/Cost가 과소평가)
*   유니버스 정의의 생존편향 주의
