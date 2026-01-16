# 실시간 Gainers 스캐너 구현 계획서

**작성일**: 2026-01-05  
**버전**: v2.0  
**상태**: ✅ 구현 완료

---

## 1. 배경 및 문제점

### 현재 상황
SMXT가 40% 급등 중인데 Watchlist에 탐지되지 않음.

### 근본 원인
Masterplan (Section 7.3)에 정의된 **Source B (Real-Time Gainers)**가 구현되지 않음.

---

## 2. 구현 목표

| 목표 | 설명 |
|------|------|
| **실시간 Gainers 스캔** | Polygon Gainers API 1초 간격 조회 |
| **change_pct 필터 삭제** | 기존 0~5% 제한 완전 제거 |
| **자동 Watchlist 병합** | 신규 종목 자동 추가 + 실시간 GUI 업데이트 |

---

## 3. API 스펙

### Polygon Gainers API
```
GET https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/gainers
```

### 응답 데이터 (측정 완료)
| 항목 | 값 |
|------|-----|
| 응답 크기 | ~10KB |
| 종목 수 | 21개 |
| 주요 필드 | ticker, todaysChangePerc, day (OHLCV) |

### 부하 분석
| 간격 | 데이터량/분 | 평가 |
|------|------------|------|
| **1초** | **600KB/분** | ✅ 무시 가능 |

---

## 4. 상세 설계

### 4.1 새 모듈: `backend/core/realtime_scanner.py`

```python
class RealtimeScanner:
    """실시간 급등 종목 스캐너 (1초 폴링)"""
    
    def __init__(self, polygon_client, ws_manager):
        self.polygon_client = polygon_client
        self.ws_manager = ws_manager
        self.poll_interval = 1.0  # 1초
        self._running = False
        self._known_tickers: Set[str] = set()  # 이미 알고 있는 종목
    
    async def start(self):
        """1초 간격 폴링 루프 시작"""
        self._running = True
        while self._running:
            await self._poll_gainers()
            await asyncio.sleep(self.poll_interval)
    
    async def _poll_gainers(self):
        """Gainers API 조회 및 신규 종목 탐지"""
        gainers = await self.polygon_client.get_gainers()
        
        for item in gainers:
            ticker = item["ticker"]
            change_pct = item["todaysChangePerc"]
            
            # 신규 종목만 처리
            if ticker not in self._known_tickers:
                self._known_tickers.add(ticker)
                await self._handle_new_gainer(item)
    
    async def _handle_new_gainer(self, item):
        """신규 급등 종목 처리 → Watchlist 추가 + 브로드캐스트"""
        # 1. Watchlist에 추가
        # 2. WebSocket 브로드캐스트
        # 3. IgnitionMonitor에 등록
```

### 4.2 Polygon Client 확장

**파일**: `backend/data/polygon_client.py`

```python
async def get_gainers(self) -> List[Dict]:
    """Top Gainers 조회 (1초 폴링용 최적화)"""
    url = f"{self.base_url}/v2/snapshot/locale/us/markets/stocks/gainers"
    resp = await self._client.get(url, params={"apiKey": self.api_key})
    data = resp.json()
    
    # 필요한 필드만 추출 (메모리 최적화)
    return [
        {
            "ticker": t["ticker"],
            "change_pct": t.get("todaysChangePerc", 0),
            "price": t.get("day", {}).get("c", 0),
            "volume": t.get("day", {}).get("v", 0),
        }
        for t in data.get("tickers", [])
    ]
```

### 4.3 Universe Filter 제거

**파일**: `backend/strategies/seismograph.py`

```diff
- # 당일 변동률: 0% ~ 5% (아직 터지지 않은 종목)
- "change_pct_min": 0.0,
- "change_pct_max": 5.0,
+ # change_pct 제한 없음 (실시간 스캐너가 급등 종목도 포함)
```

---

## 5. 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                REALTIME GAINERS SCANNER (1s Polling)             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [asyncio loop] ─── 1초 ──▶ [RealtimeScanner._poll_gainers]     │
│                                        │                        │
│                                        ▼                        │
│                           [Polygon Gainers API]                 │
│                           ~10KB, 21 tickers                     │
│                                        │                        │
│                                        ▼                        │
│                        [신규 종목 탐지 (Set diff)]               │
│                                        │                        │
│                           ┌────────────┴────────────┐           │
│                           ▼                         ▼           │
│                   [Watchlist 추가]          [WebSocket 브로드캐스트]│
│                           │                         │           │
│                           ▼                         ▼           │
│                 [IgnitionMonitor 등록]      [GUI 실시간 업데이트]  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. 수정 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| **[NEW]** `backend/core/realtime_scanner.py` | 1초 폴링 스캐너 |
| `backend/data/polygon_client.py` | `get_gainers()` 메서드 추가 |
| `backend/server.py` | RealtimeScanner 초기화 및 시작 |
| `backend/strategies/seismograph.py` | `change_pct_max` 필터 삭제 |

---

## 7. 구현 순서

1. **`polygon_client.py`**: `get_gainers()` 메서드 추가
2. **`realtime_scanner.py`**: 신규 모듈 생성
3. **`server.py`**: RealtimeScanner 시작 로직 추가
4. **`seismograph.py`**: change_pct 필터 제거
5. **테스트**: 급등 종목 탐지 확인

---

## 8. 예상 결과

| 상황 | 수정 전 | 수정 후 |
|------|--------|--------|
| SMXT +40% 급등 | ❌ 탐지 안됨 | ✅ **1초 내 탐지** |
| 신규 급등 종목 | ❌ 놓침 | ✅ 실시간 Watchlist 추가 |
| Tier 2 승격 | ❌ 불가 | ✅ 자동 승격 |

---

## 9. 승인 요청

위 계획에 따라 구현을 진행해도 괜찮을까요?
