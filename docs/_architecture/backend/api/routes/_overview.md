# Routes 문서 통합

> 📍 **Location**: `backend/api/routes/`

---

## 파일 목록 요약

| 파일 | 엔드포인트 | 역할 |
|------|-----------|------|
| [__init__.py](./__init__.md) | - | 라우터 조합 |
| [models.py](./models.md) | - | Pydantic 요청/응답 모델 |
| [common.py](./common.md) | - | 공용 유틸리티 |
| [status.py](./status.md) | `/status`, `/engine/status` | 서버 상태 조회 |
| [control.py](./control.md) | `/control`, `/kill-switch`, `/engine/*` | 엔진 제어 |
| [watchlist.py](./watchlist.md) | `/watchlist/*` | Watchlist 조회/재계산 |
| [position.py](./position.md) | `/positions` | 포지션 조회 |
| [strategy.py](./strategy.md) | `/strategies/*` | 전략 관리 |
| [scanner.py](./scanner.md) | `/scanner/*`, `/gainers/*` | 스캐너 실행 |
| [ignition.py](./ignition.md) | `/ignition/*` | Ignition 모니터링 |
| [chart.py](./chart.md) | `/chart/*` | 차트 데이터 |
| [llm.py](./llm.md) | `/oracle/*` | LLM 분석 |
| [tier2.py](./tier2.md) | `/tier2/*` | Tier2 승격 |
| [zscore.py](./zscore.md) | `/zscore/*` | Z-Score 조회 |
| [sync.py](./sync.md) | `/sync/*` | 데이터 동기화 |

---

## models.py - Pydantic 모델

| 모델 | 설명 |
|------|------|
| `EngineCommand` | 엔진 제어 명령 Enum (start/stop/kill) |
| `ControlRequest` | 엔진 제어 요청 |
| `ControlResponse` | 엔진 제어 응답 |
| `ServerStatus` | 서버 상태 |
| `WatchlistItem` | Watchlist 항목 |
| `PositionItem` | 포지션 항목 |
| `StrategyInfo` | 전략 정보 |
| `AnalysisRequest` | LLM 분석 요청 |
| `Tier2PromoteRequest` | Tier2 승격 요청 |
| `Tier2CheckRequest` | Tier2 승격 조건 판단 요청 |

---

## common.py - 공용 유틸리티

| 함수 | 설명 |
|------|------|
| `get_timestamp()` | ISO8601 타임스탬프 반환 |
| `get_uptime_seconds()` | 서버 가동 시간 (초) |
| `is_engine_running()` | 엔진 상태 조회 |
| `set_engine_running(bool)` | 엔진 상태 설정 |

---

## 엔드포인트별 상세

### status.py
- `GET /status` - 서버 전체 상태
- `GET /engine/status` - 엔진 상세 상태

### control.py
- `POST /control` - 엔진 제어 (start/stop/kill)
- `POST /kill-switch` - 긴급 정지
- `POST /engine/start` - 엔진 시작
- `POST /engine/stop` - 엔진 정지

### watchlist.py
- `GET /watchlist` - Watchlist 조회
- `POST /watchlist/recalculate` - Score V3 재계산

### position.py
- `GET /positions` - 포지션 조회

### strategy.py
- `GET /strategies` - 전략 목록
- `POST /strategies/{name}/load` - 전략 로드
- `POST /strategies/{name}/reload` - 전략 리로드

### scanner.py
- `POST /scanner/run` - 스캐너 실행
- `GET /gainers` - 급등주 조회
- `POST /gainers/add-to-watchlist` - 급등주 추가

### ignition.py
- `POST /ignition/start` - 모니터링 시작
- `POST /ignition/stop` - 모니터링 중지
- `GET /ignition/scores` - 점수 조회

### chart.py
- `GET /chart/intraday/{ticker}` - 인트라데이 차트
- `GET /chart/historical/{ticker}` - 히스토리컬 바

### llm.py
- `GET /oracle/models` - LLM 모델 목록
- `POST /oracle/analyze` - 종목 분석

### tier2.py
- `POST /tier2/promote` - Tier2 승격
- `POST /tier2/demote` - Tier2 해제
- `GET /tier2/status` - Tier2 상태
- `POST /tier2/check` - 승격 조건 판단

### zscore.py
- `GET /zscore/{ticker}` - Z-Score 조회

### sync.py
- `POST /sync/daily` - 일봉 동기화
- `GET /sync/status` - 동기화 상태
