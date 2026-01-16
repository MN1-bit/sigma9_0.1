# [11-003] Parquet 폴더 구조 복원 Devlog

> **작성일**: 2026-01-14
> **계획서**: [11-003_parquet_structure_recovery.md](../../Plan/refactor/11-003_parquet_structure_recovery.md)

## 진행 현황

| Step | 상태 | 시간 |
|------|------|------|
| Step 1: ParquetManager 수정 | ✅ | 08:40 |
| Step 2: 마이그레이션 스크립트 | ✅ | 08:45 |
| Step 3: 품질 검사 스크립트 | ✅ | 08:50 |
| Step 4: 마이그레이션 실행 | 🔄 | - |
| Step 5: 검증 | ⏳ | - |

---

## Step 1: ParquetManager 수정

### 변경 사항
- `backend/data/parquet_manager.py`:
  - `__init__`: TF별 폴더 초기화 (`1m/`, `5m/`, `1h/` 등)
  - `_get_intraday_path`: 경로를 `{tf}/{ticker}.parquet`로 변경
  - `read_intraday`: 레거시 fallback 추가
  - `get_intraday_tickers`: 새 구조 + 레거시 모두 검색
  - `get_stats`: TF별 통계 추가
  - `delete_ticker_intraday`: 새 구조 + 레거시 모두 삭제

### 검증
- lint: ✅ `ruff check backend/data/parquet_manager.py` - All checks passed!

---

## Step 2: 마이그레이션 스크립트

### 변경 사항
- `backend/scripts/migrate_intraday_structure.py` [NEW]:
  - `intraday/AAPL_1m.parquet` → `1m/AAPL.parquet` 이동
  - `--dry-run` 옵션으로 시뮬레이션 가능
  - 마이그레이션 마커 파일 생성 (롤백 지원)

### 검증
- lint: ✅ `ruff check backend/scripts/migrate_intraday_structure.py` - All checks passed!

---

## Step 3: 품질 검사 스크립트

### 변경 사항
- `backend/scripts/validate_parquet_quality.py` [NEW]:
  - Daily: all_daily.parquet 무결성 검사
  - Intraday: TF별 폴더 + 레거시 폴더 검사
  - 필수 컬럼, 중복 레코드, NULL 값 검사

### 검증
- lint: ✅ (자동 수정 후 통과)

---

## Step 4: 마이그레이션 실행

### 실행 명령
```powershell
python -m backend.scripts.migrate_intraday_structure -v
```

### 결과
```
✅ 마이그레이션 완료: 24,871 파일
├── 1m/: 12,283 파일
├── 1h/: 12,588 파일
├── 스킵: 0
└── 오류: 0
```

---

## Step 5: 검증

### 품질 검사 실행
```powershell
python -m backend.scripts.validate_parquet_quality
```

### 결과
```
📊 Daily 데이터:
  - 티커: 19,688개
  - 레코드: 13,636,453개
  - 날짜: 2021-01-04 ~ 2026-01-12

📊 Intraday 데이터:
  - 파일 수: 24,871
  - 정상: 24,871
  - 오류: 0

✅ 모든 데이터 품질 검사 통과!
```

### 폴더 구조 확인
```
data/parquet/
├── 1m/          ← 12,283 파일 (신규)
├── 1h/          ← 12,588 파일 (신규)
├── daily/       ← all_daily.parquet
├── intraday/    ← 마이그레이션 마커만 존재
├── indicators/
└── scores/
```

---

## 완료

| 항목 | 상태 |
|------|------|
| ParquetManager 수정 | ✅ |
| 마이그레이션 스크립트 | ✅ |
| 품질 검사 스크립트 | ✅ |
| 마이그레이션 실행 | ✅ 24,871개 |
| 품질 검사 | ✅ 통과 |
| GUI 차트 테스트 | ⏳ 사용자 확인 필요 |
