# test_data_integrity.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `tests/test_data_integrity.py` |
| **역할** | [11-004] 데이터 정합성 검증 함수 단위 테스트 |
| **라인 수** | 321 |
| **바이트** | 12,918 |

## Fixtures

| Fixture | 설명 |
|---------|------|
| `valid_ohlc_df` | 정상 OHLC 데이터 |
| `invalid_ohlc_df` | OHLC 관계 위반 데이터 |
| `temp_parquet_dir` | 임시 Parquet 디렉터리 |

## 테스트 클래스

### `TestValidateOHLC`
> OHLC 관계 검증 테스트

| 테스트 | 검증 내용 |
|-------|----------|
| `test_valid_ohlc_no_violations` | 정상 데이터는 위반 없음 |
| `test_detects_high_lt_low` | High < Low 탐지 |
| `test_detects_high_lt_close` | High < Close 탐지 |
| `test_detects_low_gt_open` | Low > Open 탐지 |
| `test_detects_non_positive_price` | 음수/0 가격 탐지 |

### `TestValidateVolume`
> Volume 검증 테스트

### `TestDetectDailyGaps`
> Daily 갭 탐지 테스트

### `TestDetectIntradayGaps`
> Intraday 갭 탐지 테스트

### `TestDetectPriceOutliers`
> 가격 이상치 탐지 테스트

## 🔗 외부 연결 (Connections)

### Imports From (이 파일이 가져오는 것)
| 파일 | 가져오는 항목 |
|------|--------------|
| `backend/data/validators.py` | `validate_ohlc_relationship`, `validate_volume`, `detect_daily_gaps`, `detect_intraday_gaps`, `detect_price_outliers` |

## 외부 의존성
- `pytest`
- `pandas`
