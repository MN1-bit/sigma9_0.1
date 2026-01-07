# 07. SESSION PROTOCOL: 세션 적응형 프로토콜

## 세션 정의

| Session | 시간 (ET) | 설명 |
|---------|-----------|------|
| **PRE_EARLY** | 04:00-07:00 | 프리마켓 초반, 유동성 매우 낮음 |
| **PRE_LATE** | 07:00-09:30 | 프리마켓 후반, 뉴스 반응 |
| **REG_EARLY** | 09:30-10:30 | 정규장 오픈, 변동성 높음 |
| **REG_MID** | 10:30-14:00 | 정규장 중반, 안정적 유동성 |
| **REG_LATE** | 14:00-16:00 | 정규장 후반, 포지션 정리 |
| **POST_EARLY** | 16:00-18:00 | 에프터 초반, 실적 반응 |
| **POST_LATE** | 18:00-20:00 | 에프터 후반, 유동성 급감 |

---

## Session Multiplier (예산 승수)

$$
M(t) = \left\lfloor M_{max} \cdot SessionMultiplier \cdot (1 - q^{mkt,session}_{spread}) \cdot (1 - q^{mkt,session}_{range}) \cdot q_D \right\rfloor
$$

| Session | Multiplier |
|---------|------------|
| PRE_EARLY | 0.5 |
| PRE_LATE | 0.8 |
| REG | 1.0 |
| POST_EARLY | 0.6 |
| POST_LATE | 0.3 |

---

## 4차원 버킷 시스템

$$
Bucket(s,t) = (Stock\_Tier, Session, Time\_Bucket, VIX\_Regime)
$$

### Stock Tier

| Tier | 시가총액 |
|------|---------|
| MEGA | >$200B |
| LARGE | $10B-$200B |
| MID | $2B-$10B |
| SMALL | <$2B |

### VIX Regime

| Regime | VIX 범위 |
|--------|---------|
| low | < 15 |
| normal | 15-25 |
| high | 25-35 |
| extreme | ≥ 35 |

---

## Session-Specific Level Sets

| Session | 레벨 후보 |
|---------|----------|
| PRE | PDC, PDH, PDL, ATR_Upper, ATR_Lower, Rolling_PMH |
| REG | PMH, PDH, PDL, VWAP, HOD, LOD |
| POST | HOD, LOD, VWAP, PDC, AH_High, AH_Low |

### ATR Bands

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

### Rolling PMH

$$
Rolling\_PMH(t) = \max\{P(\tau) : \tau \in [PRE\_OPEN, t]\}
$$

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

---

## Session-Aware Gates

### Activity Gate

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

### Liquidity Gate

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

---

## Session End Exit

$$
SESSION\_END = t \geq session_{end} - 5min
$$

PRE, POST 세션 종료 5분 전 자동 청산

---

## Trailing Stop (세션 적응)

$$
TrailingStop = Entry - k \times ATR_{session}
$$

| Session | k |
|---------|---|
| PRE | 1.5 |
| REG | 1.0 |
| POST | 2.0 |
