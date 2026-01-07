# Seismograph 전략 가이드

> **버전**: v3.1 (2026-01-07)  
> **철학**: "매집을 탐지하고, 폭발 순간에 진입하고, 급등을 수확한다."

---

## 1. 전략 개요

Seismograph는 미국 **마이크로캡 주식**에서 **세력의 매집(Accumulation)**을 사전 탐지하고, 
**폭발 순간(Ignition)**을 포착하여 진입하는 2단계 전략입니다.

```
[Phase 1: Setup]        [Phase 2: Trigger]       [Phase 3: Harvest]
     ↓                        ↓                        ↓
  일봉 스캔 ──→ Watchlist 50 ──→ 실시간 감시 ──→ 진입 ──→ 청산
  (매집 탐지)    (상위 선별)      (폭발 감지)     (OCA)    (Trail)
```

---

## 2. Phase 1: 매집 탐지

### 2.1 Universe 필터

### 2.2 매집 4단계

| Stage | 신호 | 조건 | 점수 |
|-------|------|------|------|
| 1 | Volume Dry-out | 3일 거래량 < 20일 평균의 40% | 10점 |
| 2 | OBV Divergence | 주가 ≤ 0 & OBV > 0 | 30점 |
| 3 | Accumulation Bar | 가격 ±2.5% & 거래량 > 3× | 50점 |
| 4 | Tight Range (VCP) | 5일 ATR < 20일 ATR의 50% | **100점** 🔥 |

---

## 3. Score V3 알고리즘

### 3.1 4가지 신호와 가중치

| 신호 | 가중치 | 의미 |
|------|--------|------|
| **OBV Divergence** | 35% | 주가 횡보 + 거래량 누적 |
| **Tight Range** | 30% | 가격 변동폭 수축 |
| **Accumulation Bar** | 20% | 조용한 매집 패턴 |
| **Volume Dryout** | 15% | 거래량 감소 |

### 3.2 점수 계산

```
Base Score = (TR × 0.30 + OBV × 0.35 + AB × 0.20 + VD × 0.15) × 100

Final Score = Base Score × Signal Modifier
```

### 3.3 Signal Modifier

**조건**: 4개 신호 모두 ≥ 0.6 → **1.30x** 부스트

**계산 공식**:
```python
avg = mean(intensities)
min_val = min(intensities)

weakness_penalty = max(0, 0.3 - min_val) * 1.5
adjusted = avg - weakness_penalty

modifier = 0.6 + (adjusted * 0.8)  # 범위: 0.6 ~ 1.4
```

---

## 4. 개별 신호 상세

### 4.1 OBV Divergence (35%)

**무엇을 보는가?**  
On-Balance Volume이 상승하는데 주가는 제자리

**계산**:
1. 주가 변화율의 Z-Score
2. OBV 변화율의 Z-Score
3. 둘의 차이 → Sigmoid(0~1)

### 4.2 Tight Range (30%)

**무엇을 보는가?**  
최근 N일간 가격 변동폭이 극히 좁은 상태

**해석**:
- 0.8+ = 매우 좁음 (폭발 직전) 🔥
- 0.5 = 정상 범위

### 4.3 Accumulation Bar (20%)

**Base 0.5 + 가감점**:
- 양봉 비율 (50% 기준): ±0.15
- 조용한 날 비율: +0.15
- Body Ratio: ±0.10
- 거래량: ±0.10

### 4.4 Volume Dryout (15%)

**무엇을 보는가?**  
거래량이 점진적으로 줄어드는 현상 (역발상)

---

## 5. 파라미터

### Phase 1 (Setup)

| 파라미터 | 기본값 |
|----------|--------|
| Lookback Period | 20일 |
| Spike Factor | 3.0× |
| Dry-out Threshold | 40% |
| Min Score | 60점 |

### Phase 3 (Exit)

| 파라미터 | 기본값 |
|----------|--------|
| **Stop Loss** | **-5.0%** |
| Time Stop | 3분 |
| Trail Activation | +3.0% |
| Trail Amount | ATR×1.5 |

---

## 6. 점수 해석

| 점수 | 의미 | 액션 |
|------|------|------|
| **80+** | 폭발 임박 | 주시 필요 |
| **60-80** | 강한 매집 신호 | 관심 대상 |
| **40-60** | 일부 신호 탐지 | 모니터링 |
| **0-40** | 약함 | 관망 |

---

> **"Smart money leaves footprints. We just need to read them."**
