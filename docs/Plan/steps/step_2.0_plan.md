# Step 2.0: Market Data Pipeline Implementation Plan

> **작성일**: 2025-12-18
> **작성자**: Antigravity (Assistant)
> **Phase**: 2 (Core Engine)
> **목표**: Polygon.io와 SQLite를 활용한 고성능 매집 탐지 데이터 파이프라인 구축

---

## 1. 개요 (Overview)

Sigma9의 핵심 전략인 Seismograph는 5,000개 이상의 미국 주식 전체에 대해 정밀한 매집 패턴(Volume Dry-out, OBV Divergence, Tight Range)을 탐지해야 합니다. IBKR API의 Rate Limit 한계를 극복하고 분석 효율을 극대화하기 위해 **Polygon.io Grouped Daily API**와 **로컬 SQLite 데이터베이스**를 결합한 하이브리드 파이프라인을 구축합니다.

### 1.1 핵심 전략: Database-Centric Incremental Update

- **Source**: Polygon.io (`Grouped Daily` - 하루 1회 호출로 전 종목 수신, 최초 1회 1년치 데이터 저장)
- **Storage**: SQLite (`market_data.db` - 로컬 영구 저장)
- **Update Strategy**: **증분 업데이트 (Incremental Update)**
    - 매일 장 시작 전, DB의 마지막 업데이트 날짜 확인
    - 누락된 날짜(주말/휴일 제외)에 대해서만 Polygon API 호출
    - DB에 Upsert 수행

---

## 2. 아키텍처 설계 (Architecture Design)

### 2.1 데이터 흐름도

```mermaid
graph TD
    A[Polygon.io API] -->|Grouped Daily JSON| B(PolygonLoader)
    B -->|Parse & Clean| C{Latest Date Check}
    C -->|Missing Dates| D[Upsert to DB]
    E[MarketDB (SQLite)] -->|Latest 20 Days| F(Seismograph Strategy)
    F -->|Accumulation Logic| G[Watchlist 50]
    G -->|Subscribe| H[IBKR Real-time Feed]
```


### 2.2 데이터베이스 스키마

#### A. `daily_bars` (시계열 데이터)
| Column | Type | Description |
|--------|------|-------------|
| **ticker** | TEXT | Primary Key (Composite) |
| **date** | TEXT | Primary Key (YYYY-MM-DD) |
| open | REAL | 시가 |
| high | REAL | 고가 |
| low | REAL | 저가 |
| close | REAL | 종가 |
| volume | INTEGER | 거래량 |
| vwap | REAL | 거래량 가중 평균가 |
| transactions | INTEGER | 체결 건수 |

#### B. `tickers` (기본 정보 & 펀더멘털)
| Column | Type | Description |
|--------|------|-------------|
| **ticker** | TEXT | Primary Key |
| name | TEXT | 종목명 |
| market_cap | REAL | 시가총액 (USD) - *Universe Filter용* |
| outstanding_shares | REAL | 총 발행 주식 수 |
| float_shares | REAL | 유통 주식 수 (Float) - *Universe Filter용* |
| primary_exchange | TEXT | 주 거래소 (NYSE, NASDAQ etc) |
| last_updated | TEXT | 마지막 업데이트 날짜 |

---

## 3. 상세 구현 계획 (Implementation Steps)

### 3.1 Database Setup (`backend/data/database.py`)
- **Library**: `SQLAlchemy 2.0` (Async), `Alembic`
- **Task**:
    - `MarketDB` 클래스 구현
    - `DailyBar`, `Ticker` ORM 모델 정의
    - `initialize()`: 테이블 생성 & **WAL Mode (Write-Ahead Logging) 활성화** (성능 최적화)
    - `upsert_bulk(bars)`: `INSERT OR REPLACE` 최적화
    - `update_fundamentals(ticker_info_list)`: Ticker 정보 Upsert 로직 구현

### 3.2 Polygon Client (`backend/data/polygon_client.py`)
- **Library**: `httpx`, `polygon-api-client` (Optional)
- **Task**:
    - `PolygonClient` 클래스 구현
    - Rate Limit 핸들링 (Free Tier: 5 req/min)
    - `fetch_grouped_daily(date)`: `/v2/aggs/grouped/locale/us/market/stocks/{date}`

### 3.3 Data Loader & Fundamental (`backend/data/polygon_loader.py`)
- **Task**:
    - `PolygonLoader` 클래스 구현
    - `update_market_data()`: 증분 업데이트 메인 로직
    - `fetch_fundamentals()`: Ticker Details API(`/v3/reference/tickers/{ticker}`) 연동
        - *Rate Limit 고려*: 필요 시 Bulk API 사용하거나 주요 종목만 Lazy Loading
        - `tickers` 테이블에 Market Cap, Float 업데이트

### 3.4 Integration
- **Task**:
    - `config.yaml`: Polygon API Key, DB Path 설정 추가
    - `main.py` (또는 `server.py`): 서버 시작 시 `update_market_data()` 자동 실행

---

## 4. 검증 계획 (Verification Plan)

### 4.1 Unit Tests
- `test_database.py`: DB 생성, CRUD, Bulk Insert 성능 테스트
- `test_polygon_loader.py`: Mock API를 이용한 증분 업데이트 로직(날짜 계산) 검증

### 4.2 Integration Tests
- 실제 Polygon Free Key 사용
- 최근 1일치 데이터 Fetch -> DB 저장 -> 조회 검증

---

## 5. 승인 요청 사항
- [ ] Polygon.io API Key 발급 및 `config.yaml` 등록 확인
- [ ] DB 스키마 설계 (`daily_bars`) 승인
