# [11-004] 데이터 정합성 검사 및 복구 시스템 구현 계획서

> **작성일**: 2026-01-14 | **예상**: 10h (Phase 1-5)
> **우선순위**: 11 (Data Layer) | **상태**: ✅ 계획 확정

---

## 1. 배경 및 목표

11-003 Parquet 마이그레이션 완료 후 일부 파일에 오염된 데이터 존재 가능성 발견.
데이터 품질 보장을 위한 체계적인 검사 및 자동 복구 시스템 구현.

**핵심 기능**:
1. **Validation** - OHLCV 무결성, 시계열 연속성, 이상치 탐지
2. **Repair** - 중복 제거, API 갭 채우기, NULL/이상치 자동 보간
3. **Report** - 검사/복구 결과 JSON 리포트 생성
4. **Sync** - 리샘플링 TF 및 보조지표 동기화 검증

---

## 2. 문제 유형

### 2.1 Daily 데이터 (`all_daily.parquet`)
| 문제 유형 | 설명 | 심각도 |
|-----------|------|--------|
| 날짜 갭 | 거래일인데 데이터 없음 | 높음 |
| 중복 레코드 | 동일 (ticker, date) 중복 | 중간 |
| 이상치 | 가격 급등락 (전일 대비 ±100% 등) | 높음 |
| NULL 값 | OHLCV 필수 컬럼에 NULL | 중간 |
| OHLC 무결성 | High < Low, Open/Close 범위 벗어남 | 높음 |

### 2.2 Intraday 데이터 (`1m/`, `1h/`)
| 문제 유형 | 설명 | 심각도 |
|-----------|------|--------|
| 타임스탬프 갭 | 장중 연속 분봉 누락 | 중간 |
| 타임스탬프 중복 | 동일 timestamp 중복 | 중간 |
| 이상치 | 가격 스파이크 | 높음 |

### 2.3 리샘플링/보조지표 (3m, 5m, 15m + OBV, ATR 등)
| 문제 유형 | 설명 | 심각도 |
|-----------|------|--------|
| OHLCV 집계 불일치 | 5m ≠ 1m×5 집계 | 높음 |
| Cross-TF 불일치 | 1h close ≠ 마지막 1m close | 높음 |
| 지표 비동기 | 보조지표 timestamp ≠ OHLCV | 중간 |

---

## 3. 레이어 체크

- [x] 레이어 규칙 위반 없음 (`backend.data` / `backend.scripts` 내부)
- [x] 순환 의존성 없음
- [ ] DI Container 등록: **불필요** (CLI 스크립트)

---

## 4. 기존 솔루션 검색 결과

| 솔루션 | 출처 | 채택 여부 | 사유 |
|--------|------|----------|------|
| **Pandera** | PyPI | ⚠️ 부분 채택 | OHLC 관계식 등 커스텀 검사 필요 |
| **Great Expectations** | PyPI | ❌ 미채택 | 프로젝트 규모 대비 과도한 설정 |
| **Pandas 내장** | stdlib | ✅ 채택 | 이미 사용 중, OHLC 검증에 충분 |
| **validate_parquet_quality.py** | 프로젝트 | ✅ 확장 | 280줄 구현 완료, 기본 검증 존재 |

**결정**: 기존 스크립트 확장 + Pandas 활용 (외부 의존성 최소화)

---

## 5. 사용자 결정 사항 (확정)

| 항목 | 결정 |
|------|------|
| 이상치 처리 | ✅ **자동 보간** 후 보고서 생성 |
| 백업 정책 | ✅ **변경 파일만** 백업 |
| 검사 우선순위 | ✅ **Daily 먼저** → Intraday |
| API 호출 제한 | ✅ **무제한 티어** |

---

## 6. 변경 파일

| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
| `backend/scripts/validate_parquet_quality.py` | MODIFY | +250 (총 530줄) |
| `backend/scripts/repair_parquet_data.py` | NEW | ~300줄 |
| `backend/data/validators.py` | NEW | ~250줄 |
| `tests/test_data_integrity.py` | NEW | ~300줄 |

---

## 7. 실행 단계

### Phase 1: 검사 강화 (2h)

#### Step 1.1: OHLC 관계 검증

`backend/data/validators.py`:

```python
def validate_ohlc_relationship(df: pd.DataFrame) -> list[dict]:
    """
    OHLC 관계 무결성 검사
    - High >= max(Open, Close)
    - Low <= min(Open, Close)
    - High >= Low
    """
```

#### Step 1.2: 시계열 갭 탐지

```python
def detect_daily_gaps(df: pd.DataFrame, trading_calendar: list[str]) -> list[str]:
    """거래일 갭 탐지"""

def detect_intraday_gaps(df: pd.DataFrame, market_hours: tuple) -> list[int]:
    """장중 시간 갭 탐지"""
```

#### Step 1.3: JSON 리포트 출력

`validate_parquet_quality.py`에 `--output-json` 옵션 추가

---

### Phase 2: 복구 기능 (1h)

```python
class DataRepairer:
    def __init__(self, pm: ParquetManager, dry_run: bool = True):
        self.backup_dir = Path("data/backup")
        
    def remove_duplicates(self, data_type: str = "daily") -> int
    def fill_nulls(self, strategy: str = "forward") -> int
    def backup_changed_files(self, files: list[Path]) -> Path
```

---

### Phase 3: API 갭 채우기 (3h)

```python
async def fetch_missing_daily(ticker: str, missing_dates: list[str]) -> pd.DataFrame:
    """Massive.com API로 누락된 일봉 데이터 조회 (무제한 티어)"""

async def fetch_missing_intraday(ticker: str, tf: str, gaps: list[int]) -> pd.DataFrame:
    """Massive.com API로 누락된 분봉 데이터 조회"""
```

---

### Phase 4: 이상치 탐지 (2h)

```python
def detect_and_interpolate_outliers(
    df: pd.DataFrame, 
    z_threshold: float = 3.0
) -> tuple[pd.DataFrame, list[dict]]:
    """
    Z-score 기반 이상치 탐지 및 자동 보간
    Returns: (보간된 df, 보간 리포트)
    """
```

---

### Phase 5: 리샘플링 및 보조지표 동기화 (2h)

#### Step 5.1: 리샘플링 정합성

```python
def validate_resampled_data(source_tf: str, target_tf: str, ticker: str) -> dict:
    """
    검사 항목:
    1. 타임스탬프 정렬 (5m = 1m×5 집계)
    2. OHLCV 집계 규칙 (O=first, H=max, L=min, C=last, V=sum)
    3. 누락 캔들 탐지
    """
```

#### Step 5.2: 보조지표 동기화

```python
def validate_indicator_sync(ohlcv_df, indicator_df, indicator_name: str) -> list[dict]:
    """
    검사 항목:
    1. 타임스탬프 일치
    2. 레코드 수 일치
    3. 재계산 vs 저장값 비교 (허용 오차 내)
    """
```

#### Step 5.3: Cross-TF 정합성

```python
def validate_cross_tf_consistency(
    ticker: str, 
    timeframes: list[str] = ["1m", "3m", "5m", "15m", "1h"]
) -> dict:
    """
    검사 항목:
    1. 동일 시점 가격 일치 (1h close == 마지막 1m close)
    2. 볼륨 합계 일치 (1h volume == sum(1m volumes))
    """
```

---

## 8. 검증

### 8.1 자동화 테스트

```bash
pytest tests/test_data_integrity.py -v
```

**테스트 케이스**:
1. `test_ohlc_validation_detects_high_lt_low`
2. `test_daily_gap_detection`
3. `test_duplicate_removal`
4. `test_dry_run_no_modification`
5. `test_resampled_ohlcv_aggregation` (Phase 5)
6. `test_indicator_sync_with_ohlcv` (Phase 5)
7. `test_cross_tf_price_consistency` (Phase 5)

### 8.2 수동 검증

```powershell
# 검사 실행
python -m backend.scripts.validate_parquet_quality --verbose --output-json data/reports/integrity.json

# Dry-run 복구
python -m backend.scripts.repair_parquet_data --dry-run

# 실제 복구
python -m backend.scripts.repair_parquet_data --apply
```

---

## 9. 비기능 요구사항

| 항목 | 구현 방법 |
|------|----------|
| 성능 (Daily < 5분) | PyArrow 네이티브 연산, chunked 처리 |
| 멱등성 | 동일 입력 → 동일 결과 |
| 롤백 | 변경 파일만 자동 백업 |
| 로깅 | loguru JSON 구조화 |
| Dry-run | `--dry-run` 기본값 |

---

## 10. API 연동

| 데이터 | Endpoint | 비고 |
|--------|----------|------|
| Daily | `GET /v2/aggs/ticker/{ticker}/range/1/day/{from}/{to}` | Massive REST |
| Intraday | `GET /v2/aggs/ticker/{ticker}/range/1/minute/{from}/{to}` | 분봉 |

> **API 티어**: 무제한 (Rate limit 불필요)

---

## 11. 아키텍처

```
backend/scripts/
├── validate_parquet_quality.py    # [MODIFY] 검사 로직 강화
├── repair_parquet_data.py         # [NEW] 복구 CLI
└── __init__.py

backend/data/
├── validators.py                  # [NEW] 검증 유틸리티 (Phase 1-5)
└── parquet_manager.py             # 기존, I/O 활용

tests/
└── test_data_integrity.py         # [NEW] 검증 테스트
```

---

> [!NOTE]
> Phase 1 먼저 구현 후 결과 확인 → Phase 2-5 순차 진행
