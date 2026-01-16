# procure_intraday_data.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `backend/scripts/procure_intraday_data.py` |
| **역할** | 8,000 종목 Intraday (1m/1h) 데이터 조달 스크립트 |
| **라인 수** | 252 |
| **바이트** | 13,025 |

## 설명

> 대량 종목의 1분봉/1시봉 데이터를 Massive API에서 수집하여 Parquet에 저장

#### 특징
- 재개 지원 (진행 상황 파일 저장)
- Rate Limit 고려한 배치 처리
- Test Mode 지원 (10개 종목만)

## 함수

### `load_progress() -> set`
> 완료된 티커 목록 로드 (재개 지원)

### `save_progress(completed: set)`
> 진행 상황 저장

### `procure_intraday_data(test_mode=False)` (async)
> 메인 조달 함수

#### Args
| 인자 | 설명 |
|------|------|
| `test_mode` | True면 10개 종목만 테스트 |

## 실행 방법

```bash
python -m backend.scripts.procure_intraday_data
python -m backend.scripts.procure_intraday_data --test
python -m backend.scripts.procure_intraday_data --reset
```

## 🔗 외부 연결 (Connections)

### Imports From (이 파일이 가져오는 것)
| 파일 | 가져오는 항목 |
|------|--------------|
| `backend/data/massive_client.py` | `MassiveClient` |
| `backend/data/parquet_manager.py` | `ParquetManager` |
| `backend/data/database.py` | `MarketDB` |

## 외부 의존성
- `dotenv`
- `tqdm`
- `loguru`
