# test_parquet_manager.py

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `tests/test_parquet_manager.py` |
| **역할** | ParquetManager 모듈 단위 테스트 (Write/Read/Append) |
| **라인 수** | 296 |

## Fixtures

| Fixture | 설명 |
|---------|------|
| `temp_parquet_dir` | 임시 Parquet 디렉터리 (테스트 후 자동 삭제) |
| `parquet_manager` | ParquetManager 인스턴스 |
| `sample_daily_df` | 샘플 일봉 데이터 (AAPL, MSFT) |
| `sample_intraday_df` | 샘플 분봉 데이터 (3 rows) |

## 테스트 클래스

### `TestDailyOperations`
> 일봉 데이터 CRUD 테스트

| 테스트 | 설명 |
|--------|------|
| `test_write_and_read_daily` | Write/Read 라운드트립 |
| `test_append_daily_deduplication` | Append 시 중복 제거 |
| `test_read_empty_daily` | 빈 데이터 읽기 |

### `TestIntradayOperations`
> 분봉 데이터 CRUD 테스트

| 테스트 | 설명 |
|--------|------|
| `test_write_and_read_intraday` | Write/Read 라운드트립 |
| `test_intraday_file_path` | 파일 경로 확인 |
| `test_read_nonexistent_intraday` | 존재하지 않는 파일 읽기 |

### `TestUtilities`
> 유틸리티 메서드 테스트

| 테스트 | 설명 |
|--------|------|
| `test_get_available_tickers` | 티커 목록 조회 |
| `test_get_stats` | 통계 조회 |
| `test_delete_ticker_intraday` | 티커 분봉 삭제 |

### `TestPerformance`
> 성능 테스트

| 테스트 | 설명 |
|--------|------|
| `test_large_daily_insert` | 5000 rows 삽입 (< 5초) |

## 🔗 외부 연결 (Connections)

### Tests (테스트 대상)
| 파일 | 테스트 항목 |
|------|------------|
| `backend/data/parquet_manager.py` | `ParquetManager` 전체 |

## 외부 의존성
- `pytest`
- `pandas`
- `tempfile`, `shutil`
