# archt.md

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `.agent/Ref/archt.md` |
| **역할** | 시스템 아키텍처 상세 문서 v3.7 |
| **라인 수** | 612 |

## 문서 구조

### 1. Tech Stack
| 영역 | 핵심 스택 |
|------|----------|
| Backend | FastAPI, ib_insync, pandas, loguru, pyarrow |
| Frontend | PyQt6, finplot, httpx, qasync |

### 2. 데이터 파이프라인
- Massive WebSocket → TickBroadcaster → GUI
- RealtimeScanner (1초 폴링) → WatchlistStore

### 3. 모듈 구조
| 경로 | 역할 |
|------|------|
| `backend/startup/` | 서버 초기화 (4개 모듈) |
| `backend/core/` | 전략 엔진, 리스크 관리 (25개) |
| `backend/models/` | 중앙 모델 저장소 (7개) |
| `backend/strategies/seismograph/` | 메인 전략 패키지 |
| `backend/data/` | DB, API 클라이언트 (11개) |

### 4. 아키텍처 패턴
- DI Container (dependency-injector)
- 인터페이스 추출 (순환 의존성 해결)

### 5. 데이터 저장소
| 경로 | 형식 | 용도 |
|------|------|------|
| `data/parquet/daily/` | Parquet | 일봉 OHLCV |
| `data/parquet/1m/` | Parquet | 분봉 차트 |
| `data/watchlist.json` | JSON | Watchlist |
