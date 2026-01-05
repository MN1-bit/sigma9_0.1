# Issue Report: Watchlist 데이터 리프레시 시 소실

**작성일**: 2026-01-06  
**버전**: v1.0  
**우선순위**: 🟡 High  
**상태**: ✅ 구현 완료

---

## 문제 설명

### 증상
- Watchlist Refresh 시 `dollar_volume`, `score`, `ignition` 값이 **일부 종목에서 사라짐**
- 특히 Day Gainer로 추가된 종목에서 발생
- 값이 있다가도 다음 갱신에서 사라지는 **불안정한** 동작

### 기대 동작
1. 모든 Watchlist 종목에 대해 실시간 데이터 유지
2. **1초 간격**으로 `dollar_volume`, `score`, `ignition` 재계산/업데이트
3. Refresh 시에도 기존 값 보존 또는 재계산

---

## 현재 데이터 흐름 분석

### Watchlist 데이터 소스

```
[Backend]
  ├── Scanner → score, stage, stage_number
  ├── RealtimeScanner → price, volume, change_pct, dollar_volume
  └── IgnitionMonitor → ignition_score

[Frontend]
  └── dashboard.py
        ├── _update_watchlist_panel() → GUI 테이블 업데이트
        ├── _ignition_cache → ticker → ignition_score
        └── _price_cache → ticker → current_price
```

### 문제 지점

| 데이터 | 소스 | 업데이트 주기 | 문제 |
|--------|------|--------------|------|
| `dollar_volume` | RealtimeScanner | 탐지 시 1회 | ❌ 갱신 안됨 |
| `score` | Scanner | 스캔 시 1회 | ⚠️ Day Gainer는 기본값 50 |
| `ignition` | IgnitionMonitor | WebSocket 실시간 | ✅ 정상 (캐시 사용) |

---

## 해결 방안

### 목표
- **1초 간격**으로 모든 Watchlist 종목의 핵심 데이터 업데이트
- Backend에서 데이터 누락 시 **사용자에게 경고 표시** (숨기지 않음)
- GUI가 최신 데이터를 항상 표시하도록 보장

### 설계 원칙

> ⚠️ **Fallback 구현하지 않음**: Backend에서 정보 누락 시 사용자가 알 수 있어야 함.  
> 캐시로 숨기지 않고 **경고 표시**로 문제를 명시적으로 드러냄.

### 방안: Backend 주기적 브로드캐스트 + Frontend 경고 표시

#### 1. Backend: 1초 주기 Watchlist 브로드캐스트

```python
# backend/core/realtime_scanner.py
async def _periodic_watchlist_broadcast(self):
    """1초마다 전체 Watchlist를 GUI에 브로드캐스트"""
    while self._running:
        await asyncio.sleep(1.0)
        
        # 최신 Watchlist 로드
        watchlist = load_watchlist()
        
        # 실시간 가격/볼륨으로 dollar_volume 재계산
        for item in watchlist:
            ticker = item.get("ticker")
            if ticker in self._latest_prices:
                price, volume = self._latest_prices[ticker]
                item["dollar_volume"] = price * volume
        
        # 브로드캐스트
        await self.ws_manager.broadcast_watchlist(watchlist)
```

#### 2. Frontend: 데이터 누락 시 경고 표시

```python
# frontend/gui/dashboard.py
def _update_watchlist_panel(self, items):
    for item in items:
        ticker = item.get("ticker") or item.ticker
        
        # DolVol 표시 (누락 시 경고)
        dollar_volume = item.get("dollar_volume", 0)
        if dollar_volume > 0:
            dolvol_item = NumericTableWidgetItem(self._format_dollar_volume(dollar_volume), dollar_volume)
        else:
            dolvol_item = QTableWidgetItem("⚠️")  # 경고 표시
            dolvol_item.setToolTip("Dollar Volume 데이터 없음")
            dolvol_item.setForeground(QColor(255, 165, 0))  # 주황색
```

---

## 구현 계획

### Phase 1: Backend 주기적 브로드캐스트

| 파일 | 변경 내용 |
|------|----------|
| `realtime_scanner.py` | `_periodic_watchlist_broadcast()` 메서드 추가 |
| `realtime_scanner.py` | `start()`에서 브로드캐스트 태스크 시작 |
| `realtime_scanner.py` | `_latest_prices` 딕셔너리 추가 (실시간 가격 캐시) |

### Phase 2: Frontend 경고 표시

| 파일 | 변경 내용 |
|------|----------|
| `dashboard.py` | `_update_watchlist_panel()`에서 누락 데이터 경고 표시 |
| `dashboard.py` | ToolTip으로 누락 원인 표시 |

---

## 예상 결과

### Before
```
Ticker | Change | DolVol | Score | Ign
SMXT   | +15.2% | -      | -     | 🔥72
ABCD   | +8.3%  | 2.5M   | 65    | -
```

### After (1초마다 갱신)
```
Ticker | Change | DolVol | Score | Ign
SMXT   | +15.3% | 1.8M   | 50    | 🔥73
ABCD   | +8.4%  | 2.6M   | 65    | 🔥45
```

---

## 검증 계획

1. GUI 시작 → Watchlist 50개 로드
2. Day Gainer 탐지 → 51개 표시
3. **1초 대기** → 모든 컬럼에 값 표시되는지 확인
4. 10초 관찰 → 값이 사라지지 않는지 확인

---

## 관련 이슈

- `01-001_realtime_scanner_integration.md` (Issue 6.1: DolVol 누락)
- `01-002_daygainer_watchlist_merge.md` (Day Gainer 병합)

---

## Phase 3: 추가 원인 분석 (2026-01-06 01:00)

**상태**: 🔍 분석 중

### 증상
Phase 1, 2 구현 후에도 `dollar_volume`, `score` 등이 GUI에서 빈칸(⚠️)으로 표시됨.

### 원인 분석

#### 1. `_latest_prices` 캐시 범위 제한 문제

```
[현재 구현]
_poll_gainers() → Gainers API 호출 → 반환된 종목만 _latest_prices에 저장

[문제점]
- Gainers API는 상위 ~20개 급등주만 반환
- 기존 Watchlist의 50+개 종목은 Gainers에 포함되지 않음
- → 대부분의 종목에 대해 _latest_prices 캐시가 비어있음
- → hydration 실패 → dollar_volume = 0 → ⚠️ 표시
```

#### 2. Watchlist 저장소 데이터 문제

```
[데이터 흐름]
Scanner 결과 → watchlist_store → load_watchlist() → broadcast

[잠재적 문제]
- Scanner가 저장할 때 dollar_volume 필드를 포함하지 않을 수 있음
- 또는 저장 시 dollar_volume이 0으로 저장됨
```

#### 3. score가 0인 이유

```
[현재 상황]
- Source A (Scanner) 결과의 score는 정상적으로 계산됨
- Source B (Day Gainer)는 기본값 score=50으로 설정됨
- 하지만 GUI에서 score=0으로 표시됨

[추정 원인]
- REST API 초기 로드 시 score 필드가 누락될 수 있음
- 또는 저장소에서 score가 저장되지 않음
```

### 근본 해결 방안

#### Option A: Hydration 소스 확장
`_latest_prices`를 Gainers API뿐 아니라 다른 소스(저장소, REST API)에서도 채우기

```python
# 브로드캐스트 시 저장소의 기존 데이터 활용
async def _periodic_watchlist_broadcast(self):
    watchlist = load_watchlist()
    
    for item in watchlist:
        ticker = item.get("ticker")
        
        # 1. 실시간 캐시 우선
        if ticker in self._latest_prices:
            price, volume = self._latest_prices[ticker]
            item["dollar_volume"] = price * volume
        # 2. 저장소의 기존 값 보존 (덮어쓰지 않음)
        elif item.get("dollar_volume", 0) == 0:
            # 기존 price/volume으로 계산 시도
            price = item.get("price", 0)
            volume = item.get("volume", 0)
            if price > 0 and volume > 0:
                item["dollar_volume"] = price * volume
```

#### Option B: 저장소 데이터 무결성 보장
Scanner/Scheduler가 저장할 때 모든 필드가 포함되도록 보장

#### Option C: REST API 응답 확인
초기 Watchlist 로드 시 `dollar_volume`, `score` 필드 포함 여부 확인

### 다음 단계

1. [x] `load_watchlist()` 반환 데이터에 `dollar_volume`, `score` 필드 확인
2. [x] Scanner 저장 로직에서 필드 포함 여부 확인
3. [ ] Hydration 로직 개선 (저장소 기존 값 보존)

---

## Phase 3.1: 근본 원인 발견 (2026-01-06 01:03)

**상태**: ✅ 원인 발견

### 핵심 원인: `WatchlistItem` Dataclass 필드 누락

```python
# frontend/services/backend_client.py (Line 50-74)
@dataclass
class WatchlistItem:
    ticker: str
    score: float
    stage: str
    last_close: float = 0.0
    change_pct: float = 0.0
    avg_volume: float = 0.0  # ← dollar_volume 필드가 없음!
    
    @classmethod
    def from_dict(cls, data: dict) -> "WatchlistItem":
        return cls(
            ticker=data.get("ticker", ""),
            score=data.get("score", 0),
            stage=data.get("stage", ""),
            last_close=data.get("last_close", 0),
            change_pct=data.get("change_pct", 0),
            avg_volume=data.get("avg_volume", 0)  # ← dollar_volume 파싱 안함!
        )
```

### 문제 흐름

```
Backend → {"ticker": "SMXT", "dollar_volume": 1800000, "score": 50, ...}
    ↓
WatchlistItem.from_dict() → dollar_volume 필드 무시
    ↓
_update_watchlist_panel() → getattr(item, 'dollar_volume', 0) = 0
    ↓
GUI → ⚠️ (또는 빈칸) 표시
```

### 해결 방안

#### Option 1: WatchlistItem에 dollar_volume 필드 추가 (권장)

```python
@dataclass
class WatchlistItem:
    ticker: str
    score: float
    stage: str
    last_close: float = 0.0
    change_pct: float = 0.0
    avg_volume: float = 0.0
    dollar_volume: float = 0.0  # [NEW] 추가
    price: float = 0.0  # [NEW] 추가
    volume: float = 0.0  # [NEW] 추가
    
    @classmethod
    def from_dict(cls, data: dict) -> "WatchlistItem":
        return cls(
            ticker=data.get("ticker", ""),
            score=data.get("score", 0),
            stage=data.get("stage", ""),
            last_close=data.get("last_close", 0),
            change_pct=data.get("change_pct", 0),
            avg_volume=data.get("avg_volume", 0),
            dollar_volume=data.get("dollar_volume", 0),  # [NEW]
            price=data.get("price", 0),  # [NEW]
            volume=data.get("volume", 0),  # [NEW]
        )
```

#### Option 2: Dictionary 직접 사용

`WatchlistItem` 변환 없이 raw dictionary를 직접 사용하도록 변경

### 구현 위치

| 파일 | 변경 |
|------|------|
| `frontend/services/backend_client.py` | WatchlistItem 필드 추가 |

---

## Phase 4: 정렬 시 데이터 소실 (2026-01-06 01:14)

**상태**: 🔍 분석 중

### 증상
- Watchlist 테이블에서 정렬(DolVol, Change% 등으로)하면 데이터가 사라짐
- 초기 로드 시에는 정상 표시됨

### 원인 분석

#### Qt QTableWidget 정렬 동작

```python
# frontend/gui/dashboard.py (Line 642)
self.watchlist_table.setSortingEnabled(True)
```

**문제 흐름:**

```
사용자가 컬럼 헤더 클릭 → 정렬 활성화
    ↓
Qt가 내부적으로 행 재배열
    ↓
_update_watchlist_panel()이 호출될 때:
    1. setRowCount(0) → 초기화
    2. setRowCount(len(items)) → 행 추가
    3. setItem(row, col, item) → 데이터 삽입
        ↓
    정렬이 활성화된 상태에서 setItem() 호출 시
    Qt가 자동으로 정렬을 시도 → 인덱스 불일치 → 데이터 꼬임
```

### 핵심 원인

Qt의 `QTableWidget`에서 **`setSortingEnabled(True)` 상태로 `setItem()`을 호출하면**
정렬이 자동으로 발생하여 **행 인덱스가 변경**됩니다.

그러나 `_update_watchlist_panel()`는 고정된 `row` 인덱스로 데이터를 삽입하므로,
정렬로 인해 행이 이동하면 **잘못된 위치에 데이터가 들어가거나** 누락됩니다.

### 해결 방안

#### Option 1: 업데이트 중 정렬 비활성화 (권장)

```python
def _update_watchlist_panel(self, items: list):
    # 정렬 임시 비활성화
    self.watchlist_table.setSortingEnabled(False)
    
    # ... 기존 업데이트 로직 ...
    
    # 정렬 다시 활성화
    self.watchlist_table.setSortingEnabled(True)
```

#### Option 2: blockSignals 사용

```python
def _update_watchlist_panel(self, items: list):
    self.watchlist_table.blockSignals(True)
    
    # ... 기존 업데이트 로직 ...
    
    self.watchlist_table.blockSignals(False)
```

### 구현 위치

| 파일 | 변경 |
|------|------|
| `frontend/gui/dashboard.py` | `_update_watchlist_panel()` 시작/끝에 정렬 제어 추가 |

### 왜 이후 업데이트에서도 빈칸이 채워지지 않는가?

**핵심: 매 업데이트마다 동일한 문제가 반복됨**

```python
for row, item in enumerate(items):  # row = 0, 1, 2, 3...
    # 1. Row 0에 Ticker "AAPL" 설정
    self.watchlist_table.setItem(row, 0, QTableWidgetItem(ticker))
    
    # 2. Row 0에 Change% 설정
    #    → 이때 Qt가 값에 따라 자동 정렬 발생!
    #    → Row 0이 Row 5로 이동됨
    self.watchlist_table.setItem(row, 1, change_item)
    
    # 3. 여전히 row=0에 DolVol 설정하려고 함
    #    → 그러나 원래 "AAPL" 행은 이제 Row 5!
    #    → Row 0은 이제 다른 종목이 되어 있음
    #    → 결과: 잘못된 행에 데이터 삽입
    self.watchlist_table.setItem(row, 2, dolvol_item)
```

**결과:**
- 일부 행: Ticker, Change%만 있고 DolVol, Score, Ign은 비어있음
- 다른 행: DolVol, Score, Ign만 있고 Ticker, Change%는 비어있음
- 매 업데이트마다 **동일한 뒤섞임** 발생 → 영원히 수정 안 됨

