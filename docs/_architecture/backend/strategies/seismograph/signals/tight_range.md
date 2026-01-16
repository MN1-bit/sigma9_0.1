# tight_range.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `backend/strategies/seismograph/signals/tight_range.py` |
| **역할** | VCP(Volatility Contraction Pattern) 시그널 - ATR 기반 변동성 수축 감지 |
| **라인 수** | 125 |
| **바이트** | 3,635 |

## 함수

### `calc_tight_range_intensity(data) -> float`
> V2: ATR 비율 기반 (0.0~1.0)

#### 수식
```
ratio = ATR_5 / ATR_20
intensity = (0.7 - ratio) / 0.4  (클리핑 0~1)
```

| 비율 | 강도 |
|------|------|
| ≤ 30% | 1.0 (최고) |
| ≥ 70% | 0.0 (없음) |

---

### `calc_tight_range_intensity_v3(data, ...) -> float`
> V3.2: Percentile 기반 정규화

#### 인자
| 인자 | 기본값 | 설명 |
|------|--------|------|
| `lookback_days` | 60 | ATR 히스토리 기간 |
| `use_percentile` | True | Percentile/Z-Score 선택 |
| `min_samples` | 20 | 최소 샘플 수 |
| `sigmoid_k` | 2.5 | Sigmoid 기울기 |
| `sigmoid_x0` | -0.5 | Sigmoid 중심점 |

#### Percentile 방식
```
percentile = (현재 ATR보다 낮은 값 개수) / 전체
intensity = 1.0 - percentile
```
> 변동성 낮을수록 (percentile 낮을수록) 강도 높음

## 🔗 외부 연결

### Imports From
| 파일 | 가져오는 항목 |
|------|--------------|
| `base.py` | `get_column`, `calculate_atr` |

### Imported By
| 파일 | 사용 목적 |
|------|----------|
| `signals/__init__.py` | export |

## 외부 의존성
- `numpy`
