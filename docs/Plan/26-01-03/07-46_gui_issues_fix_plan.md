# GUI 이슈 해결 계획

**작성일시**: 2026-01-03 06:39:39 (KST)
**수정일시**: 2026-01-03 06:42:52 (KST)

---

## 개요

GUI에서 발견된 네 가지 이슈를 해결하기 위한 구현 계획입니다.

---

## Issue 4: ⚠️ [긴급] Scanner 실행 시 GUI 프리즈

### 원인 분석 (추정)
1. **메인 스레드 블로킹**: Scanner가 메인(UI) 스레드에서 동기적으로 실행되어 GUI 이벤트 루프가 멈춤
2. **대량 데이터 처리**: Scanner가 수천 개의 종목을 처리하면서 UI 업데이트가 블로킹됨
3. **동기 API 호출**: `backend_client.run_scanner_sync()` 같은 동기 호출이 UI를 블로킹

### 해결 방안
1. **비동기 처리**: Scanner를 별도 스레드(QThread) 또는 asyncio 태스크로 실행
2. **프로그레스 표시**: 스캔 중임을 표시하는 로딩 인디케이터 추가
3. **결과 시그널**: 스캔 완료 시 시그널로 UI 업데이트

### 수정 대상 파일
- `frontend/services/backend_client.py`: 비동기 스캐너 호출
- `frontend/gui/dashboard.py`: QThread 사용 또는 시그널 기반 업데이트
- `backend/api/routes.py`: (필요 시) 스트리밍 응답 지원

---

## Issue 1: 일봉 차트가 2025년 12월 31일까지만 표시되고 실시간 업데이트 안됨

### 원인 분석
1. **DB 데이터 부재**: 일봉 차트는 `ChartDataService._get_daily_data()`에서 `MarketDB.get_daily_bars()`를 호출하여 SQLite DB에서 데이터를 조회합니다. DB에 2025-12-31 이후 데이터가 없으면 표시되지 않습니다.
2. **자동 동기화 없음**: 현재 DB는 수동으로 동기화해야 하며, GUI 시작 시 또는 주기적으로 최신 데이터를 가져오는 로직이 없습니다.
3. **실시간 일봉 업데이트 없음**: 틱 데이터는 수신되지만 (`_on_tick_received`), 일봉 차트에 반영하는 로직이 없습니다.

### 해결 방안

#### A. DB 동기화 로직 추가 (백엔드)
- 서버 시작 시 또는 주기적으로 Polygon.io API를 호출하여 누락된 일봉 데이터를 DB에 저장

#### B. 일봉 차트 실시간 업데이트 (프론트엔드)
- 틱 수신 시 현재 일봉 캔들 업데이트 (이미 구현된 `update_current_candle` 활용)
- 새로운 거래일 시작 시 새 캔들 추가

### 수정 대상 파일
- `backend/data/polygon_loader.py`: `sync_daily_data()` 메서드 추가
- `backend/server.py`: `/api/sync/daily` 엔드포인트 추가
- `frontend/services/chart_data_service.py`: 데이터 보완 로직 추가
- `frontend/gui/dashboard.py`: 일봉 타임프레임 실시간 업데이트 활성화

---

## Issue 2: Tier 2 / Oracle 패널에 색상이 들어있음 → 전부 제거

### 원인 분석

1. **Tier 2 테이블**: `_create_left_panel()` (line 559-583)에서 배경색과 강조색이 적용됨:
   - `background-color: rgba(255, 193, 7, 0.05)` (노란색 틴트)
   - `border: 1px solid {c['warning']}` (노란색 테두리)
   - 헤더 배경: `rgba(255, 193, 7, 0.15)`

2. **Oracle 패널**: `_create_right_panel()` (line 950-955)에서:
   - `border: 1px solid {theme.get_color('primary')}` (파란색 테두리)

3. **Oracle 버튼**: `_get_oracle_btn_style()` (line 1000-1016)에서:
   - `background-color: rgba(33, 150, 243, 0.2)` (파란색 틴트)

### 해결 방안
- 모든 배경색을 `transparent` 또는 제거
- 테두리도 기본 테마 색상(`border`)으로 통일

### 수정 대상 파일
- `frontend/gui/dashboard.py`

### ✅ 상태: 완료

---

## Issue 3: Tier 1 / Tier 2 테이블 컬럼 너비 가변 조절 및 저장

### 원인 분석

1. **현재 상태**: `QHeaderView.ResizeMode.Fixed`로 설정되어 있어 사용자가 드래그로 크기 조절 불가
2. **저장 로직 없음**: 컬럼 너비가 `settings.yaml`에 저장되지 않음

### 해결 방안

1. **크기 조절 가능하게**: `QHeaderView.ResizeMode.Fixed` → `QHeaderView.ResizeMode.Interactive`
2. **설정 저장/로드**: 
   - 컬럼 너비 변경 시 `settings.yaml`에 저장
   - GUI 시작 시 저장된 너비 로드

### 수정 대상 파일
- `frontend/config/settings.yaml`: 테이블 컬럼 너비 설정 섹션 추가
- `frontend/gui/dashboard.py`: Interactive 모드 전환 + 저장/로드 로직

---

## 구현 우선순위

| 순서 | 이슈 | 난이도 | 예상 시간 | 상태 |
|------|------|--------|-----------|------|
| 1 | Issue 4 (GUI 프리즈) | 🔴 높음 | 1-2시간 | ✅ 완료 |
| 2 | Issue 2 (색상 제거) | 🟢 낮음 | 10분 | ✅ 완료 |
| 3 | Issue 3 (컬럼 너비) | 🟡 중간 | 30분 | ✅ 완료 |
| 4 | Issue 1 (일봉 데이터) | 🔴 높음 | 1-2시간 | ✅ 완료 |
| 5 | Issue 5 (Ignition 자동시작) | 🟡 중간 | 15분 | ✅ 완료 |
| 6 | Issue 6 (테이블 버그 3건) | 🟡 중간 | 30분 | ✅ 완료 |
| 7 | Issue 7 (Tier 2 승격 로직) | 🔴 높음 | 1시간 | ✅ 완료 |

---

## 수정 리포트

- [Issue 4: GUI 프리즈](report_issue4_gui_freeze.md)
- [Issue 2: 색상 제거](report_issue2_color_removal.md)
- [Issue 3: 컬럼 너비](report_issue3_column_width.md)
- [Issue 1: 일봉 차트](report_issue1_daily_chart.md)
- [Issue 5: Ignition 자동시작](report_issue5_ignition_autostart.md)
- [Issue 6: 테이블 버그 (컬럼 연동, Tier2, 정렬)](report_issue6_table_bugs.md)
- [Issue 7: Tier 2 승격 로직](report_issue7_tier2_promotion.md)

---

## 세션 요약 (2026-01-03)

### 완료된 작업

1. **Issue 4: GUI 프리즈 해결**
   - `run_scanner_sync`를 non-blocking fire-and-forget 패턴으로 변경
   - Scanner 실행 시 UI가 멈추지 않음

2. **Issue 2: Tier 2 / Oracle 색상 제거**
   - 노란색/파란색 강조 색상을 기본 테마 색상으로 변경
   - 투명 배경, 기본 테두리 적용

3. **Issue 3: 테이블 컬럼 너비 가변 조절 및 저장**
   - Fixed → Interactive 모드 전환
   - `settings.yaml`에 컬럼 너비 저장/로드

4. **Issue 1: 일봉 차트 날짜 제한 해결**
   - 서버 시작 시 `PolygonLoader.update_market_data()` 자동 호출
   - `/api/sync/daily` 엔드포인트 추가

5. **Issue 5: IgnitionMonitor 자동 시작/종료**
   - 서버 시작 시 `ignition_monitor.start(watchlist)` 호출
   - 서버 종료 시 `ignition_monitor.stop()` 호출

6. **Issue 6: 테이블 버그 3건**
   - 컬럼 연동 문제: Stretch → Interactive 변경
   - Tier2 가변 너비: 동일하게 수정
   - 정렬 오류: `NumericTableWidgetItem` 클래스 추가

7. **Issue 7: Tier 2 승격 로직 개선**
   - Ignition Score v3: `base × 14 + stage_bonus + volume_bonus`
   - +5% 상승 시 70점 달성 가능 (기존 +7% 필요)
   - Watchlist 없을 시 Auto-Scanner 실행
