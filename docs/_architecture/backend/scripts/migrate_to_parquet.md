# migrate_to_parquet.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `backend/scripts/migrate_to_parquet.py` |
| **역할** | SQLite → Parquet 일봉 데이터 마이그레이션 |
| **라인 수** | 174 |
| **바이트** | 5,263 |

## 함수

### `migrate_daily_data(db_path, parquet_dir, batch_size=50)` (async)
> SQLite의 일봉 데이터를 Parquet으로 변환

#### Args
| 인자 | 기본값 | 설명 |
|------|--------|------|
| `db_path` | `data/market_data.db` | SQLite 경로 |
| `parquet_dir` | `data/parquet` | Parquet 저장 디렉터리 |
| `batch_size` | 50 | 티커당 배치 크기 |

#### Returns
- `total_tickers`: 전체 티커 수
- `total_rows`: 전체 레코드 수
- `elapsed_seconds`: 소요 시간

---

### `verify_migration(db_path, parquet_dir)` (async)
> 마이그레이션 데이터 무결성 검증

#### Returns
- `sqlite_rows`: SQLite 레코드 수
- `parquet_rows`: Parquet 레코드 수
- `match`: 일치 여부

---

### `main()` (async)
> CLI 진입점 (`--verify-only` 지원)

## 실행 방법

```bash
python -m backend.scripts.migrate_to_parquet
python -m backend.scripts.migrate_to_parquet --verify-only
```

## 🔗 외부 연결 (Connections)

### Imports From (이 파일이 가져오는 것)
| 파일 | 가져오는 항목 |
|------|--------------|
| `backend/data/database.py` | `MarketDB` |
| `backend/data/parquet_manager.py` | `ParquetManager` |

## 외부 의존성
- `pandas`
- `tqdm`
- `loguru`
