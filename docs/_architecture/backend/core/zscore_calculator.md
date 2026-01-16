# zscore_calculator.py

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `backend/core/zscore_calculator.py` |
| **역할** | Z-Score 계산 - Seismograph 전략의 핵심 지표 (zenV, zenP) |
| **라인 수** | 187 |
| **바이트** | 7,052 |

---

## 클래스

### `ZScoreCalculator`
> Z-Score 계산기 - 통계적 이상 탐지

**핵심 지표**:
| 지표 | 설명 | 용도 |
|------|------|------|
| `zenV` | Volume Z-Score | 거래량이 평균 대비 얼마나 높은지 |
| `zenP` | Price Z-Score | 가격 변동이 평균 대비 얼마나 큰지 |

**Divergence 조건** (매집 패턴):
- `zenV >= 2.0` (거래량 폭발)
- `zenP < 0.5` (가격 조용)

| 메서드 | 시그니처 | 설명 |
|--------|----------|------|
| `__init__` | `(lookback: int = 20)` | 초기화 (lookback 기간) |
| `calculate_zenV` | `(volumes: List[float]) -> float` | Volume Z-Score 계산 |
| `calculate_zenP` | `(prices: List[float]) -> float` | Price Change Z-Score 계산 |
| `calculate_both` | `(volumes, prices) -> Tuple[float, float]` | zenV, zenP 동시 계산 |
| `calculate_from_bars` | `(bars: List[dict]) -> Tuple[float, float]` | OHLCV 바에서 계산 |
| `is_divergence` | `(zenV, zenP) -> bool` | Divergence 조건 체크 |
| `_zscore` | `(values, current) -> float` | 범용 Z-Score 계산 |

---

## Z-Score 공식

```
Z = (X - μ) / σ

X = 현재값
μ = 평균 (lookback 기간)
σ = 표준편차 (lookback 기간)
```

---

## 사용 예시

```python
from backend.core.zscore_calculator import ZScoreCalculator

calc = ZScoreCalculator(lookback=20)

# 일봉 데이터에서 계산
zenV, zenP = calc.calculate_from_bars(daily_bars)

print(f"zenV: {zenV:.2f}")  # 예: 2.5 (평균 대비 2.5σ 높은 거래량)
print(f"zenP: {zenP:.2f}")  # 예: 0.3 (평균 대비 낮은 가격 변동)

# Divergence 체크
if calc.is_divergence(zenV, zenP):
    print("🔥 매집 패턴 감지!")
```

---

## 🔗 외부 연결 (Connections)

### Used By
| 파일 | 사용 목적 |
|------|----------|
| `SeismographStrategy` | Watchlist/Ignition Score 계산 |
| `DivergenceDetector` | zenV-zenP Divergence 판정 |
| `Scanner` | 축적 점수 계산 |

### Data Flow
```mermaid
graph LR
    A["OHLCV Bars"] --> B["ZScoreCalculator"]
    B -->|zenV| C["Seismograph"]
    B -->|zenP| C
    C --> D["Divergence Detector"]
    D --> E["Early Alert"]
```

---

## 외부 의존성
| 패키지 | 사용 목적 |
|--------|----------|
| `numpy` | 평균, 표준편차 계산 |
| `statistics` | 대체 계산 |
| `loguru` | 로깅 |
