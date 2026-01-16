# obv_divergence.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `backend/strategies/seismograph/signals/obv_divergence.py` |
| **역할** | OBV Divergence (V2) / Absorption (V3) - 가격-거래량 괴리 및 흡수 감지 |
| **라인 수** | 133 |
| **바이트** | 4,312 |

## 함수

### `calc_obv_divergence_intensity(data, obv_lookback=20) -> float`
> V2: 가격 하락 + OBV 상승 = 매집 신호

#### 조건
1. 가격 2% 이상 상승 시 → 0.0 (divergence 아님)
2. OBV 하락 시 → 0.0 (divergence 아님)

#### 강도 계산
```
divergence_strength = |price_change| × 10 + obv_change_ratio × 5
```

---

### `calc_absorption_intensity_v3(data) -> float`
> V3.2: Signed Volume 기반 흡수 감지

#### 핵심 개념
> 거래량 많은데 가격 반응 작으면 → 흡수 발생

#### 수식
```
sv = Σ(sign(returns) × volume)   # Signed Volume
pr = Σ(|returns|)                 # Price Reaction
absorption = sigmoid(sv_norm - pr_norm)
```

#### 반환값
| 조건 | 강도 범위 |
|------|----------|
| 매도 우세 (sv ≤ 0) | 0.0 ~ 0.5 |
| 매수 우세 (sv > 0) | 0.5 ~ 1.0 |
| 5% 초과 상승 중 | 0.3 (페널티) |
| 예외 발생 | 0.5 (중립) |

## 🔗 외부 연결

### Imports From
| 파일 | 가져오는 항목 |
|------|--------------|
| `base.py` | `get_column`, `calculate_obv` |

### Imported By
| 파일 | 사용 목적 |
|------|----------|
| `signals/__init__.py` | export |

## 외부 의존성
- `numpy`
