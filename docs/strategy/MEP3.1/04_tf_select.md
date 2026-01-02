# 04. TF SELECT: 타임프레임 선택

## 대상

$$
\mathcal{M}(t)\cap\mathcal{P}(t)
$$

---

## 타임프레임 레이어 (Dual-Mode)

| 레이어 | 용도 | TF |
|--------|------|-----|
| Setup | 권한부여 | 5m |
| Execution | 진입/관리 | TF-Adaptive |
| Micro | 보조 | 1s/tick |

---

## TF 후보 (v3.2 확대)

$$
T_{exec}=\{1m,2m,3m,5m,10m,15m\}
$$

### Session별 TF 제약

| Session | 허용 TF | 최적 TF |
|---------|---------|---------|
| PRE_EARLY | {5m, 10m, 15m} | 10m |
| PRE_LATE | {3m, 5m, 10m} | 5m |
| REG_EARLY | {1m, 2m, 3m, 5m} | 1-2m |
| REG_MID | {1m, 2m, 3m, 5m} | 2-3m |
| REG_LATE | {2m, 3m, 5m} | 3-5m |
| POST_EARLY | {3m, 5m, 10m} | 5m |
| POST_LATE | {5m, 10m, 15m} | 10m |

---

## TFScore (Session-Aware)

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

---

## Persist 기반 TF 전환 (Session-Aware)

$$
tf_{exec}(s,t)=
\begin{cases}
tf^{cand}(s,t) & \text{if } R_s^{session}(t) \ge R_{emergency}(session) \text{ (Emergency)} \\
tf^{cand}(s,t) & \text{if } tf^{cand} \text{ wins for } L_{tf}(session) \text{ consecutive} \\
tf_{exec}(s,t-1) & \text{otherwise}
\end{cases}
$$

> $R_s(t) \ge 0.99$: 초급등(Ignition) 상황에서는 기민함 우선
