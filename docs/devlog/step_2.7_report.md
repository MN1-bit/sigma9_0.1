# Step 2.7: Multi-Timeframe Chart Support 개발 리포트

> **완료일**: 2025-12-18  
> **상태**: ✅ 구현 완료 (테스트 대기)

---

## 📋 개요

Massive.com (구 Polygon.io) Aggregates API를 활용하여 **Intraday 데이터 (1m, 5m, 15m, 1h)** 지원을 추가했습니다.

---

## 🔧 변경 사항

### Backend - Data Layer

#### `polygon_client.py`
- **base_url** 변경: `api.polygon.io` → `api.massive.com`
- **`fetch_intraday_bars()`** 메서드 추가
  - Massive Aggregates API 호출 (`/v2/aggs/ticker/{ticker}/range/{multiplier}/minute/{from}/{to}`)
  - 1m, 5m, 15m, 60m 타임프레임 지원
  - 응답 데이터 정규화 (timestamp, OHLCV, vwap, transactions)

#### `polygon_loader.py`
- 환경변수 `POLYGON_API_KEY` → `MASSIVE_API_KEY` 변경

### Backend - API Layer

#### `routes.py`
- **`/api/chart/intraday/{ticker}`** 엔드포인트 추가
  - Query Parameters: `timeframe` (1, 5, 15, 60), `days` (1-10)
  - 차트 위젯 호환 포맷으로 응답 (time in seconds)
- 환경변수 `POLYGON_API_KEY` → `MASSIVE_API_KEY` 변경

### Frontend - Services

#### `chart_data_service.py`
- **`get_chart_data()`** 타임프레임 파라미터 추가
- **`_get_intraday_data()`** 메서드 추가 (API 호출)
- **`_get_daily_data()`** 메서드 분리 (DB 조회)

### Frontend - Chart Widget

#### `pyqtgraph_chart.py`
- **`TIMEFRAMES`** 상수 업데이트: `['1m', '5m', '15m', '1h', '1D']`

### Config Files

- `settings.yaml`: MASSIVE_API_KEY 환경변수 안내
- `server_config.yaml`: MASSIVE_API_KEY 환경변수 안내

---

## 📊 API 사용 예시

```bash
# 5분봉 조회 (최근 2일)
curl "http://localhost:8000/api/chart/intraday/AAPL?timeframe=5&days=2"

# 1시간봉 조회 (최근 5일)
curl "http://localhost:8000/api/chart/intraday/NVDA?timeframe=60&days=5"
```

**응답 예시**:
```json
{
  "status": "success",
  "ticker": "AAPL",
  "timeframe": 5,
  "count": 156,
  "candles": [
    {"time": 1702905600, "open": 195.5, "high": 196.0, "low": 195.2, "close": 195.8, "volume": 123456},
    ...
  ],
  "timestamp": "2024-12-18T13:00:00Z"
}
```

---

## ⚠️ 주의사항

1. **API 엔드포인트 변경**: `api.polygon.io` → `api.massive.com`
2. **환경변수 변경**: `POLYGON_API_KEY` → `MASSIVE_API_KEY`
3. **Intraday 데이터 비용**: Massive Stock Advanced 플랜 필요

---

## ✅ 다음 단계

1. ~~서버 실행 후 API 테스트~~
2. ~~GUI에서 타임프레임 변경 시 차트 데이터 갱신 확인~~
3. Step 4.A (Tiered Watchlist System) 진행 가능

---

## 🔧 추가 수정 사항 (2025-12-18 23:08)

### 문제점 발견
타임프레임 변경 시 로그만 출력되고 실제 데이터 로드가 되지 않음.

**원인**: `dashboard.py`의 `_on_timeframe_changed()` 핸들러가 비어 있었음.

```python
# 수정 전 (버그)
def _on_timeframe_changed(self, timeframe: str):
    self.log(f"[INFO] Timeframe changed to: {timeframe}")
    # TODO: 백엔드에서 해당 타임프레임 데이터 요청  ← 미구현
```

### 수정 내용

#### `dashboard.py`
- **`_on_timeframe_changed()`** 완전 구현
  - 현재 선택된 종목 확인
  - `ChartDataService.get_chart_data(ticker, timeframe=...)` 호출
  - Intraday(1m/5m/15m/1h)는 Massive API, Daily(1D)는 DB 조회
  - 비동기 스레드에서 데이터 로드 → 메인 스레드에서 차트 업데이트

```python
# 수정 후
def _on_timeframe_changed(self, timeframe: str):
    # 1. 현재 선택된 종목 가져오기
    ticker = self.watchlist.currentItem().text().split()[0]
    
    # 2. 해당 타임프레임 데이터 로드
    data = await service.get_chart_data(ticker, timeframe=timeframe, days=...)
    
    # 3. 차트 업데이트
    self._apply_pending_chart_data()
```

---

## ✅ 테스트 완료 (2025-12-18 23:09)

- [x] GUI 실행 성공
- [x] Watchlist에서 종목 선택
- [x] 타임프레임 변경 시 데이터 로드 시작 로그 확인
- [x] 차트 데이터 갱신 확인

**로그 예시**:
```
[23:09:30] [INFO] Timeframe changed to: 5m
[23:09:30] [INFO] Reloading AAPL data for 5m...
[23:09:31] [INFO] Chart updated for AAPL (156 bars)
```

---

## 📊 개발 통계

| 항목 | 값 |
|------|---|
| 수정 파일 수 | 8 |
| 추가된 메서드 | 3 |
| 추가된 엔드포인트 | 1 |
| 소요 시간 | ~30분 |
