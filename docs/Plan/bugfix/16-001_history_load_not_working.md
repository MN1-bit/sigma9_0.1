# 16-001: 히스토리 로드 작동 안함

> **작성일**: 2026-01-13 | **예상**: 1시간

---

## 1. 목표

- 차트 좌측 끝 스크롤 시 과거 데이터 자동 로드
- Edge trigger 메커니즘 정상 동작 확인

---

## 2. 레이어 체크

- [x] 레이어 규칙 위반 없음 (frontend 내부 변경)
- [x] 순환 의존성 없음
- [ ] DI Container 등록 필요: **아니오**

---

## 3. 기존 솔루션 검색 결과

| 솔루션 | 출처 | 채택 여부 | 사유 |
|--------|------|----------|------|
| `sigXRangeChanged` | pyqtgraph | ✅ 이미 사용 | viewport 변경 감지 |

---

## 4. 변경 파일

| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
| `frontend/gui/chart/finplot_chart.py` | MODIFY | +20 |
| `frontend/services/chart_data_service.py` | MODIFY | +5 |

---

## 5. 실행 단계

### Step 1: 디버그 로그 추가 (finplot_chart.py)

```python
def _on_viewport_changed(self, vb, range_) -> None:
    print(f"[CHART] Viewport changed: range={range_}")
    
    if not range_ or len(range_) < 2:
        print(f"[CHART] Invalid range")
        return
    
    x_min, x_max = range_[0], range_[1]
    print(f"[CHART] x_min={x_min}, threshold=5, ticker={getattr(self, '_current_ticker', None)}")
    # ... 기존 코드
```

### Step 2: 티커 설정 확인 (finplot_chart.py)

```python
def set_candlestick_data(self, candles, ticker=None):
    if ticker:
        self._current_ticker = ticker
        print(f"[CHART] Ticker set: {ticker}")
    
    self._data_start_ts = min(c.get("time", 0) for c in candles)
    print(f"[CHART] Data start ts: {self._data_start_ts}")
    # ... 기존 코드
```

### Step 3: chart_data_service에서 티커 전달 확인

- `get_chart_data_sync()` 호출 시 `ticker` 파라미터 확인

### Step 4: 로그 분석 후 원인별 수정

| 증상 | 원인 | 수정 |
|------|------|------|
| `Viewport changed` 안 나옴 | sigXRangeChanged 연결 안됨 | 연결 확인 |
| `x_min` 항상 0 이상 | 데이터 범위 제한 | `_disable_viewport_limits()` 확인 |
| `ticker=None` | 티커 미설정 | chart_data_service 수정 |

---

## 6. 검증

### 자동 테스트
```bash
ruff check frontend/gui/chart/finplot_chart.py
```

### 수동 테스트
1. 앱 실행 → 차트 로드
2. 콘솔에서 `[CHART] Viewport changed` 로그 확인
3. 좌측 끝으로 스크롤 → `[CHART] 🎯 Edge trigger fired!` 출력
4. 과거 데이터 로드 후 차트에 표시

### Parquet 데이터 확인 (사전)
```bash
python -c "from backend.data.parquet_manager import ParquetManager; pm = ParquetManager(); print(pm.get_intraday_bars('AAPL', '1D', 30))"
```

---

**다음**: `/IMP-execution`
