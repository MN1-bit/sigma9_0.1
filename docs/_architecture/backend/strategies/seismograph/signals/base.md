# base.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `backend/strategies/seismograph/signals/base.py` |
| **역할** | Signals 공통 유틸리티 - 데이터 추출, ATR/OBV 계산 |
| **라인 수** | 84 |
| **바이트** | 2,315 |

## 함수

### `get_column(data, col_name, lookback=20) -> List[float]`
> 데이터에서 특정 컬럼 추출 (DataFrame/dict 호환)

| 인자 | 타입 | 설명 |
|------|------|------|
| `data` | Any | OHLCV 데이터 (DataFrame 또는 list of dict) |
| `col_name` | str | 컬럼명 ('open', 'high', 'low', 'close', 'volume') |
| `lookback` | int | 가져올 데이터 수 (기본 20) |

---

### `calculate_atr(highs, lows, closes) -> List[float]`
> True Range 리스트 계산

```
TR = max(H-L, |H-PC|, |L-PC|)
```
- `H`: 고가, `L`: 저가, `PC`: 전일 종가

---

### `calculate_obv(closes, volumes) -> List[float]`
> On-Balance Volume 계산

```
OBV[i] = OBV[i-1] + (sign(close_change) × volume[i])
```

## 🔗 외부 연결

### Imported By
| 파일 | 사용 목적 |
|------|----------|
| `tight_range.py` | `get_column`, `calculate_atr` |
| `obv_divergence.py` | `get_column`, `calculate_obv` |
| `accumulation_bar.py` | `get_column` |
| `volume_dryout.py` | `get_column`, `calculate_atr` |

## 외부 의존성
- (없음)
