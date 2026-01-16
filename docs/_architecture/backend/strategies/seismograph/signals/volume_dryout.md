# volume_dryout.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `backend/strategies/seismograph/signals/volume_dryout.py` |
| **역할** | Volume Dryout 시그널 - 거래량 마름 ("폭풍 전 고요") 감지 |
| **라인 수** | 157 |
| **바이트** | 4,284 |

## 함수

### `calc_volume_dryout_intensity(data, dryout_threshold=0.4) -> float`
> V2: 최근 3일 vs 20일 평균 비율 (0.0~1.0)

| 비율 | 강도 |
|------|------|
| ≥ 40% | 0.0 |
| 20% | 0.5 |
| 0% | 1.0 |

---

### `calc_volume_dryout_intensity_v3(data, ...) -> float`
> V3.2: Volume Dryout + Support 확인 (Sigmoid 페널티)

#### 수식
```
intensity = volume_intensity × support_penalty
support_penalty = 1 / (1 + exp(-k × support_dist))
```

#### 인자
| 인자 | 기본값 | 설명 |
|------|--------|------|
| `dryout_threshold` | 0.4 | 거래량 마름 임계값 |
| `support_factor_func` | None | 커스텀 Support 계산 함수 |
| `min_price_location` | 0.4 | 최소 가격 위치 |
| `penalty_steepness` | 3.0 | Sigmoid 기울기 |

---

### `_calc_support_factor_default(data) -> float`
> 기본 Support Factor (0.0~1.0)

```
location = (현재 종가 - 20일 저가) / (20일 고가 - 20일 저가)
```
- 1.0: 상단, 0.0: 하단

## 🔗 외부 연결

### Imports From
| 파일 | 가져오는 항목 |
|------|--------------|
| `base.py` | `get_column` |

### Imported By
| 파일 | 사용 목적 |
|------|----------|
| `signals/__init__.py` | export |

## 외부 의존성
- `numpy`
