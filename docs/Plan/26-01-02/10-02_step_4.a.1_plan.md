# Step 4.A.1: Tier 1 Watchlist Enhancement 계획

> **버전**: 1.0  
> **작성일**: 2026-01-02  
> **선행 조건**: Step 4.A.0.d 완료  

---

## 📋 범위

Phase 4.A.1 전체 구현 (Tier 1 Watchlist 개선)

| # | 서브스텝 | 설명 |
|---|----------|------|
| 4.A.1.1 | Dollar Volume 컬럼 | K/M/B 포맷 표기 |
| 4.A.1.2 | 헤더 정렬 기능 | 등락율/Score/Ignition 정렬 |
| 4.A.1.3 | 주기적 갱신 | 1분/5분 자동 갱신 |

---

## 📊 현재 구조

- **위젯**: `QListWidget` (단일 컬럼)
- **포맷**: `"AAPL  +2.3%  [85]"`
- **한계**: 다중 컬럼/정렬 불가

---

## 🎯 목표 구조

### QTableWidget 전환

| # | 컬럼 | 너비 | 정렬 | 설명 |
|---|------|------|------|------|
| 0 | Ticker | 60px | ✓ | 종목 코드 |
| 1 | Change | 55px | ✓ | 등락율 (%) |
| 2 | DolVol | 60px | ✓ | Dollar Volume (K/M/B) |
| 3 | Score | 45px | ✓ | 매집 점수 |
| 4 | Ignition | 50px | ✓ | Ignition Score |

---

## 📝 구현 계획

### 1. QTableWidget 전환 (4.A.1.1 + 4.A.1.2)

| 파일 | 변경 |
|------|------|
| `frontend/gui/dashboard.py` | `_create_left_panel()` 전면 수정 |

**핵심 코드:**
```python
self.watchlist_table = QTableWidget()
self.watchlist_table.setColumnCount(5)
self.watchlist_table.setHorizontalHeaderLabels(
    ["Ticker", "Change", "DolVol", "Score", "Ign"]
)
self.watchlist_table.setSortingEnabled(True)  # 정렬 활성화
```

---

### 2. 포맷팅 유틸 (4.A.1.1)

| 파일 | 변경 |
|------|------|
| `frontend/gui/dashboard.py` | `_format_dollar_volume()` 함수 추가 |

```python
def _format_dollar_volume(self, value: float) -> str:
    if value >= 1_000_000_000: return f"${value/1e9:.1f}B"
    if value >= 1_000_000: return f"${value/1e6:.1f}M"
    if value >= 1_000: return f"${value/1e3:.0f}K"
    return f"${value:.0f}"
```

---

### 3. 주기적 갱신 타이머 (4.A.1.3)

| 파일 | 변경 |
|------|------|
| `frontend/gui/dashboard.py` | `QTimer` 기반 자동 갱신 |

```python
self._watchlist_refresh_timer = QTimer()
self._watchlist_refresh_timer.timeout.connect(self._refresh_watchlist)
self._watchlist_refresh_timer.start(60_000)  # 1분
```

---

### 4. Backend 데이터 필드 추가

| 파일 | 변경 |
|------|------|
| `backend/api/routes.py` | `WatchlistItem`에 `dollar_volume` 필드 |
| `backend/data/watchlist_store.py` | 저장 시 dollar_volume 포함 |

---

### 5. Watchlist 업데이트 핸들러

| 파일 | 변경 |
|------|------|
| `dashboard.py` | `_update_watchlist_panel()` → 테이블 채우기 |

---

## ✅ 검증 계획

### 수동 검증
1. GUI 실행 후 5개 컬럼 표시 확인
2. 각 헤더 클릭 시 정렬 동작 확인
3. Dollar Volume K/M/B 포맷 확인
4. 1분 후 자동 갱신 확인

---

## ⏱️ 예상 시간

| 작업 | 시간 |
|------|------|
| QTableWidget 전환 + 스타일링 | 25분 |
| 포맷팅 유틸 | 5분 |
| Backend 필드 추가 | 10분 |
| 자동 갱신 타이머 | 10분 |
| 테스트 | 10분 |
| **총계** | **60분** |
