# 05. ENTRY/BUY: 진입 (Hold + FlowConfirm + 예산)

## Level 시스템 (Session-Specific)

### 레벨 후보 (세션별)

| Session | 레벨 후보 |
|---------|----------|
| PRE | PDC, PDH, PDL, ATR_Upper, ATR_Lower, Rolling_PMH |
| REG | PMH, PDH, PDL, VWAP, HOD, LOD |
| POST | HOD, LOD, VWAP, PDC, AH_High, AH_Low |

### LevelScore (Session-Aware)

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

---

## 게이트 통과 집합

$$
\mathcal{E}(t)=\{s\in\mathcal{P}(t)\cap\mathcal{M}(t): Touch_{L}(t)=1,\ GatesOK\}
$$

(GatesOK: Spread + Overheat + Activity + Liquidity 게이트 모두 통과)

---

## FlowConfirm (Session-Aware)

$$
FC_s^{session}(t)=rank_{session}(q^{self,session}_{ofi,s}(t)) + rank_{session}(q^{self,session}_{tick,s}(t)) + rank_{session}(q^{self,session}_{vol,s}(t))
$$

---

## 최종 진입 집합 (예산 기반)

$$
\mathcal{B}(t)=TopM(T^{session}(t))\cap TopX(FC^{session}(t))\cap \mathcal{E}(t)
$$

*   $M=M(t)$ (Session-Aware 동적 예산)
*   $X$: 동시 체결 품질 예산

---

## PreTrigger Zone (Tick Mode 활성화)

$$
PreTrigger: \quad P(t) \geq L \times (1 - \epsilon)
$$

$\epsilon = 0.002$ (0.2%)

레벨 0.2% 이내 진입 시 **Bar Mode → Tick Mode 전환**

---

## Session-Aware Hold Duration

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

## BUY 트리거 (Tick Mode)

$$
Hold_L(t)=\mathbf{1}\{P(\tau)>L,\ \forall \tau \in [t, t + HoldDuration]\}=1 \Rightarrow BUY
$$

---

## 포지션 사이징

### Tradeability 기반 softmax 분배

$$
w_s(t)=\frac{\exp(\alpha \cdot z(T_s^{session}(t)))}{\sum_{j\in \mathcal{B}(t)}\exp(\alpha \cdot z(T_j^{session}(t)))}
$$

### 비용 기반 소프트 사이즈 컷

$$
size_s \propto w_s(t)\cdot (1-q^{self,session}_{spread,s}(t))\cdot (1-O_s^{session}(t))
$$

