# massive_rest_spec.json

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `massive_rest_spec.json` |
| **역할** | Massive API REST 엔드포인트 OpenAPI 스펙 |
| **라인 수** | 31,831 |
| **파일 크기** | ~1.3 MB |

## 개요

Massive.com (금융 데이터 제공 API)의 REST API 전체 명세서입니다.  
이 파일은 `backend/data/massive_client.py`에서 API 호출 시 참조용으로 사용됩니다.

## 주요 API 카테고리

### Stocks (주식)
| 엔드포인트 | 설명 |
|-----------|------|
| `/v2/aggs/ticker/{ticker}/range` | 기간별 집계 데이터 (OHLCV) |
| `/v2/aggs/grouped/locale/us/market/stocks/{date}` | 일별 전종목 집계 |
| `/v3/reference/tickers` | 티커 메타데이터 조회 |
| `/v3/reference/exchanges` | 거래소 정보 |
| `/v2/snapshot/locale/us/markets/stocks/tickers` | 스냅샷 데이터 |
| `/v2/snapshot/locale/us/markets/stocks/{direction}` | Gainers/Losers |

### Options (옵션)
| 엔드포인트 | 설명 |
|-----------|------|
| `/v3/reference/options/contracts` | 옵션 계약 조회 |
| `/v2/snapshot/options/{ticker}` | 옵션 스냅샷 |

### Crypto & Forex
| 엔드포인트 | 설명 |
|-----------|------|
| `/v2/aggs/ticker/{cryptoTicker}` | 암호화폐 집계 |
| `/v2/aggs/ticker/{forexTicker}` | 외환 집계 |

## 주요 파라미터

| 파라미터 | 설명 |
|----------|------|
| `adjusted` | 분할 조정 여부 (default: true) |
| `sort` | 정렬 순서 (asc/desc) |
| `limit` | 결과 제한 (max 50,000) |
| `timespan` | 시간 단위 (second/minute/hour/day/week/month) |

## 🔗 연결

### 사용 위치
| 파일 | 사용 목적 |
|------|----------|
| `backend/data/massive_client.py` | REST API 호출 구현 |
| `backend/data/massive_loader.py` | 데이터 로드 로직 |

### Data Flow
```mermaid
graph LR
    A["massive_rest_spec.json"] -->|API 명세| B["massive_client.py"]
    B -->|HTTP 요청| C["Massive.com API"]
    C -->|응답| D["MarketDB / Parquet"]
```
