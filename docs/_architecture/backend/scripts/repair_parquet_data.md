# repair_parquet_data.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `backend/scripts/repair_parquet_data.py` |
| **역할** | [11-004] Parquet 데이터 복구 CLI - 중복 제거, NULL 보간, 백업 |
| **라인 수** | 456 |
| **바이트** | 16,570 |

## 클래스

### `DataRepairer`
> 데이터 품질 문제 자동 수정

#### 생성자
```python
DataRepairer(
    base_dir: Path,
    backup_dir: Path = Path("data/backup"),
    dry_run: bool = True,  # 기본 시뮬레이션
)
```

#### 주요 메서드
| 메서드 | 설명 |
|--------|------|
| `backup_file(file_path)` | 파일 백업 생성 |
| `remove_duplicates_daily()` | Daily 중복 제거 (ticker+date) |
| `remove_duplicates_intraday()` | Intraday 중복 제거 (timestamp) |
| `fill_nulls_daily(strategy)` | NULL 보간 (ffill/linear/drop) |
| `repair_all(null_strategy)` | 전체 복구 실행 |

## 실행 방법

```bash
python -m backend.scripts.repair_parquet_data --dry-run
python -m backend.scripts.repair_parquet_data --apply
python -m backend.scripts.repair_parquet_data --apply --null-strategy linear
```

## 🔗 외부 연결 (Connections)

### Imports From (이 파일이 가져오는 것)
| 파일 | 가져오는 항목 |
|------|--------------|
| (없음) | pyarrow만 사용 |

## 외부 의존성
- `pyarrow`
- `loguru`
