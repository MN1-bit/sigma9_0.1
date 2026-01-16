# 14-005: TickerInfo 서비스 아키텍처 리팩터링

> **작성일**: 2026-01-13 12:10 | **수정일**: 2026-01-13 14:36
> **우선순위**: 높음 | **예상 소요**: 4h | **위험도**: 중간

---

## 1. 목표

TickerInfo 데이터 처리를 **Backend 중심 아키텍처 + 부분 갱신 정책**으로 전환:
- Backend: API 호출 + 캐싱 + 전략 계산에 활용
- Frontend: DB에서 캐시 데이터 조회만
- **부분 갱신**: 만료된 카테고리만 개별 API 호출 (전체 갱신 폐지)

### 해결되는 문제들

| 문제 | 현재 | 개선 후 |
|------|------|---------|
| 자동매매 전략에서 시총/Float 필요 | 별도 API 호출 (중복) | DB 캐시에서 즉시 조회 |
| Frontend 초기 로드 느림 | API 대기 | DB 캐시에서 즉시 로드 |
| 캐시 불일치 | Frontend 로컬 캐시만 | 중앙 DB 단일 소스 |
| Dynamic 데이터 캐시 없음 | 매번 API 호출 | TTL 기반 캐시 |
| **전체 갱신 비효율** | 1개 만료 시 13개 전부 fetch | **만료된 것만 fetch** |

---

## 2. 아키텍처 비교

### 현재 (문제점)

```
[Frontend]                              [Backend (AWS)]
    │                                        │
    ├── TickerInfoService ───► Massive API   │ (접근 불가)
    ├── SQLite 캐시 (로컬)                   │
    └── 직접 API 호출                        └── 전략 계산 시 데이터 없음
```

### 제안 (Backend 중심 + Selective Refresh)

```
[Frontend]                              [Backend (AWS)]
    │                                        │
    └── DB 조회 ◄──────── 공유 DB ◄───────── TickerInfoService
                              │               │
                              └── (캐시) ◄─── Massive API (개별 카테고리만)
                                              │
                              전략 엔진 ◄─────┘ (즉시 접근 가능)
```

---

## 3. 13개 카테고리 종합 분석

### 현재 데이터 구조

| # | 카테고리 | API Endpoint | 데이터 형태 | 변경 빈도 |
|---|----------|--------------|-------------|-----------|
| 1 | `profile` | `/v3/reference/tickers/{ticker}` | dict | 거의 안 변함 |
| 2 | `float_data` | `/stocks/vX/float` | dict | 분기별 |
| 3 | `financials` | `/vX/reference/financials` | list[4] | 분기별 |
| 4 | `dividends` | `/v3/reference/dividends` | list[5] | 분기~연간 |
| 5 | `splits` | `/v3/reference/splits` | list[5] | 드묾 |
| 6 | `ipo` | `/vX/reference/ipos` | dict | **불변** |
| 7 | `ticker_events` | `/vX/reference/tickers/{ticker}/events` | list | 드묾 |
| 8 | `filings` | `/v1/reference/sec/filings` | list[5] | 일~주간 |
| 9 | `news` | `/v2/reference/news` | list[5] | **수시** |
| 10 | `related` | `/v1/related-companies/{ticker}` | list | 거의 안 변함 |
| 11 | `snapshot` | `/v2/snapshot/.../tickers/{ticker}` | dict | **실시간** |
| 12 | `short_interest` | `/vX/reference/short-interest/ticker/{ticker}` | list[5] | 일별 |
| 13 | `short_volume` | `/vX/reference/short-volume/{ticker}` | list[5] | 일별 |

---

## 4. 부분 갱신 정책 (Selective Refresh)

### Tier 분류

```
┌─────────────────────────────────────────────────────────────────────┐
│  TIER 1: IMMUTABLE (영구 캐시, TTL = -1)                            │
│  - ipo: 상장 정보는 절대 안 변함                                     │
├─────────────────────────────────────────────────────────────────────┤
│  TIER 2: STATIC (7~30일)                                            │
│  - profile: 회사명, CIK, SIC 등                                     │
│  - related: 경쟁사 목록                                             │
│  - splits: 액면분할 이력 (30일)                                     │
├─────────────────────────────────────────────────────────────────────┤
│  TIER 3: SEMI-STATIC (1~7일)                                        │
│  - float_data: 분기별 업데이트 (7일)                                 │
│  - financials: 분기 실적 (90일)                                     │
│  - dividends: 배당 일정 (7일)                                       │
│  - ticker_events: 이름 변경 등 (7일)                                │
│  - filings: SEC 공시 (1일)                                          │
├─────────────────────────────────────────────────────────────────────┤
│  TIER 4: DYNAMIC (분~시간 단위)                                      │
│  - news: 30분 (뉴스 빈도)                                           │
│  - short_interest: 1일 (장 마감 후 업데이트)                         │
│  - short_volume: 1일 (장 마감 후 업데이트)                           │
├─────────────────────────────────────────────────────────────────────┤
│  TIER 5: REAL-TIME (5분 또는 WebSocket)                             │
│  - snapshot: 현재가 (5분 캐시)                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 새로운 REFRESH_POLICY

```python
REFRESH_POLICY: dict[str, int] = {
    # TIER 1: IMMUTABLE (-1 = 영구 캐시)
    "ipo": -1,
    
    # TIER 2: STATIC
    "profile": 7 * 24 * 3600,      # 7일
    "related": 7 * 24 * 3600,      # 7일
    "splits": 30 * 24 * 3600,      # 30일
    
    # TIER 3: SEMI-STATIC
    "float_data": 7 * 24 * 3600,   # 7일
    "financials": 90 * 24 * 3600,  # 90일
    "dividends": 7 * 24 * 3600,    # 7일
    "ticker_events": 7 * 24 * 3600,# 7일
    "filings": 24 * 3600,          # 1일
    
    # TIER 4: DYNAMIC
    "news": 30 * 60,               # 30분
    "short_interest": 24 * 3600,   # 1일
    "short_volume": 24 * 3600,     # 1일
    
    # TIER 5: REAL-TIME
    "snapshot": 5 * 60,            # 5분
}
```

### 네트워크 비용 비교

| 시나리오 | 전체 갱신 (현재) | 부분 갱신 (제안) |
|----------|------------------|------------------|
| Snapshot만 만료 | 13 API (~500ms) | **1 API (~200ms)** |
| News만 만료 | 13 API (~500ms) | **1 API (~200ms)** |
| Profile + Float 만료 | 13 API (~500ms) | **2 API (~300ms)** |
| 10개 티커 배치 갱신 | ~5초 | **~2초** |

---

## 5. Priority Loading + 섹션별 로딩 스피너

### 현재 문제

첫 로드 시 13개 API를 병렬 호출해도 **가장 느린 endpoint 기준**으로 3-5초 대기 필요:

```
[현재] asyncio.gather(13개) → 모두 완료될 때까지 대기 → 3-5초 후 UI 표시
```

### Priority Loading 전략

**핵심 아이디어**: 중요한 데이터부터 순차적으로 로드하고, 도착 즉시 UI 업데이트

```
[제안] 우선순위별 순차 로드 → 각 섹션 도착 즉시 UI 반영 → 체감 <1초
```

### 로딩 우선순위 (13개 카테고리)

| 우선순위 | 카테고리 | 근거 | 예상 응답 |
|:--------:|----------|------|-----------|
| **P1** | `profile` (시총 포함) | 회사 정체성 + Market Cap | ~200ms |
| **P2** | `float_data` | 트레이딩 핵심 지표 | ~200ms |
| **P3** | `filings` | SEC 공시 (희석 리스크) | ~300ms |
| **P4** | `news` | 최신 뉴스/촉매 | ~300ms |
| **P5** | `snapshot` | 현재가 (가격 확인용) | ~200ms |
| **P6** | `short_interest` | 공매도 잔고 | ~300ms |
| **P7** | `short_volume` | 공매도 거래량 | ~300ms |
| **P8** | `financials` | 재무제표 | ~400ms |
| **P9** | `dividends` | 배당 이력 | ~200ms |
| **P10** | `splits` | 액면분할 | ~200ms |
| **P11** | `ipo` | IPO 정보 | ~200ms |
| **P12** | `ticker_events` | 티커 이벤트 | ~200ms |
| **P13** | `related` | 관련 기업 | ~300ms |

### UI 로딩 스피너 설계

각 섹션에 개별 로딩 상태 표시:

```
┌─────────────────────────────────────────────────────────────┐
│  AAPL - Apple Inc.                                          │
├─────────────────────────────────────────────────────────────┤
│  Market Cap: $3.2T  ✅                                      │
│  Float: ⟳ (로딩 중...)                                      │
│  SEC Filings: ⟳ (로딩 중...)                                │
│  News: ⟳ (로딩 중...)                                       │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
         ↓ 200ms 후
┌─────────────────────────────────────────────────────────────┐
│  AAPL - Apple Inc.                                          │
├─────────────────────────────────────────────────────────────┤
│  Market Cap: $3.2T  ✅                                      │
│  Float: 15.2B shares  ✅                                    │
│  SEC Filings: ⟳ (로딩 중...)                                │
│  News: ⟳ (로딩 중...)                                       │
│  ...                                                        │
└─────────────────────────────────────────────────────────────┘
```

### 로딩 스피너 컴포넌트

```python
# frontend/gui/components/loading_spinner.py
class LoadingSpinner(QLabel):
    """애니메이션 로딩 스피너 위젯."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._movie = QMovie(":/icons/spinner.gif")  # 또는 CSS 애니메이션
        self.setMovie(self._movie)
        self._movie.start()
    
    def stop(self):
        self._movie.stop()
        self.hide()

# 또는 CSS 기반 스피너 (더 가벼움)
class CSSSpinner(QLabel):
    """CSS 애니메이션 기반 스피너."""
    
    SPINNER_STYLE = """
        QLabel {
            color: #888;
            font-size: 14px;
        }
    """
    
    def __init__(self, parent=None):
        super().__init__("⟳", parent)  # 또는 "◌" "⏳"
        self.setStyleSheet(self.SPINNER_STYLE)
        # QPropertyAnimation으로 회전 효과
```

### 체감 성능 개선

| 시점 | 현재 | Priority Loading 적용 후 |
|------|------|--------------------------|
| 0ms | 빈 화면 | 빈 화면 + 모든 섹션 스피너 |
| 200ms | 빈 화면 | **Profile/Cap 표시** |
| 400ms | 빈 화면 | **Float 표시** |
| 600ms | 빈 화면 | **Filings + News 표시** |
| 1000ms | 빈 화면 | **대부분 로드 완료** |
| 3-5초 | **전체 표시** | 모든 섹션 완료 |

**결과**: 체감 로딩 시간 **3-5초 → <1초**

---

## 6. 실행 계획

### Step 1: REFRESH_POLICY 업데이트

```python
# backend/data/ticker_info_service.py
REFRESH_POLICY: dict[str, int] = {
    "ipo": -1,  # 영구 캐시
    "profile": 7 * 24 * 3600,
    # ... (위 정책 적용)
}

# 로딩 우선순위
LOADING_PRIORITY: list[str] = [
    "profile",       # P1: 시총 포함
    "float_data",    # P2: 트레이딩 핵심
    "filings",       # P3: SEC 공시
    "news",          # P4: 뉴스
    "snapshot",      # P5: 현재가
    "short_interest",# P6
    "short_volume",  # P7
    "financials",    # P8
    "dividends",     # P9
    "splits",        # P10
    "ipo",           # P11
    "ticker_events", # P12
    "related",       # P13
]
```

### Step 2: 스트리밍 로드 API 구현

```python
async def stream_ticker_info(
    self, 
    ticker: str,
    on_category_loaded: Callable[[str, Any], None]
) -> TickerInfo:
    """
    Priority Loading: 카테고리별 순차 로드 + 콜백.
    
    Args:
        ticker: 종목 심볼
        on_category_loaded: 카테고리 로드 완료 시 호출되는 콜백
    """
    ticker = ticker.upper()
    info = TickerInfo(ticker=ticker)
    
    for category in LOADING_PRIORITY:
        fetch_fn = self._get_fetch_fn(category, ticker)
        result = await self._fetch_with_policy(ticker, category, fetch_fn)
        
        # 결과를 info에 할당
        setattr(info, category, result)
        
        # 콜백 호출 → UI 즉시 업데이트
        on_category_loaded(category, result)
    
    return info
```

### Step 3: Frontend 콜백 기반 UI 업데이트

```python
# frontend/gui/ticker_info_window.py
class TickerInfoWindow:
    def __init__(self):
        self._section_spinners: dict[str, LoadingSpinner] = {}
        self._init_section_spinners()
    
    def _init_section_spinners(self):
        """각 섹션에 로딩 스피너 초기화."""
        for section in LOADING_PRIORITY:
            spinner = LoadingSpinner(self)
            self._section_spinners[section] = spinner
    
    async def load_ticker(self, ticker: str):
        # 모든 스피너 표시
        for spinner in self._section_spinners.values():
            spinner.show()
        
        # 스트리밍 로드
        await self._service.stream_ticker_info(
            ticker,
            on_category_loaded=self._on_section_loaded
        )
    
    def _on_section_loaded(self, category: str, data: Any):
        """개별 섹션 로드 완료 시 호출."""
        # 스피너 숨기기
        self._section_spinners[category].stop()
        
        # 해당 섹션 UI 업데이트
        self._update_section(category, data)
```

### Step 4: 부분 갱신 로직 (기존)

```python
async def get_ticker_info(
    self, 
    ticker: str, 
    force_categories: set[str] | None = None
) -> TickerInfo:
    # ... (기존 부분 갱신 로직 유지)
```

### Step 5: _get_cached() 수정 (영구 캐시 지원)

```python
def _get_cached(self, ticker: str, category: str) -> Optional[dict[str, Any]]:
    ttl = REFRESH_POLICY.get(category, 0)
    
    # IMMUTABLE: TTL 체크 안함
    if ttl == -1:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(...)
            row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return None
    
    # 기존 TTL 체크 로직
    # ...
```

---

## 7. 영향 분석

### 변경 대상 파일

| 파일 | 변경 유형 | 영향도 |
|------|----------|--------|
| `backend/data/ticker_info_service.py` | 부분 갱신 + 스트리밍 API | 중간 |
| `frontend/gui/ticker_info_window.py` | 콜백 기반 UI + 스피너 | 높음 |
| `frontend/gui/components/loading_spinner.py` | 신규 생성 | 낮음 |

### 변경 없는 파일

- `backend/models/ticker_info.py`: 데이터 모델 그대로
- `frontend/services/`: Reader 분리는 후속 작업으로 이관

---

## 8. 검증 계획

| 검증 항목 | 방법 | 기대 결과 |
|-----------|------|-----------|
| Priority Loading | Profile 로드 시간 측정 | <500ms 내 첫 섹션 표시 |
| 스피너 동작 | 각 섹션 로딩 시 스피너 확인 | 회전 애니메이션 표시 |
| 스피너 해제 | 섹션 로드 완료 시 | 스피너 사라지고 데이터 표시 |
| IPO 영구 캐시 | 2회 조회 후 API 호출 로그 확인 | 2회차에 API 호출 없음 |
| 부분 갱신 | `force_categories={"news"}` 호출 | news만 API 호출 |

---

## 9. 롤백 계획

1. `stream_ticker_info()` 제거, 기존 `get_ticker_info()` 사용
2. 스피너 컴포넌트 비활성화
3. `force_categories` 파라미터를 `force_refresh: bool`로 복원
4. REFRESH_POLICY에서 `-1` (영구 캐시) 제거

---

## 10. 후속 작업

- [ ] Frontend TickerInfoReader 분리 (읽기 전용 레이어)
- [ ] Backend Container 등록 (전략 엔진 접근)
- [ ] 캐시 DB 크기 관리 (오래된 데이터 정리)
- [ ] WebSocket 기반 실시간 snapshot 갱신 고려
- [ ] 스피너 디자인 테마 통합
