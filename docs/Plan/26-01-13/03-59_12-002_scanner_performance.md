# Scanner 성능 최적화 계획서

> **작성일**: 2026-01-10 06:58
> **우선순위**: 12 (Performance) | **예상 소요**: 4-5h | **위험도**: 중간
> **의존성**: 12-001 (Full Universe Scan) 완료

---

## 1. 목표

`run_daily_scan()` 실행 시간을 **10초 이하**로 단축 (현재 ~300초).

### 해결 전략
5가지 최적화 조합:
1. **Predicate Pushdown** - Row Group 레벨 필터링 (구현 완료)
2. **벌크 로드** - 파일 1회 읽기 후 메모리 처리
3. **병렬 처리** - CPU 병렬 스코어 계산 (AWS 호환)
4. **스코어 캐싱** - 일일 스코어 저장/재사용
5. **증분 스캔** - 변경된 티커만 재계산

---

## 2. 레이어 체크 (IMP-planning §2)

- [x] **레이어 규칙 위반 없음**: `backend.data` → `backend.core` 단방향
- [x] **순환 의존성 없음**: 데이터 레이어 내부 확장
- [x] **DI Container 등록**: 불필요 (기존 Scanner 사용)
- [x] **파일 크기 제한**: 신규 파일 < 500줄

---

## 3. 영향 분석

### 변경 파일

| 파일 | 유형 | 변경 내용 | 예상 라인 |
|------|------|----------|----------|
| `parquet_manager.py` | MODIFY | `read_daily_bulk()` 추가 | +30줄 |
| `data_repository.py` | MODIFY | `get_daily_bars_bulk()` 추가 | +10줄 |
| `scanner.py` | MODIFY | 벌크 조회 + 병렬 처리 적용 | +40줄 |
| `score_cache.py` | NEW | 스코어 캐싱 (S3 호환) | ~80줄 |

### 영향받는 모듈
- `backend/core/scanner.py` (주요 변경)
- `backend/data/` (메서드 추가, 기존 호환 유지)

### 순환 의존성
- 없음 (데이터 레이어 확장)

---

## 4. 실행 계획

### Step 1: Predicate Pushdown 적용 ✅ (완료)

```python
# parquet_manager.py
def read_daily(self, ticker=None, ...):
    if ticker:
        filters = [("ticker", "=", ticker)]
        df = pq.read_table(self.daily_path, filters=filters).to_pandas()
```

**검증**: Row Groups 13 → 28개 (완료)

---

### Step 2: 벌크 로드 메서드 추가 (30분) ✅

```python
# parquet_manager.py
def read_daily_bulk(
    self,
    tickers: list[str] | None = None,
    days: int = 20,
) -> dict[str, list[dict]]:
    """
    [12-002] 여러 티커의 일봉 데이터를 한 번에 조회
    ELI5: 파일 1회만 읽고 티커별로 나눕니다
    """
    df = pq.read_table(self.daily_path).to_pandas()
    
    # 날짜 필터
    unique_dates = sorted(df["date"].unique(), reverse=True)[:days]
    df = df[df["date"].isin(unique_dates)]
    
    # 티커 필터
    if tickers:
        df = df[df["ticker"].isin(tickers)]
    
    # 티커별 그룹화
    return {t: g.sort_values("date").to_dict("records") 
            for t, g in df.groupby("ticker")}
```

---

### Step 3: Scanner 벌크 조회 적용 (45분) ✅

```python
# scanner.py
async def run_daily_scan(self, ...):
    # 1. 전체 티커 필터링
    candidates = await self._get_universe_candidates(...)
    
    # 2. 벌크 로드 (파일 1회 읽기)
    all_data = self.repo._pm.read_daily_bulk(candidates, days=20)
    
    # 3. 스코어 계산
    results = []
    for ticker, data in all_data.items():
        if len(data) < 5:
            continue
        result = self.strategy.calculate_watchlist_score_detailed(ticker, data)
        results.append(result)
```

---

### Step 4: 병렬 처리 적용 (1시간) ✅

**AWS 환경별 Executor 분기**:

```python
import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

# AWS Lambda 환경 감지
IS_LAMBDA = "AWS_LAMBDA_FUNCTION_NAME" in os.environ

def _calculate_score_worker(args, strategy_config):
    """워커용 스코어 계산 함수"""
    ticker, data = args
    strategy = SeismographStrategy(**strategy_config)
    return strategy.calculate_watchlist_score_detailed(ticker, data)

async def run_daily_scan(self, ...):
    # 환경별 Executor 선택
    Executor = ThreadPoolExecutor if IS_LAMBDA else ProcessPoolExecutor
    max_workers = 2 if IS_LAMBDA else 4
    
    with Executor(max_workers=max_workers) as pool:
        results = list(pool.map(calc_fn, all_data.items()))
```

---

### Step 5: 스코어 캐싱 추가 (1시간)

**로컬/S3 겸용**:

```python
# backend/data/score_cache.py
class ScoreCache:
    """일일 스코어 캐시 (로컬 Parquet or S3)"""
    
    def __init__(self, cache_dir=None, s3_bucket=None):
        self.use_s3 = s3_bucket is not None
        ...
    
    def get(self, ticker: str, date: str) -> dict | None:
        ...
    
    def set(self, ticker: str, date: str, score: dict):
        ...
    
    def flush(self):
        """캐시 저장 (로컬 or S3)"""
        ...
```

---

### Step 6: 증분 스캔 적용 (1시간)

```python
async def run_daily_scan(self, ...):
    cache = self.score_cache.load(today)
    
    for ticker, data in all_data.items():
        cached = cache.get(ticker)
        if cached and cached["date"] == data[-1]["date"]:
            results.append(cached)  # 캐시 히트
        else:
            result = calc_score(ticker, data)
            cache.set(ticker, result)
            results.append(result)
    
    cache.flush()
```

---

## 5. 예상 성능

| 단계 | 예상 시간 |
|------|----------|
| 현재 (개별 조회) | ~300초 |
| Step 1 (Predicate Pushdown) | ~200초 ❌ |
| Step 2-3 (벌크 로드) | ~30초 |
| Step 4 (병렬 처리) | ~10초 (EC2) / ~15초 (Lambda) |
| Step 5-6 (캐싱+증분) | ~2초 (캐시 히트) |

---

## 6. AWS 호환성

| 환경 | Executor | 캐시 | 예상 성능 |
|------|----------|------|----------|
| **로컬/EC2** | ProcessPoolExecutor | 로컬 Parquet | ~10초 |
| **Lambda** | ThreadPoolExecutor | S3 | ~15초 |
| **ECS/Fargate** | ProcessPoolExecutor | S3 or EFS | ~10초 |

---

## 7. 검증 계획

### 자동화 테스트

```bash
# 린트
ruff check backend/data/parquet_manager.py backend/core/scanner.py

# lint-imports (레이어 검증)
lint-imports

# 순환 의존성
pydeps backend --show-cycles --no-output
```

### 성능 테스트

```bash
python -c "
import asyncio, time
from backend.core.scanner import run_scan

async def test():
    start = time.time()
    result = await run_scan()
    elapsed = time.time() - start
    print(f'Time: {elapsed:.1f}s, Items: {len(result)}')
    assert elapsed < 20, f'Too slow: {elapsed}s'

asyncio.run(test())
"
```

**성공 기준**:
- [ ] `lint-imports` 통과
- [ ] `pydeps --show-cycles` 순환 없음
- [ ] 스캔 시간 < 20초 (로컬)

---

## 8. 롤백 계획

1. Git revert
2. 기존 개별 조회 로직 복원

---

## 9. 관련 문서

- [12-001_full_universe_scan.md](./12-001_full_universe_scan.md)
