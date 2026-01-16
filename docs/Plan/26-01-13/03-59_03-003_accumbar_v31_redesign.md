# 03-003 AccumBar V3.1 재설계 및 구현

> **문서 유형**: 구현 계획서 (Implementation Plan)  
> **작성일**: 2026-01-06  
> **참고 문서**: `docs/strategy/accumulation_bar_v3_argument.md`  
> **우선순위**: HIGH  
> **예상 소요 시간**: 2-3시간

---

## 1. 개요

### 1.1 문제 정의
현재 Accumulation Bar V3 알고리즘이 대부분의 종목에서 **0.00**을 반환한다.
20개 종목 중 0개가 0이 아닌 값을 가지면, 20% 가중치가 사실상 무용지물이 된다.

```
SMXT:  Tight Range=0.62, OBV=0.51, AccumBar=0.00, VolDryout=0.38
AMCI:  Tight Range=0.55, OBV=0.48, AccumBar=0.00, VolDryout=0.41
RETO:  Tight Range=0.71, OBV=0.44, AccumBar=0.00, VolDryout=0.29
```

### 1.2 근본 원인
1. **과도하게 엄격한 조건**: 양봉 + 1.5x 거래량 둘 다 필요
2. **이진 판단**: 조건 미충족 시 즉시 0.0 반환
3. **시간 분리 없음**: AccumBar와 Dryout이 같은 시기를 관찰하여 상쇄

### 1.3 해결 방향
**"Base 0.5 + 가감점 + 시간 분리 + 이상치 내성"** 구조 채택

---

## 2. 알고리즘 설계

### 2.1 핵심 변경점

| 요소 | 기존 V3 | 신규 V3.1 |
|------|---------|----------|
| 기준점 | 0.0 (이진) | **0.5 (중립)** |
| 관찰 기간 | data[-1] (오늘 1일) | **data[-N:-M] (10일간)** |
| 거래량 | Dryout과 상쇄 | **시간 분리로 보완적** |
| 이상치 | Mean (취약) | **Median + 비율 (Robust)** |
| Dryout 기간 | 고정 5일 | **Float 기반 동적 (3~10일)** |

### 2.2 시간 분리 개념

```
     과거                                      현재
     ├────────────────────────────────────────────┤
     │                                            │
     │  [AccumBar 기간]      [Dryout 기간]        │
     │  (세력이 매집)        (거래량 고갈)        │
     │                                            │
     Day -20        Day -10    Day -5     Day 0
                         └──────┬──────┘
                                │
                         Ignition 임박!
```

| 단계 | 기간 | 거래량 | 캔들 | 신호 |
|------|------|--------|------|------|
| 1. 매집 | Day -15 ~ -5 | 📈 높음 | 양봉 + 작은 변동 | AccumBar HIGH |
| 2. 고갈 | Day -5 ~ 0 | 📉 낮음 | 횡보 | Dryout HIGH |
| 3. 폭발 | Day 0+ | 🚀 급증 | 급등 | Ignition! |

### 2.3 Float 기반 동적 기간

```python
def get_dryout_days(float_shares: int) -> int:
    """Float 기반 동적 Dryout 기간 계산
    
    - float 3M → 4일 (매물이 빨리 고갈)
    - float 6M → 5일
    - float 12M → 7일
    - float 15M+ → 10일 (고갈에 오래 걸림)
    """
    return min(10, max(3, 3 + float_shares // 3_000_000))

def get_accumbar_period(float_shares: int) -> tuple[int, int]:
    """AccumBar 관찰 기간 계산 (Dryout와 연동)"""
    dryout_days = get_dryout_days(float_shares)
    start = dryout_days + 10  # Dryout 시작점 + 10일
    end = dryout_days         # Dryout 시작점
    return (start, end)  # 예: 3M float → (14, 4)
```

### 2.4 가감점 구조

| 요소 | 임계값 | 보너스 | 페널티 |
|------|-------|-------|-------|
| 양봉 비율 | 70% / 30% | +0.15 | -0.15 |
| 조용한 날 비율 | 70% / 30% | +0.15 | -0.10 |
| Body Ratio (Median) | 60% / 30% | +0.10 | -0.10 |
| 거래량 (Median) | 130% / 70% | +0.10 | -0.10 |

**최종 범위: 0.0 ~ 1.0 (0.5 = 중립)**

---

## 3. 구현 상세

### 3.1 수정 대상 파일

```
backend/strategies/seismograph.py
├── _calc_accumulation_bar_intensity_v3()  ← 재작성
└── _calc_volume_dryout_intensity_v3()     ← Float 파라미터 추가 (선택)

backend/strategies/score_v3_config.py
└── ACCUMBAR_CONFIG (신규)                 ← 상수 정의
```

### 3.2 최종 알고리즘 코드

```python
# backend/strategies/score_v3_config.py에 추가
@dataclass(frozen=True)
class AccumBarConfig:
    """Accumulation Bar V3.1 설정"""
    base_score: float = 0.5
    accum_period_days: int = 10  # 매집 기간 (일)
    
    # 가감점 임계값
    bullish_threshold_high: float = 0.7  # 70% 이상 양봉
    bullish_threshold_low: float = 0.3   # 30% 이하 양봉
    quiet_threshold_high: float = 0.7    # 70% 이상 조용
    quiet_threshold_low: float = 0.3     # 30% 미만 조용
    quiet_range_pct: float = 0.03        # 조용한 날 기준 (3%)
    body_ratio_high: float = 0.6         # 60% 이상 실체
    body_ratio_low: float = 0.3          # 30% 미만 실체
    volume_ratio_high: float = 1.3       # 130% 이상
    volume_ratio_low: float = 0.7        # 70% 미만
    
    # 가감점 값
    adj_bullish: float = 0.15
    adj_quiet: float = 0.15
    adj_body: float = 0.10
    adj_volume: float = 0.10

ACCUMBAR_CONFIG = AccumBarConfig()
```

```python
# backend/strategies/seismograph.py
from backend.strategies.score_v3_config import ACCUMBAR_CONFIG

def _calc_accumulation_bar_intensity_v3(
    self, 
    data: Any, 
    float_shares: int = 10_000_000
) -> float:
    """
    Accumulation Bar V3.1 - 시간 분리 + 이상치 내성 버전
    
    특징:
    1. Base 0.5 + 가감점 구조
    2. 과거 10일간의 매집 기간 분석 (Dryout와 시간 분리)
    3. Median + 비율 기반 (이상치에 강건)
    4. Float 기반 동적 기간 계산
    
    Args:
        data: OHLCV 캔들 데이터 (list of dict)
        float_shares: 유통 주식 수 (기본값 10M)
    
    Returns:
        float: 0.0 ~ 1.0 (0.5 = 중립)
    """
    cfg = ACCUMBAR_CONFIG
    BASE_SCORE = cfg.base_score
    
    # === 1. 동적 기간 계산 ===
    dryout_days = min(10, max(3, 3 + float_shares // 3_000_000))
    accum_start = dryout_days + cfg.accum_period_days  # 예: 4 + 10 = 14일 전
    accum_end = dryout_days                            # 예: 4일 전
    
    # 데이터 부족 시 중립 반환
    if len(data) < accum_start:
        return BASE_SCORE
    
    period = data[-accum_start:-accum_end]
    n = len(period)
    
    if n == 0:
        return BASE_SCORE
    
    adjustment = 0.0
    
    # === 2. 양봉 비율 (카운팅 - 이미 robust) ===
    bullish_ratio = sum(1 for d in period if d["close"] > d["open"]) / n
    if bullish_ratio >= cfg.bullish_threshold_high:
        adjustment += cfg.adj_bullish
    elif bullish_ratio <= cfg.bullish_threshold_low:
        adjustment -= cfg.adj_bullish
    
    # === 3. 조용한 날 비율 (이상치 내성) ===
    quiet_days = sum(
        1 for d in period 
        if d["close"] > 0 and (d["high"] - d["low"]) / d["close"] < cfg.quiet_range_pct
    )
    quiet_ratio = quiet_days / n
    if quiet_ratio >= cfg.quiet_threshold_high:
        adjustment += cfg.adj_quiet
    elif quiet_ratio < cfg.quiet_threshold_low:
        adjustment -= cfg.adj_quiet * 0.67  # 약간 약한 페널티
    
    # === 4. Body Ratio - Median (이상치 무시) ===
    body_ratios = [
        abs(d["close"] - d["open"]) / (d["high"] - d["low"])
        for d in period 
        if d["high"] != d["low"]
    ]
    if body_ratios:
        body_median = sorted(body_ratios)[len(body_ratios) // 2]
        if body_median >= cfg.body_ratio_high:
            adjustment += cfg.adj_body
        elif body_median < cfg.body_ratio_low:
            adjustment -= cfg.adj_body
    
    # === 5. 거래량 - Median (하루 폭발 무시) ===
    accum_vols = [d["volume"] for d in period]
    total_vols = [d["volume"] for d in data]
    
    if accum_vols and total_vols:
        accum_median = sorted(accum_vols)[len(accum_vols) // 2]
        total_median = sorted(total_vols)[len(total_vols) // 2]
        
        if total_median > 0:
            if accum_median > total_median * cfg.volume_ratio_high:
                adjustment += cfg.adj_volume  # 매집 기간에 거래량 높음 = 좋음
            elif accum_median < total_median * cfg.volume_ratio_low:
                adjustment -= cfg.adj_volume  # 매집 기간에 거래량 낮음 = 매집 없음
    
    # === 6. 최종 점수 ===
    intensity = max(0.0, min(1.0, BASE_SCORE + adjustment))
    return round(intensity, 2)
```

### 3.3 예상 점수 분포

| 조건 | 가감점 | 점수 | 해석 |
|------|-------|------|------|
| 양봉 70%+ 조용 70%+ 실체↑ 거래량↑ | +0.15+0.15+0.10+0.10 | **1.00** | 🔥 완벽한 매집 |
| 양봉 70%+ 조용 | +0.15+0.15 | **0.80** | ✅ 강한 매집 신호 |
| 양봉 60% 보통 | +0.05 | **0.55** | ✅ 약한 매집 신호 |
| 보합 | 0 | **0.50** | ➖ 중립 |
| 음봉 40% 변동↑ | -0.15-0.10 | **0.25** | ⚠️ 경고 |
| 음봉 70%+ 변동↑ 거래량↓ | -0.15-0.10-0.10 | **0.15** | 🚨 투매/하락 |

---

## 4. 테스트 계획

### 4.1 단위 테스트

```python
# tests/test_accumbar_v3.py

def test_perfect_accumulation():
    """완벽한 매집 패턴 → 1.00"""
    data = generate_candles(
        bullish_ratio=0.8,
        avg_range_pct=0.015,
        body_ratio=0.7,
        volume_boost=1.5
    )
    result = strategy._calc_accumulation_bar_intensity_v3(data, float_shares=5_000_000)
    assert result >= 0.9

def test_distribution_pattern():
    """투매 패턴 → 0.2 이하"""
    data = generate_candles(
        bullish_ratio=0.2,
        avg_range_pct=0.08,
        body_ratio=0.25,
        volume_boost=0.5
    )
    result = strategy._calc_accumulation_bar_intensity_v3(data, float_shares=5_000_000)
    assert result <= 0.25

def test_neutral():
    """중립 패턴 → 0.5 근처"""
    data = generate_candles(
        bullish_ratio=0.5,
        avg_range_pct=0.03,
        body_ratio=0.5,
        volume_boost=1.0
    )
    result = strategy._calc_accumulation_bar_intensity_v3(data, float_shares=5_000_000)
    assert 0.4 <= result <= 0.6

def test_outlier_robustness():
    """10일 중 1일 발작해도 결과 영향 적음"""
    base_data = generate_candles(bullish_ratio=0.7, avg_range_pct=0.015)
    outlier_data = base_data.copy()
    outlier_data[5] = {"open": 10, "high": 15, "low": 8, "close": 9, "volume": 10_000_000}
    
    base_result = strategy._calc_accumulation_bar_intensity_v3(base_data)
    outlier_result = strategy._calc_accumulation_bar_intensity_v3(outlier_data)
    
    assert abs(base_result - outlier_result) < 0.2  # 차이 0.2 미만

def test_float_dynamic_period():
    """Float에 따라 기간 달라짐"""
    assert get_dryout_days(3_000_000) == 4
    assert get_dryout_days(6_000_000) == 5
    assert get_dryout_days(12_000_000) == 7
    assert get_dryout_days(20_000_000) == 10

def test_insufficient_data():
    """데이터 부족 시 중립 반환"""
    short_data = [{"open": 10, "high": 10.5, "low": 9.5, "close": 10.2, "volume": 100}]
    result = strategy._calc_accumulation_bar_intensity_v3(short_data)
    assert result == 0.5  # 중립
```

### 4.2 통합 테스트

1. **GUI 확인**: Score V3 점수가 정상적으로 표시되는지
2. **툴팁 확인**: AccumBar 값이 0.00이 아닌 다양한 값 표시
3. **실제 종목**: 최소 10개 종목에서 0.3~0.7 범위 분포 확인

---

## 5. 구현 체크리스트

### Phase 1: 설정 추가
- [ ] `score_v3_config.py`에 `AccumBarConfig` 클래스 추가
- [ ] `ACCUMBAR_CONFIG` 상수 정의

### Phase 2: 알고리즘 재작성
- [ ] `seismograph.py`의 `_calc_accumulation_bar_intensity_v3()` 백업
- [ ] 새 알고리즘으로 교체
- [ ] 헬퍼 함수 `get_dryout_days()`, `get_accumbar_period()` 추가

### Phase 3: 테스트
- [ ] Python 구문 검사
- [ ] 단위 테스트 작성 및 실행
- [ ] GUI 실행하여 실제 점수 분포 확인

### Phase 4: 문서화
- [ ] devlog 작성
- [ ] 본 계획서 체크리스트 업데이트

---

## 6. 성능 고려사항

### 6.1 계산 복잡도

| 연산 | n | 복잡도 | 대략적 연산 수 |
|------|---|--------|---------------|
| 캔들 순회 | 10 | O(n) | 10 |
| 비율 계산 | 10 | O(n) | 10 |
| Median (정렬) | 10 | O(n log n) | 40 |
| 총 1종목 | - | - | **~100** |

### 6.2 실제 부하

```
50종목 × 100연산 = 5,000 연산/주기
1분 재계산 = 5,000 연산/분 = 83 연산/초

현대 CPU: ~10,000,000,000 연산/초
→ 0.000001% 부하 (무시 가능)
```

---

## 7. 롤백 계획

문제 발생 시:
1. `_calc_accumulation_bar_intensity_v3()` 원래 코드로 복원
2. `ACCUMBAR_CONFIG` 삭제
3. Git revert 사용

---

## 8. 참고 자료

- **상세 논의**: `docs/strategy/accumulation_bar_v3_argument.md`
- **기존 V3 구현**: `docs/Plan/bugfix/03-002_score_v3_full_implementation.md`
- **Score V3 전략**: `docs/strategy/Score_v3.md`
