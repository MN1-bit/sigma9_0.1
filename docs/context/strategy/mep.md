# MEP v3.2 — Microstructure Execution Protocol

> **버전**: v3.2 (2026-01-07)  
> **목적**: 단타 트레이딩을 위한 상태머신 기반 실행 정책

---

## 1. 철학

### 1.1 MEP란?

**MEP(Microstructure Execution Protocol)**는 "급등 예측"이 아닌  
**"거래 가능성(Tradeability)"**을 우선하는 실행 시스템입니다.

- 아무리 급등이 예상되어도, **스프레드가 너무 넓으면** 진입하지 않음
- 아무리 신호가 강해도, **거래량이 없으면** 진입하지 않음
- **"먹힐 수 있는 상황"**에서만 진입

### 1.2 Dual-Mode Architecture

| Mode | 단계 | 데이터 |
|------|------|--------|
| **Bar Mode** | SCAN → TF | 1m/5m 봉 |
| **Tick Mode** | ENTRY → EXIT | 실시간 tick |

---

## 2. Session Protocol

### 2.1 세션 정의

| Session | 시간 (ET) | 설명 |
|---------|-----------|------|
| PRE_EARLY | 04:00-07:00 | 프리마켓 초반, 유동성 낮음 |
| PRE_LATE | 07:00-09:30 | 프리마켓 후반, 뉴스 반응 |
| REG_EARLY | 09:30-10:30 | 정규장 오픈, 변동성 높음 |
| REG_MID | 10:30-14:00 | 정규장 중반, 안정적 |
| REG_LATE | 14:00-16:00 | 정규장 후반 |
| POST_EARLY | 16:00-18:00 | 에프터 초반 |
| POST_LATE | 18:00-20:00 | 에프터 후반, 유동성 급감 |

### 2.2 Session Multiplier (예산 승수)

| Session | Multiplier |
|---------|------------|
| PRE_EARLY | 0.5 |
| REG | 1.0 |
| POST_LATE | 0.3 |

---

## 3. State Machine

```
SCAN → PERMIT → PRIME → TF → ENTRY → INPOS → EXIT
 ↑                                              ↓
 └──────────────────────────────────────────────┘
```

| 상태 | 설명 |
|------|------|
| SCAN | 유니버스에서 후보군 선별 |
| PERMIT | Macro 권한 부여 (5분봉) |
| PRIME | 임박 모드 (실시간 모니터링) |
| TF | 최적 타임프레임 선택 |
| ENTRY | 진입 조건 충족 시 매수 |
| INPOS | 보유 중 (Hold/Exit 판단) |
| EXIT | 청산 후 SCAN 복귀 |

---

## 4. 핵심 스코어

### 4.1 Ready Score (임박 강도)

```
R = rank(OFI) + rank(TickIntensity) + rank(VolumeAccel)
```

### 4.2 Cost Score (거래 불리)

```
C = rank(Spread_self) + rank(Spread_xs) + rank(Range_self) + rank(Range_xs)
```

### 4.3 Tradeability (먹힘 가능성)

```
T = R - C
```

---

## 5. Hard Gates

### 5.1 비용 폭탄 차단

```
Spread_quantile ≥ 0.95 → 진입 금지
```

### 5.2 Smart Overheat

**"Flow가 없는 공허한 급등"** 차단:

```
O = rank(Range) - rank(Volume) - rank(OFI)
O ∈ TopY → 진입 금지
```

### 5.3 Activity Gate

```
TickCount_1m ≥ N_min(session)
```

---

## 6. 진입 규칙

### 6.1 Level System

| Session | 레벨 후보 |
|---------|----------|
| PRE | PDC, PDH, PDL, ATR_Upper |
| REG | PMH, PDH, VWAP, HOD |
| POST | HOD, LOD, VWAP, PDC |

### 6.2 BUY 트리거

```
Hold_L(t) = Price > Level for HoldDuration → BUY
```

### 6.3 포지션 사이징

```
size ∝ Tradeability × (1 - Spread) × (1 - Overheat)
```

---

## 7. 청산 규칙

### 7.1 SELL-FAIL (레벨 실패)

```
Price < Level ∧ T ↓ → SELL
```

### 7.2 SELL-END (TopH 이탈)

```
Stock ∉ TopH(T) → SELL
```

### 7.3 Session End Exit

```
t ≥ session_end - 5min → 자동 청산
```

### 7.4 Trailing Stop (세션 적응)

| Session | k (ATR 배수) |
|---------|--------------|
| PRE | 1.5 |
| REG | 1.0 |
| POST | 2.0 |

---

## 8. 주의사항

> [!WARNING]
> **미래 정보 누수 방지**  
> 분위수/랭크 계산은 반드시 **온라인(롤링)** 방식으로 수행

- **PMH**: 장전 거래 기준, 정규장 시작 전 확정
- **VWAP**: 당일 누적으로 실시간 계산
- **체결 가정**: slippage 모델 포함 필수
