# Score V3 전략 완전 가이드

> **버전**: V3.1 (2026-01-06)  
> **목적**: 매집 단계에 있는 종목을 탐지하여 점수화

---

## 핵심 컨셉

**"조용한 매집 → 폭발 직전 종목 찾기"**

기관/세력이 주가를 올리지 않고 조용히 매집할 때 나타나는 4가지 패턴을 탐지합니다.

---

## 4가지 신호와 가중치

| 신호 | 가중치 | 의미 |
|------|--------|------|
| **OBV Divergence** | 35% | 주가는 횡보인데 거래량 누적은 상승 → "누군가 사고 있다" |
| **Tight Range** | 30% | 가격 변동폭이 좁음 → "팔 사람이 없다" |
| **Accumulation Bar** | 20% | 양봉 비율, 조용한 날 비율 등 → "조용히 올라간다" |
| **Volume Dryout** | 15% | 거래량이 말라감 → "관심이 없어 보이지만..." |

---

## 점수 계산 공식

```
Base Score = (TR × 0.30 + OBV × 0.35 + AB × 0.20 + VD × 0.15) × 100

Final Score = Base Score × Signal Modifier
```

### Signal Modifier (가감 배수)
| 조건 | 배수 | 설명 |
|------|------|------|
| **4개 신호 모두 ≥ 0.6** | **1.30x** | "올스타" 부스트 |
| 그 외 | 1.0x | 중립 |
| ~~1개 약함~~ | ~~0.85x~~ | 임시 무력화 |
| ~~2개+ 약함~~ | ~~0.60x~~ | 임시 무력화 |

---

## 각 신호 상세 설명

### 1. OBV Divergence (35%)

**무엇을 보는가?**  
On-Balance Volume이 상승하는데 주가는 제자리인 현상

**계산 방식**:
1. 주가 변화율의 Z-Score 계산
2. OBV 변화율의 Z-Score 계산
3. 둘의 차이 → Sigmoid로 0~1 정규화

**해석**:
- 0.8+ = 강한 매집 신호 (거래량 누적 중)
- 0.5 = 중립
- 0.2- = 매도 압력

---

### 2. Tight Range (30%)

**무엇을 보는가?**  
최근 N일간 가격 변동폭이 극히 좁은 상태

**계산 방식**:
1. 최근 5일 (High - Low) / Close 평균
2. 과거 20일 대비 얼마나 좁은지 비교
3. Z-Score → Sigmoid 정규화

**해석**:
- 0.8+ = 매우 좁음 (폭발 직전)
- 0.5 = 정상 범위
- 0.2- = 변동성 큼 (노이즈)

---

### 3. Accumulation Bar (20%) - V3.1

**무엇을 보는가?**  
조용한 매집 패턴 (Base 0.5 + 가감점)

**계산 방식**:
1. **양봉 비율** (50% 기준): 많으면 +0.15, 적으면 -0.15
2. **조용한 날 비율**: 변동 2% 이하인 날이 많으면 +0.15
3. **Body Ratio Median**: 캔들 몸통 비율 중앙값
4. **거래량 Median**: 분석 기간 vs 전체 비교

**기본 점수**: 0.5 (중립)에서 시작

---

### 4. Volume Dryout (15%)

**무엇을 보는가?**  
거래량이 점진적으로 줄어드는 현상

**계산 방식**:
1. 최근 N일 거래량 중앙값
2. 과거 20일 평균 대비 비율
3. 하방 경직성 체크 (Support 이탈 시 0점)

**해석**:
- 0.8+ = 거래량 극도로 감소 (관심 없어 보임 → 역발상)
- 0.5 = 보통
- 0.2- = 거래량 활발 (이미 관심 받는 중)

---

## 점수 해석

| 점수 | 의미 | 액션 |
|------|------|------|
| **80+** | 폭발 임박 | 주시 필요 |
| **60-80** | 강한 매집 신호 | 관심 대상 |
| **40-60** | 일부 신호 탐지 | 모니터링 |
| **20-40** | 약한 신호 | 관망 |
| **0-20** | 신호 없음 | 무시 |

---

## 설정값 참조표

### Tight Range (Z-Score Sigmoid)
```python
ZSCORE_SIGMOID = ZScoreSigmoidConfig(
    z_scale=2.0,    # Z-Score 감도
    center=0.0,     # Sigmoid 중심
    steepness=1.0   # 경사
)
```

### Accumulation Bar
```python
ACCUMBAR_CONFIG = AccumBarConfig(
    base_score=0.5,
    adj_bullish=0.15,
    adj_quiet=0.15,
    adj_body=0.10,
    adj_volume=0.10
)
```

### Signal Modifier
```python
SIGNAL_MODIFIER_CONFIG = SignalModifierConfig(
    weak_threshold=0.2,
    strong_threshold=0.6,
    boost_multiplier=1.30,   # 4개 모두 강할 때
    mild_penalty=1.0,        # 임시 무력화
    severe_penalty=1.0       # 임시 무력화
)
```

---

## 수정 가이드

### 가중치 변경
`score_v3_config.py` → `V3_WEIGHTS`

### Signal Modifier 조정
`score_v3_config.py` → `SignalModifierConfig`

### 개별 신호 로직 수정
`seismograph.py` → 각 `_calc_*_intensity_v3()` 함수
