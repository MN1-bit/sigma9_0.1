# Step 2.0 Devlog: Market Data Pipeline

> **완료일**: 2025-12-18  
> **Phase**: 2 (Core Engine)  
> **Status**: ✅ 전체 완료 (8/8 항목)

---

## 📋 개요

Polygon.io API + SQLite + IBKR 연동으로 완성된 Market Data Pipeline.

---

## ✅ 완료된 항목

| Step | Description | 비고 |
|------|-------------|------|
| 2.0.1 | `database.py` Setup | SQLAlchemy 2.0, WAL Mode |
| 2.0.2 | `polygon_client.py` | Rate Limit (5/min), Retry |
| 2.0.3 | `polygon_loader.py` | Grouped Daily Fetch |
| 2.0.4 | `update_market_data()` | 증분 업데이트 |
| 2.0.5 | Universe Scanner | DB 기반 필터링 |
| 2.0.6 | Fundamental Data | `fetch_fundamentals_batch()` |
| 2.0.7 | Multi-ticker Subscription | IBKR 50개 동시 구독 |
| 2.0.8 | SeismographStrategy 연동 | Scanner Orchestrator |

---

## 📊 테스트 결과

```
📦 DB 상태
- 레코드: 823,307개
- 기간: 2025-09-08 ~ 2025-12-16 (71일)
- 종목: ~11,800개/일

🔍 Scanner 결과
- Universe 후보: 2,095개
- 신호 탐지: 309개
- Stage 4 (100점): 5개 🔥

📋 TOP 5 Watchlist
1. EPSM  $2.35  (Tight Range + OBV)
2. LKSP  $9.92  (Tight Range + OBV)
3. NNOX  $3.21  (Tight Range + OBV)
4. SGBX  $2.80  (Tight Range + OBV)
5. TWG   $3.53  (Tight Range + OBV)
```

---

## 📁 생성된 파일

```
backend/data/
├── __init__.py
├── database.py          # MarketDB 클래스 (DailyBar, Ticker ORM)
├── polygon_client.py    # Polygon API 클라이언트
└── polygon_loader.py    # 증분 업데이트 + Fundamental Batch

backend/core/
└── scanner.py           # Scanner Orchestrator

data/
└── market_data.db       # SQLite DB (823K 레코드)

tests/
├── test_database.py     # 13개 테스트 통과
└── test_polygon_loader.py
```

---

## ⚙️ 설정 변경

### settings.yaml
```yaml
polygon:
  enabled: true
  rate_limit: 5
  retry_count: 3

market_data:
  db_path: "data/market_data.db"
  initial_load_days: 30
```

### .env
```
POLYGON_API_KEY=K8W67WixH74Ps...
```

---

## 💡 주요 구현 포인트

1. **Rate Limiting**: `aiolimiter` 사용, 5 req/min 정확 제어
2. **Chunked Upsert**: SQLite 999개 파라미터 제한 우회 (500개씩 배치)
3. **Stage-Based Scoring**: Weighted Sum → Stage Priority 변경
4. **Symbol Filtering**: 가격 $2-$20, 거래량 100K+ 조건
