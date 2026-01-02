# 01. SCAN: 유니버스 → 후보군

## 표준화 규칙 (Session-Aware)

### Self-Quantile (세션 분리)

각 종목의 원시 지표는 **종목/세션/버킷별** 경험분포로 분위수화:

$$
q^{self,session}_{x,s}(t)=F_{x,s,session,b(t)}(x_s(t))
$$

### Cross-Section Rank (세션 범위)

**동일 세션 활성 종목** 내에서만 절대 수준 비교:

$$
r^{xs,session}_{x}(s,t)=rank_{j\in U^{session}(t)}(x_j(t))
$$

> **Session-Scoped Universe**: 해당 세션에서 최소 유동성 조건을 충족하는 종목만 포함

---

## 입력 신호 (1m 봉 기반 피처)

| 카테고리 | 피처 | 계산 방식 |
|----------|------|----------|
| 관심/유동성 | $vol_{1m}$ | 1m 봉 거래량 |
| 과열/변동 | $range_{1m}$ | (High - Low) / Open |
| 체결 가속 | $tick\_intensity_{1m}$ | 1m 내 체결 건수 |
| 압력/불균형 | $ofi_{1m}$ | 1m 내 OFI 누적 |
| 비용(핵심) | $spread_{1m}$ | 1m 평균 스프레드 |
| 레벨 이벤트 | Touch/Hold/Fail + ActiveLevel | 레벨 상호작용 |

---

## 핵심 스코어 (Session-Aware)

### Ready(임박 강도)

$$
R_s^{session}(t)=rank_{session}(q^{self,session}_{ofi,s}(t)) + rank_{session}(q^{self,session}_{tick,s}(t)) + rank_{session}(q^{self,session}_{vol\_accel,s}(t))
$$

### Cost(거래 불리)

$$
C_s^{session}(t)= rank_{session}(q^{self,session}_{spread,s}(t)) + rank_{session}(r^{xs,session}_{spread}(s,t)) + rank_{session}(q^{self,session}_{range,s}(t)) + rank_{session}(r^{xs,session}_{range}(s,t))
$$

### Tradeability(먹힘 가능성)

$$
T_s^{session}(t)=R_s^{session}(t)-C_s^{session}(t)
$$

---

## SCAN 스코어 (Session-Scoped)

$$
S^{scan,session}_s(t)=rank_{session}(r^{xs,session}_{vol}(s,t)) - rank_{session}(r^{xs,session}_{spread}(s,t))
$$

$$
\mathcal{C}(t)=TopN(S^{scan,session}(t))
$$

---

## 새로운 SCAN 게이트

### Empty Bar Gate

$$
empty\_bar\_ratio_{10} < 0.7
$$

최근 10봉 중 빈 봉(거래 없는 봉) 비율이 70% 이상이면 SCAN 제외

