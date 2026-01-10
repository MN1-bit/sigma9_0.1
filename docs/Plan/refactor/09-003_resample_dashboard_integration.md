# ResamplePanel 대시보드 통합 + 차트 스크롤링

> **상태**: 📋 **구현 계획** (USER 승인 대기)
> **작성일**: 2026-01-10
> **예상 작업 시간**: 3h
> **선행 작업**: [09-002_finplot_chart_enhancements.md](./09-002_finplot_chart_enhancements.md)
> **레이어**: Frontend

---

## 1. 목표

1. **ResamplePanel 대시보드 통합** - Settings 영역에 리샘플링 컨트롤 패널 추가
2. **차트 좌측 스크롤링** - 드래그 시 과거 데이터 로드 (현재 데이터 boundary 문제 해결)

---

## 2. 레이어 체크 (REFACTORING.md §2-§3)

- [x] **레이어 규칙 위반 없음**
  - 모든 변경은 `frontend.*` 레이어 내부
  - Backend import: `ParquetManager` (하위 레이어) ✅
- [x] **순환 의존성 없음** - Frontend 내부 컴포넌트 간 단방향 의존
- [x] **DI Container 등록 필요**: **아니오**
  - `ResamplePanel`은 GUI 위젯 (Container 불필요)
  - `ParquetManager`는 이미 Container 등록됨 (09-002에서 주입)

---

## 3. 크기 제한 체크 (REFACTORING.md §8)

| 파일 | 현재 라인 | 예상 추가 | 합계 | 상태 |
|------|----------|----------|------|------|
| `dashboard.py` | ~300 | +20 | ~320 | ✅ < 500 |
| `finplot_chart.py` | 447 | +40 | ~487 | ✅ < 500 |
| `chart_panel.py` | ~200 | +30 | ~230 | ✅ < 500 |
| `chart_data_service.py` | 438 | +20 | ~458 | ✅ < 500 |

---

## 4. 기존 솔루션 검색 결과 (REFACTORING.md §5)

| 솔루션 | 출처 | 채택 여부 | 사유 |
|--------|------|----------|------|
| finplot `sigXRangeChanged` | finplot 내장 | ✅ 채택 | pyqtgraph ViewBox 시그널 재사용 |
| pyqtgraph infinite scrolling | pyqtgraph examples | ✅ 참고 | 패턴 참조 (autoRange 비활성화) |
| third-party lazy loading | PyPI | ❌ 미채택 | Qt 시그널로 충분 |

> ✅ 검색 완료: finplot 내장 `sigXRangeChanged` + pyqtgraph autoRange 비활성화 패턴 사용

---

## 5. 현재 문제점

### 5.1 ResamplePanel 미통합
- `ResamplePanel` 클래스 생성 완료 (09-002)
- 대시보드 UI에 통합되지 않음 → Settings 영역에 배치 필요

### 5.2 차트 스크롤 Boundary 문제
- 현재: 로드된 데이터 범위를 넘어서 좌측으로 드래그 불가
- 원인: finplot의 ViewBox가 데이터 boundary로 제한됨 (`enableAutoRange`)
- 해결: `sigXRangeChanged` 시그널로 viewport 변경 감지 → 추가 데이터 로드

```
┌────────────────────────────────────────────────────────┐
│  현재 상태: 왼쪽 스크롤이 데이터 시작점에서 막힘      │
│                                                        │
│  [막힘] ◀─────────── 로드된 데이터 ──────────────▶    │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│  목표: 왼쪽 스크롤 시 과거 데이터 자동 로드           │
│                                                        │
│  ◀── 추가 로드 ──[viewport]── 로드된 데이터 ─────▶   │
└────────────────────────────────────────────────────────┘
```

---

## 6. 아키텍처

### 6.1 ResamplePanel 통합 위치

```
Dashboard
├── Left Panel (Watchlist)
├── Center Panel (Chart)
├── Right Panel
│   ├── Position Panel
│   ├── Oracle Panel
│   └── ⭐ ResamplePanel (NEW)  ← Settings 영역 또는 별도 탭
└── Bottom Panel (Log)
```

### 6.2 차트 스크롤 데이터 로딩 흐름

```
User drags left → sigXRangeChanged (finplot)
    → FinplotChartWidget._on_viewport_changed
    → viewport_data_needed.emit(start_ts, end_ts)
    → ChartPanel receives signal
    → ChartDataService.get_chart_data(older_range=True)
    → ParquetManager.read_intraday(start_timestamp=...)
    → FinplotChartWidget.prepend_candlestick_data()
```

---

## 7. 변경 파일

| 파일 | 유형 | 예상 라인 | 설명 |
|------|------|----------|------|
| `frontend/gui/dashboard.py` | MODIFY | +20 | ResamplePanel 추가 |
| `frontend/gui/chart/finplot_chart.py` | MODIFY | +40 | viewport 시그널 + prepend 메서드 |
| `frontend/gui/panels/chart_panel.py` | MODIFY | +30 | viewport_data_needed 핸들러 |
| `frontend/services/chart_data_service.py` | MODIFY | +20 | 범위 지정 데이터 로드 |

---

## 8. 실행 단계

### Step 1: ResamplePanel 대시보드 통합 (1h)
- `dashboard.py`에서 ResamplePanel import
- Settings 영역 또는 Right Panel에 배치
- ParquetManager DI 연결

### Step 2: 차트 viewport 시그널 설정 (0.5h)
- `sigXRangeChanged` 연결
- Debounce 타이머 (150ms)
- `viewport_data_needed(start_ts, end_ts)` emit
- `ax.vb.disableAutoRange()` 호출

### Step 3: ChartPanel 핸들러 구현 (0.5h)
- viewport_data_needed 수신
- ChartDataService 호출
- prepend_candlestick_data() 호출

### Step 4: 데이터 로딩 + 병합 (0.5h)
- start_timestamp 기반 이전 데이터 로드
- 기존 candle 데이터와 병합
- finplot refresh

### Step 5: 검증 (0.5h)

---

## 9. 검증 계획

### 9.1 린트 검증 (필수)
```powershell
ruff check frontend/gui/dashboard.py
ruff check frontend/gui/chart/finplot_chart.py
ruff check frontend/gui/panels/chart_panel.py
ruff check frontend/services/chart_data_service.py
```

### 9.2 수동 테스트
1. GUI 실행: `python -m frontend.main`
2. ResamplePanel이 대시보드에 표시되는지 확인
3. Start 버튼 클릭 → 진행 상황 표시 확인
4. 차트에서 좌측으로 드래그 → 과거 데이터 로드 확인
5. 로그에 `[INFO] 📊 Loading more data` 확인

---

## 10. 보강작업 (2026-01-10)

### 10.1 다중 타임프레임 체크박스
- **변경**: Target Timeframe 드롭다운 → 체크박스 5개 (3m/5m/15m/4h/1W)
- **기능**: 여러 TF 선택 후 일괄 리샘플 가능
- **순차 처리**: 선택된 TF를 순서대로 처리, 각 TF 완료 후 다음 TF 자동 시작

### 10.2 ParquetManager DI 연결
- **문제**: Settings Dialog에서 "ParquetManager not set" 에러
- **해결**: Dashboard에서 Settings Dialog 생성 시 ParquetManager 주입 필요
- **위치**: `dashboard.py`의 `_on_settings()` 메서드에서 `settings_dialog.set_parquet_manager(pm)` 호출

---

## Phase 2: Historical Data Scrolling 구현 계획

> **상태**: 📋 **구현 계획** (USER 승인 대기)
> **선행**: Phase 1 완료
> **예상 작업 시간**: 2h

---

### 2.1 목표

**첫 번째 캔들이 뷰포트에 보일 때** (Edge Trigger) 과거 데이터 자동 로드:

> [!NOTE]
> finplot은 의도적으로 데이터 범위 밖 스크롤을 제한합니다 ([GitHub #106](https://github.com/highfestiva/finplot/issues/106)).
> 우회책: **첫 번째(가장 오래된) 캔들이 화면에 나타나면** 더 많은 과거 데이터를 로드하여 prepend.

1. **Edge Trigger**: 뷰포트에 `data_start` 캔들이 보이면 트리거
2. **100 bars 통일**: 모든 타임프레임에서 결과 100개 캔들 로드
3. **소스 배수 로드 + 리샘플**: 파생 타임프레임은 소스 데이터를 배수로 로드 후 리샘플
4. **차트에 prepend**: `pd.concat()` 사용

#### 로드 정책 (100 bars 통일)

| 타겟 TF | 소스 TF | 소스 요청량 | 결과 |
|--------|--------|-----------|------|
| **1m** | 1m | 100개 | 100개 1분봉 |
| **3m** | 1m | 300개 | → 리샘플 → 100개 3분봉 |
| **5m** | 1m | 500개 | → 리샘플 → 100개 5분봉 |
| **15m** | 1m | 1500개 | → 리샘플 → 100개 15분봉 |
| **1h** | 1h | 100개 | 100개 1시간봉 |
| **4h** | 1h | 400개 | → 리샘플 → 100개 4시간봉 |
| **1D** | 1D | 100개 | 100개 일봉 |
| **1W** | 1D | 700개 | → 리샘플 → 100개 주봉 |

#### 안전장치
- **중복 로드 방지**: 이전 `data_start` 기록 → 같은 범위 재요청 안함
- **로딩 상태 표시**: 로딩 중 추가 트리거 방지 (debounce + flag)
- **데이터 없음 종료**: API가 빈 데이터 반환 시 해당 티커 로딩 중단

---

### 2.2 레이어 체크 (REFACTORING.md §3.3)

- [x] **레이어 규칙 위반 없음**
  - Frontend → Backend API (REST) → DataRepository → ParquetManager
  - Frontend가 Backend 모듈 직접 import 제거 (현재 위반 수정)
- [x] **순환 의존성 없음** - Frontend → Backend 단방향
- [x] **DI Container 등록 필요**: **아니오**
  - DataRepository는 이미 Container 등록됨 (11-002)
  - ChartDataService는 GUI 서비스 (Container 불필요)

---

### 2.3 크기 제한 체크 (REFACTORING.md §8)

| 파일 | 현재 라인 | 예상 변경 | 합계 | 상태 |
|------|----------|----------|------|------|
| `chart_data_service.py` | 480 | +30 | ~510 | ✅ < 1000 |
| `finplot_chart.py` | 598 | -40 (제거) | ~560 | ✅ < 1000 |
| `chart.py` (routes) | 269 | +0 (기존 사용) | 269 | ✅ < 1000 |

---

### 2.4 기존 솔루션 검색 결과 (REFACTORING.md §5)

| 솔루션 | 출처 | 채택 여부 | 사유 |
|--------|------|----------|------|
| pyqtgraph `sigXRangeChanged` | finplot/pyqtgraph 내장 | ✅ 채택 | viewport 변경 감지 표준 방식 |
| `pd.concat()` prepend | pandas 내장 | ✅ 채택 | DataFrame 앞 병합에 효율적 |
| Debounce QTimer | Qt 내장 | ✅ 채택 | 빠른 스크롤 시 과도한 API 호출 방지 |
| REST API 호출 | httpx/BackendClient | ✅ 채택 | 레이어 분리 준수 |

> ✅ 검색 완료: 모든 필요 기능이 기존 라이브러리/패턴으로 구현 가능

---

### 2.5 현재 구현 상태 분석

> [!IMPORTANT]
> Phase 2의 핵심 컴포넌트가 **이미 구현**되어 있음. 리팩터링만 필요.

#### 이미 구현된 부분 ✅

| 컴포넌트 | 위치 | 상태 |
|---------|------|------|
| `sigXRangeChanged` + debounce | `finplot_chart.py` L82-89, L475-490 | ✅ 구현됨 |
| `prepend_candlestick_data()` | `finplot_chart.py` L572-597 | ✅ 구현됨 |
| `get_historical_bars()` API | `chart.py` L136-242 | ✅ 구현됨 |
| DataRepository + auto_fill | `data_repository.py` | ✅ 구현됨 |
| On-demand resampling | `parquet_manager.py` | ✅ 구현됨 |

#### 수정 필요 부분 ⚠️

| 문제 | 위치 | 수정 내용 |
|------|------|----------|
| **레이어 위반** | `finplot_chart.py` L516-520 | `from backend.data.parquet_manager import ParquetManager` 제거 |
| **직접 ParquetManager 호출** | `finplot_chart.py` L520 | Backend API 호출로 변경 |
| **Thread 내 동기 호출** | `finplot_chart.py` L514-560 | async + httpx로 변경 |

---

### 2.6 변경 파일

| 파일 | 유형 | 예상 라인 | 설명 |
|------|------|----------|------|
| `frontend/gui/chart/finplot_chart.py` | MODIFY | -40 | ParquetManager 직접 호출 제거, BackendClient 사용 |
| `frontend/services/chart_data_service.py` | MODIFY | +30 | `load_historical()` 메서드 추가 (Backend API 호출) |

> [!NOTE]
> `backend/api/routes/chart.py`의 `get_historical_bars()` API는 **이미 완성**되어 추가 변경 불필요.

---

### 2.7 아키텍처 (수정 후)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Frontend (Local)                                  │
│                                                                          │
│  FinplotChartWidget                                                      │
│  ├── _on_viewport_changed()  ← sigXRangeChanged (debounce 150ms)        │
│  │       │                                                               │
│  │       ↓                                                               │
│  └── ChartDataService.load_historical(ticker, tf, before_ts)            │
│              │                                                           │
│              ↓ REST API (httpx)                                          │
└──────────────┼───────────────────────────────────────────────────────────┘
               │
               ↓ GET /api/chart/bars?ticker=X&timeframe=5m&before=123456
┌──────────────┼───────────────────────────────────────────────────────────┐
│              ↓                        Backend (AWS)                       │
│  chart.py::get_historical_bars()                                         │
│              │                                                            │
│              ↓                                                            │
│  DataRepository.get_intraday_bars(auto_fill=True)                        │
│              │                                                            │
│              ├── Parquet Hit → 데이터 반환                                │
│              │                                                            │
│              └── Parquet Miss → MassiveClient.fetch_intraday_bars()      │
│                       │                                                   │
│                       ↓                                                   │
│                  ParquetManager.append_intraday() (캐싱)                  │
│                       │                                                   │
│                       ↓ (파생 TF인 경우)                                  │
│                  ParquetManager._try_resample()                          │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

---

### 2.8 실행 단계

#### Step 1: ChartDataService에 `load_historical()` 추가 (0.5h)

`frontend/services/chart_data_service.py`:
```python
async def load_historical(
    self,
    ticker: str,
    timeframe: str,
    before_ts: int,
    limit: int = 100,
) -> Dict:
    """
    Backend API를 통해 과거 데이터 로드
    
    Args:
        ticker: 종목 심볼
        timeframe: 타임프레임 ("1m", "5m", "15m", "1h")
        before_ts: 이 타임스탬프(초) 이전 데이터 조회
        limit: 가져올 바 개수
    
    Returns:
        {"candles": [...], "count": int, ...}
    """
    import httpx
    
    url = f"{self._api_base}/api/chart/bars"
    params = {
        "ticker": ticker,
        "timeframe": timeframe,
        "before": int(before_ts * 1000),  # seconds → ms
        "limit": limit,
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=30.0)
        resp.raise_for_status()
        return resp.json()
```

#### Step 2: FinplotChartWidget 레이어 위반 수정 (1h)

`frontend/gui/chart/finplot_chart.py`:

1. **ParquetManager import 제거** (L516):
   ```diff
   - from backend.data.parquet_manager import ParquetManager
   ```

2. **`_emit_viewport_data_needed()` 수정** (L492-560):
   - Thread + ParquetManager → async + ChartDataService
   ```python
   async def _load_historical_data(self) -> None:
       """Backend API를 통해 과거 데이터 로드"""
       start_ts, _ = self._pending_viewport_range
       if start_ts <= 0 or not self._current_ticker:
           return
       
       try:
           from frontend.services.chart_data_service import ChartDataService
           service = ChartDataService()
           result = await service.load_historical(
               ticker=self._current_ticker,
               timeframe=self._current_timeframe,
               before_ts=start_ts,
               limit=100,
           )
           
           if result.get("candles"):
               self.prepend_candlestick_data(result["candles"])
               print(f"[CHART] Loaded {result['count']} historical bars")
       except Exception as e:
           print(f"[CHART] Historical load error: {e}")
   ```

3. **QTimer timeout 핸들러 수정**:
   - 메인 스레드에서 async 함수 호출 → `asyncio.create_task()` 사용

#### Step 3: 검증 (0.5h)

---

### 2.9 검증 계획

#### 2.9.1 린트 검증 (필수)
```powershell
# turbo
ruff check frontend/gui/chart/finplot_chart.py
ruff check frontend/services/chart_data_service.py
```

#### 2.9.2 Import 규칙 검증
```powershell
# finplot_chart.py에서 backend.* import가 없는지 확인
grep -r "from backend\." frontend/gui/chart/finplot_chart.py
# 결과: 없어야 정상
```

#### 2.9.3 수동 테스트

1. **GUI 실행**:
   ```powershell
   python -m frontend.main
   ```

2. **차트에서 좌측 스크롤**:
   - AAPL 차트 로드
   - 마우스 휠로 좌측(과거)으로 스크롤
   - 데이터가 없는 영역에 도달 시 로딩 확인

3. **확인 사항**:
   - [ ] 콘솔에 `[CHART] Loaded N historical bars` 로그 출력
   - [ ] 과거 캔들이 차트에 추가됨
   - [ ] 오류 메시지 없음

---

## 11. 다음 단계

- [x] Phase 1 완료
- [ ] Phase 2 구현

