# Parquet Migration 리팩터링 Devlog

> **작성일**: 2026-01-10 02:38
> **관련 계획서**: [11-001_parquet_migration.md](../refactor/11-001_parquet_migration.md)

## 진행 현황

| Step | 상태 | 완료 시간 |
|------|------|----------|
| Step 1: ParquetManager 구현 | ✅ 완료 | 02:46 |
| Step 2: MassiveLoader 저장 분기 | ✅ 완료 | 02:55 |
| Step 3: ChartDataService 연동 | ✅ 완료 | 02:57 |
| Step 4: 마이그레이션 스크립트 | ✅ 완료 | 02:47 |

---

## Step 1: ParquetManager 구현

### 변경 사항

- `backend/data/parquet_manager.py`: **신규 생성** (344 lines)
  - `ParquetManager` 클래스: Parquet 파일 Read/Write 관리
  - Daily 메서드: `write_daily()`, `append_daily()`, `read_daily()`
  - Intraday 메서드: `write_intraday()`, `append_intraday()`, `read_intraday()`
  - 유틸리티: `get_available_tickers()`, `get_stats()`, `delete_ticker_intraday()`

### 주요 설계 결정

1. **PyArrow 선택**: pandas 호환성, 표준 라이브러리
2. **일봉 통합 파일**: `data/parquet/daily/all_daily.parquet`
3. **분봉 티커별 분리**: `data/parquet/intraday/{ticker}_{timeframe}.parquet`
4. **중복 제거**: append 시 ticker+date 또는 timestamp 기준 dedup

### 발생한 이슈

- **Bug**: `read_daily()`의 날짜 필터가 현재 날짜 기준으로 동작하여 테스트 데이터 조회 실패
- **Fix**: `days=None` 또는 `days=0`이면 필터링 스킵, 아니면 데이터 내 최신 N일 기준 필터

### 검증 결과

- ruff check: ✅ 통과
- 기본 테스트: ✅ Write=2, Read=2 정상

---

## Step 2: MassiveLoader 저장 분기

### 변경 사항

- `backend/data/massive_loader.py`: **수정** (+40 lines)
  - `__init__`: `parquet_manager` 선택적 파라미터 추가
  - `_save_daily_bars()`: SQLite + Parquet 듀얼 라이트 헬퍼 메서드
  - `initial_load()`, `update_market_data()`, `fetch_single_day()`: `_save_daily_bars()` 호출

### 검증 결과

- ruff check: ✅ 통과
- import test: ✅ 통과

---

## Step 3: ChartDataService 연동

### 변경 사항

- `frontend/services/chart_data_service.py`: **수정** (+50 lines)
  - `__init__`: `parquet_dir` 선택적 파라미터 추가
  - `_get_daily_data()`: Parquet 우선, SQLite fallback 로직
  - `_df_to_bars()`: Parquet DataFrame → DailyBar 유사 객체 변환

### 검증 결과

- ruff check: ✅ 통과 (DynamicStopLoss 미사용 import 제거)
- import test: ✅ 통과

---

## Step 4: 마이그레이션 스크립트

### 변경 사항

- `backend/scripts/migrate_to_parquet.py`: **신규 생성** (167 lines)
  - `migrate_daily_data()`: SQLite → Parquet 배치 변환
  - `verify_migration()`: 데이터 무결성 검증 (row count 비교)
  - CLI 지원: `--verify-only`, `--db-path`, `--parquet-dir`

### 검증 결과

- 구문 검사: ✅ 통과

---

## 최종 검증 결과

| 검증 항목 | 결과 |
|----------|------|
| ruff format | ✅ (16 files reformatted) |
| ruff check | ✅ (1 pre-existing error in archive) |
| import tests | ✅ all passed |
| 수동 테스트 | ⏭️ (마이그레이션 실행 후 확인) |

## 다음 단계

1. ~~`python -m backend.scripts.migrate_to_parquet` 실행으로 데이터 마이그레이션~~ ✅ 완료
2. GUI 실행 후 차트 정상 표시 확인

---

## 마이그레이션 실행 결과 (2026-01-10 03:07)

| 항목 | 값 |
|------|-----|
| 총 티커 수 | 19,669 |
| 처리 시간 | ~4분 |
| 검증 결과 | ✅ 레코드 일치 |
| Parquet 파일 크기 | **368.74 MB** |
| 압축률 | ~74% (1.4GB → 369MB)
