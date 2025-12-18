# Step 2.7: Multi-Timeframe Chart Support 구현 계획

> **버전**: 1.0  
> **작성일**: 2025-12-18  
> **데이터 소스**: Massive.com Stock Advanced 구독

---

## 📋 개요

현재 시스템은 **일봉(Daily) 데이터**만 지원합니다. 이 단계에서는 **Intraday 데이터 (1m, 5m, 15m, 1h)**를 추가하여 Multi-Timeframe 차트를 제공합니다.

```
현재 상태                          목표 상태
┌─────────────┐                   ┌─────────────────────────┐
│ DailyBar    │                   │ DailyBar (기존)          │
│ (1D 전용)   │       →          │ IntradayBar (1m,5m,15m,1h)│
└─────────────┘                   └─────────────────────────┘
```

---

## ⚠️ 선행 조건

- [x] Massive.com Stock Advanced 구독 완료

### 📚 API 참조 문서

> [!CAUTION]
> **polygon.io 엔드포인트 Deprecation 예정**  
> `api.polygon.io` 도메인은 조만간 중단될 예정입니다.  
> **반드시 `api.massive.com` 엔드포인트를 사용하세요!**

> Massive.com (구 Polygon.io) API 엔드포인트 정보:  
> - [API Reference](../../references/research/massive.com.api.md)
> - REST API: https://massive.com/docs/rest/quickstart
> - WebSocket: https://massive.com/docs/websocket/quickstart

---

## 🔧 구현 항목

### 2.7.1: [Backend] Implement Intraday Data API (1m, 5m, 15m, 1h)

**`massive_client.py`** 수정:

```python
async def fetch_intraday_bars(
    self,
    ticker: str,
    multiplier: int = 5,       # 1, 5, 15, 60
    from_date: str = None,
    to_date: str = None,
    limit: int = 5000,
) -> list[dict]:
    """
    Massive Aggregates API로 Intraday Bar 조회
    
    API: GET /v2/aggs/ticker/{ticker}/range/{multiplier}/minute/{from}/{to}
    """
```

**`routes.py`** 수정:

```python
@router.get("/api/chart/intraday/{ticker}")
async def get_intraday_chart(
    ticker: str,
    timeframe: str = Query("5", description="1, 5, 15, 60"),
    days: int = Query(2, description="1-10"),
):
    """Intraday 차트 데이터 조회"""
```

---

### 2.7.2: [Backend] Add `intraday_bars` table to database

**`database.py`** 수정 (선택적 - 캐싱 구현 시):

```python
class IntradayBar(Base):
    __tablename__ = "intraday_bars"
    
    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    timestamp: Mapped[int] = mapped_column(Integer, primary_key=True)  # Unix ms
    timeframe: Mapped[str] = mapped_column(String(5), primary_key=True)
    
    open: Mapped[float]
    high: Mapped[float]
    low: Mapped[float]
    close: Mapped[float]
    volume: Mapped[int]
    vwap: Mapped[Optional[float]]
```

> **Note**: 초기 구현에서는 DB 저장 없이 실시간 Fetch만 구현. 필요시 캐싱 추가.

---

### 2.7.3: [Frontend] Timeframe change handler → data reload

**`pyqtgraph_chart.py`** 수정:

```python
TIMEFRAMES = ["1m", "5m", "15m", "1h", "1D"]

def _on_timeframe_changed(self, timeframe: str):
    """타임프레임 변경 시 데이터 리로드"""
    self.current_timeframe = timeframe
    self.timeframe_changed.emit(timeframe)
```

**`chart_data_service.py`** 수정:

```python
async def get_chart_data(
    self,
    ticker: str,
    timeframe: str = "1D",  # "1m", "5m", "15m", "1h", "1D"
    days: int = 100,
) -> dict:
    if timeframe == "1D":
        return await self._get_daily_data(ticker, days)
    else:
        return await self._get_intraday_data(ticker, timeframe, days)
```

---

### 2.7.4: [Frontend] Dynamic data loading on pan/zoom

**차트 뷰포트 변경 시 추가 데이터 로드**:

```python
def _on_viewport_changed(self, view_range):
    """Pan/Zoom 시 필요한 데이터 동적 로드"""
    # 현재 범위 외의 데이터 필요 시 추가 fetch
    pass
```

> **Note**: 지금 구현으로 정책 바뀜!!!

---

## 📊 Massive API 참고

### Aggregates (Bars) API

```
GET /v2/aggs/ticker/{stocksTicker}/range/{multiplier}/{timespan}/{from}/{to}
```

| Parameter | Description | Example |
|-----------|-------------|---------|
| stocksTicker | 종목 심볼 | AAPL |
| multiplier | 타임프레임 배수 | 5 |
| timespan | 시간 단위 | minute |
| from | 시작일 | 2024-12-16 |
| to | 종료일 | 2024-12-18 |

**예시 요청**:
```bash
curl "https://api.massive.com/v2/aggs/ticker/AAPL/range/5/minute/2024-12-16/2024-12-18?adjusted=true&sort=asc&limit=5000&apiKey=YOUR_KEY"
```

**예시 응답**:
```json
{
  "ticker": "AAPL",
  "status": "OK",
  "resultsCount": 234,
  "results": [
    {
      "v": 1234567,    // volume
      "vw": 178.5,     // vwap
      "o": 178.0,      // open
      "c": 179.0,      // close
      "h": 179.5,      // high
      "l": 177.5,      // low
      "t": 1702905600000,  // timestamp (ms)
      "n": 5678        // transactions
    }
  ]
}
```

---

## 📝 구현 순서

| # | 작업 | 예상 시간 |
|---|------|----------|
| 1 | `massive_client.py` - `fetch_intraday_bars()` | 30분 |
| 2 | `routes.py` - `/api/chart/intraday` 엔드포인트 | 30분 |
| 3 | `chart_data_service.py` - Intraday 지원 | 30분 |
| 4 | `pyqtgraph_chart.py` - Timeframe 핸들러 | 30분 |
| 5 | 통합 테스트 | 30분 |

**총 예상 시간**: 2-3시간

---

## ✅ 완료 조건

1. [ ] Massive Intraday API 호출 성공
2. [ ] `/api/chart/intraday/{ticker}` 엔드포인트 동작
3. [ ] GUI에서 Timeframe 변경 시 차트 데이터 갱신
4. [ ] 1m, 5m, 15m, 1h, 1D 모든 타임프레임 동작 확인
