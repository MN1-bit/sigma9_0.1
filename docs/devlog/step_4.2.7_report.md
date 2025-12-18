# Step 4.2.7 Report: GUI-Server Connection & Scanner Integration

**Date**: 2025-12-18
**Session Focus**: 로컬/AWS 서버 연결 문제 해결 및 Scanner API 통합

---

## ✅ 완료된 작업

### 1. BackendClient 동기 래퍼 추가
- `connect_sync()`, `disconnect_sync()`, `start_engine_sync()`, `stop_engine_sync()`, `kill_switch_sync()`, `run_scanner_sync()`
- 백그라운드 스레드에서 영구 이벤트 루프 유지 (`_get_event_loop()`, `_run_async()`)
- PyQt 콜백에서 async 메서드 호출 가능하게 함

### 2. Smart Auto-Connect 기능 (`_on_connect`)
Connect 버튼 클릭 시 자동 수행:
1. AWS 서버 연결 시도
2. 실패 시 → 로컬 서버 연결 시도
3. 로컬 서버 없으면 → 자동으로 서버 시작 (subprocess)
4. 연결 성공 → 엔진 자동 시작
5. Scanner 자동 실행

### 3. Settings Connection 탭 개선
- 서버 프리셋 드롭다운 추가 (🖥️ Local / ☁️ AWS / 🔧 Custom)
- Test Connection 버튼 기능 구현 (httpx 사용)
- 프리셋에 따라 Host/Port 자동 설정

### 4. Scanner API 구현 (`/api/scanner/run`)
- MarketDB 기반 Scanner 클래스 호출
- 12,501개 종목 중 조건 필터링 (가격 $2~$20, 거래량 100K+)
- Seismograph 전략으로 50개 종목 스캔 성공
- WatchlistStore에 결과 저장

### 5. Watchlist API 수정 (`/api/watchlist`)
- Mock 데이터 대신 WatchlistStore에서 실제 데이터 로드

---

## ❌ 남은 문제

### 1. Watchlist 세부 데이터 미표시
- **증상**: 종목명은 표시되나 +0.0%로 표시, 차트 불러와지지 않음
- **원인 추정**: 
  - Scanner가 `last_close`, `change_pct` 필드를 제대로 채우지 않음
  - 또는 GUI의 Watchlist 패널이 해당 필드를 사용하지 않음
- **해결 필요**: Scanner.run_daily_scan() 결과에 last_close, change_pct 포함 확인

### 2. 차트 데이터 로드 API 미구현
- **증상**: 종목 클릭 시 차트가 표시되지 않음
- **원인**: `/api/chart/{ticker}` 또는 유사 API가 없음
- **해결 필요**: MarketDB에서 OHLCV 데이터를 조회하는 Chart API 추가



---

## 📁 수정된 파일

| 파일 | 변경 내용 |
|------|----------|
| `frontend/services/backend_client.py` | 동기 래퍼, `set_server()`, 백그라운드 이벤트 루프 |
| `frontend/gui/dashboard.py` | Smart Connect, `_auto_start_engine()` |
| `frontend/gui/settings_dialog.py` | 서버 프리셋, Test Connection |
| `frontend/services/rest_adapter.py` | `run_scanner()` 메서드 |
| `backend/api/routes.py` | `/api/scanner/run`, `/api/watchlist` 수정 |

---

## 🔜 다음 세션 작업

1. Scanner 결과에 `last_close`, `change_pct` 데이터 포함
2. Chart API 추가 (`/api/chart/{ticker}`)
3. Connect 버튼 비동기 처리 (UI 블로킹 해결)
4. Git revert point 생성
