# 14-001: 검색창 자동완성 및 Info Panel 연동

> **작성일**: 2026-01-13 | **예상**: 45분

---

## 1. 목표

- 검색창에 티커 입력 시 자동완성 드롭다운 표시
- Info Panel이 티커 변경 시 자동 갱신

---

## 2. 레이어 체크

- [x] 레이어 규칙 위반 없음 (frontend 내부 변경)
- [x] 순환 의존성 없음
- [ ] DI Container 등록 필요: **아니오**

---

## 3. 기존 솔루션 검색 결과

| 솔루션 | 출처 | 채택 여부 | 사유 |
|--------|------|----------|------|
| QCompleter | Qt 내장 | ✅ 이미 사용 | 데이터만 로드 필요 |

---

## 4. 변경 파일

| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
| `frontend/gui/dashboard.py` | MODIFY | +15 |
| `frontend/gui/ticker_info_window.py` | MODIFY | +15 |

---

## 5. 실행 단계

### Step 1: DB에서 티커 로드 + 자동완성 최대 8개 표시

```python
# dashboard.py - __init__() 또는 _auto_connect_backend()

# DB에서 전체 티커 목록 로드
from backend.data.database import DatabaseClient
db = DatabaseClient()
tickers = db.get_all_tickers()  # [{ticker, name, ...}, ...]

ticker_data = {t["ticker"]: t["name"] for t in tickers}
self.control_panel.ticker_search.set_ticker_data(ticker_data)
```

```python
# ticker_search_bar.py - QCompleter 설정

self.completer.setMaxVisibleItems(8)  # 최대 8개 표시
```

### Step 2: Info Panel pending ticker 패턴 (ticker_info_window.py)

```python
def _on_ticker_changed(self, ticker: str, source: str) -> None:
    self._pending_ticker = ticker
    if self.isVisible():
        self.load_ticker(ticker)

def showEvent(self, event):
    super().showEvent(event)
    if hasattr(self, "_pending_ticker") and self._pending_ticker:
        self.load_ticker(self._pending_ticker)
```

### Step 3: 창 표시 시 현재 티커 로드 (dashboard.py)

```python
# _show_ticker_info() 수정
current = self._state.current_ticker
if current:
    self._ticker_info_window.load_ticker(current)
```

---

## 6. 검증

### 자동 테스트
```bash
ruff check frontend/gui/dashboard.py frontend/gui/ticker_info_window.py
```

### 수동 테스트
1. 앱 실행 → 검색창에 "A" 입력 → AAPL, AMZN 등 드롭다운 표시
2. 검색창에서 "AAPL" Enter → Info 창 열기 → 정보 자동 표시
3. Info 창 열린 상태에서 검색창 "MSFT" Enter → 자동 갱신

---

**다음**: `/IMP-execution`
