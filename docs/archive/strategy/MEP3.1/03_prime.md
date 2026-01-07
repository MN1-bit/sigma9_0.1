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
O_s(t) = rank(q^{self}_{range,s}(t)) - rank(q^{self}_{vol,s}(t)) - rank(q^{self}_{ofid,s}(t))
$$

$$
O_s(t) \in TopY(\text{RiskBudget}) \Rightarrow \text{진입 금지}
$$

> 변동성은 1등인데, 거래량과 OFI는 꼴등 = **나쁜 과열(Bad Volatility)**
