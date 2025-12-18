# Step 2.7.A: Multi-Timeframe Chart Support - 구현 현황 및 이슈

> **마지막 업데이트**: 2025-12-18 23:29  
> **상태**: ✅ 문제 해결 완료

---

## ✅ 완료된 작업

### Backend
1. **`polygon_client.py`**
   - `fetch_intraday_bars()` 메서드 추가 ✅
   - base_url: `api.polygon.io` → `api.massive.com` ✅
   - 환경변수: `POLYGON_API_KEY` → `MASSIVE_API_KEY` ✅
   - **인증 방식 수정**: Bearer Header → `apiKey` Query Parameter ✅

2. **`routes.py`**
   - `/api/chart/intraday/{ticker}` 엔드포인트 추가 ✅
   - Query params: `timeframe` (1,5,15,60), `days` (1-10)

### Frontend
1. **`chart_data_service.py`**
   - `get_chart_data(ticker, timeframe, days)` - timeframe 파라미터 추가 ✅
   - `_get_intraday_data()` 메서드 추가 ✅
   - `_get_daily_data()` 메서드 분리 ✅
   - `get_chart_data_sync()` - timeframe 파라미터 추가 ✅
   - days 제한: Intraday는 max 10일 ✅

2. **`dashboard.py`**
   - `_on_timeframe_changed()` 핸들러 구현 ✅

3. **`pyqtgraph_chart.py`**
   - `TIMEFRAMES = ['1m', '5m', '15m', '1h', '1D']` ✅

---

## ✅ 해결된 이슈

### Issue #1: Intraday API 500 Internal Server Error - **해결됨!**

**원인 분석**:
- `polygon_client.py`에서 **Bearer 토큰 헤더** 방식으로 인증하고 있었음
- Massive.com API는 **apiKey 쿼리 파라미터** 방식을 사용함

**수정 내용** (`polygon_client.py`):
```python
# 변경 전 (잘못된 방식)
self._client = httpx.AsyncClient(
    headers={"Authorization": f"Bearer {self.api_key}"},
)

# 변경 후 (올바른 방식)
# _request_with_retry() 메서드에서 API 키를 쿼리 파라미터로 전달
kwargs["params"]["apiKey"] = self.api_key
```

**테스트 결과**:
```
Using API key: p18EZNu...
Fetching AAPL 5m intraday bars...
✅ AAPL 5m: 417개 바 데이터 수신
Got 417 bars
```

---

## 📁 수정된 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| `backend/data/polygon_client.py` | `fetch_intraday_bars()`, base_url 변경, **apiKey 인증 수정** |
| `backend/data/polygon_loader.py` | MASSIVE_API_KEY 환경변수 |
| `backend/api/routes.py` | `/api/chart/intraday` 엔드포인트 |
| `backend/config/settings.yaml` | MASSIVE_API_KEY 안내 |
| `backend/config/server_config.yaml` | MASSIVE_API_KEY 안내 |
| `frontend/services/chart_data_service.py` | timeframe 지원, `_get_intraday_data()` |
| `frontend/gui/dashboard.py` | `_on_timeframe_changed()` 구현 |
| `frontend/gui/chart/pyqtgraph_chart.py` | TIMEFRAMES 상수 업데이트 |

---

## ✅ 다음 단계

1. [x] ~~서버 콘솔에서 500 에러 상세 로그 확인~~
2. [x] ~~MASSIVE_API_KEY 환경변수 올바른지 확인~~
3. [x] ~~AAPL 등 메이저 종목으로 Intraday API 테스트~~
4. [ ] 서버 재시작 후 GUI에서 전체 플로우 테스트
5. [ ] Step 4.A (Tiered Watchlist) 진행

