# SQLite → Parquet 대규모 마이그레이션 계획서

> **작성일**: 2026-01-10 02:34
> **우선순위**: 11 (Data Format) | **예상 소요**: 12-16h | **위험도**: 중간

## 1. 목표

현재 SQLite 기반 데이터 레이어를 Parquet 포맷으로 마이그레이션하여:
- **조회 성능 향상**: 컬럼형 저장소로 분석 쿼리 최적화
- **파일 관리 용이성**: 티커별 분리로 백업/복구 단순화
- **finplot 차트 통합**: Parquet → DataFrame 직접 로딩으로 차트 렌더링 최적화

### 파일 구조 (목표)
```
data/parquet/
├── intraday/
│   ├── AAPL_1m.parquet     # 티커별 1분봉
│   ├── AAPL_1h.parquet     # 티커별 1시봉
│   ├── MSFT_1m.parquet
│   └── ...
└── daily/
    └── all_daily.parquet   # 전체 티커 일봉 통합
```

---

## 2. 영향 분석

### 2.1 현재 상태

| 항목 | 값 |
|------|---|
| DB 크기 | ~1.4 GB |
| ORM 모델 | `DailyBar`, `IntradayBar`, `Ticker` |
| 핵심 파일 | `database.py` (783L), `massive_loader.py` (565L), `chart_data_service.py` (401L) |

### 2.2 변경 대상 파일 (직접 영향)

| 파일 | 변경 유형 | 영향도 |
|------|----------|--------|
| `backend/data/database.py` | 수정 (Parquet fallback 추가) | 높음 |
| `backend/data/massive_loader.py` | 수정 (저장 로직 분기) | 높음 |
| `backend/data/parquet_manager.py` | **신규 생성** | - |
| `frontend/services/chart_data_service.py` | 수정 (Parquet 읽기) | 중간 |
| `backend/core/backtest_engine.py` | 수정 (데이터 소스) | 중간 |
| `backend/container.py` | 수정 (DI 등록) | 낮음 |
| `backend/startup/database.py` | 수정 (초기화) | 낮음 |

### 2.3 간접 영향 (DB 호출)

- `backend/api/routes/scanner.py` — MarketDB 사용
- `backend/api/routes/chart.py` — 차트 데이터 조회
- `tests/test_database.py` — 테스트 수정 필요
- `tests/test_massive_loader.py` — Mock 업데이트

### 2.4 순환 의존성 현황

현재 `backend` 모듈에 순환 의존성 없음 (pydeps 확인됨).

---

## 3. 실행 계획

### Step 1: ParquetManager 구현 (3-4h)

신규 파일 `backend/data/parquet_manager.py` 생성:

```python
class ParquetManager:
    """Parquet 파일 Read/Write 관리"""
    
    def __init__(self, base_dir: str = "data/parquet"):
        ...
    
    # Intraday (티커별 분리)
    async def write_intraday(self, ticker: str, timeframe: str, df: pd.DataFrame)
    async def read_intraday(self, ticker: str, timeframe: str, days: int) -> pd.DataFrame
    async def append_intraday(self, ticker: str, timeframe: str, df: pd.DataFrame)
    
    # Daily (통합 파일)
    async def write_daily(self, df: pd.DataFrame)
    async def read_daily(self, ticker: str | None, days: int) -> pd.DataFrame
    async def append_daily(self, df: pd.DataFrame)
```

**세부 작업**:
- [ ] 디렉터리 구조 자동 생성
- [ ] PyArrow 또는 Polars 기반 I/O
- [ ] 파티셔닝 전략: 일봉은 `(ticker, date)`, 분봉은 `(date)`
- [ ] 중복 방지 로직 (append 시 dedup)

---

### Step 2: MassiveLoader 저장 분기 (2-3h)

`backend/data/massive_loader.py` 수정:

```diff
  async def _save_bars(self, bars: list[dict]):
+     # Parquet에 저장 (primary)
+     df = pd.DataFrame(bars)
+     await self.parquet_manager.append_daily(df)
+ 
      # SQLite에도 저장 (레거시 호환)
      await self.db.upsert_bulk(bars)
```

**세부 작업**:
- [ ] 생성자에 `ParquetManager` 주입
- [ ] 일봉/분봉 저장 경로 분기
- [ ] WAL 모드 유지 (SQLite 호환)

---

### Step 3: ChartDataService Parquet 연동 (2-3h)

`frontend/services/chart_data_service.py` 수정:

```diff
  async def _get_daily_data(self, ticker: str, days: int):
+     # Try Parquet first
+     try:
+         df = await self.parquet_manager.read_daily(ticker, days)
+         if not df.empty:
+             return self._df_to_candles(df)
+     except FileNotFoundError:
+         pass
+ 
      # Fallback to SQLite
      bars = await self.db.get_daily_bars(ticker, days)
```

**세부 작업**:
- [ ] `ParquetManager` 의존성 추가
- [ ] DataFrame → Candle 변환 유틸리티
- [ ] 캐싱 전략 (메모리 df 재사용)

---

### Step 4: 마이그레이션 스크립트 (2h)

`backend/scripts/migrate_to_parquet.py` 신규 생성:

```python
async def migrate_sqlite_to_parquet():
    """기존 SQLite → Parquet 일괄 변환"""
    db = MarketDB("data/market_data.db")
    pm = ParquetManager("data/parquet")
    
    # Daily bars
    tickers = await db.get_all_tickers_with_data()
    for ticker in tqdm(tickers):
        bars = await db.get_daily_bars(ticker, days=365)
        df = pd.DataFrame([b.to_dict() for b in bars])
        await pm.append_daily(df)
```

---

## 4. 검증 계획

### 4.1 자동화 테스트

| 테스트 | 명령어 | 검증 내용 |
|--------|--------|----------|
| 기존 DB 테스트 | `pytest tests/test_database.py -v` | SQLite 레거시 호환 |
| Loader 테스트 | `pytest tests/test_massive_loader.py -v` | 증분 업데이트 로직 |
| 전체 테스트 | `pytest tests/ -v` | 회귀 테스트 |
| Lint | `ruff check . && lint-imports` | 코드 품질 |
| 순환 의존성 | `pydeps backend --show-cycles --no-output` | 순환 없음 확인 |

### 4.2 신규 테스트 (추가 예정)

- `tests/test_parquet_manager.py`:
  - [ ] write/read/append 라운드트립
  - [ ] 중복 데이터 처리
  - [ ] 빈 파일 처리
  - [ ] 대용량 데이터 성능 (5000 rows < 1s)

### 4.3 수동 검증

1. **마이그레이션 완료 후**:
   - SQLite row count == Parquet row count 확인
   - 랜덤 샘플 10개 티커 OHLCV 비교

2. **차트 표시 확인**:
   - Frontend GUI 실행 (`python -m frontend`)
   - 임의 티커 선택 → 일봉/분봉 차트 정상 표시 확인

3. **성능 벤치마크**:
   - 동일 쿼리 SQLite vs Parquet 조회 시간 비교
   - 목표: Parquet ≤ SQLite × 0.5 (50% 이상 개선)

---

## 5. 롤백 계획

1. Parquet 파일 삭제: `rm -rf data/parquet/`
2. `ChartDataService` fallback이 SQLite로 자동 전환
3. Git revert 커밋

---

## 6. User Review Required

> [!IMPORTANT]
> **결정 필요 사항**:
> 1. Parquet 라이브러리 선택: **PyArrow** vs **Polars** (성능 vs 의존성 크기)
> 2. 일봉 통합 파일 파티셔닝: `all_daily.parquet` 단일 vs `daily/{date}.parquet` 날짜별 분리
> 3. SQLite 완전 제거 시점: Phase 2 (점진적 전환) vs 즉시 제거

---

## 7. 관련 문서

- [REFACTORING.md](file:///d:/Codes/Sigma9-0.1/docs/Plan/refactor/REFACTORING.md) — 리팩터링 가이드
- [09-001_finplot_chart_migration.md](file:///d:/Codes/Sigma9-0.1/docs/Plan/refactor/09-001_finplot_chart_migration.md) — finplot 차트 마이그레이션 (연관)
