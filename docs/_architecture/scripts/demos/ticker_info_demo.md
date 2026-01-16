# ticker_info_demo.py

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `scripts/demos/ticker_info_demo.py` |
| **역할** | Massive API를 이용한 티커 종합 정보 조회 데모 |
| **라인 수** | 614 |

## CLI 옵션
```bash
python scripts/demos/ticker_info_demo.py AAPL          # 기본 출력
python scripts/demos/ticker_info_demo.py AAPL --json   # JSON 출력
python scripts/demos/ticker_info_demo.py AAPL --output # 마크다운 저장
```

## 클래스

### `TickerInfo` (dataclass)
> 티커 종합 정보 컨테이너

| 필드 | 타입 | 설명 |
|------|------|------|
| `profile` | dict | 기본 정보 (시가총액, 직원수 등) |
| `float_data` | dict | 유동 주식수 |
| `financials` | list | 재무제표 |
| `dividends` | list | 배당 이력 |
| `splits` | list | 주식 분할 이력 |
| `filings` | list | SEC 공시 |
| `news` | list | 뉴스 |
| `related_companies` | list | 관련 기업 |
| `snapshot` | dict | 현재가/거래량 |
| `short_interest` | list | 공매도 잔고 |
| `short_volume` | list | 공매도 거래량 |

### `MassiveTickerClient`
> Massive API 클라이언트

| 메서드 | 역할 |
|--------|------|
| `get_ticker_info(ticker)` | 종합 정보 비동기 조회 |
| `_get_profile()` | 기본 정보 조회 |
| `_get_float()` | 유동 주식수 조회 |
| `_get_financials()` | 재무제표 조회 |
| `_get_dividends()` | 배당 조회 |
| `_get_splits()` | 주식 분할 조회 |
| `_get_filings()` | SEC 공시 조회 |
| `_get_news()` | 뉴스 조회 |
| `_get_snapshot()` | 현재가 조회 |
| `_get_short_interest()` | 공매도 잔고 조회 |

## 🔗 외부 연결 (Connections)

### Imports From (이 파일이 가져오는 것)
| 파일 | 가져오는 항목 |
|------|--------------|
| (없음 - 직접 API 호출) | - |

### External API
| API | 설명 |
|----|------|
| Massive API | 티커 정보 REST API |

## 외부 의존성
- `httpx`
- `asyncio`
- `dotenv`
