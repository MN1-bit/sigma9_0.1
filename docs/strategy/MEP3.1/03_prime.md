# 03. PRIME: 임박 모드

## PRIME 집합

$$
\mathcal{P}(t)=TopK(R^{session}(t))
$$

Persist(상대적 지속성)로 prime 유지/해제.

---

## Hard Gates (Session-Aware)

### Gate #1 비용 폭탄 (Session-Relative)

$$
q^{self,session}_{spread,s}(t)\ge 0.95 \Rightarrow \text{진입 금지}
$$

### Gate #2 Smart Overheat (Session-Aware)

**"Flow가 없는 공허한 급등"**만 차단:

$$
O_s^{session}(t) = rank_{session}(q^{self,session}_{range,s}(t)) - rank_{session}(q^{self,session}_{vol,s}(t)) - rank_{session}(q^{self,session}_{ofi,s}(t))
$$

$$
O_s^{session}(t) \in TopY(RiskBudget, session) \Rightarrow \text{진입 금지}
$$

### Gate #3 Activity Gate (NEW)

$$
TickCount_{1m}(s,t) \geq N_{min}(session) \Rightarrow \text{통과}
$$

| Session | N_min |
|---------|-------|
| PRE_EARLY | 5 |
| PRE_LATE | 15 |
| REG | 50 |
| POST_EARLY | 15 |
| POST_LATE | 5 |

### Gate #4 Liquidity Gate (NEW)

$$
\overline{Volume}_{10min}(s,t) \geq V_{min}(session) \Rightarrow \text{통과}
$$

| Session | V_min |
|---------|-------|
| PRE_EARLY | 5,000 |
| PRE_LATE | 10,000 |
| REG | 50,000 |
| POST_EARLY | 10,000 |
| POST_LATE | 3,000 |

> 변동성은 1등인데, 거래량과 OFI는 꼴등 = **나쁜 과열(Bad Volatility)**
> 최소 체결 건수/거래량 미달 = **진입 불가**

