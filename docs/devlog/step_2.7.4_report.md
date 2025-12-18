# Step 2.7.4 Report: Dynamic Data Loading on Pan/Zoom

> **작성일**: 2025-12-19  
> **소요 시간**: ~1시간  
> **상태**: ✅ 기본 프레임워크 완료 (L2/L3 연동은 추후 완성)

---

## 📋 구현 요약

차트 Pan/Zoom 시 동적 데이터 로딩을 위한 **2-Tier Cache 기본 프레임워크**를 구현했습니다.

### 변경된 파일

| 파일 | 변경 내용 |
|------|----------|
| `backend/data/database.py` | `IntradayBar` 모델 + CRUD 함수 추가 |
| `frontend/gui/chart/chart_data_manager.py` | **신규** - 2-Tier Cache 로직 |
| `frontend/gui/chart/pyqtgraph_chart.py` | `viewport_data_needed` 시그널 + 디바운싱 |
| `frontend/gui/dashboard.py` | 시그널 핸들러 연결 |

---

## 🏗️ 아키텍처

```
┌──────────────────────────────────────────────────────────────┐
│  Chart Pan/Zoom                                              │
│       │                                                      │
│       ▼                                                      │
│  sigXRangeChanged → _on_viewport_changed() (150ms debounce)  │
│       │                                                      │
│       ▼                                                      │
│  viewport_data_needed.emit(start_idx, end_idx)               │
│       │                                                      │
│       ▼                                                      │
│  _on_viewport_data_needed() [dashboard.py]                   │
│       │                                                      │
│       ▼                                                      │
│  L1: Memory → L2: SQLite → L3: API                           │
└──────────────────────────────────────────────────────────────┘
```

---

## 🔧 구현 상세

### 1. IntradayBar 모델 (database.py)

```python
class IntradayBar(Base):
    __tablename__ = "intraday_bars"
    
    # PK: (ticker, timeframe, timestamp)
    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    timeframe: Mapped[str] = mapped_column(String(5), primary_key=True)
    timestamp: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # OHLCV
    open, high, low, close, volume, vwap
```

### 2. CRUD 함수

- `upsert_intraday_bulk(bars)` - Bulk Insert/Update
- `get_intraday_bars(ticker, timeframe, start_ts, end_ts)` - 범위 조회
- `get_intraday_latest_timestamp(ticker, timeframe)` - 마지막 시점

### 3. ChartDataManager (chart_data_manager.py)

```python
class ChartDataManager:
    FETCH_BUFFER = 50
    MIN_FETCH_SIZE = 100
    
    def needs_more_data(view_start, view_end) -> bool
    def calculate_fetch_range(view_start, view_end) -> tuple
    def merge_data(new_data, prepend: bool)
```

### 4. Viewport 시그널 (pyqtgraph_chart.py)

```python
viewport_data_needed = pyqtSignal(int, int)  # (start_idx, end_idx)

# 150ms 디바운싱
self._viewport_timer = QTimer()
self._viewport_timer.setInterval(150)
```

---

## 🧪 검증 결과

- [x] Python 구문 검사 통과 (모든 파일)
- [x] 시그널 연결 체인 확인
- [ ] 실제 GUI 테스트 (수동 확인 필요)
- [ ] L2/L3 연동 테스트 (추후 구현)

---

## 📝 다음 단계 (TODO)

`_on_viewport_data_needed()` 핸들러에서 실제 L2/L3 연동:

```python
# 1. ChartDataManager.calculate_fetch_range()
# 2. L2: await db.get_intraday_bars(...)
# 3. L3: await polygon_client.fetch_intraday_bars(...)
# 4. await db.upsert_intraday_bulk(...)
# 5. ChartDataManager.merge_data()
# 6. chart_widget.append_data()
```

---

## ⚠️ 주의사항

- **현재 형성 중인 Bar**는 DB에 저장하지 않음 (아직 변동 가능)
- **완성된 Bar**만 L2(SQLite)에 캐싱 (`current_time > bar_timestamp + bar_duration`)
- 디바운싱 150ms로 연속 Pan/Zoom 이벤트 통합

---

## 📌 Phase 2 구현 완료 (2025-12-19)

L2/L3 연동 완전 구현됨:

- `_on_viewport_data_needed()` - 스크롤 감지 + 스레드 실행
- `_fetch_historical_bars()` - SQLite 조회 → API fallback
- `_apply_prepend_data()` - 차트에 과거 데이터 prepend

