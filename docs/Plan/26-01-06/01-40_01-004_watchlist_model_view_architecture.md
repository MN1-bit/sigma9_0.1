# Issue Report: Watchlist 테이블 Model/View 아키텍처 전환

**작성일**: 2026-01-06  
**버전**: v1.0  
**우선순위**: 🟡 High  
**상태**: ✅ Phase 4 완료 (2026-01-06)  
**관련 이슈**: `01-003_watchlist_data_refresh.md` (Phase 4)

---

## 문제 설명

### 증상
- Watchlist 테이블에서 정렬(DolVol, Change% 등)하면 데이터가 사라짐
- 매 업데이트마다 동일한 문제 반복 → 영구적으로 수정 안 됨

### 근본 원인
Qt의 `QTableWidget`에서 `setSortingEnabled(True)` 상태로 `setItem()`을 호출하면:
1. Qt가 자동으로 정렬 시도
2. 행 인덱스가 변경됨
3. 고정 인덱스로 데이터를 삽입하면 잘못된 행에 들어감

```python
for row, item in enumerate(items):
    self.watchlist_table.setItem(row, 0, ticker)  # Row 0
    self.watchlist_table.setItem(row, 1, change)  # ← 정렬 발생, Row 0 → Row 5
    self.watchlist_table.setItem(row, 2, dolvol)  # ← Row 0에 삽입 (잘못된 행!)
```

---

## 해결 방안: Model/View 아키텍처 전환

### 개요

`QTableWidget` → `QTableView` + `QStandardItemModel` 전환

| Before | After |
|--------|-------|
| `QTableWidget` (데이터+뷰 결합) | `QTableView` (뷰만) + `QStandardItemModel` (데이터만) |
| 정렬 시 인덱스 변경됨 | 모델 인덱스 안정적 |
| setItem() 중 정렬 발생 | 모델 업데이트와 뷰 정렬 분리 |

### 아키텍처

```
[데이터 흐름]
Backend → WatchlistItem → 
    ↓
WatchlistModel (QStandardItemModel) ← 데이터 저장
    ↓
QSortFilterProxyModel ← 정렬/필터링 (optional)
    ↓
QTableView ← 표시만 담당
```

---

## 구현 계획

### Phase 1: 모델 클래스 생성

**파일**: `frontend/gui/watchlist_model.py` (신규)

```python
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtCore import Qt

class WatchlistModel(QStandardItemModel):
    """Watchlist 데이터 모델"""
    
    # 컬럼 정의
    COL_TICKER = 0
    COL_CHANGE = 1
    COL_DOLVOL = 2
    COL_SCORE = 3
    COL_IGNITION = 4
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHorizontalHeaderLabels(["Ticker", "Chg%", "DolVol", "Score", "Ign"])
        self._ticker_to_row = {}  # ticker → row 매핑 (빠른 조회)
    
    def update_item(self, item_data: dict):
        """단일 항목 업데이트 (있으면 수정, 없으면 추가)"""
        ticker = item_data.get("ticker")
        
        if ticker in self._ticker_to_row:
            row = self._ticker_to_row[ticker]
            self._set_row_data(row, item_data)
        else:
            row = self.rowCount()
            self.insertRow(row)
            self._ticker_to_row[ticker] = row
            self._set_row_data(row, item_data)
    
    def update_all(self, items: list):
        """전체 목록 업데이트"""
        for item in items:
            self.update_item(item)
    
    def _set_row_data(self, row: int, data: dict):
        """행 데이터 설정"""
        # Ticker
        self.setItem(row, self.COL_TICKER, QStandardItem(data.get("ticker", "")))
        
        # Change %
        change = data.get("change_pct", 0)
        item = QStandardItem(f"{'+' if change >= 0 else ''}{change:.1f}%")
        item.setData(change, Qt.ItemDataRole.UserRole)  # 정렬용 숫자값
        self.setItem(row, self.COL_CHANGE, item)
        
        # Dollar Volume
        dolvol = data.get("dollar_volume", 0)
        item = QStandardItem(self._format_dolvol(dolvol))
        item.setData(dolvol, Qt.ItemDataRole.UserRole)
        self.setItem(row, self.COL_DOLVOL, item)
        
        # Score
        score = data.get("score", 0)
        item = QStandardItem(str(int(score)) if score > 0 else "⚠️")
        item.setData(score, Qt.ItemDataRole.UserRole)
        self.setItem(row, self.COL_SCORE, item)
        
        # Ignition
        ign = data.get("ignition", 0)
        item = QStandardItem(f"🔥{int(ign)}" if ign > 0 else "-")
        item.setData(ign, Qt.ItemDataRole.UserRole)
        self.setItem(row, self.COL_IGNITION, item)
    
    def _format_dolvol(self, value: float) -> str:
        if value >= 1_000_000_000:
            return f"${value/1_000_000_000:.1f}B"
        elif value >= 1_000_000:
            return f"${value/1_000_000:.1f}M"
        elif value >= 1_000:
            return f"${value/1_000:.0f}K"
        elif value > 0:
            return f"${value:.0f}"
        return "⚠️"
```

---

### Phase 2: Dashboard 통합

**파일**: `frontend/gui/dashboard.py`

#### 2.1 Import 추가
```python
from PyQt6.QtWidgets import QTableView
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from .watchlist_model import WatchlistModel
```

#### 2.2 테이블 생성 변경 (`_create_left_panel`)
```python
# Before
self.watchlist_table = QTableWidget()
self.watchlist_table.setSortingEnabled(True)

# After
self.watchlist_model = WatchlistModel()
self.watchlist_table = QTableView()
self.watchlist_table.setModel(self.watchlist_model)
self.watchlist_table.setSortingEnabled(True)
```

#### 2.3 업데이트 로직 변경 (`_update_watchlist_panel`)
```python
def _update_watchlist_panel(self, items: list):
    """Model-based 업데이트 (정렬 영향 없음)"""
    for item in items:
        if isinstance(item, WatchlistItem):
            data = {
                "ticker": item.ticker,
                "change_pct": item.change_pct,
                "dollar_volume": item.dollar_volume,
                "score": item.score,
                "ignition": self._ignition_cache.get(item.ticker, 0),
            }
        else:
            data = item
            data["ignition"] = self._ignition_cache.get(item.get("ticker"), 0)
        
        self.watchlist_model.update_item(data)
    
    self.log(f"[INFO] Watchlist updated: {len(items)} stocks")
```

#### 2.4 클릭 핸들러 변경
```python
def _on_watchlist_table_clicked(self, index):
    """QModelIndex 기반 클릭 핸들러"""
    ticker_index = self.watchlist_model.index(index.row(), 0)
    ticker = self.watchlist_model.data(ticker_index)
    if ticker:
        self.log(f"[ACTION] Watchlist selected: {ticker}")
        self._load_chart_for_ticker(ticker)
```

---

### Phase 3: 기존 참조 마이그레이션

| 기존 코드 | 변경 후 |
|----------|--------|
| `watchlist_table.setRowCount(n)` | `watchlist_model.setRowCount(n)` |
| `watchlist_table.setItem(row, col, item)` | `watchlist_model.setItem(row, col, item)` |
| `watchlist_table.item(row, col)` | `watchlist_model.item(row, col)` |
| `watchlist_table.rowCount()` | `watchlist_model.rowCount()` |
| `watchlist_table.currentRow()` | `watchlist_table.currentIndex().row()` |
| `cellClicked.connect(handler)` | `clicked.connect(handler)` |

---

## 변경 파일 목록

| 파일 | 작업 |
|------|------|
| `frontend/gui/watchlist_model.py` | [NEW] WatchlistModel 클래스 |
| `frontend/gui/dashboard.py` | [MODIFY] QTableWidget → QTableView 전환 |

---

## 예상 결과

### Before
```
정렬 클릭 → 데이터 사라짐 → 업데이트해도 복구 안 됨
```

### After
```
정렬 클릭 → 정상 정렬 → 업데이트 시 제자리에서 값 갱신
```

---

## 검증 계획

1. GUI 시작 → Watchlist 데이터 로드
2. **DolVol 컬럼 정렬** → 데이터 유지 확인
3. **Change% 컬럼 정렬** → 데이터 유지 확인
4. 1초 대기 → 업데이트 후 데이터 정상 표시 확인
5. 10초 관찰 → 값이 사라지지 않음

---

## 위험 요소

| 위험 | 완화 방안 |
|------|----------|
| API 차이로 인한 버그 | QTableView와 QTableWidget API 유사, 점진적 테스트 |
| 색상/스타일 깨짐 | delegate 또는 stylesheet 적용 |
| NumericTableWidgetItem 호환 | UserRole에 숫자값 저장하여 정렬 지원 |

---

## 🔴 Phase 4: 정렬 상태 유지 문제 (신규 발견)

**발견일**: 2026-01-06  
**상태**: ✅ 구현 완료 (2026-01-06)

### 증상

- 사용자가 컬럼 헤더 클릭으로 정렬 적용
- 매 업데이트(1초 간격) 시 정렬이 **원래 데이터 순서**로 리셋됨
- 기대: 정렬 상태 유지하면서 데이터만 갱신

### 근본 원인

**`QSortFilterProxyModel` 미사용**

현재 아키텍처:
```
WatchlistModel (QStandardItemModel)
    ↓ (직접 연결)
QTableView
```

문제점:
1. `QTableView.setSortingEnabled(True)`는 **모델 데이터 자체를 정렬**
2. 모델에 `setItem()` 호출 시 정렬 순서가 **저장되지 않음**
3. 새 데이터 삽입 시 삽입된 순서대로 표시됨

**핵심 이슈**: `QStandardItemModel`은 정렬 상태를 기억하지 않음.  
`QTableView`가 정렬을 요청하면 해당 시점에만 모델 데이터 순서가 변경되고,  
이후 `setItem()` 호출은 변경된 순서와 무관하게 원래 행 인덱스 기준으로 동작.

### 해결 방안: QSortFilterProxyModel 도입

**올바른 아키텍처**:
```
WatchlistModel (QStandardItemModel)
    ↓
QSortFilterProxyModel ← 정렬/필터 상태 관리 (뷰와 모델 사이 중개)
    ↓
QTableView ← setSortingEnabled(True)
```

**장점**:
- 소스 모델(WatchlistModel) 데이터 순서는 그대로 유지
- ProxyModel이 정렬 상태를 별도로 관리
- 데이터 업데이트 시 정렬 키 기준으로 자동 재정렬

### 구현 계획

#### 4.1 Dashboard에 ProxyModel 추가

**파일**: `frontend/gui/dashboard.py` (`_create_left_panel`)

```python
from PyQt6.QtCore import QSortFilterProxyModel

# 현재 코드:
self.watchlist_model = WatchlistModel()
self.watchlist_table = QTableView()
self.watchlist_table.setModel(self.watchlist_model)

# 변경 후:
self.watchlist_model = WatchlistModel()
self.watchlist_proxy = QSortFilterProxyModel()
self.watchlist_proxy.setSourceModel(self.watchlist_model)
self.watchlist_proxy.setSortRole(Qt.ItemDataRole.UserRole)  # 숫자 정렬

self.watchlist_table = QTableView()
self.watchlist_table.setModel(self.watchlist_proxy)  # Proxy를 연결
self.watchlist_table.setSortingEnabled(True)
```

#### 4.2 클릭 핸들러 수정

**문제**: `clicked` 시그널이 전달하는 `index`는 **Proxy의 인덱스**

```python
def _on_watchlist_table_clicked(self, proxy_index):
    """ProxyModel 인덱스 → SourceModel 인덱스 변환"""
    source_index = self.watchlist_proxy.mapToSource(proxy_index)
    ticker_index = self.watchlist_model.index(source_index.row(), 0)
    ticker = self.watchlist_model.data(ticker_index)
    if ticker:
        self._load_chart_for_ticker(ticker)
```

#### 4.3 변경 없음

- `WatchlistModel`: 변경 불필요 (소스 모델로 그대로 사용)
- `_update_watchlist_panel`: 변경 불필요 (소스 모델 직접 업데이트)

### 예상 결과

**Before (현재)**:
```
① 정렬 클릭 → 정렬됨
② 1초 후 업데이트 → 원래 순서로 리셋 ❌
```

**After (수정 후)**:
```
① 정렬 클릭 → 정렬됨
② 1초 후 업데이트 → 정렬 유지된 채 값만 갱신 ✅
```

### 검증 계획

1. GUI 시작 → Watchlist 데이터 로드
2. **DolVol 컬럼 정렬** (내림차순)
3. 5초 대기 (업데이트 여러 번 발생)
4. **정렬 순서 유지 확인** ✅
5. 데이터 값 변경 확인 (값은 갱신되면서 순서만 유지)

### 변경 파일

| 파일 | 작업 |
|------|------|
| `frontend/gui/dashboard.py` | [MODIFY] QSortFilterProxyModel 추가 |

