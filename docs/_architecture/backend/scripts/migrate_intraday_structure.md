# migrate_intraday_structure.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `backend/scripts/migrate_intraday_structure.py` |
| **역할** | [11-003] Parquet Intraday 폴더 구조 마이그레이션 |
| **라인 수** | 234 |
| **바이트** | 7,063 |

## 설명

> 평탄화 구조에서 타임프레임별 폴더 구조로 마이그레이션

```
기존: data/parquet/intraday/AAPL_1m.parquet
신규: data/parquet/1m/AAPL.parquet
```

## 상수

| 이름 | 값 |
|------|---|
| `SUPPORTED_TIMEFRAMES` | `["1m", "3m", "5m", "15m", "1h", "4h"]` |

## 함수

### `parse_legacy_filename(filename) -> tuple[str, str] | None`
> 레거시 파일명에서 티커와 타임프레임 추출

### `migrate_intraday_structure(base_dir, dry_run, verbose) -> dict`
> 마이그레이션 수행

#### 반환값
- `total`: 전체 파일 수
- `migrated`: 마이그레이션 완료 수
- `skipped`: 스킵 수
- `errors`: 오류 목록
- `by_tf`: 타임프레임별 통계

### `main()`
> CLI 진입점 (`--dry-run`, `--verbose` 지원)

## 실행 방법

```bash
python -m backend.scripts.migrate_intraday_structure --dry-run
python -m backend.scripts.migrate_intraday_structure
```

## 🔗 외부 연결 (Connections)

### Imports From (이 파일이 가져오는 것)
| 파일 | 가져오는 항목 |
|------|--------------|
| (없음) | 표준 라이브러리만 사용 |

## 외부 의존성
- `loguru`
- `shutil`, `argparse`
