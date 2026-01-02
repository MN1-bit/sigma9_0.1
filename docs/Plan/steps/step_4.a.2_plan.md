# Step 4.A.2: Tier 2 Hot Zone 구현 계획

> **버전**: 1.0  
> **작성일**: 2026-01-02  
> **선행 조건**: Step 4.A.1 완료  
> **참조 파일**: 
> - `frontend/gui/dashboard.py` (Tier 1 Watchlist 구현)
> - `backend/api/routes.py` (Tier 2 API: `/api/tier2/promote`)
> - `backend/core/subscription_manager.py` (tick 구독 관리)

---

## 📋 목표

Tier 1 Watchlist **상단**에 Tier 2 Hot Zone 테이블 추가.  
고우선순위 종목 실시간 모니터링 (틱 레벨 1초 업데이트)

---

## 📊 현재 상태 분석

### Tier 1 (Step 4.A.1 완료)
- **위치**: `dashboard.py` → `_create_left_panel()`
- **위젯**: `self.watchlist_table` (QTableWidget)
- **컬럼**: Ticker, Chg%, DolVol, Score, Ign
- **갱신**: 1분 타이머

### Tier 2 API (Step 4.A.0.d 완료)
- `POST /api/tier2/promote` → T채널 구독 + TickDispatcher 필터
- `POST /api/tier2/demote` → T채널 해제
- `GET /api/tier2/status` → 현재 Tier 2 종목 조회

### Tick 데이터 흐름
```
Massive T채널 → TickBroadcaster → GUI WebSocket
                                     ↓
                     backend_client.tick_received 시그널
                                     ↓
                     dashboard._on_tick_received() 핸들러
```

---

## 🎯 구현 범위

| # | 서브스텝 | 설명 |
|---|----------|------|
| 4.A.2.1 | Tier 2 데이터 모델 | zenV, zenP, 실시간 가격 |
| 4.A.2.2 | Ignition ≥ 70 승격 | 자동 Tier 2 승격 로직 |
| 4.A.2.3 | Day Gainers 자동 추가 | Gainers API → Tier 2 |
| 4.A.2.4 | GUI 패널 | Watchlist 상단 테이블 |
| 4.A.2.5 | 1초 실시간 업데이트 | tick_received 핸들러 |

---

## 📝 상세 구현 계획

### 1. Tier 2 데이터 모델 정의

> 파일: `frontend/gui/dashboard.py` (또는 별도 `models.py`)

```python
@dataclass
class Tier2Item:
    ticker: str
    price: float           # 실시간 가격
    change_pct: float      # 등락율
    zenV: float            # Z-score Volume (Step 4.A.3에서 계산)
    zenP: float            # Z-score Price
    ignition: float        # Ignition Score
    last_update: datetime  # 마지막 틱 수신 시간
```

---

### 2. Left Panel 레이아웃 수정

> 파일: `frontend/gui/dashboard.py` → `_create_left_panel()`

**현재 구조:**
```
┌─────────────────┐
│  📋 Watchlist   │
│  [Tier 1 Table] │
│                 │
└─────────────────┘
```

**목표 구조:**
```
┌─────────────────┐
│  🔥 Hot Zone    │  ← Tier 2 테이블 (상단, 고정 높이 150px)
│  [Tier 2 Table] │
├─────────────────┤
│  📋 Watchlist   │  ← Tier 1 테이블 (하단, 확장)
│  [Tier 1 Table] │
└─────────────────┘
```

**구현:**
```python
def _create_left_panel(self) -> QFrame:
    frame, layout = self._create_panel_frame("📋 Watchlist")
    
    # ═══════════════════════════════════════════════════════════
    # 1. Tier 2 Hot Zone (상단)
    # ═══════════════════════════════════════════════════════════
    tier2_label = QLabel("🔥 Hot Zone")
    layout.addWidget(tier2_label)
    
    self.tier2_table = QTableWidget()
    self.tier2_table.setColumnCount(6)
    self.tier2_table.setHorizontalHeaderLabels(
        ["Ticker", "Price", "Chg%", "zenV", "zenP", "Ign"]
    )
    self.tier2_table.setMaximumHeight(150)
    layout.addWidget(self.tier2_table)
    
    # ═══════════════════════════════════════════════════════════
    # 2. Tier 1 Watchlist (하단) - 기존 코드
    # ═══════════════════════════════════════════════════════════
    tier1_label = QLabel("📋 Watchlist")
    layout.addWidget(tier1_label)
    
    self.watchlist_table = QTableWidget()
    # ... 기존 Tier 1 코드 ...
```

---

### 3. Tier 2 테이블 컬럼 정의

| # | 컬럼 | 너비 | 설명 |
|---|------|------|------|
| 0 | Ticker | Stretch | 종목 코드 |
| 1 | Price | 60px | 실시간 가격 |
| 2 | Chg% | 50px | 등락율 |
| 3 | zenV | 50px | Z-score Volume |
| 4 | zenP | 50px | Z-score Price |
| 5 | Ign | 40px | Ignition Score |

---

### 4. Tick 수신 핸들러 수정

> 파일: `frontend/gui/dashboard.py` → `_on_tick_received()`

**현재 상태**: 존재하지만 Tier 2 업데이트 로직 없음

**수정 내용**:
```python
def _on_tick_received(self, data: dict):
    """
    실시간 틱 데이터 수신 핸들러
    
    Args:
        data: {"ticker": str, "price": float, "size": int, "time": int}
    """
    ticker = data.get("ticker", "")
    price = data.get("price", 0.0)
    
    if not ticker:
        return
    
    # 가격 캐시 업데이트
    self._price_cache[ticker] = price
    
    # Tier 2 테이블에서 해당 종목 찾아서 업데이트
    for row in range(self.tier2_table.rowCount()):
        ticker_item = self.tier2_table.item(row, 0)
        if ticker_item and ticker_item.text() == ticker:
            # Price 컬럼 업데이트
            price_item = QTableWidgetItem(f"${price:.2f}")
            self.tier2_table.setItem(row, 1, price_item)
            break
```

---

### 5. Ignition ≥ 70 자동 승격 (4.A.2.2)

> 파일: `frontend/gui/dashboard.py` → `_on_ignition_update()`

**수정 내용**:
```python
def _on_ignition_update(self, data: dict):
    ticker = data.get("ticker", "")
    score = data.get("score", 0.0)
    
    # ... 기존 Tier 1 업데이트 로직 ...
    
    # Ignition ≥ 70 → Tier 2 자동 승격
    if score >= 70:
        self._promote_to_tier2(ticker)

def _promote_to_tier2(self, ticker: str):
    """종목을 Tier 2로 승격"""
    # 이미 Tier 2에 있는지 확인
    for row in range(self.tier2_table.rowCount()):
        if self.tier2_table.item(row, 0).text() == ticker:
            return  # 이미 존재
    
    # Tier 2 테이블에 추가
    row = self.tier2_table.rowCount()
    self.tier2_table.insertRow(row)
    self.tier2_table.setItem(row, 0, QTableWidgetItem(ticker))
    # ... 나머지 컬럼 채우기 ...
    
    # Backend API 호출 (T채널 구독)
    asyncio.create_task(
        self.backend_client.rest.promote_to_tier2([ticker])
    )
```

---

### 6. Backend 연동

> 기존 API 활용: `frontend/services/rest_adapter.py`

```python
# 이미 구현됨 (Step 4.A.0.d)
await self.rest.promote_to_tier2([ticker])
await self.rest.demote_from_tier2([ticker])
status = await self.rest.get_tier2_status()
```

---

## ✅ 완료 조건

1. [x] Tier 2 테이블이 Tier 1 상단에 표시
2. [x] 6개 컬럼: Ticker, Price, Chg%, zenV, zenP, Ign
3. [x] Tick 수신 시 Price 실시간 업데이트
4. [x] Ignition ≥ 70 시 자동 Tier 2 승격
5. [x] 문법 오류 없음 (py_compile)

---

## ⚠️ 주의사항

### zenV/zenP 계산
- Step 4.A.3에서 구현 예정
- 현재는 placeholder (0.0) 표시

### QTableWidget 정렬 시 주의
- 실시간 업데이트 중 정렬 변경 시 깜빡임 발생 가능
- `setSortingEnabled(False)` 후 업데이트, 완료 후 다시 활성화

---

## ⏱️ 예상 시간

| 작업 | 시간 |
|------|------|
| Tier 2 테이블 추가 | 20분 |
| 레이아웃 수정 | 10분 |
| _on_tick_received 수정 | 15분 |
| 자동 승격 로직 | 15분 |
| 스타일링 | 10분 |
| 테스트 | 10분 |
| **총계** | **80분** |
