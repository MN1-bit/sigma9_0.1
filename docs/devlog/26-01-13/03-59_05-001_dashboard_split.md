# dashboard.py 분리 리팩터링 Devlog

> **작성일**: 2026-01-08 01:21
> **관련 계획서**: [05-001_dashboard_split.md](../../../docs/Plan/refactor/05-001_dashboard_split.md)

## 진행 현황

| Step | 상태 | 완료 시간 |
|------|------|----------|
| Step 1 | ✅ 완료 | 01:22 |
| Step 2 | ✅ 완료 | 01:30 |
| Step 3 | ✅ 완료 | 01:32 |
| Step 4 | ✅ 완료 | 01:28 |
| Step 5 | ✅ 완료 | 01:25 |
| Step 6 | 🔄 진행중 | - |

---

## Step 1: panels/ 및 state/ 디렉터리 생성

### 변경 사항
- `frontend/gui/panels/__init__.py`: 패널 패키지 초기화
- `frontend/gui/state/__init__.py`: 상태 관리 패키지 초기화

### 검증 결과
- ruff check: ✅

---

## Step 5: dashboard_state.py 생성 (순서 변경 - 다른 패널의 의존성)

### 변경 사항
- `frontend/gui/state/dashboard_state.py`: 
  - `DashboardState` 클래스: 중앙 상태 관리자
  - `Tier2Item` dataclass: Hot Zone 종목 모델
  - 시그널: tier2_updated, ignition_updated, price_updated, chart_ticker_changed, log_message

### 설계 결정
- 싱글톤 대신 DI 패턴 사용
- QObject 상속으로 Qt 시그널 지원

---

## Step 4: LogPanel 분리

### 변경 사항
- `frontend/gui/panels/log_panel.py`:
  - `LogPanel(QFrame)` 클래스
  - `log()` 메서드: 타임스탬프 + 자동 스크롤
  - DashboardState.log_message 시그널 연결

### 검증 결과
- ruff check: ✅

---

## Step 3: Tier2Panel 분리

### 변경 사항
- `frontend/gui/panels/tier2_panel.py`:
  - `Tier2Panel(QFrame)` 클래스
  - `NumericTableWidgetItem` 클래스: 숫자 정렬 지원
  - `set_row_data()`, `add_row()`, `remove_row_by_ticker()` 메서드
  - 컬럼: Ticker, Price, Chg%, zenV, zenP, Ign, Sig
  - Z-Score 색상 코딩 (Orange/Green/Gray)

### 검증 결과
- ruff check: ✅

---

## Step 2: WatchlistPanel 분리

### 변경 사항
- `frontend/gui/panels/watchlist_panel.py`:
  - `WatchlistPanel(QFrame)` 클래스
  - Tier2Panel 포함 (상단 Hot Zone)
  - QTableView + QSortFilterProxyModel (정렬 유지)
  - Score V3 Refresh 버튼 + Last Updated 라벨
  - 시그널: tier1_row_clicked, tier2_row_clicked, refresh_score_clicked

### 검증 결과
- ruff check: ✅

---

## Step 6: dashboard.py 정리
(진행 중...)

### 변경 사항
- 신규 패널 모듈 import 준비 완료
- dashboard.py 완전 통합은 Phase 2에서 진행 예정

### 파일 라인 수 검증

| 파일 | 라인 수 | 목표 충족 |
|------|--------|----------|
| `log_panel.py` | 104 | ✅ ≤500 |
| `tier2_panel.py` | 284 | ✅ ≤500 |
| `watchlist_panel.py` | 278 | ✅ ≤500 |
| `dashboard_state.py` | 181 | ✅ ≤500 |
| `panels/__init__.py` | 22 | ✅ |
| `state/__init__.py` | 16 | ✅ |

---

## 최종 검증 결과

| 검증 항목 | 결과 |
|----------|------|
| ruff format | ✅ |
| ruff check | ✅ |
| Import 테스트 | ✅ |
| 파일 라인 수 | ✅ (모두 ≤500) |
| 순환 의존성 | ✅ (없음) |

---

## 다음 단계

> **Phase 2**: dashboard.py에서 새 패널 사용하도록 점진적 마이그레이션
> 
> 현재 패널 모듈들이 준비되었으나, dashboard.py의 2,616줄을 한번에 변경하면 위험합니다.
> 별도 PR에서 점진적으로 통합할 예정입니다.

### 통합 절차 (Phase 2)
1. `_create_left_panel()` → `WatchlistPanel` 사용으로 교체
2. `_create_bottom_panel()` → `LogPanel` 사용으로 교체
3. 이벤트 핸들러들을 패널 시그널에 연결
4. `Tier2Item`, `NumericTableWidgetItem` 중복 제거
5. `DashboardState` 도입 및 캐시 마이그레이션

---

# Phase 2: dashboard.py 통합 (2026-01-08 01:45)

## Phase 2 진행 현황

| Step | 상태 | 완료 시간 |
|------|------|----------|
| P2-1: LogPanel 통합 | ✅ 완료 | 01:45 |
| P2-2: WatchlistPanel 통합 | ✅ 완료 | 01:50 |
| P2-3: 중복 클래스 제거 | 📋 대기 (Phase 3) | - |
| P2-4: 이벤트 핸들러 연결 | ✅ 완료 | 01:50 |
| P2-5: 최종 검증 | ✅ 완료 | 01:52 |

---

## P2-1: LogPanel 통합

### 변경 사항
- `_create_bottom_panel()` 메서드를 LogPanel 사용으로 교체
- 약 30줄 → 13줄 (17줄 감소)
- `self.log_console` 호환성 유지

### 검증 결과
- Import 테스트: ✅

---

## P2-2: WatchlistPanel 통합

### 변경 사항
- `_create_left_panel()` 메서드를 WatchlistPanel 사용으로 교체
- 약 250줄 → 60줄 (190줄 감소)
- 호환성 속성 포워딩 유지:
  - `self.tier2_table`
  - `self.watchlist_model`, `self.watchlist_proxy`, `self.watchlist_table`
  - `self._score_v2_updated_label`, `self._refresh_score_v2_btn`
  - `self._tier2_cache`

### 시그널 연결
- `tier2_row_clicked` → `_on_tier2_table_clicked`
- `tier1_row_clicked` → `_on_watchlist_table_clicked`
- `refresh_score_clicked` → `_on_refresh_score_v2`

### 검증 결과
- Import 테스트: ✅

---

## Phase 2 최종 결과

| 지표 | Before | After | 변화 |
|------|--------|-------|------|
| dashboard.py 라인 수 | 2,616 | 2,362 | **-254줄** |
| LogPanel 코드 | inline | 분리 | 모듈화 |
| WatchlistPanel 코드 | inline | 분리 | 모듈화 |

### 검증 항목
- ✅ Import 테스트 통과
- ✅ ruff check (신규 코드)
- 📋 GUI 실행 테스트 (사용자 확인 필요)

---

## 다음 단계 (Phase 3)

1. `Tier2Item`, `NumericTableWidgetItem` 중복 클래스 제거
2. 기타 패널 분리 (ChartPanel, RightPanel 등)
3. dashboard.py ≤500줄 목표 달성
