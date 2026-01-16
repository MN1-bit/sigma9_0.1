# test_database.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `tests/test_database.py` |
| **역할** | MarketDB (SQLite) CRUD 테스트 |
| **라인 수** | 387 |
| **바이트** | 12,193 |

## Fixtures

| Fixture | 설명 |
|---------|------|
| `temp_db` | 임시 SQLite DB (테스트 후 자동 삭제) |
| `sample_bars` | 테스트용 샘플 일봉 데이터 |
| `sample_tickers` | 테스트용 샘플 종목 정보 |

## 테스트 함수

### Database Initialization
| 테스트 | 설명 |
|-------|------|
| `test_db_initialization` | 테이블 생성, WAL 모드 확인 |
| `test_db_creation_with_directory` | 디렉터리 자동 생성 |

### DailyBar CRUD
| 테스트 | 설명 |
|-------|------|
| `test_upsert_bulk` | Bulk Insert |
| `test_upsert_update` | Upsert 업데이트 |
| `test_get_daily_bars` | 일봉 조회 |
| `test_get_latest_date` | 최신 날짜 조회 |
| `test_get_all_tickers_with_data` | 데이터 있는 종목 리스트 |

### Ticker CRUD
| 테스트 | 설명 |
|-------|------|
| `test_update_fundamentals` | 펀더멘털 Upsert |
| `test_get_ticker_info` | 종목 정보 조회 |
| `test_get_universe_candidates` | Universe Filter |

### Performance
| 테스트 | 설명 |
|-------|------|
| `test_bulk_insert_performance` | 5000 레코드 삽입 성능 |

## 🔗 외부 연결 (Connections)

### Imports From (이 파일이 가져오는 것)
| 파일 | 가져오는 항목 |
|------|--------------|
| `backend/data/database.py` | `MarketDB`, `DailyBar`, `Ticker` |

## 외부 의존성
- `pytest`
- `tempfile`
