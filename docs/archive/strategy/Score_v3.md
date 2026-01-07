# Score V3.0 "Pinpoint" Algorithm - 완전 명세서

> **버전**: V3.0 (2026-01-06)  
> **목적**: 매집(Accumulation) 강도를 정량화하여 폭발 임박 종목을 사전 탐지

---

## 1. 개요 (Executive Summary)

Score V3는 **"Base Score × Boost Factor × Penalty Factor"** 의 승수 구조를 채택한 매집 강도 측정 알고리즘입니다.

### V2 → V3 핵심 개선점

| 문제점 (V2) | 해결책 (V3) |
|-------------|-------------|
| 점수가 0 또는 100으로 쏠림 (이진화) | Z-Score Sigmoid로 연속 분포 보장 |
| 거래량 고갈 ≠ 매집 (죽은 종목 혼동) | Support Check로 하방 경직성 검증 |
| 단순 합산으로 변별력 부족 | Boost/Penalty 승수로 복합 조건 강화 |
| OBV/AccumBar가 0 또는 1만 출력 | 로그 스케일 및 시그모이드 적용 |

---

## 2. 철학 (Philosophy)

### 2.1 "Pinpoint" 전략의 핵심

**"변동성 수축(Tight Range) + 거래량 고갈(Volume Dryout) = 폭발 직전"**

- 세력은 가격을 좁은 박스에 가두고(Tight Range) 매집
- 거래량이 줄면 매도세가 고갈되었다는 신호
- 하지만 **가격이 지지선을 지키지 못하면** 그냥 망해가는 종목
- VWAP(평균 단가) 위에서 유지되어야 세력이 "관리 중"

### 2.2 전문가 의견 종합

| 관점 | 핵심 인사이트 |
|------|---------------|
| 📉 **Quant** | "시그모이드 중심값을 고정하면 모든 종목이 50점으로 수렴. Z-Score로 상대평가 필수" |
| ⚡ **Trader** | "거래량 고갈 + 하방 지지 확인 = 진짜 매집. 둘 다 만족 시 점수 부스트" |
| 🏦 **기관** | "VWAP 위에서 횡보해야 세력 평단 관리 중. 그 아래면 물린 것" |
| 💻 **개발자** | "로그 스케일로 극단값 방지, NaN 예외 처리 필수" |

---

## 3. 수식 구조 (Formula Structure)

### 3.1 최종 점수 공식

```
Final Score = Base Score × Boost Factor × Penalty Factor
```

### 3.2 Base Score (가중합)

```
Base Score = Σ (Intensity × Weight) × 100

가중치:
- Tight Range (I_TR):     30%
- OBV Divergence (I_OBV): 35%  
- Accumulation Bar (I_AB): 20%
- Volume Dryout (I_VD):   15%
```

### 3.3 Boost Factor (승수)

```
IF (I_TR ≥ 0.7) AND (I_VD ≥ 0.5):
    Boost = 1.3  (폭발 임박 조건)
ELSE:
    Boost = 1.0
```

### 3.4 Penalty Factor (감점)

```
IF (Close < Open) AND (Volume > AvgVol × 2):
    Penalty = 0.5  (대량 음봉 = 세력 이탈 경고)
ELSE:
    Penalty = 1.0
```

---

## 4. 개별 신호 상세 (Signal Details)

### 4.1 Tight Range (I_TR) - Z-Score Sigmoid

**V2 문제**: 단순 ATR 비율 → 0.3~0.7 범위 외에서 0 또는 1로 고정

**V3 해결**: Z-Score 기반 시그모이드로 상대적 수축 강도 측정

```python
# Z-Score 계산 (최근 20일 기준)
atr_zscore = (ATR_5d - mean(ATR_20d)) / std(ATR_20d)

# 시그모이드 변환 (음수 Z-Score = 수축 = 높은 점수)
I_TR = sigmoid(-atr_zscore, k=2)

def sigmoid(x, k=2):
    return 1 / (1 + exp(-k * x))
```

**효과**: 평소보다 1σ 이상 변동성이 낮으면 점수 급상승

---

### 4.2 Volume Dryout (I_VD) - Support Check 포함

**V2 문제**: 거래량 감소 = 높은 점수 → 망해가는 종목도 고점수

**V3 해결**: 거래량 고갈 + 하방 지지 확인

```python
# 기본 거래량 고갈 강도
vol_ratio = AvgVol_5d / AvgVol_20d
base_dryout = max(0, 1 - vol_ratio)

# Support Check (하방 경직성)
# 최근 5일간 종가가 저가 대비 상단에 위치하는지
support_score = mean((Close - Low) / (High - Low))  # 0~1

# 최종 강도 = 거래량 고갈 × 지지력
I_VD = base_dryout × support_score
```

**효과**: 거래량이 줄어도 가격이 바닥을 치면 0점

---

### 4.3 OBV Divergence (I_OBV) - V3 개선안

**V2 문제**: 가격 상승 시 무조건 0 → 완만한 상승 매집 감지 불가

**V3 목표 (추가 구현 필요)**:
- 가격 변화 조건 완화: 2.5% → 5%
- OBV 기울기를 Z-Score로 표준화
- VWAP 대비 현재가 위치 결합

```python
# 현재 구현 (V2 로직 유지)
if price_change > 0.025:  # 2.5% 상승 시
    I_OBV = 0
else:
    I_OBV = clamp(obv_slope_normalized, 0, 1)

# V3 목표 (미구현)
# I_OBV = sigmoid(obv_zscore) × vwap_location_factor
```

---

### 4.4 Accumulation Bar (I_AB) - 로그 스케일

**V2 문제**: Volume Ratio 2x~5x 범위만 인식 → 이진화

**V3 목표 (추가 구현 필요)**:

```python
# V2 (선형)
I_AB = clamp((ratio - 2) / 3, 0, 1)

# V3 목표 (로그 스케일)
# log_ratio = log(max(1, ratio))
# I_AB = sigmoid(log_ratio - log(2), k=1.5)
```

---

## 5. VWAP 통합 (Price Location)

**목적**: 현재가가 세력 평균 단가(VWAP) 위에 있는지 확인

```python
# 5일 누적 VWAP 계산
vwap_5d = sum(Typical_Price × Volume) / sum(Volume)
where Typical_Price = (High + Low + Close) / 3

# VWAP 이격도
vwap_distance = (Close - VWAP_5d) / VWAP_5d × 100

# 활용
# - 양수: 세력 평단 위 (관리 중)
# - 음수: 세력 평단 아래 (물림 or 이탈)
```

> ⚠️ **구현 현황**: Massive.com API에서 실시간 VWAP 제공 (AM 채널)

---

## 6. 이진화 방지 대책 요약

| 신호 | V2 문제 | V3 해결책 | 구현 상태 |
|------|---------|-----------|-----------|
| Tight Range | 선형 Clamp | Z-Score Sigmoid | ✅ 완료 |
| Volume Dryout | 단순 비율 | Support Check | ✅ 완료 |
| OBV Divergence | 가격 조건 엄격 | Z-Score + 완화 | ❌ 미완료 |
| Accum Bar | 선형 범위 | 로그 스케일 | ❌ 미완료 |

---

## 7. 구현 파일 매핑

| 컴포넌트 | 파일 |
|----------|------|
| V3 설정 상수 | `backend/strategies/score_v3_config.py` |
| V3 계산 로직 | `backend/strategies/seismograph.py` |
| GUI 표시 | `frontend/gui/watchlist_model.py` |
| API 모델 | `backend/api/routes.py` |

---

## 8. 로드맵

### Phase 1 (완료)
- [x] Tight Range: Z-Score Sigmoid
- [x] Volume Dryout: Support Check
- [x] Boost/Penalty 구조

### Phase 2 (예정)
- [ ] OBV Divergence: Z-Score 표준화 + 조건 완화
- [ ] Accumulation Bar: 로그 스케일 적용
- [ ] VWAP 이격도 통합

### Phase 3 (예정)
- [ ] IPO 기준 5일 → 20일 확대
- [ ] 동적 파라미터 튜닝 (백테스트 기반)

---

*"점수가 40~60에 뭉치면 변별력이 없다. Boost와 Penalty로 상위 종목을 확실히 분리하라."* — 심판
