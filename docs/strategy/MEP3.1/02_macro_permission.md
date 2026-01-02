# 02. MACRO PERMISSION: 셋업 권한부여(5m)

## MacroScore (Session-Aware)

$$
MacroScore_s^{session}(t)=rank_{session}(q^{self,session}_{rvol,5m})+rank_{session}(q^{self,session}_{trend,5m})+rank_{session}(q^{self,session}_{level\_event,5m})
$$

$$
\mathcal{M}(t)=TopK(MacroScore^{session}(t))
$$

---

## Market Permission + Dispersion Budget (Session-Aware)

v3.2는 세션별 예산 승수를 적용하여 Extended Hours 적응:

### Market Cost/Heat 분위수 (Session-Scoped)

$$
Spread^{mkt,session}(t)=median_{s\in U^{session}(t)}(spread_s(t))
$$
$$
q^{mkt,session}_{spread}(t)=F_{Spread^{mkt},session,b(t)}(Spread^{mkt,session}(t))
$$

range도 동일 ($q^{mkt,session}_{range}$).

### Dispersion 분위수

$$
D(t)=IQR(\{T_s^{session}(t)\}_{s\in U^{session}(t)})
$$
$$
q_D(t)=F_{D,session,b(t)}(D(t))
$$

### Session Multiplier

| Session | Multiplier |
|---------|------------|
| PRE_EARLY | 0.5 |
| PRE_LATE | 0.8 |
| REG | 1.0 |
| POST_EARLY | 0.6 |
| POST_LATE | 0.3 |

### 동적 진입 예산 M(t) (Session-Aware)

$$
M(t)=\Big\lfloor M_{max}\cdot SessionMultiplier \cdot (1-q^{mkt,session}_{spread}(t))\cdot (1-q^{mkt,session}_{range}(t))\cdot q_D(t)\Big\rfloor
$$

*   장이 비싸고/과열이면 → M 감소
*   엣지가 납작하면 → M 감소 (무엣지 자동 휴식)
*   Extended Hours면 → SessionMultiplier로 추가 감소

> **예산이 0으로 수렴**하게 만드는 방식 + **세션 적응**

