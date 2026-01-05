# Step 4.A.5: Realtime Gainers Scanner 구현

**작성일**: 2026-01-05  
**상태**: ✅ 완료

---

## 개요

Masterplan Section 7.3에 정의된 **Source B (Real-Time Gainers)**를 구현하였습니다. Polygon Gainers API를 1초 간격으로 폴링하여 실시간 급등 종목을 탐지하고 Watchlist에 자동 병합합니다.

### 문제점
- SMXT가 40% 급등 중인데 Watchlist에 탐지되지 않음
- 기존 Scanner는 일봉 기반으로 Pre-market 매집 종목만 탐지
- 장중 급등 종목을 실시간으로 캐치할 수 없었음

### 해결책
- 1초 폴링 기반 RealtimeScanner 구현
- 신규 급등 종목 자동 탐지 + Watchlist 병합
- IgnitionMonitor와 연동하여 실시간 모니터링

---

## 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| **[NEW]** `backend/core/realtime_scanner.py` | 1초 폴링 기반 급등 종목 스캐너 |
| `backend/data/polygon_client.py` | `get_gainers()` 메서드 추가 |
| `backend/server.py` | RealtimeScanner 초기화 및 시작/종료 로직 |

---

## 상세 변경 내용

### 1. `polygon_client.py`: `get_gainers()` 메서드

```python
async def get_gainers(self) -> list[dict]:
    """
    Top Gainers 조회 (1초 폴링용 최적화)
    
    Returns:
        list[dict]: 급등주 리스트 (최소 필드)
            - ticker: 종목 심볼
            - change_pct: 변동률 (%)
            - price: 현재가
            - volume: 거래량
    """
    gainers = await self.fetch_day_gainers()
    
    # 필요한 필드만 추출 (메모리 최적화)
    return [
        {
            "ticker": g["ticker"],
            "change_pct": g.get("todaysChangePerc", g.get("change_pct", 0)),
            "price": g.get("last_price", 0),
            "volume": g.get("volume", 0),
        }
        for g in gainers
    ]
```

### 2. `realtime_scanner.py`: 신규 모듈

주요 기능:
- `RealtimeScanner` 클래스: 1초 폴링 루프
- `_poll_gainers()`: Gainers API 조회
- `_handle_new_gainer()`: 신규 종목 처리 (Watchlist 추가, WebSocket 브로드캐스트)
- 싱글톤 패턴: `get_realtime_scanner()`, `initialize_realtime_scanner()`

### 3. `server.py`: 서버 통합

- `AppState`에 `realtime_scanner` 필드 추가
- `lifespan()` 시작 시 RealtimeScanner 초기화 및 시작
- 환경변수 `REALTIME_SCANNER_ENABLED=true` (기본값)로 활성화
- Shutdown 시 graceful stop

---

## 데이터 흐름

```
[asyncio loop] ─── 1초 ──▶ [RealtimeScanner._poll_gainers]
                                   │
                                   ▼
                      [Polygon Gainers API]
                      ~10KB, 21 tickers
                                   │
                                   ▼
                   [신규 종목 탐지 (Set diff)]
                                   │
                      ┌────────────┴────────────┐
                      ▼                         ▼
              [Watchlist 추가]          [WebSocket 브로드캐스트]
                      │                         │
                      ▼                         ▼
            [IgnitionMonitor 등록]      [GUI 실시간 업데이트]
```

---

## 예상 결과

| 상황 | 수정 전 | 수정 후 |
|------|--------|--------|
| SMXT +40% 급등 | ❌ 탐지 안됨 | ✅ **1초 내 탐지** |
| 신규 급등 종목 | ❌ 놓침 | ✅ 실시간 Watchlist 추가 |
| Tier 2 승격 | ❌ 불가 | ✅ 자동 승격 |

---

## 설정

환경변수로 제어:
- `REALTIME_SCANNER_ENABLED`: `true` (기본) / `false`
- `MASSIVE_API_KEY`: Polygon/Massive API 키 (필수)

---

## 관련 문서

- 계획서: `docs/Plan/steps/realtime_scanner_plan.md`
- Masterplan: Section 7.3 (Source B)
