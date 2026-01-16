# routes.py 분할 리팩터링 Devlog

> **작성일**: 2026-01-08 01:20
> **관련 계획서**: [06-001_routes_split.md](../../Plan/refactor/06-001_routes_split.md)

## 진행 현황

| Step | 상태 | 완료 시간 |
|------|------|----------|
| Step 1: routes/ 디렉터리 생성 | ✅ 완료 | 01:22 |
| Step 2: models.py 분리 | ✅ 완료 | 01:22 |
| Step 3: 각 도메인 라우터 분리 | ✅ 완료 | 01:35 |
| Step 4: __init__.py에서 조합 | ✅ 완료 | 01:37 |
| Step 5: 기존 routes.py 삭제 | ✅ 완료 | 01:40 |

---

## Step 1: routes/ 디렉터리 생성

### 목표
- `backend/api/routes/` 디렉터리 구조 생성
- 빈 `__init__.py` 파일 생성

### 변경 사항
- `backend/api/routes/` 디렉터리 생성 완료

### 검증 결과
- ✅ 디렉터리 생성 성공

---

## Step 2: models.py 분리

### 목표
- Pydantic 모델을 `models.py`로 추출

### 변경 사항
- `backend/api/routes/models.py`: Pydantic 모델 9개 추출
  - `EngineCommand`, `ControlRequest`, `ControlResponse`
  - `ServerStatus`, `WatchlistItem`, `PositionItem`
  - `StrategyInfo`, `AnalysisRequest`, `Tier2PromoteRequest`

- `backend/api/routes/common.py`: 공용 유틸리티 추출
  - `get_timestamp()`, `get_uptime_seconds()`
  - `is_engine_running()`, `set_engine_running()`

### 검증 결과
- ✅ models.py, common.py 생성 완료

---

## Step 3: 각 도메인 라우터 분리

### 목표
- 기능별로 라우터 파일 분리

### 생성된 파일

| 파일 | 라인수 | 엔드포인트 |
|------|--------|-----------|
| status.py | ~80 | /status, /engine/status |
| control.py | ~115 | /control, /kill-switch, /engine/start, /engine/stop |
| watchlist.py | ~85 | /watchlist, /watchlist/recalculate |
| position.py | ~35 | /positions |
| strategy.py | ~100 | /strategies, /strategies/{name}/load, /strategies/{name}/reload |
| scanner.py | ~160 | /scanner/run, /gainers, /gainers/add-to-watchlist |
| ignition.py | ~100 | /ignition/start, /ignition/stop, /ignition/scores |
| chart.py | ~110 | /chart/intraday/{ticker} |
| llm.py | ~55 | /oracle/models, /oracle/analyze |
| tier2.py | ~140 | /tier2/promote, /tier2/demote, /tier2/status |
| zscore.py | ~85 | /zscore/{ticker} |
| sync.py | ~130 | /sync/daily, /sync/status |

### 검증 결과
- ✅ 12개 도메인 라우터 생성 완료
- ✅ 모든 파일 ≤ 200줄 (목표 ≤ 300줄 충족)

---

## Step 4: __init__.py에서 조합

### 목표
- 모든 도메인 라우터를 하나의 router로 조합

### 변경 사항
- `backend/api/routes/__init__.py`: 라우터 조합 및 모델 re-export
  - 12개 도메인 라우터 include
  - 하위 호환성을 위한 모델 re-export

### 검증 결과
- ✅ import 테스트 통과: `from backend.api.routes import router`
- ✅ 서버 import 테스트 통과: 33개 엔드포인트 등록 확인

---

## Step 5: 기존 routes.py 삭제

### 목표
- 기존 `backend/api/routes.py` (1,194줄) 삭제

### 변경 사항
- `backend/api/routes.py` → 삭제됨
- 백업 후 테스트 완료 후 백업 삭제

### 검증 결과
- ✅ 서버 시작 테스트 통과
- ✅ pydeps 순환 의존성 검사 통과 (exit code 0)

---

## 최종 검증 결과

| 검증 항목 | 결과 |
|----------|------|
| ruff format | ✅ |
| ruff check | ✅ (All checks passed!) |
| pydeps cycles | ✅ (순환 없음) |
| Server Import | ✅ (33 endpoints) |
| 각 파일 ≤300줄 | ✅ |
| models re-export | ✅ |

---

## 분석: 기존 vs 변경 후

### 변경 전
```
backend/api/
├── __init__.py
├── routes.py (1,194줄) ← 거대 파일
└── websocket.py
```

### 변경 후
```
backend/api/
├── __init__.py
├── routes/
│   ├── __init__.py (~105줄) - 라우터 조합
│   ├── models.py (~95줄) - 공유 모델
│   ├── common.py (~60줄) - 공용 유틸리티
│   ├── status.py (~80줄)
│   ├── control.py (~115줄)
│   ├── watchlist.py (~85줄)
│   ├── position.py (~35줄)
│   ├── strategy.py (~100줄)
│   ├── scanner.py (~160줄)
│   ├── ignition.py (~100줄)
│   ├── chart.py (~110줄)
│   ├── llm.py (~55줄)
│   ├── tier2.py (~140줄)
│   ├── zscore.py (~85줄)
│   └── sync.py (~130줄)
└── websocket.py
```

**총 라인수**: 1,194줄 → ~1,455줄 (모듈화로 인한 약간의 증가, 주석 및 docstring 추가)
**평균 파일 크기**: ~100줄 (유지보수성 대폭 향상)
