# Devlog: 01-004 Watchlist Model/View Architecture Transition

**작성일**: 2026-01-06  
**관련 계획**: `docs/Plan/bugfix/01-004_watchlist_model_view_architecture.md`

---

## 개요

Watchlist 테이블에서 정렬(DolVol, Change% 등)하면 데이터가 사라지는 문제를 해결하기 위해  
`QTableWidget` → `QTableView` + `QStandardItemModel` 아키텍처로 전환합니다.

---

## Phase 1: 모델 클래스 생성

### 작업 시작: 2026-01-06T01:26

**목표**: `frontend/gui/watchlist_model.py` 신규 생성

**구현 내용**:
- `WatchlistModel` 클래스 (QStandardItemModel 상속)
- 컬럼 정의: COL_TICKER(0), COL_CHANGE(1), COL_DOLVOL(2), COL_SCORE(3), COL_IGNITION(4)
- `_ticker_to_row` 딕셔너리로 빠른 조회 지원
- `update_item()`: 단일 항목 업데이트 (있으면 수정, 없으면 추가)
- `update_all()`: 전체 목록 업데이트
- `_set_row_data()`: 행 데이터 설정 (UserRole에 숫자값 저장으로 정렬 지원)
- `_format_dolvol()`: Dollar Volume K/M/B 포맷팅

**생성 완료**: `frontend/gui/watchlist_model.py`

**구현 결과**:
- ✅ WatchlistModel 클래스 구현 완료
- ✅ 5개 컬럼 정의 (Ticker, Chg%, DolVol, Score, Ign)
- ✅ ticker→row 매핑 (_ticker_to_row dict)
- ✅ update_item(), update_all(), clear_all(), remove_ticker() 메서드
- ✅ UserRole에 숫자값 저장 → 정렬 시 올바른 비교
- ✅ Transparency Protocol: 데이터 없을 시 ⚠️ 표시
- ✅ 색상 테마 연동 (success/danger/warning)

---

## Phase 2: Dashboard 통합

### 작업 시작: 2026-01-06T01:27

**목표**: `dashboard.py`에서 `QTableWidget` → `QTableView` + `WatchlistModel` 전환

**변경 사항**:
1. Import 추가: `QTableView`, `WatchlistModel`
2. `_create_left_panel()`: 
   - `self.watchlist_table = QTableWidget()` → `QTableView()`
   - `self.watchlist_model = WatchlistModel()` 추가
   - `self.watchlist_table.setModel(self.watchlist_model)`
3. `_update_watchlist_panel()`: Model-based 업데이트로 변경
4. `_on_watchlist_table_clicked()`: QModelIndex 기반으로 변경
5. `cellClicked` → `clicked` 시그널 변경

**구현 중...**

**변경 완료**:

#### 2.1 Import 추가
- ✅ `from .watchlist_model import WatchlistModel` (line 61)
- ✅ `QTableView` import 추가 (line 527)

#### 2.2 `_create_left_panel()` 변경
- ✅ `self.watchlist_model = WatchlistModel()` 추가
- ✅ `self.watchlist_table = QTableView()` (QTableWidget → QTableView)
- ✅ `self.watchlist_table.setModel(self.watchlist_model)` 연결
- ✅ 스타일시트 `QTableWidget` → `QTableView`로 변경
- ✅ `cellClicked` → `clicked` 시그널 변경

#### 2.3 `_update_watchlist_panel()` 변경
- ✅ `watchlist_model.update_item()` 사용으로 변경
- ✅ `setRowCount()`, `setItem()` 직접 호출 제거
- ✅ Model이 색상/포맷/정렬 처리

#### 2.4 `_on_watchlist_table_clicked()` 변경
- ✅ 시그니처: `(row, column)` → `(index)` (QModelIndex)
- ✅ `self.watchlist_model.index(row, 0)` 및 `.data()` 사용
- ✅ 중복 함수 제거

#### 2.5 `_add_watchlist_sample_data()` 변경
- ✅ `watchlist_model.clear_all()` 사용

---

## 검증

### 구문 검사
```
python -m py_compile frontend\gui\watchlist_model.py frontend\gui\dashboard.py
```
**결과**: ✅ 성공 (오류 없음)

### 변경 파일 요약

| 파일 | 작업 | 상태 |
|------|------|------|
| `frontend/gui/watchlist_model.py` | [NEW] WatchlistModel 클래스 | ✅ 완료 |
| `frontend/gui/dashboard.py` | [MODIFY] QTableWidget → QTableView 전환 | ✅ 완료 |

### 예상 결과 (GUI 테스트 필요)

**Before**:
```
정렬 클릭 → 데이터 사라짐 → 업데이트해도 복구 안 됨
```

**After**:
```
정렬 클릭 → 정상 정렬 → 업데이트 시 제자리에서 값 갱신
```

---

## 결론

`01-004` Model/View 아키텍처 전환 완료.
GUI 실행 후 정렬 기능 테스트 권장.

---

## Phase 4: 정렬 상태 유지 (QSortFilterProxyModel)

### 작업 시작: 2026-01-06T01:38

**문제**: 정렬 후 업데이트 시 원래 데이터 순서로 리셋됨

**원인**: `QStandardItemModel` 직접 연결 시 정렬 상태가 유지되지 않음

**해결책**: `QSortFilterProxyModel` 도입

**변경 내용**:

#### 4.1 Proxy 모델 추가 (`_create_left_panel`)
```python
self.watchlist_proxy = QSortFilterProxyModel()
self.watchlist_proxy.setSourceModel(self.watchlist_model)
self.watchlist_proxy.setSortRole(Qt.ItemDataRole.UserRole)

self.watchlist_table.setModel(self.watchlist_proxy)  # Proxy 연결
```

#### 4.2 클릭 핸들러 수정
```python
def _on_watchlist_table_clicked(self, proxy_index):
    source_index = self.watchlist_proxy.mapToSource(proxy_index)
    ticker_index = self.watchlist_model.index(source_index.row(), 0)
    ticker = self.watchlist_model.data(ticker_index)
```

**구문 검사**: ✅ 통과

---

## 최종 검증

### GUI 테스트 결과: 2026-01-06T01:42

**테스트 환경**: Backend 연결 상태에서 Watchlist 실시간 업데이트

**테스트 항목**:
1. ✅ Watchlist 데이터 정상 로드
2. ✅ DolVol 컬럼 정렬 클릭 → 정상 정렬
3. ✅ Change% 컬럼 정렬 클릭 → 정상 정렬
4. ✅ **정렬 후 업데이트 시 정렬 상태 유지** ← Phase 4 핵심 검증
5. ✅ 종목 클릭 시 차트 정상 로드 (Proxy→Source 인덱스 변환 정상)

**사용자 확인**: "seems working great. good job."

---

## 결론

### 해결된 문제

| 문제 | 원인 | 해결 방안 |
|------|------|----------|
| 정렬 시 데이터 사라짐 | `QTableWidget`에서 `setItem()` 중 정렬 발생 | Phase 1-3: `QTableView` + `WatchlistModel` 전환 |
| 업데이트 시 정렬 리셋 | `QStandardItemModel` 직접 연결 시 정렬 상태 미유지 | Phase 4: `QSortFilterProxyModel` 도입 |

### 최종 아키텍처

```
[데이터 흐름]
Backend → WatchlistItem → 
    ↓
WatchlistModel (QStandardItemModel) ← 데이터 저장
    ↓
QSortFilterProxyModel ← 정렬 상태 관리
    ↓
QTableView ← 표시만 담당
```

### 변경 파일

| 파일 | 작업 |
|------|------|
| `frontend/gui/watchlist_model.py` | [NEW] WatchlistModel 클래스 |
| `frontend/gui/dashboard.py` | [MODIFY] Model/View + ProxyModel 전환 |

### 상태

✅ **Issue 01-004 완전 해결** (2026-01-06)
