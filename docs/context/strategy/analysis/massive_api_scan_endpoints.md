# Massive.com API 스캔 범위 조절 엔드포인트 분석

> **작성일**: 2026-01-09  
> **목적**: Seismograph 스캔 대상 선별을 위한 Massive.com API 엔드포인트 조사  
> **다음 작업**: Tier2 승격 로직, Trading Method 오버홀

---

## 1. 배경

현재 Seismograph 전략의 스캔 대상 선별은 다음 조건을 사용합니다:

| 조건 | 현재 값 | 문제점 |
|------|---------|--------|
| 주가 | $2 ~ $10 | 경험적 설정, API 필터 미활용 |
| 시가총액 | $50M ~ $300M | 개별 Ticker API 호출 필요 |
| 유통주식수 | ≤ 15M | API에서 직접 지원 안 함 |
| 평균 거래량 | ≥ 100K | Grouped Daily에서 필터링 |

**목표**: Massive.com API에서 제공하는 엔드포인트를 활용하여 더 효율적이고 정확한 스캔 범위 조절

---

## 2. 스캔 활용 가능 엔드포인트 (Top 10)

### 2.1 Full Market Snapshot ⭐⭐⭐

| 항목 | 내용 |
|------|------|
| **엔드포인트** | `GET /v2/snapshot/locale/us/markets/stocks/tickers` |
| **설명** | 전체 미국 주식 10,000+ 종목의 실시간 데이터 일괄 조회 |
| **반환 필드** | `ticker`, `day.o/h/l/c/v`, `prevDay.c`, `todaysChange`, `todaysChangePerc` |
| **활용도** | **매우 높음** - 1회 호출로 전체 시장 스캔 가능 |
| **플랜** | Starter 이상 |

**스캔 활용**:
- 전체 시장 가격/거래량 실시간 필터링
- 당일 변화율 기반 사전 필터링
- Rate Limit 효율성 극대화

---

### 2.2 Ticker Overview (Ticker Details) ⭐⭐⭐

| 항목 | 내용 |
|------|------|
| **엔드포인트** | `GET /v3/reference/tickers/{ticker}` |
| **설명** | 특정 종목의 상세 정보 (시가총액, 발행주식 등) |
| **반환 필드** | `market_cap`, `share_class_shares_outstanding`, `weighted_shares_outstanding`, `sic_code`, `list_date`, `primary_exchange` |
| **활용도** | **높음** - 마이크로캡 필터링의 핵심 |
| **플랜** | 모든 플랜 |

**스캔 활용**:
- `market_cap`: $50M ~ $300M 필터
- `share_class_shares_outstanding`: 총 발행주식 확인
- `sic_code`: 업종 필터링 (선택)

**제한점**: 종목별 개별 호출 필요 → Rate Limit 고려

---

### 2.3 Float ⭐⭐⭐

| 항목 | 내용 |
|------|------|
| **엔드포인트** | `GET /v3/reference/fundamentals/float/{ticker}` |
| **설명** | 특정 종목의 유통주식수 (Free Float) |
| **반환 필드** | `float` |
| **활용도** | **매우 높음** - 핵심 마이크로캡 기준 |
| **플랜** | Starter 이상 |

**스캔 활용**:
- `float ≤ 15,000,000` 필터링
- 급등 가능성 평가의 핵심 지표

**제한점**: 종목별 개별 호출 필요

---

### 2.4 Top Market Movers (Gainers/Losers) ⭐⭐

| 항목 | 내용 |
|------|------|
| **엔드포인트** | `GET /v2/snapshot/locale/us/markets/stocks/{direction}` |
| **파라미터** | `direction` = `gainers` 또는 `losers` |
| **설명** | 상위 20개 급등/급락 종목 (거래량 10K+ 필터) |
| **반환 필드** | `ticker`, `todaysChangePerc`, `day.v`, `day.c` |
| **활용도** | **중간** - 현재 이미 사용 중 (`fetch_day_gainers`) |
| **플랜** | 모든 플랜 |

**스캔 활용**:
- 실시간 급등주 모니터링 (보조)
- 20개 한정으로 전체 스캔에는 부적합

---

### 2.5 All Tickers (Reference) ⭐⭐

| 항목 | 내용 |
|------|------|
| **엔드포인트** | `GET /v3/reference/tickers` |
| **설명** | 전체 티커 목록 조회 (필터링 지원) |
| **쿼리 파라미터** | `type`, `market`, `exchange`, `active`, `limit`, `cursor` |
| **반환 필드** | `ticker`, `name`, `type`, `primary_exchange`, `active` |
| **활용도** | **중간** - 마스터 목록 유지용 |
| **플랜** | 모든 플랜 |

**스캔 활용**:
- `type=CS` (Common Stock만 필터)
- `active=true` (활성 종목만)
- `exchange` 필터로 OTC 제외

---

### 2.6 Unified Snapshot ⭐⭐

| 항목 | 내용 |
|------|------|
| **엔드포인트** | `GET /v3/snapshot` |
| **설명** | 여러 종목의 스냅샷 일괄 조회 |
| **쿼리 파라미터** | `ticker.any_of` (최대 250개) |
| **반환 필드** | `session` (OHLCV), `last_trade`, `last_quote` |
| **활용도** | **높음** - Watchlist 모니터링에 최적 |
| **플랜** | Starter 이상 |

**스캔 활용**:
- Tier 1 Watchlist (~50개) 일괄 모니터링
- 개별 호출 대비 효율적

---

### 2.7 Short Interest ⭐

| 항목 | 내용 |
|------|------|
| **엔드포인트** | `GET /v3/reference/fundamentals/short-interest/{ticker}` |
| **설명** | FINRA 보고 공매도 데이터 (격주 업데이트) |
| **반환 필드** | `short_interest`, `days_to_cover`, `settlement_date` |
| **활용도** | **보조** - Short Squeeze 필터 (선택) |
| **플랜** | Starter 이상 |

**스캔 활용**:
- 고공매도 종목 식별
- Short Squeeze 가능성 평가

---

### 2.8 Financial Ratios ⭐

| 항목 | 내용 |
|------|------|
| **엔드포인트** | `GET /v3/reference/fundamentals/ratios/{ticker}` |
| **설명** | 재무 비율 (P/E, D/E, ROE 등) |
| **반환 필드** | `pe_ratio`, `debt_to_equity`, `current_ratio`, `return_on_equity` |
| **활용도** | **보조** - 펀더멘털 필터 (선택) |
| **플랜** | Starter 이상 |

**스캔 활용**:
- 부채비율 등 재무건전성 필터
- Tier 2 승격 시 추가 검증

---

### 2.9 Technical Indicators ⭐

| 항목 | 내용 |
|------|------|
| **엔드포인트** | `GET /v1/indicators/{indicator}/{ticker}` |
| **지표 종류** | `sma`, `ema`, `macd`, `rsi` |
| **설명** | 사전 계산된 기술적 지표 |
| **반환 필드** | `value`, `timestamp` |
| **활용도** | **보조** - Tight Range 대체 가능성 |
| **플랜** | Starter 이상 |

**스캔 활용**:
- ATR 기반 Tight Range 대신 API 제공 지표 활용 검토
- 현재는 자체 계산 사용 중

---

### 2.10 Stock News ⭐

| 항목 | 내용 |
|------|------|
| **엔드포인트** | `GET /v2/reference/news` |
| **설명** | 종목별 뉴스 및 감성 데이터 |
| **반환 필드** | `title`, `description`, `sentiment`, `article_url` |
| **활용도** | **보조** - 뉴스 기반 필터 (선택) |
| **플랜** | 모든 플랜 |

**스캔 활용**:
- 촉매 이벤트 감지
- Tier 2 승격 시 뉴스 검증

---

## 3. 스캔 전략 개선 권장

### 3.1 Phase 1: 효율적 전체 스캔

```
현재: Grouped Daily (5000+ 종목) → 개별 Ticker Details 호출

개선: Full Market Snapshot → 가격/거래량 사전 필터
     → 후보 종목에만 Ticker Details + Float 호출
```

| 단계 | API | 호출 수 | 필터 |
|------|-----|---------|------|
| 1 | Full Market Snapshot | 1회 | 가격 $2-$10, 거래량 100K+ |
| 2 | Ticker Details (병렬) | ~200회 | 시가총액 $50M-$300M |
| 3 | Float (병렬) | ~50회 | Float ≤ 15M |

### 3.2 Phase 2: Watchlist 모니터링

```
현재: 개별 AM 채널 구독 + 1초 폴링

개선: Unified Snapshot (250개 일괄) + AM 채널 (Tier 2만)
```

### 3.3 캐싱 전략

| 데이터 | 캐시 TTL | 이유 |
|--------|----------|------|
| Ticker Details | 24시간 | 시가총액은 일일 단위 변동 |
| Float | 7일 | Float은 월 단위 변동 |
| Full Market Snapshot | 1초 (실시간) | 가격/거래량 실시간 필요 |

---

## 4. 다음 작업 항목

- [ ] **Tier 2 승격 로직 오버홀**: Stage 4 조건 재정의
- [ ] **Trading Method 오버홀**: Ignition Score → 개선된 진입 조건

---

## 5. 참고 자료

- [Massive.com REST API 문서](https://massive.com/docs/rest/stocks)
- 브라우저 탐색 녹화: [massive_api_docs.webp](file:///C:/Users/USER/.gemini/antigravity/brain/09758bc1-117a-4385-a6ff-30af20decf18/massive_api_docs_1767887025169.webp)
