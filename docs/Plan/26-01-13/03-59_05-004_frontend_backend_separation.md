# 05-004: Frontend/Backend 책임 분리 계획서

> **작성일**: 2026-01-08 16:07  
> **우선순위**: 5 (God Class 분해) | **위험도**: 중간

---

## 1. 목표

`dashboard.py`에서 **Tier2 승격 판단 로직**을 Backend로 분리:
- Frontend → UI 업데이트만 담당
- Backend → 승격 조건 판단 (비즈니스 로직)

> **범위 제외**: `chart_data_service.py`의 DB 직접 접근은 현행 유지

---

## 2. 현황 분석

### 2.1 기존 인프라

| 파일 | 엔드포인트 | 역할 |
|------|-----------|------|
| `backend/api/routes/tier2.py` | `POST /tier2/promote`, `demote`, `GET /status` | 승격/해제/상태 조회 |

### 2.2 이동 대상

| 메서드 | 위치 | 라인 수 | 문제점 |
|--------|------|---------|--------|
| `_check_tier2_promotion` | dashboard.py:1438-1489 | 52줄 | **비즈니스 로직이 Frontend에 있음** |

---

## 3. 실행 계획

### Step 1: `POST /api/tier2/check-promotion` 엔드포인트 추가

**파일**: `backend/api/routes/tier2.py`

```python
@router.post("/tier2/check-promotion", summary="Tier2 승격 조건 판단")
async def check_tier2_promotion(request: Tier2CheckRequest):
    """
    Tier2 승격 조건 판단
    
    Returns: {"should_promote": bool, "reason": str}
    """
```

**이동할 로직** (4가지 조건):
1. Ignition Score ≥ 70
2. Stage ≥ 4 (VCP Breakout Imminent)
3. zenV ≥ 2.0 && zenP < 0.5 (Divergence)
4. Acc Score ≥ 80 && source == "realtime_gainer"

---

### Step 2: Pydantic 모델 추가

**파일**: `backend/api/routes/models.py`

```python
class Tier2CheckRequest(BaseModel):
    ticker: str
    ignition_score: float
    passed_filter: bool = True
    stage_number: int = 0
    acc_score: float = 0.0
    source: str = ""
    zenV: float = 0.0
    zenP: float = 0.0
```

---

### Step 3: Frontend `_check_tier2_promotion` 간소화

**Before** (52줄):
```python
def _check_tier2_promotion(self, ticker, ignition_score, passed_filter, data):
    # 4가지 조건 로직...
```

**After** (~10줄):
```python
def _check_tier2_promotion(self, ticker, ignition_score, passed_filter, data):
    """Backend API로 승격 조건 확인"""
    resp = self.backend_client.check_tier2_promotion_sync(
        ticker=ticker,
        ignition_score=ignition_score,
        passed_filter=passed_filter,
        **self._get_watchlist_context(ticker)
    )
    return resp.get("should_promote", False), resp.get("reason", "")
```

---

### Step 4: BackendClient 메서드 추가

**파일**: `frontend/services/backend_client.py`

```python
def check_tier2_promotion_sync(self, **params) -> dict:
    resp = httpx.post(f"{self.base_url}/api/tier2/check-promotion", json=params)
    return resp.json()
```

---

## 4. 예상 효과

| 항목 | Before | After |
|------|--------|-------|
| `_check_tier2_promotion` | 52줄 | ~10줄 |
| **dashboard.py 감소** | - | **-42줄** |

---

## 5. 검증 계획

```bash
# API 테스트
curl -X POST http://localhost:8000/api/tier2/check-promotion \
  -H "Content-Type: application/json" \
  -d '{"ticker":"AAPL","ignition_score":75,"passed_filter":true}'

# Lint
lint-imports
ruff check backend/api/routes/tier2.py
```

**수동 검증**:
- Backend 실행 후 Ignition ≥ 70 종목 승격 동작 확인

---

## 6. 롤백 계획

```bash
git checkout -- backend/api/routes/tier2.py
git checkout -- backend/api/routes/models.py
git checkout -- frontend/gui/dashboard.py
git checkout -- frontend/services/backend_client.py
```
