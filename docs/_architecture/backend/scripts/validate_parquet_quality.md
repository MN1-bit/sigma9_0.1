# validate_parquet_quality.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `backend/scripts/validate_parquet_quality.py` |
| **역할** | [11-003, 11-004] Parquet 데이터 품질 검사 CLI |
| **라인 수** | 482 |
| **바이트** | 16,550 |

## 검사 항목

| 항목 | 설명 |
|------|------|
| 파일 무결성 | 읽기 가능 여부 |
| 필수 컬럼 | Daily: ticker, date, OHLCV / Intraday: timestamp, OHLCV |
| OHLC 관계 | H≥max(O,C), L≤min(O,C), H≥L |
| 중복 레코드 | ticker+date 또는 timestamp 기준 |
| NULL 값 | OHLCV 컬럼 NULL 비율 |
| 날짜 갭 | 거래일 누락 |
| 가격 이상치 | Z-score > 4.0 |

## 함수

### `validate_daily(daily_dir, verbose) -> dict`
> Daily Parquet 품질 검사

### `validate_intraday(base_dir, verbose, full_ohlc, sample_ratio) -> dict`
> Intraday Parquet 품질 검사 (병렬 처리)

### `main()`
> CLI 진입점

## 실행 방법

```bash
python -m backend.scripts.validate_parquet_quality
python -m backend.scripts.validate_parquet_quality --full --sample 0.1
python -m backend.scripts.validate_parquet_quality --output-json report.json
```

## 🔗 외부 연결 (Connections)

### Imports From (이 파일이 가져오는 것)
| 파일 | 가져오는 항목 |
|------|--------------|
| `backend/data/validators.py` | `validate_ohlc_relationship`, `validate_volume`, `detect_daily_gaps`, `detect_price_outliers` |

## 외부 의존성
- `pyarrow`
- `loguru`
