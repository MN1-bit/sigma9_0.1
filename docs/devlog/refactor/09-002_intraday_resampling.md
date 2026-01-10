# Intraday Resampling Infrastructure Devlog

> **작성일**: 2026-01-10
> **계획서**: [09-002_finplot_chart_enhancements.md](../../Plan/refactor/09-002_finplot_chart_enhancements.md)

## 진행 현황

| Step | 상태 | 시간 |
|------|------|------|
| Step 1 | ✅ | 11:50 |
| Step 2 | ✅ | 11:45 |
| Step 3 | ⏸️ deferred | WS 연동 필요 |
| Step 4 | ⏸️ deferred | WS 연동 필요 |
| Step 5 | ✅ | 11:47 |

---

## Step 1: ParquetManager 확장

### 변경 사항
- `backend/data/parquet_manager.py`:
  - `RESAMPLE_RULES` 상수 추가 (3m/5m/15m→1m, 4h→1h, 1W→1D)
  - `get_intraday_bars(ticker, tf, auto_fill=True)` On-demand 리샘플링
  - `_try_resample()`, `_resample_df()` 내부 헬퍼
  - `resample_all_tickers()` 일괄 처리 (GUI 콜백 지원)
  - 172줄 추가 (426줄 → 598줄)

### 검증
- ruff check: ✅

---

## Step 2: ResamplePanel GUI 구현

### 변경 사항
- `frontend/gui/panels/resample_panel.py` [NEW]:
  - Start/Pause/Stop/Resume 버튼
  - QProgressBar (현재/전체 + %)
  - 타임프레임 선택 (3m/5m/15m/4h/1W)
  - 최대 이력 설정 (숫자 + 단위)
  - ResampleWorker QThread (백그라운드 처리)
  - ~320줄
- `frontend/gui/panels/__init__.py`: ResamplePanel 등록

### 검증
- ruff check: ✅

---

## Step 3-4: Deferred (WebSocket 연동 필요)

실시간 차트 리샘플 업데이트 및 viewport 연결은 WebSocket 데이터 스트림과의 연동이 필요합니다.
향후 WebSocket 1분봉 수신 로직과 함께 구현 예정.

---

## Step 5: 검증

### 린트 검증
- `ruff check backend/data/parquet_manager.py`: ✅
- `ruff check frontend/gui/panels/resample_panel.py`: ✅
- `ruff check frontend/gui/panels/__init__.py`: ✅

### 계획서 수정
계획서 모순 수정: "전역 실시간 (체크박스 ON)" → "수동 일괄 (Start 버튼)"

