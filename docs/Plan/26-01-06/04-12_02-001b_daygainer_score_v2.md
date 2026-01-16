# 02-001b: Day Gainer 실시간 Score V2 계산

**작성일**: 2026-01-06  
**우선순위**: 🟡 Medium  
**상태**: ✅ 구현 완료 (2026-01-06)

---

## 개요

현재 Day Gainer(실시간 급등 종목)는 고정값 `score=50`, `score_v2=50`으로 표시됨.
DB의 일봉 데이터를 활용하여 진짜 **score_v2** 계산 필요.

**추가**: DB에 일봉이 없는 경우 Massive API에서 데이터를 가져와 DB에 삽입

---

## 현재 문제

| 데이터 소스 | 현재 score | 원인 |
|-------------|-----------|------|
| Daily Scan | ✅ 연속 v2 | `scanner.py`가 일봉 데이터로 계산 |
| Day Gainer | ❌ 고정값 50 | 일봉 데이터 접근 없음 |

---

## 해결 방안

### 데이터 흐름

```
[Day Gainer 탐지]
       ↓
[DB에서 일봉 조회]
       ↓
  ┌─ 있으면 → score_v2 계산
  └─ 없으면 → Massive API에서 fetch → DB 삽입 → score_v2 계산
```

### 활용 가능한 기존 메서드

| 메서드 | 파일 | 설명 |
|--------|------|------|
| `MarketDB.get_daily_bars()` | `database.py` | DB에서 일봉 조회 |
| `PolygonClient.fetch_grouped_daily()` | `polygon_client.py` | 특정 날짜 전체 종목 일봉 |
| `PolygonLoader.fetch_single_day()` | `polygon_loader.py` | 특정 날짜 데이터 fetch 후 DB 삽입 |

---

## 구현 계획

### 1. RealtimeScanner 초기화 수정

**파일**: `backend/core/realtime_scanner.py`

```diff
 def __init__(
     self,
     polygon_client: Any,
     ws_manager: Any,
+    db: Optional[Any] = None,
     ignition_monitor: Optional[Any] = None,
 ):
     self.polygon_client = polygon_client
     self.ws_manager = ws_manager
+    self.db = db
+    self.strategy = SeismographStrategy() if db else None
```

### 2. `_handle_new_gainer()` 수정 (핵심)

```python
async def _handle_new_gainer(self, item: Dict[str, Any]):
    ticker = item["ticker"]
    score, score_v2, stage = None, None, "Gainer"
    
    if self.db and self.strategy:
        try:
            # 1) DB에서 일봉 조회
            bars = await self.db.get_daily_bars(ticker, days=20)
            
            # 2) DB에 일봉이 부족하면 Massive API에서 fetch
            if not bars or len(bars) < 5:
                logger.info(f"📥 {ticker}: DB에 일봉 부족, Massive API에서 fetch...")
                await self._fetch_and_store_daily_bars(ticker, days=30)
                bars = await self.db.get_daily_bars(ticker, days=20)
            
            # 3) Score V2 계산
            if bars and len(bars) >= 5:
                data = [bar.to_dict() for bar in reversed(bars)]
                result = self.strategy.calculate_watchlist_score_detailed(ticker, data)
                score = result["score"]
                score_v2 = result["score_v2"]
                stage = result["stage"]
        except Exception as e:
            logger.warning(f"⚠️ {ticker} score 계산 실패: {e}")
```

### 3. Massive API fetch 헬퍼 메서드 추가

```python
async def _fetch_and_store_daily_bars(self, ticker: str, days: int = 30):
    """
    Massive API에서 특정 종목의 일봉 데이터를 가져와 DB에 삽입
    
    fetch_grouped_daily()는 전체 종목을 가져오므로,
    단일 종목만 필요할 때는 해당 종목만 필터링하여 저장
    """
    from datetime import datetime, timedelta
    from backend.data.polygon_loader import PolygonLoader
    
    try:
        # 최근 N 거래일 계산
        end_date = datetime.now() - timedelta(days=1)
        start_date = end_date - timedelta(days=days)
        trading_days = PolygonLoader.get_trading_days_between(start_date, end_date)
        
        stored_count = 0
        for date in trading_days[-10:]:  # 최근 10거래일만 (API 부하 감소)
            bars = await self.polygon_client.fetch_grouped_daily(date)
            for bar in bars:
                if bar.get("T") == ticker or bar.get("ticker") == ticker:
                    await self.db.insert_daily_bar(ticker, date, bar)
                    stored_count += 1
                    break
        
        logger.info(f"✅ {ticker}: {stored_count}개 일봉 저장됨")
    except Exception as e:
        logger.warning(f"⚠️ {ticker} 일봉 fetch 실패: {e}")
```

### 4. 서버 초기화에서 DB 주입

**파일**: `backend/api/main.py`

```python
scanner = initialize_realtime_scanner(
    polygon_client=polygon_client,
    ws_manager=ws_manager,
    db=db,  # [02-001b] DB 주입
)
```

---

## 수정 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `backend/core/realtime_scanner.py` | `db` 파라미터 추가, `_fetch_and_store_daily_bars()` 추가, `_handle_new_gainer` 수정 |
| `backend/api/main.py` | MarketDB 인스턴스 주입 |

---

## 예상 결과

| 상황 | 수정 전 | 수정 후 |
|------|--------|--------|
| DB에 일봉 있음 | score=50 | score_v2=67.5 (계산) |
| DB에 일봉 없음 | score=50 | API fetch → score_v2 계산 |
| API fetch 실패 | score=50 | ⚠️ 경고 표시 |

---

## 검증 계획

1. 백엔드 실행 후 새 Day Gainer 탐지 시 로그 확인
2. `📥 fetch` 로그가 표시되면 API에서 데이터 가져오는 중
3. GUI에서 Day Gainer Score가 v2 값 또는 ⚠️ 표시인지 확인

---

## Phase 6: 이모지(⚠️) 표시 지속 원인 분석

> **작성일**: 2026-01-06 03:47  
> **증상**: 구현 완료 후에도 Day Gainer Score가 ⚠️로 표시됨

### 6.1 근본 원인 분석

| 원인 | 설명 | 해결 방안 |
|------|------|----------|
| **백엔드 미실행** | GUI만 실행하면 WebSocket 연결 실패 → Watchlist 데이터 없음 | 백엔드 먼저 실행: `python -m backend` |
| **기존 Watchlist에 score_v2 없음** | 이전에 저장된 watchlist.json에 score_v2 필드가 없음 | 스캐너 재실행 또는 기존 데이터 마이그레이션 |
| **API fetch 실패/시간 초과** | Massive API 호출 실패 시 score_v2=None으로 설정 | API 키 확인, 네트워크 연결 확인 |
| **DB 일봉 부족** | 새 종목은 DB에 일봉이 없고, API fetch도 해당 종목 데이터가 없을 수 있음 | API에서 개별 종목 일봉 조회 메서드 추가 고려 |

### 6.2 데이터 흐름 진단

```
[백엔드]                                  [프론트엔드]
────────────────────────────────────────────────────────────────
RealtimeScanner._handle_new_gainer()
  └─ DB.get_daily_bars() → 일봉 없음
  └─ _fetch_and_store_daily_bars()
     └─ fetch_grouped_daily(date) → 전체 종목 중 해당 티커 없음
  └─ score_v2 = None  ←────────────────────────────┐
                                                   │
ws_manager.broadcast_watchlist()                   │
  └─ WATCHLIST:{"items": [{..., "score_v2": null}]}│
                                                   ↓
                                          ws_adapter.py
                                            └─ watchlist_updated.emit(items)
                                          
                                          watchlist_model.py
                                            └─ score_v2 is None → ⚠️ 표시
```

### 6.3 확인 방법

1. **백엔드 로그 확인**: 
   - `📥 fetch` 로그 표시 여부
   - `✅ 저장됨` 또는 `⚠️ 데이터를 찾을 수 없음` 로그
   - `📊 score_v2=XX.X` 로그 표시 여부

2. **watchlist.json 확인**:
   ```bash
   cat data/watchlist.json | python -m json.tool
   ```
   - `score_v2` 필드가 있는지 확인
   - 값이 숫자인지 `null`인지 확인

### 6.4 추가 수정 사항 (추후 고려)

| 개선안 | 설명 |
|--------|------|
| **개별 종목 일봉 API** | `fetch_grouped_daily` 대신 단일 종목 조회 API 사용 |
| ~~기존 Watchlist 마이그레이션~~ | ✅ Periodic Broadcast에서 자동 계산 구현됨 |
| ~~캐시 스토어 업데이트~~ | ✅ `save_watchlist()` 호출하여 영구 저장 구현됨 |

### 6.5 해결 구현 완료 (2026-01-06 03:51)

`_periodic_watchlist_broadcast()`에 Phase 6 로직 추가:

```python
# [Phase 6] score_v2 없는 항목 실시간 계산
score_v2 = item.get("score_v2")
if (score_v2 is None or score_v2 == 0) and ticker not in _score_v2_calculated:
    if self.db and self.strategy:
        bars = await self.db.get_daily_bars(ticker, days=20)
        if bars and len(bars) >= 5:
            result = self.strategy.calculate_watchlist_score_detailed(ticker, data)
            item["score_v2"] = result.get("score_v2")
            # ... 저장소에 영구 반영
```

**동작 원리**:
1. 매 1초마다 Watchlist 로드
2. score_v2가 없거나 0인 항목 탐지
3. DB에서 일봉 조회 → score_v2 계산
4. `save_watchlist()`로 영구 저장
5. GUI에 브로드캐스트

---

## Phase 7: 이중 이모지 시스템 (데이터 부족 구분)

> **작성일**: 2026-01-06 04:03  
> **목적**: 데이터 부족(IPO/신규)과 계산 오류를 구분하여 표시

### 7.1 이모지 분류

| 상황 | score_v2 값 | 이모지 | 의미 |
|------|-------------|--------|------|
| 일봉 5일 미만 | `-1` | 🆕 | 신규/IPO - 차후 모멘텀 전략 적용 |
| 계산 오류/실패 | `None` 또는 `0` | ⚠️ | 오류 - 확인 필요 |
| 정상 계산 | `> 0` | `65.3` | 매집 점수 |

### 7.2 구현 계획

**백엔드**: `realtime_scanner.py`
```python
if bars is None or len(bars) < 5:
    item["score_v2"] = -1  # 신규 종목 마커
    item["stage"] = "신규/IPO (데이터 부족)"
```

**프론트엔드**: `watchlist_model.py`
```python
if score_v2 == -1:
    return "🆕"  # 신규
elif score_v2 is None or score_v2 == 0:
    return "⚠️"  # 오류
else:
    return f"{score_v2:.1f}"
```

### 7.3 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `backend/core/realtime_scanner.py` | score_v2=-1 마커 추가 |
| `frontend/gui/watchlist_model.py` | 🆕/⚠️ 분기 처리 |

---

## Phase 8: 0점 전용 이모지 (매집 신호 없음)

> **작성일**: 2026-01-06 04:11  
> **목적**: score_v2=0 (매집 신호 미탐지)을 별도 이모지로 표시

### 8.1 원인 분석

문제 종목 (BVC, TMDE, VRME, ARBEW, MNTSW, FUSEW, INBS):
- DB에 20일치 일봉 있음 ✓
- 하지만 `calculate_watchlist_score_v2()` = **0.0**
- 4가지 매집 신호 중 어느 것도 탐지되지 않음
- Warrant(W 접미사) 종목은 특히 일반 주식과 패턴이 다름

### 8.2 최종 이모지 분류

| score_v2 값 | 이모지 | 의미 | 툴팁 |
|-------------|--------|------|------|
| `> 0` | `65.3` | 매집 점수 | - |
| `0` | ➖ | 신호 없음 | "매집 신호 없음 (Warrant 또는 패턴 미탐지)" |
| `-1` | 🆕 | 신규/IPO | "신규/IPO 종목 - 일봉 데이터 부족" |
| `None` | ⚠️ | 계산 오류 | "score_v2 계산 실패" |
