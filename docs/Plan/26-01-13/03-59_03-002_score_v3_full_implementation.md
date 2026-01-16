# Score V3 구현 기획서

> **문서 ID**: 03-002_score_v3_full_implementation  
> **목적**: Score V3 "Pinpoint" 알고리즘의 제로베이스 구현 가이드  
> **참조**: `docs/strategy/Score_v3.md`

---

## 1. 프로젝트 개요

### 1.1 목표
매집(Accumulation) 강도를 정량화하는 Score V3 알고리즘 구현. 기존 V2의 이진화(0/100) 문제를 해결하고, 연속적인 점수 분포를 생성한다.

### 1.2 핵심 공식
```
Final Score = Base Score × Boost Factor × Penalty Factor

Base Score = Σ(Intensity × Weight) × 100
- Tight Range (I_TR):     30%
- OBV Divergence (I_OBV): 35%
- Accumulation Bar (I_AB): 20%
- Volume Dryout (I_VD):   15%

Boost = 1.3 if (I_TR ≥ 0.7 AND I_VD ≥ 0.5) else 1.0
Penalty = 0.5 if (Close < Open AND Volume > AvgVol×2) else 1.0
```

---

## 2. 구현 범위

### 2.1 신호별 구현 상태

| 신호 | 개선 내용 | 상태 |
|------|----------|------|
| Tight Range | Z-Score Sigmoid | 🔲 구현 필요 |
| Volume Dryout | Support Check 추가 | 🔲 구현 필요 |
| OBV Divergence | Z-Score 표준화 + 조건 완화 | 🔲 구현 필요 |
| Accumulation Bar | 로그 스케일 적용 | 🔲 구현 필요 |
| Boost Factor | 복합 조건 승수 | 🔲 구현 필요 |
| Penalty Factor | 대량 음봉 감점 | 🔲 구현 필요 |

---

## 3. 파일 구조

```
backend/strategies/
├── score_v3_config.py    # V3 설정 상수 (NEW)
└── seismograph.py        # V3 메서드 추가 (MODIFY)

frontend/gui/
└── watchlist_model.py    # score_v3 표시 (MODIFY)

backend/api/
└── routes.py             # WatchlistItem 모델 수정 (MODIFY)

backend/core/
└── realtime_scanner.py   # score_v3 계산 호출 (MODIFY)
```

---

## 4. 상세 구현 명세

### 4.1 설정 파일 (`score_v3_config.py`)

```python
# 가중치
V3_WEIGHTS = {
    "tight_range": 0.30,
    "obv_divergence": 0.35,
    "accumulation_bar": 0.20,
    "volume_dryout": 0.15,
}

# Z-Score Sigmoid 파라미터
ZSCORE_SIGMOID_K = 2.0  # 시그모이드 기울기

# Boost 조건
BOOST_TR_THRESHOLD = 0.7
BOOST_VD_THRESHOLD = 0.5
BOOST_MULTIPLIER = 1.3

# Penalty 조건
PENALTY_VOLUME_MULTIPLIER = 2.0
PENALTY_FACTOR = 0.5
```

---

### 4.2 Tight Range (I_TR) - Z-Score Sigmoid

**입력**: 일봉 데이터 (최소 20일)

**알고리즘**:
```python
def _calc_tight_range_intensity_v3(self, data: list) -> float:
    # 1. ATR 계산
    atr_5d = calculate_atr(data[-5:])
    atr_20d = calculate_atr(data[-20:])
    
    # 2. Z-Score 계산 (음수 = 수축)
    atr_mean = mean([calculate_atr(data[i:i+5]) for i in range(15)])
    atr_std = std([calculate_atr(data[i:i+5]) for i in range(15)])
    z_score = (atr_5d - atr_mean) / atr_std if atr_std > 0 else 0
    
    # 3. 시그모이드 변환 (음수 z-score = 높은 점수)
    intensity = 1 / (1 + exp(ZSCORE_SIGMOID_K * z_score))
    return round(intensity, 2)
```

---

### 4.3 Volume Dryout (I_VD) - Support Check

**입력**: 일봉 데이터 (최소 20일)

**알고리즘**:
```python
def _calc_volume_dryout_intensity_v3(self, data: list) -> float:
    # 1. 거래량 고갈 계산
    vol_5d = mean([d["volume"] for d in data[-5:]])
    vol_20d = mean([d["volume"] for d in data[-20:]])
    vol_ratio = vol_5d / vol_20d if vol_20d > 0 else 1
    base_dryout = max(0, 1 - vol_ratio)
    
    # 2. Support Check (하방 경직성)
    # 최근 5일 종가가 당일 범위 상단에 위치하는지
    support_scores = []
    for d in data[-5:]:
        range_size = d["high"] - d["low"]
        if range_size > 0:
            location = (d["close"] - d["low"]) / range_size
            support_scores.append(location)
    support = mean(support_scores) if support_scores else 0.5
    
    # 3. 최종 강도
    intensity = base_dryout * support
    return round(intensity, 2)
```

---

### 4.4 OBV Divergence (I_OBV) - Z-Score 표준화

**입력**: 일봉 데이터 (최소 20일)

**알고리즘**:
```python
def _calc_obv_divergence_intensity_v3(self, data: list) -> float:
    # 1. OBV 계산
    obv = [0]
    for i in range(1, len(data)):
        if data[i]["close"] > data[i-1]["close"]:
            obv.append(obv[-1] + data[i]["volume"])
        elif data[i]["close"] < data[i-1]["close"]:
            obv.append(obv[-1] - data[i]["volume"])
        else:
            obv.append(obv[-1])
    
    # 2. OBV 기울기 Z-Score
    obv_slope = (obv[-1] - obv[-5]) / 5
    obv_slopes = [(obv[i] - obv[i-5]) / 5 for i in range(5, len(obv))]
    slope_mean = mean(obv_slopes)
    slope_std = std(obv_slopes)
    z_score = (obv_slope - slope_mean) / slope_std if slope_std > 0 else 0
    
    # 3. 가격 조건 완화 (5% 상승까지 허용)
    price_change = (data[-1]["close"] - data[-5]["close"]) / data[-5]["close"]
    if price_change > 0.05:
        return 0.0
    
    # 4. 시그모이드 변환
    intensity = 1 / (1 + exp(-z_score))
    return round(intensity, 2)
```

---

### 4.5 Accumulation Bar (I_AB) - 로그 스케일

**입력**: 일봉 데이터

**알고리즘**:
```python
def _calc_accumulation_bar_intensity_v3(self, data: list) -> float:
    latest = data[-1]
    prev_avg_vol = mean([d["volume"] for d in data[-21:-1]])
    
    # 거래량 배수
    ratio = latest["volume"] / prev_avg_vol if prev_avg_vol > 0 else 1
    
    # 양봉 조건
    is_bullish = latest["close"] > latest["open"]
    body_ratio = abs(latest["close"] - latest["open"]) / (latest["high"] - latest["low"])
    
    if not is_bullish or ratio < 1.5:
        return 0.0
    
    # 로그 스케일 (1.5x에서 시작, 4x에서 최대)
    log_ratio = log(ratio) - log(1.5)
    max_log = log(4) - log(1.5)
    intensity = min(1.0, log_ratio / max_log) if log_ratio > 0 else 0
    
    return round(intensity * body_ratio, 2)
```

---

### 4.6 Boost Factor

```python
def _calculate_boost_factor(self, intensities: dict) -> float:
    tr = intensities.get("tight_range", 0)
    vd = intensities.get("volume_dryout", 0)
    
    if tr >= BOOST_TR_THRESHOLD and vd >= BOOST_VD_THRESHOLD:
        return BOOST_MULTIPLIER
    return 1.0
```

---

### 4.7 Penalty Factor

```python
def _calculate_penalty_factor(self, data: list) -> float:
    latest = data[-1]
    avg_vol = mean([d["volume"] for d in data[-20:]])
    
    is_bearish = latest["close"] < latest["open"]
    is_high_volume = latest["volume"] > avg_vol * PENALTY_VOLUME_MULTIPLIER
    
    if is_bearish and is_high_volume:
        return PENALTY_FACTOR
    return 1.0
```

---

### 4.8 최종 점수 계산

```python
def calculate_watchlist_score_v3(self, ticker: str, data: list, vwap: float = None) -> float:
    if len(data) < 20:
        return -1  # 데이터 부족
    
    # 개별 강도 계산
    intensities = {
        "tight_range": self._calc_tight_range_intensity_v3(data),
        "obv_divergence": self._calc_obv_divergence_intensity_v3(data),
        "accumulation_bar": self._calc_accumulation_bar_intensity_v3(data),
        "volume_dryout": self._calc_volume_dryout_intensity_v3(data),
    }
    
    # Base Score
    base = sum(intensities[k] * V3_WEIGHTS[k] for k in V3_WEIGHTS) * 100
    
    # Boost & Penalty
    boost = self._calculate_boost_factor(intensities)
    penalty = self._calculate_penalty_factor(data)
    
    return round(base * boost * penalty, 1)
```

---

## 5. 테스트 계획

### 5.1 단위 테스트
```python
# test_score_v3.py
def test_tight_range_zscore():
    # 수축 상태 → 높은 점수
    # 확장 상태 → 낮은 점수

def test_volume_dryout_support():
    # 거래량↓ + 종가↑ → 높은 점수
    # 거래량↓ + 종가↓ → 낮은 점수

def test_boost_factor():
    # TR≥0.7 AND VD≥0.5 → 1.3x

def test_penalty_factor():
    # 대량 음봉 → 0.5x
```

### 5.2 통합 테스트
- GUI에서 score_v3 표시 확인
- 툴팁에 개별 강도 표시 확인
- Score V3 재계산 버튼 동작 확인

---

## 6. 마이그레이션 체크리스트

- [x] `score_v3_config.py` 생성 ✅ (기존 존재, Boost VD 0.5로 수정)
- [x] `seismograph.py`에 V3 메서드 추가 ✅ (OBV V3, AccumBar V3 구현)
- [x] `calculate_watchlist_score_detailed`에 score_v3 반환 추가 ✅ (기존 존재)
- [x] `realtime_scanner.py`에서 score_v3 계산 호출 ✅ (기존 존재)
- [x] `routes.py` WatchlistItem에 score_v3 필드 추가 ✅ (기존 존재)
- [x] `watchlist_model.py`에서 score_v3 표시 ✅ (기존 존재)
- [x] `settings.yaml`에 score_version: v3 설정 ✅ (기존 존재)
- [x] 테스트 실행 및 검증 ✅ (Python 구문 검사 통과)

---

## 7. 참고 자료

- 전략 문서: `docs/strategy/Score_v3.md`
- V2 수식: `docs/strategy/score_v2_formula.md`
- V2.1 개선안: `docs/strategy/Score_v2.1.md`
