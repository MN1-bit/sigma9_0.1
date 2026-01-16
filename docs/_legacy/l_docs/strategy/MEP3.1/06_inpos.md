# 06. INPOS/EXIT: 보유 및 청산

## 기본 보유(랭크 유지)

$$
s\in TopH(T(t)) \Rightarrow Hold
$$

---

## SELL-FAIL (레벨 실패 + T 붕괴)

$$
Fail_L(t)=\mathbf{1}\{P(t)<L \wedge P(t+1s)<L\}=1
$$
$$
Fail_L(t)=1\ \wedge\ rank(T_s(t))\downarrow \Rightarrow SELL
$$

---

## SELL-END (TopH 이탈)

$$
s\notin TopH(T(t)) \Rightarrow SELL
$$

---

## SELL-FT (Follow-through 붕괴)

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
