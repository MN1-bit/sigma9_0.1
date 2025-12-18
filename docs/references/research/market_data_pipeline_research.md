# Market Data Pipeline Research: 5000종목 Accumulation 탐지 전략

> **작성일**: 2025-12-18  
> **목적**: 5000개 종목에 대한 **정밀 매집 탐지(Volume Dry-out, OBV, Tight Range)**를 위한 데이터 파이프라인 설계  
> **핵심 이슈**: IBKR Scanner의 기능적 한계와 Rate Limit으로 인한 전수 조사 불가능 문제 해결

---

## 1. Problem Statement

우리의 핵심 전략인 **Seismograph Strategy (Phase 1 Accumulation)**은 단순한 가격/거래량 필터링이 아님.
다음 4단계 조건을 **모두** 확인해야 함:

1.  **Volume Dry-out**: 최근 3일 거래량 < 20일 평균의 40% (상대적 비교)
2.  **OBV Divergence**: 주가 하락/횡보 중 OBV 상승
3.  **Accumulation Bar**: 특정 조건의 매집봉 출현
4.  **Tight Range**: 5일 ATR < 20일 ATR의 50% (변동성 축소)

### ❌ IBKR Scanner의 한계

| 조건 | IBKR Scanner 지원 여부 |
|------|------------------------|
| **평균 대비 상대 거래량** | ❌ (절대값만 가능) |
| **OBV 계산** | ❌ |
| **ATR 비교** | ❌ |
| **Float 필터** | ❌ |

### ❌ IBKR API Rate Limit의 한계 (로컬 계산 시도 시)

만약 5000종목의 20일치 데이터를 받아와서 로컬에서 계산한다면?

- **Pacing Violation**: IBKR은 10초당 6개의 Historical Data 요청만 허용.
- **소요 시간**: `5000종목 / (0.6종목/초) = 8333초 (약 2시간 20분)`
- **결론**: 장 시작 전(Pre-market)에 Watchlist 생성 불가능.

---

## 2. Solution: Polygon.io "Grouped Daily" (Bulk Fetch)

**외부 데이터 공급자(Polygon.io)를 사용하여 "전체 시장 스냅샷"을 로컬로 가져오는 방식.**

### 2.1 Polygon.io Grouped Daily Endpoint

- **기능**: 특정 날짜의 **미국 주식 전체(5000+)**의 OHLCV 데이터를 **단 1번의 API 호출**로 반환.
- **Endpoint**: `GET /v2/aggs/grouped/locale/us/market/stocks/{date}`
- **비용**: Free Tier에서도 사용 가능 (Rate Limit: 분당 5회).

### 2.2 Feasibility Calculation (성능 검증)

우리가 필요한 데이터: **최근 20일치 전체 시장 데이터**

1.  **데이터 요청**: 20일치 = 20번 API 호출.
2.  **Rate Limit 적용**:
    - Free Tier (5회/분): `20회 / 5회 = 4분` 소요.
    - Paid Tier (Unlimited): `2초` 소요.
3.  **데이터 크기**:
    - 1일치 JSON ≈ 200KB (압축 시) ~ 1MB.
    - 20일치 ≈ 20MB ~ 50MB.
    - **Memory Load**: Python pandas로 로딩 시 1초 미만.

### ✅ 결론: "Polygon.io를 사용하면 5000종목 전수 조사가 4분 만에 가능하다!"

---

## 3. Proposed Architecture (Option D: Database-Centric Incremental Update)

**"DB에 저장해두고, 매일 누락분(하루치)만 채워넣자."**

### 3.1 Workflow

1.  **데이터베이스 구축 (SQLite)**:
    - `backend/data/market_data.db` 생성.
    - 테이블: `daily_bars` (ticker, date, open, high, low, close, volume).

2.  **Polygon.io Bulk Fetch (Incremental)**:
    - **최초 실행**: 최근 2년치 데이터 Fetch (Free Tier 기준 10분 내외).
    - **매일 실행**: **어제 날짜 하루치** 데이터만 Fetch (`/v2/aggs/grouped/...` 1회 호출).
    - **비용**: 매일 API 호출 **단 1회**.

3.  **Seismograph Strategy (Local DB)**:
    - DB에서 `SELECT * FROM daily_bars WHERE date >= (20일전)` 쿼리.
    - 메모리에 로드 후 매집 조건(Dry-out, OBV, Tight Range) 전수 검사.
    - 네트워크 Latency 없이 초고속 처리 가능.

### 3.2 장점
- **API 의존성 최소화**: 매일 호출 1회. 장전 네트워크 장애 시에도 어제까지의 데이터로 분석 가능.
- **데이터 자산화**: 5000종목의 히스토리가 쌓이면서 백테스팅 자산이 됨.
- **Zero Latency**: 로컬 DB에서 읽으므로 매우 빠름.

---

## 4. Implementation Details

### 4.1 Schema Design
```sql
CREATE TABLE daily_bars (
    ticker TEXT,
    date TEXT, -- YYYY-MM-DD
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    PRIMARY KEY (ticker, date)
);
CREATE INDEX idx_date ON daily_bars(date);
```

### 4.2 Polygon Loader Logic
```python
def update_market_data():
    last_date = db.get_last_date()
    today = datetime.now().date()
    
    # 누락된 날짜만큼 Loop (주말/휴일 제외)
    for date in date_range(last_date + 1, today - 1):
        data = polygon.fetch_grouped_daily(date) # 1 API Call
        db.upsert_bulk(data)
```

---

## 5. 결론 (Action Plan)

1.  **SQLite 스키마 설계**: `backend/data/database.py`
2.  **Polygon 증분 로더 구현**: `backend/data/polygon_loader.py`
3.  **Seismograph 연동**: DB 기반 Watchlist 생성 로직 구현.
