# 14-005: TickerInfo 서비스 아키텍처 리팩터링

> **작성일**: 2026-01-13 12:10
> **우선순위**: 높음 | **예상 소요**: 6h | **위험도**: 높음

---

## 1. 목표

TickerInfo 데이터 처리를 **Backend 중심 아키텍처**로 전환:
- Backend: API 호출 + 캐싱 + 전략 계산에 활용
- Frontend: DB에서 캐시 데이터 조회만

### 해결되는 문제들

| 문제 | 현재 | 개선 후 |
|------|------|---------|
| 자동매매 전략에서 시총/Float 필요 | 별도 API 호출 (중복) | DB 캐시에서 즉시 조회 |
| Frontend 초기 로드 느림 | API 대기 | DB 캐시에서 즉시 로드 |
| 캐시 불일치 | Frontend 로컬 캐시만 | 중앙 DB 단일 소스 |
| Dynamic 데이터 캐시 없음 | 매번 API 호출 | TTL 기반 캐시 |

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

### 제안 (Backend 중심)

```
[Frontend]                              [Backend (AWS)]
    │                                        │
    └── DB 조회 ◄──────── 공유 DB ◄───────── TickerInfoService
                              │               │
                              └── (캐시) ◄─── Massive API
                                              │
                              전략 엔진 ◄─────┘ (즉시 접근 가능)
```

---

## 3. 캐싱 전략 전면 재설계

### 현재 캐시 정책

| 카테고리 | 현재 TTL | 비고 |
|----------|----------|------|
| profile | 7일 | ✅ |
| float | 1일 | ✅ |
| financials | 90일 | ✅ |
| **snapshot** | 0 (없음) | ❌ 매번 API |
| **short_interest** | 0 (없음) | ❌ 매번 API |
| **short_volume** | 0 (없음) | ❌ 매번 API |
| **news** | 0 (없음) | ❌ 매번 API |

### 제안 캐시 정책 (전체 적용)

| 카테고리 | 제안 TTL | 근거 |
|----------|----------|------|
| profile | 7일 | 잘 변하지 않음 |
| float | 1일 | 분기별 갱신 |
| financials | 90일 | 분기 보고서 |
| filings | 1일 | 공시는 하루 단위 |
| dividends | 7일 | 배당 일정 |
| splits | 30일 | 드문 이벤트 |
| related | 7일 | 잘 변하지 않음 |
| ipo | 영구 | 불변 |
| **snapshot** | **5분** | 가격 변동 반영 |
| **short_interest** | **1일** | 일별 갱신 |
| **short_volume** | **1일** | 일별 갱신 |
| **news** | **30분** | 뉴스 빈도 |

---

## 4. 기존 솔루션 검색 결과

| 솔루션 | 출처 | 채택 여부 | 사유 |
|--------|------|----------|------|
| Redis 캐시 | 일반적 패턴 | ❌ 미채택 | 현재 SQLite로 충분 |
| SQLite WAL mode | SQLite 공식 | ✅ 채택 | 동시 읽기/쓰기 최적화 |
| Backend 스케줄러 | APScheduler | ✅ 채택 | 주기적 캐시 갱신 |

---

## 5. 실행 계획

### Step 1: DB 위치 변경 및 공유 설정

**현재**: `data/ticker_info_cache.db` (프로젝트 루트, Frontend 접근)
**변경**: 동일 위치 유지, Backend에서 쓰기 + Frontend에서 읽기

```python
# backend/data/ticker_info_service.py
DB_PATH = Path(__file__).parent.parent.parent / "data" / "ticker_info_cache.db"
```

### Step 2: Backend에서 TickerInfoService 활성화

**현재**: Frontend에서 직접 서비스 인스턴스화
**변경**: Backend Container에 등록, 전략 엔진에서 사용 가능

```python
# backend/container.py
class Container:
    ticker_info_service = providers.Singleton(
        TickerInfoService,
        api_key=config.MASSIVE_API_KEY,
        db_path="data/ticker_info_cache.db",
    )
```

### Step 3: Frontend 조회 레이어 분리

Frontend는 DB에서 직접 읽기만:

```python
# frontend/services/ticker_info_reader.py
class TickerInfoReader:
    """읽기 전용 티커 정보 조회 (캐시에서만)."""
    
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
    
    def get_ticker_info(self, ticker: str) -> Optional[TickerInfo]:
        """DB 캐시에서 티커 정보 조회. 없으면 None."""
        # 캐시에서만 조회, API 호출 없음
```

### Step 4: Dynamic 데이터 캐시 정책 적용

```python
# REFRESH_POLICY 업데이트
REFRESH_POLICY: dict[str, int] = {
    # ... 기존 ...
    # Dynamic → 캐시 적용
    "snapshot": 5 * 60,       # 5분
    "short_interest": 24 * 3600,  # 1일
    "short_volume": 24 * 3600,    # 1일
    "news": 30 * 60,          # 30분
}
```

### Step 5: Backend 스케줄러로 주기적 갱신

```python
# backend/startup/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

async def refresh_watchlist_ticker_info():
    """Watchlist 티커들의 캐시 갱신."""
    service = get_container().ticker_info_service()
    for ticker in watchlist_tickers:
        await service.get_ticker_info(ticker, force_refresh=True)

scheduler.add_job(refresh_watchlist_ticker_info, 'interval', minutes=5)
```

### Step 6: TickerInfoWindow 수정

```python
# frontend/gui/ticker_info_window.py
class TickerInfoWindow:
    def __init__(self):
        # 서비스 대신 Reader 사용
        self._reader = TickerInfoReader(DB_PATH)
    
    def load_ticker(self, ticker: str):
        # DB에서 즉시 로드 (캐시된 데이터)
        info = self._reader.get_ticker_info(ticker)
        if info:
            self._update_ui(info)
        else:
            self._show_no_cache_message()
```

---

## 6. 영향 분석

### 변경 대상 파일

| 파일 | 변경 유형 | 영향도 |
|------|----------|--------|
| `backend/data/ticker_info_service.py` | 캐시 정책 수정 | 중간 |
| `backend/container.py` | 서비스 등록 | 낮음 |
| `backend/startup/scheduler.py` | 신규 생성 | 낮음 |
| `frontend/services/ticker_info_reader.py` | 신규 생성 | 중간 |
| `frontend/gui/ticker_info_window.py` | 서비스→Reader 전환 | 높음 |

### 영향받는 모듈

- **Backend 전략 엔진**: 이제 캐시 데이터 접근 가능 (개선)
- **Frontend Dashboard**: 변경 없음

---

## 7. 검증 계획

| 검증 항목 | 방법 | 기대 결과 |
|-----------|------|-----------|
| Backend 캐시 쓰기 | 서버 시작 후 DB 확인 | 테이블에 데이터 저장 |
| Frontend 캐시 읽기 | TickerInfo 창 열기 | DB에서 즉시 로드 |
| 캐시 만료 갱신 | 5분 대기 후 snapshot 확인 | 자동 갱신 |
| 전략 엔진 접근 | 전략 코드에서 float 조회 | 즉시 반환 |

---

## 8. 롤백 계획

1. Frontend에서 TickerInfoService 직접 사용으로 복원
2. Reader 클래스 삭제
3. Backend scheduler 비활성화

---

## 9. 후속 작업

- [ ] Watchlist 외 티커 캐시 정책 (온디맨드 vs 선제적)
- [ ] 캐시 DB 크기 관리 (오래된 데이터 정리)
- [ ] Frontend↔Backend 실시간 동기화 (WebSocket 푸시 고려)
