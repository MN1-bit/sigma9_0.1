# Issue Report: Realtime Scanner 통합 이슈

**작성일**: 2026-01-05  
**버전**: v1.1  
**우선순위**: 🔴 High  
**상태**: ✅ Fix 완료 (2026-01-06)

---

## 이슈 목록

### Issue 6.1: Watchlist 컬럼 데이터 누락 🔴

**증상**: DolVol, Score, Ign 값이 일부 종목에서만 표시됨

**Root Cause 분석**:

`realtime_scanner.py` L225-245에서 생성되는 `watchlist_item`에 `dollar_volume` 필드가 없음:

```python
watchlist_item = {
    "ticker": ticker,
    "change_pct": change_pct,
    "price": price,
    "volume": volume,
    "source": "realtime_gainer",
    "score": 50.0,  # 기본값
    # ❌ dollar_volume 필드 없음!
}
```

`dashboard.py` L1349-1354에서 `dollar_volume` 계산 시도:
```python
dollar_volume = item.get("dollar_volume", 0) or item.get("avg_volume", 0) * item.get("last_close", 0)
# → avg_volume, last_close도 없어서 0 반환
```

**해결 방안**:
- `realtime_scanner.py` `_handle_new_gainer()`에 `dollar_volume` 필드 추가
- `dollar_volume = price * volume` 계산

---

### Issue 6.2: Day Gainer 종목 깜빡임 🔴 (Critical)

**증상**: Day Gainer로 받아온 종목이 수초간 사라졌다가 나타났다가 반복

**Root Cause 분석**:

1. **Watchlist 덮어쓰기 충돌**: 

`realtime_scanner.py` L247-252:
```python
self._watchlist.append(watchlist_item)  # 자체 리스트에만 추가

from backend.data.watchlist_store import save_watchlist
save_watchlist(self._watchlist)  # ❌ 자체 리스트로 전체 덮어쓰기!
```

`scheduler.py` L238:
```python
await manager.broadcast_watchlist(result)  # 주기적 Watchlist 갱신
```

→ RealtimeScanner가 자체 `_watchlist` (Gainer만 포함)로 전체 덮어쓰기 → Scheduler가 원본 Watchlist로 다시 덮어쓰기 → 반복

2. **동기화 부재**:
   - RealtimeScanner의 `_watchlist`와 WatchlistStore의 데이터가 분리됨
   - 병합(merge) 로직 없이 각자 덮어쓰기

**해결 방안**:
- `realtime_scanner.py`에서 기존 Watchlist를 **읽어온 후 병합**하도록 수정
- 또는 Watchlist 갱신을 단일 채널로 통합

**수정 코드**:
```python
# realtime_scanner.py 수정
async def _handle_new_gainer(self, item):
    # ...
    # 2. Watchlist 병합 저장 (덮어쓰기 대신)
    try:
        from backend.data.watchlist_store import load_watchlist, save_watchlist
        current = load_watchlist()  # 기존 Watchlist 로드
        
        # 중복 체크 후 추가
        existing_tickers = {w.get("ticker") for w in current}
        if ticker not in existing_tickers:
            current.append(watchlist_item)
            save_watchlist(current)
            self._watchlist = current  # 동기화
    except Exception as e:
        logger.warning(f"⚠️ Watchlist 저장 실패: {e}")
```

---

### Issue 6.3: Hot Zone 승격 실패 🟠

**증상**: 어떤 종목도 Tier 2 Hot Zone으로 승격되지 않음

**Root Cause 분석**:

`dashboard.py` L1427-1435:
```python
if score >= 70:
    # ...
    if passed_filter:
        self._promote_to_tier2(ticker, score)
```

**문제점**:
- Realtime Gainer 종목은 기본 `score=50`으로 추가됨
- IgnitionMonitor가 Gainer 종목을 모니터링하지 않거나, Ignition 계산에 필요한 Context가 부족
- `add_ticker()` 메서드가 IgnitionMonitor에 없음 (`hasattr` 체크에서 False)

---

## Hot Zone 승격 기준 재설계 (기존 매매 로직 차용)

### 철학: "상승할 가능성 × 상승 가능 배율"

Hot Zone은 단순 고수익(change_pct)이 아닌, **"오늘 내 추가 상승 가능성이 높은 종목"**을 선별해야 함.

### 기존 로직에서 차용 가능한 요소

#### 1. Seismograph - Accumulation Score (매집 점수)

| 신호 | 의미 | 점수 |
|-----|------|------|
| Volume Dry-out | 폭풍 전 고요 | 10 |
| OBV Divergence | 스마트 머니 유입 | 30 |
| Accumulation Bar | 매집 완료 | 50/70 |
| **Tight Range (VCP)** | **🔥 폭발 임박** | **80/100** |

→ **Stage 4 (Tight Range)** 종목은 "폭발 직전" 상태

#### 2. Seismograph - Ignition Score (폭발 임박 점수)

| 신호 | Weight | 의미 |
|-----|--------|------|
| Tick Velocity | 35% | 체결 속도 폭발 |
| Volume Burst | 30% | 거래량 급증 |
| Price Break | 20% | 저항선 돌파 |
| Buy Pressure | 15% | 매수세 우위 |

→ **Ignition ≥ 70** = 진입 시그널

#### 3. MEP3.1 - Ready Score (임박 강도)

$$
R_s(t) = rank(OFI) + rank(TickIntensity) + rank(VolumeAccel)
$$

→ "얼마나 빨리 움직일 준비가 되었나"

#### 4. MEP3.1 - Tradeability Score

$$
T_s(t) = Ready - Cost
$$

→ "먹힘 가능성" = 임박 강도 - 거래 불리(스프레드, 변동폭)

---

### 제안: Hot Zone 승격 조건 (우선순위)

```python
# Hot Zone 승격 조건 (OR 로직)
def should_promote_to_tier2(ticker, data):
    # 1. Ignition Score ≥ 70 (기존 유지 - 폭발 임박)
    if data.get("ignition_score", 0) >= 70:
        return True, "🎯 Ignition Ready"
    
    # 2. Accumulation Stage 4 (Tight Range) - VCP 패턴
    if data.get("stage_number", 0) >= 4:
        return True, "🔥 VCP Breakout Imminent"
    
    # 3. zenV-zenP Divergence (기존 4.A.4 로직)
    #    High Volume + Low Price Change = 매집 중
    zenV = data.get("zenV", 0)
    zenP = data.get("zenP", 0)
    if zenV >= 2.0 and zenP < 0.5:
        return True, "📊 Volume-Price Divergence"
    
    # 4. High Accumulation Score (≥ 80) + Day Gainer
    if data.get("score", 0) >= 80 and data.get("source") == "realtime_gainer":
        return True, "⭐ High Score Gainer"
    
    return False, ""
```

**핵심 변경**:
- `change_pct >= 20%` 제거 (단순 고수익은 기준이 아님)
- `stage_number >= 4` 추가 (VCP 패턴 = 폭발 임박)
- `zenV/zenP Divergence` 활용 (이미 구현됨)
- `Accumulation Score >= 80` + Gainer 조합

---

### 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `realtime_scanner.py` | `stage_number` 필드 추가, 기본값 조정 |
| `dashboard.py` | `_on_ignition_update()`에 새 승격 조건 추가 |

---

### Issue 6.4: Score 계산 고도화 (차후 구현) 🟢

**요청**: 현재 step(100, 80, 70, 50, 30, 10) 방식을 더 dynamic한 수식으로 변경

**현재 로직** (`seismograph.py`):
```python
if has_tight_range and has_obv_divergence:
    return 100.0
elif has_tight_range:
    return 80.0
# ...
```

**개선 방향**:
- 개별 신호 강도를 0~1로 정규화
- 가중합 기반 연속적 점수 (0~100)
- 시간 decay 적용

**우선순위**: 🟢 Low (Issue 6.1~6.3 해결 후)

---

## 수정 계획

| Priority | Issue | 수정 파일 | 예상 LOC |
|----------|-------|-----------|----------|
| **P0** | 6.2 깜빡임 | `realtime_scanner.py` | ~20 |
| **P1** | 6.1 데이터 누락 | `realtime_scanner.py` | ~5 |
| **P2** | 6.3 Hot Zone | `realtime_scanner.py` + `dashboard.py` | ~15 |
| 차후 | 6.4 Score 고도화 | `seismograph.py` | ~50 |

---

## 수정 코드 상세

### P0: Issue 6.2 수정 (`realtime_scanner.py`)

```python
async def _handle_new_gainer(self, item: Dict[str, Any]) -> None:
    ticker = item["ticker"]
    change_pct = item.get("change_pct", 0)
    price = item.get("price", 0)
    volume = item.get("volume", 0)
    
    # [Issue 6.1 Fix] dollar_volume 추가
    dollar_volume = price * volume
    
    watchlist_item = {
        "ticker": ticker,
        "change_pct": change_pct,
        "price": price,
        "volume": volume,
        "dollar_volume": dollar_volume,  # [NEW]
        "source": "realtime_gainer",
        "discovered_at": datetime.now().isoformat(),
        "score": 50.0,
        "stage": "Gainer (실시간)",
        "stage_number": 3,
        "signals": {...},
        "can_trade": True,
    }
    
    # [Issue 6.2 Fix] 기존 Watchlist와 병합
    try:
        from backend.data.watchlist_store import load_watchlist, save_watchlist
        current = load_watchlist()
        existing_tickers = {w.get("ticker") for w in current}
        
        if ticker not in existing_tickers:
            current.append(watchlist_item)
            save_watchlist(current)
            self._watchlist = current  # 동기화
        else:
            self._watchlist = current
    except Exception as e:
        logger.warning(f"⚠️ Watchlist 저장 실패: {e}")
    
    # ... (나머지 동일)
```

### P2: Issue 6.3 수정 - Hot Zone 승격 조건 구현

#### 1. `realtime_scanner.py` - `stage_number` 필드 추가

```python
watchlist_item = {
    "ticker": ticker,
    "change_pct": change_pct,
    "price": price,
    "volume": volume,
    "dollar_volume": price * volume,  # [Issue 6.1]
    "source": "realtime_gainer",
    "discovered_at": datetime.now().isoformat(),
    "score": 50.0,
    "stage": "Gainer (실시간)",
    "stage_number": 3,  # Day Gainer는 Stage 3 (Accumulation Bar 수준)
    # ...
}
```

#### 2. `dashboard.py` - `_on_ignition_update()` 수정

```python
def _on_ignition_update(self, data: dict):
    ticker = data.get("ticker", "")
    score = data.get("score", 0.0)
    passed_filter = data.get("passed_filter", True)
    
    # ... 기존 코드 ...
    
    # [Issue 6.3 Fix] 새로운 Hot Zone 승격 조건
    should_promote, reason = self._check_tier2_promotion(ticker, score, passed_filter)
    if should_promote:
        self._promote_to_tier2(ticker, score)
        self.log(f"[TIER2] {reason}: {ticker}")

def _check_tier2_promotion(self, ticker: str, ignition_score: float, passed_filter: bool) -> tuple:
    """Hot Zone 승격 조건 검사 (복합 조건)"""
    
    # 1. Ignition Score ≥ 70 (기존 유지)
    if ignition_score >= 70 and passed_filter:
        return True, "🎯 Ignition Ready"
    
    # 2. Watchlist에서 stage_number 확인
    for row in range(self.watchlist_table.rowCount()):
        item = self.watchlist_table.item(row, 0)
        if item and item.text() == ticker:
            # Stage 4 (VCP) 종목은 직접 승격
            stage_num = self._watchlist_data.get(ticker, {}).get("stage_number", 0)
            if stage_num >= 4:
                return True, "🔥 VCP Breakout"
            break
    
    # 3. zenV-zenP Divergence (기존 4.A.4 로직 활용)
    if ticker in self._tier2_cache:
        item = self._tier2_cache[ticker]
        if item.zenV >= 2.0 and item.zenP < 0.5:
            return True, "📊 Divergence"
    
    return False, ""
```

---

## 관련 파일 경로

| 파일 | 전체 경로 |
|------|----------|
| RealtimeScanner | `backend/core/realtime_scanner.py` |
| Dashboard | `frontend/gui/dashboard.py` |
| WatchlistStore | `backend/data/watchlist_store.py` |
| IgnitionMonitor | `backend/core/ignition_monitor.py` |
| Seismograph | `backend/strategies/seismograph.py` |

---

## 참고 문서

- Hot Zone 설계: `docs/Plan/steps/step_4.a.4_plan.md`
- Seismograph 전략: `docs/strategy/seismograph_strategy_guide.md`
- MEP3.1: `docs/strategy/MEP3.1/03_prime.md`
- RealtimeScanner 계획: `docs/Plan/steps/realtime_scanner_plan.md`

---

## 2차 조사 결과 (2026-01-06)

### 🔍 문제점 재분석

첫 번째 수정 후에도 이슈가 지속되는 이유:

#### 1. Watchlist 덮어쓰기 경로 복수 존재

| 위치 | 코드 | 문제점 |
|------|------|--------|
| `realtime_scanner.py` L252 | `save_watchlist(self._watchlist)` | ✅ 수정됨 (병합) |
| `server.py` L320 | `save_watchlist(results)` | 🔴 **전체 덮어쓰기** |
| `scheduler.py` L238 | `broadcast_watchlist(result)` | ⚠️ 별도 경로 |

→ **해결**: `server.py`도 `merge_watchlist()` 사용하도록 수정

#### 2. GUI에 Watchlist 캐시 부재

`dashboard.py`의 `_check_tier2_promotion()`에서:
- `data.get("stage_number")` 참조 → **Ignition 데이터에 없음**
- `data.get("source")` 참조 → **Ignition 데이터에 없음**

→ **해결**: `_update_watchlist_panel()`에서 Watchlist 캐시 저장 후 승격 조건에서 참조

### 📝 추가 수정 사항

#### 1. `watchlist_store.py` - `merge_watchlist()` 함수 추가

```python
def merge_watchlist(new_items: List[Dict], update_existing: bool = True) -> List[Dict]:
    """기존 Watchlist와 새 항목 병합 (덮어쓰기 대신)"""
    current = load_watchlist()
    existing_map = {item.get("ticker"): i for i, item in enumerate(current)}
    
    for new_item in new_items:
        ticker = new_item.get("ticker")
        if ticker in existing_map:
            if update_existing:
                current[existing_map[ticker]].update(new_item)
        else:
            current.append(new_item)
    
    save_watchlist(current)
    return current
```

#### 2. `server.py` L302 - 병합 로직 적용

```python
# Before
save_watchlist(results)

# After
from backend.data.watchlist_store import merge_watchlist
watchlist = merge_watchlist(results, update_existing=True)
```

#### 3. `dashboard.py` - Watchlist 캐시 추가

```python
# _update_watchlist_panel()에서
self._watchlist_data = {}  # ticker -> item dict
for item in items:
    ticker = item.get("ticker") or item.ticker
    self._watchlist_data[ticker] = item

# _check_tier2_promotion()에서
watchlist_entry = self._watchlist_data.get(ticker, {})
stage_number = watchlist_entry.get("stage_number", 0)
source = watchlist_entry.get("source", "")
```

### ✅ 수정 완료 항목

- [x] `watchlist_store.py` - `merge_watchlist()` 추가
- [x] `server.py` - 병합 로직 적용
- [x] `dashboard.py` - Watchlist 캐시 추가
- [ ] 서버 재시작 및 테스트
