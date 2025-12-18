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

> [!IMPORTANT]
> 이 기능은 **즉시 구현** 대상입니다. 메모리 효율성과 API 비용 절감을 위해 초기 릴리스에 포함합니다.

**목적**: 차트를 Pan/Zoom할 때 뷰포트 범위에 맞춰 추가 데이터를 동적으로 로드합니다. **2-Tier 캐시 (Memory + SQLite)**를 활용하여 메모리 효율성과 API 비용 절감을 동시에 달성합니다.

---

#### 📐 아키텍처 개요

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         Chart Data Request Flow                              │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │              PyQtGraphChartWidget (Viewport 변경 감지)                 │ │
│  │  ViewBox.sigRangeChanged → _on_viewport_changed() (디바운싱 150ms)    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                                    ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  L1: Memory Cache (Hot Data)                                           │ │
│  │  ├─ 현재 뷰포트 + 버퍼 (±50 bars)                                     │ │
│  │  ├─ 오늘 실시간 데이터 (변동 가능)                                    │ │
│  │  └─ LRU 방식으로 오래된 데이터 evict                                  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │ Cache Miss                              │
│                                    ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  L2: SQLite Database (Warm Data)                                       │ │
│  │  ├─ intraday_bars 테이블 (ticker, timeframe, timestamp 인덱스)        │ │
│  │  ├─ 완성된 Bar만 저장 (현재 형성 중 Bar 제외)                        │ │
│  │  └─ 한번 저장하면 API 재호출 불필요                                   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │ DB Miss                                 │
│                                    ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  L3: Massive API (Cold Data)                                           │ │
│  │  ├─ DB에 없는 과거 데이터 fetch                                       │ │
│  │  ├─ Fetch 후 L2(SQLite)에 저장                                        │ │
│  │  └─ L1(Memory)에도 로드하여 즉시 렌더링                               │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

**왜 이 아키텍처인가?**

| 문제 | 해결책 |
|------|--------|
| 1분봉 1년치 = ~98,000 bars/종목 → 메모리 부담 | L2(SQLite)에 저장, L1은 뷰포트만 유지 |
| API Rate Limit & 비용 | 과거 데이터는 불변 → 한번 저장하면 재호출 없음 |
| Daily bar 이미 DB 사용 중 | 동일 패턴 확장, 일관된 아키텍처 |
| 디스크 I/O 지연 우려 | SQLite 인덱스 + 버퍼링으로 <50ms 응답 가능 |

---

#### 🔧 구현 세부사항

##### 1. Viewport Change 감지 *(pyqtgraph_chart.py)*

```python
class PyQtGraphChartWidget(QWidget):
    # 시그널 정의
    viewport_data_needed = pyqtSignal(int, int)  # (start_idx, end_idx)
    
    def __init__(self, ...):
        super().__init__(...)
        self._data_manager = ChartDataManager()
        
        # ViewBox 시그널 연결
        self.chart_view.sigRangeChanged.connect(
            self._on_viewport_changed
        )
        
        # 디바운싱을 위한 타이머
        self._viewport_timer = QTimer()
        self._viewport_timer.setSingleShot(True)
        self._viewport_timer.setInterval(150)  # 150ms 디바운스
        self._viewport_timer.timeout.connect(self._check_data_needs)
        
        self._pending_range = None
    
    def _on_viewport_changed(self, view_box, range_changed):
        """Viewport 범위 변경 감지 (디바운싱 적용)"""
        x_range = view_box.viewRange()[0]
        self._pending_range = (int(x_range[0]), int(x_range[1]))
        self._viewport_timer.start()
    
    def _check_data_needs(self):
        """실제 데이터 로드 필요 여부 확인"""
        if self._pending_range is None:
            return
            
        start_idx, end_idx = self._pending_range
        
        # 현재 로드된 범위와 비교
        if self._data_manager.needs_more_data(start_idx, end_idx):
            # 추가 데이터 요청 시그널 발생
            needed_start, needed_end = self._data_manager.calculate_fetch_range(
                start_idx, end_idx
            )
            self.viewport_data_needed.emit(needed_start, needed_end)
```

##### 2. ChartDataManager 클래스 *(chart_data_manager.py - 신규)*

```python
# frontend/gui/chart/chart_data_manager.py

from dataclasses import dataclass
from typing import Optional
import pandas as pd


@dataclass
class LoadedRange:
    """로드된 데이터 범위 추적"""
    start_idx: int
    end_idx: int


class ChartDataManager:
    """
    차트 데이터 캐싱 및 동적 로딩 관리자
    
    책임:
    - 현재 로드된 데이터 범위 추적
    - 추가 데이터 필요 여부 판단
    - 데이터 병합 및 캐싱
    """
    
    FETCH_BUFFER = 50  # 뷰포트 양쪽에 미리 로드할 바 수
    MIN_FETCH_SIZE = 100  # 최소 fetch 크기 (API 효율성)
    
    def __init__(self):
        self._loaded_range: Optional[LoadedRange] = None
        self._data_cache: Optional[pd.DataFrame] = None
        self._current_timeframe: str = "1D"
    
    @property
    def loaded_range(self) -> Optional[LoadedRange]:
        return self._loaded_range
    
    def reset(self, timeframe: str = None):
        """타임프레임 변경 시 캐시 초기화"""
        self._loaded_range = None
        self._data_cache = None
        if timeframe:
            self._current_timeframe = timeframe
    
    def set_initial_data(self, data: pd.DataFrame):
        """초기 데이터 설정"""
        self._data_cache = data
        self._loaded_range = LoadedRange(
            start_idx=0,
            end_idx=len(data) - 1
        )
    
    def needs_more_data(self, view_start: int, view_end: int) -> bool:
        """추가 데이터 로드 필요 여부 확인"""
        if self._loaded_range is None:
            return True
        
        # 뷰포트가 버퍼 범위 밖으로 나갔는지 확인
        buffer_start = self._loaded_range.start_idx + self.FETCH_BUFFER
        buffer_end = self._loaded_range.end_idx - self.FETCH_BUFFER
        
        return view_start < buffer_start or view_end > buffer_end
    
    def calculate_fetch_range(
        self, view_start: int, view_end: int
    ) -> tuple[int, int]:
        """
        Fetch할 데이터 범위 계산
        
        Returns:
            (fetch_start, fetch_end) - API 요청에 사용할 인덱스 범위
        """
        # 뷰포트 + 버퍼 범위 계산
        desired_start = max(0, view_start - self.FETCH_BUFFER * 2)
        desired_end = view_end + self.FETCH_BUFFER * 2
        
        # 이미 로드된 범위 제외
        if self._loaded_range:
            if view_start < self._loaded_range.start_idx:
                # 왼쪽(과거) 방향으로 데이터 필요
                fetch_start = desired_start
                fetch_end = self._loaded_range.start_idx - 1
            else:
                # 오른쪽(미래) 방향으로 데이터 필요
                fetch_start = self._loaded_range.end_idx + 1
                fetch_end = desired_end
        else:
            fetch_start = desired_start
            fetch_end = desired_end
        
        # 최소 fetch 크기 보장
        if fetch_end - fetch_start < self.MIN_FETCH_SIZE:
            fetch_end = fetch_start + self.MIN_FETCH_SIZE
        
        return fetch_start, fetch_end
    
    def merge_data(self, new_data: pd.DataFrame, prepend: bool = False):
        """
        새 데이터를 기존 캐시에 병합
        
        Args:
            new_data: 새로 로드된 데이터
            prepend: True면 앞쪽(과거), False면 뒤쪽(미래)에 추가
        """
        if self._data_cache is None:
            self.set_initial_data(new_data)
            return
        
        if prepend:
            self._data_cache = pd.concat(
                [new_data, self._data_cache], 
                ignore_index=True
            )
            # 인덱스 재조정
            self._loaded_range.start_idx -= len(new_data)
        else:
            self._data_cache = pd.concat(
                [self._data_cache, new_data], 
                ignore_index=True
            )
            self._loaded_range.end_idx += len(new_data)
    
    def get_visible_data(
        self, start_idx: int, end_idx: int
    ) -> Optional[pd.DataFrame]:
        """뷰포트에 표시할 데이터 반환"""
        if self._data_cache is None:
            return None
        
        # 캐시 내 상대 인덱스로 변환
        relative_start = max(0, start_idx - self._loaded_range.start_idx)
        relative_end = min(
            len(self._data_cache),
            end_idx - self._loaded_range.start_idx + 1
        )
        
        return self._data_cache.iloc[relative_start:relative_end]
```

##### 3. Dashboard 통합 *(dashboard.py)*

```python
class Sigma9Dashboard:
    def __init__(self, ...):
        # ... 기존 코드 ...
        
        # 동적 데이터 로딩 시그널 연결
        self.chart_widget.viewport_data_needed.connect(
            self._on_viewport_data_needed
        )
    
    async def _on_viewport_data_needed(self, start_idx: int, end_idx: int):
        """뷰포트 변경에 따른 추가 데이터 로드"""
        if not self._current_ticker:
            return
        
        try:
            # 추가 데이터 fetch
            additional_data = await self._chart_service.fetch_range(
                ticker=self._current_ticker,
                timeframe=self._current_timeframe,
                start_idx=start_idx,
                end_idx=end_idx
            )
            
            if additional_data:
                # 차트에 데이터 추가
                self.chart_widget.append_data(
                    additional_data,
                    prepend=(start_idx < 0)  # 과거 방향이면 prepend
                )
        except Exception as e:
            logger.warning(f"Failed to load additional data: {e}")
```

---

#### 📊 API 확장 *(chart_data_service.py)*

```python
class ChartDataService:
    async def fetch_range(
        self,
        ticker: str,
        timeframe: str,
        start_idx: int,
        end_idx: int
    ) -> Optional[pd.DataFrame]:
        """
        특정 범위의 차트 데이터 fetch
        
        인덱스는 현재 로드된 데이터 기준 상대적 위치
        음수면 과거 방향, 양수면 미래 방향
        """
        # 인덱스를 날짜로 변환
        bars_needed = end_idx - start_idx
        
        if timeframe == "1D":
            # Daily 데이터: 인덱스 = 거래일 수
            endpoint = f"/api/chart/daily/{ticker}"
            params = {"days": bars_needed, "offset": abs(start_idx)}
        else:
            # Intraday 데이터
            endpoint = f"/api/chart/intraday/{ticker}"
            params = {
                "timeframe": timeframe.replace("m", "").replace("h", ""),
                "bars": bars_needed,
                "offset": abs(start_idx)
            }
        
        response = await self._client.get(endpoint, params=params)
        return self._parse_response(response)
```

---

#### ⚡ 성능 최적화 전략

| 전략 | 설명 | 구현 위치 |
|------|------|----------|
| **디바운싱** | 150ms 내 연속 Pan/Zoom 이벤트 통합 | `_on_viewport_changed` |
| **버퍼링** | 뷰포트 양쪽 50 bars 미리 로드 | `ChartDataManager.FETCH_BUFFER` |
| **최소 Fetch** | API 호출당 최소 100 bars 요청 | `ChartDataManager.MIN_FETCH_SIZE` |
| **LRU 캐시** | 타임프레임별 최근 데이터 캐싱 | `ChartDataManager._data_cache` |
| **점진적 렌더링** | 먼저 뷰포트 내 데이터만 렌더링 | `CandlestickItem.paint()` |

---

#### 🧪 테스트 시나리오

```python
# tests/test_dynamic_loading.py

class TestDynamicDataLoading:
    def test_needs_more_data_left_pan(self):
        """왼쪽(과거) Pan 시 추가 데이터 필요 감지"""
        manager = ChartDataManager()
        manager.set_initial_data(pd.DataFrame({'c': range(100)}))
        
        # 왼쪽 끝에서 버퍼 범위 밖으로 이동
        assert manager.needs_more_data(view_start=-10, view_end=40) == True
    
    def test_merge_prepend(self):
        """과거 데이터 병합"""
        manager = ChartDataManager()
        manager.set_initial_data(pd.DataFrame({'c': [100, 101, 102]}))
        
        new_data = pd.DataFrame({'c': [97, 98, 99]})
        manager.merge_data(new_data, prepend=True)
        
        assert len(manager._data_cache) == 6
        assert manager._loaded_range.start_idx == -3
```

---

#### 📝 구현 순서 (즉시 구현)

> [!NOTE]
> 이 기능은 **즉시 구현** 대상입니다. 2-Tier 캐시는 초기 릴리스에 포함됩니다.

| 순서 | 작업 | 예상 시간 | 상태 |
|------|------|----------|------|
| 1 | `database.py` - `IntradayBar` 테이블 추가 | 30분 | ⬜ |
| 2 | `database.py` - Intraday CRUD 함수 추가 | 30분 | ⬜ |
| 3 | `chart_data_manager.py` - 2-Tier 캐시 로직 | 1시간 | ⬜ |
| 4 | `pyqtgraph_chart.py` - Viewport 감지 + 디바운싱 | 30분 | ⬜ |
| 5 | `dashboard.py` - 동적 로딩 시그널 연결 | 30분 | ⬜ |
| 6 | 통합 테스트 | 30분 | ⬜ |

**총 예상 시간**: 3-4시간

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
