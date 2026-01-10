# Historical Bars Backend Migration Devlog

> **작성일**: 2026-01-08 16:28  
> **관련 계획서**: Phase 5 (05-004) - Frontend/Backend 책임 분리

## 진행 현황

| Step | 상태 | 완료 시간 |
|------|------|----------|
| Step 1: Backend API 생성 | ✅ 완료 | 16:27 |
| Step 2: Frontend API 호출로 교체 | ✅ 완료 | 16:28 |

---

## Step 1: Backend `/chart/bars` API 생성

### 변경 사항
- **[MODIFY]** `backend/api/routes/chart.py`: +220줄
  - `GET /chart/bars` 엔드포인트 추가
  - L2 (SQLite) → L3 (Massive API) 캐시 로직 이동
  - `_format_candles()` 헬퍼 함수 추가

### 기능
- 파라미터: `ticker`, `timeframe`, `limit`, `before`
- L2 Hit 시 SQLite에서 반환
- L2 Miss 시 Massive API 호출 후 SQLite 캐싱

---

## Step 2: Frontend `_fetch_historical_bars` 교체

### 변경 사항
- **[MODIFY]** `frontend/gui/dashboard.py`: -126줄
  - 180줄 → 55줄 (API 호출 래퍼로 교체)
  - DB/API 직접 접근 코드 제거
  - `requests.get()` 으로 Backend API 호출

---

## 최종 검증 결과

| 검증 항목 | 결과 |
|----------|------|
| Dashboard import | ✅ |
| Chart router import | ✅ |
| Line count | 2,279 → 2,153 (**-126줄**) |

## 누적 결과

| Phase | 변경 | 라인 |
|-------|------|------|
| 원본 | - | 2,532 |
| Phase 4 | ChartPanel, PositionPanel, OraclePanel | -208 |
| Cleanup | 중복 제거 | -35 |
| Phase 5a | `_fetch_historical_bars` 이동 | -126 |
| **현재** | - | **2,153** |
