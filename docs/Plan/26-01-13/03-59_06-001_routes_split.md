# 06-001: routes.py 분할

> **작성일**: 2026-01-08 01:07
> **우선순위**: 6 | **예상 소요**: 2-3h | **위험도**: 낮음

## 1. 목표

`routes.py` (1,194줄)를 기능별 라우터로 분할
→ 유지보수성 향상, 각 도메인 독립 테스트 가능

## 2. 현재 엔드포인트 분석

| 카테고리 | 엔드포인트 | 라인 수 (추정) |
|----------|-----------|---------------|
| Status | `/status`, `/engine/*` | ~80 |
| Watchlist | `/watchlist/*`, `/recalculate` | ~200 |
| Scanner | `/scanner/*`, `/gainers/*` | ~250 |
| Chart | `/chart/*` | ~150 |
| Backtest | `/backtest/*` | ~100 |
| Control | `/control`, `/kill`, `/engine/*` | ~150 |
| LLM | `/llm/*`, `/analysis/*` | ~150 |
| 기타 | Response models, helpers | ~100 |

## 3. 목표 구조 (REFACTORING.md 2.3)

```
backend/api/routes/
├── __init__.py           # 라우터 조합 (include_router)
├── status.py             # /status, /engine/*
├── watchlist.py          # /watchlist/*
├── scanner.py            # /scanner/*, /gainers/*
├── chart.py              # /chart/*
├── backtest.py           # /backtest/*
├── control.py            # /control, /kill
├── llm.py                # /llm/*, /analysis/*
└── models.py             # Response/Request 모델
```

## 4. 실행 계획

### Step 1: routes/ 디렉터리 생성
### Step 2: models.py 분리
- Pydantic 모델 추출
### Step 3: 각 도메인 라우터 분리
- 하나씩 추출 후 테스트
### Step 4: __init__.py에서 조합
```python
from .status import router as status_router
from .watchlist import router as watchlist_router
# ...
router = APIRouter()
router.include_router(status_router, tags=["Status"])
router.include_router(watchlist_router, prefix="/watchlist", tags=["Watchlist"])
```
### Step 5: 기존 routes.py 삭제

## 5. 검증 계획
- [ ] `python -m backend` 정상 시작
- [ ] `/docs` Swagger UI에서 모든 엔드포인트 표시
- [ ] 주요 API 호출 테스트
- [ ] `lint-imports` 통과
- [ ] 각 파일 ≤300줄

## 6. 롤백 계획
- `git checkout HEAD -- backend/api/routes.py`
- `rm -rf backend/api/routes/`
