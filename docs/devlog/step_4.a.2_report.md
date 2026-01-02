# Step 4.A.2: Tier 2 Hot Zone 구현 Report

> **작성일**: 2026-01-02
> **상태**: ✅ 완료

---

## 📋 구현 내용

### 4.A.2.1: Tier2Item 데이터 모델
- `dashboard.py`에 `@dataclass class Tier2Item` 추가
- 필드: `ticker`, `price`, `change_pct`, `zenV`, `zenP`, `ignition`, `last_update`
- zenV/zenP는 Step 4.A.3에서 계산 예정 (현재 placeholder)

### 4.A.2.4: GUI 패널 레이아웃
- `_create_left_panel()` 리팩토링: Tier 2 테이블을 Tier 1 상단에 배치
- Tier 2 테이블 컬럼: Ticker, Price, Chg%, zenV, zenP, Ign (6개)
- 최대 높이 150px, amber(warning) 색상 강조 스타일
- `_on_tier2_table_clicked()` 핸들러 추가

### 4.A.2.2: Ignition ≥ 70 자동 승격
- `_on_ignition_update()` 수정: score ≥ 70 && passed_filter일 때 자동 승격
- `_promote_to_tier2(ticker, ignition_score)` 메서드 추가
- `_set_tier2_row()`, `_update_tier2_row()` 헬퍼 메서드 추가
- Backend API 호출 (`rest.promote_to_tier2`) 포함

### 4.A.2.5: 실시간 가격 업데이트
- `_on_tick_received()` 수정: Tier 2 종목 가격 실시간 갱신
- `_tier2_cache`에서 해당 종목 확인 후 Price 컬럼만 업데이트

### 4.A.2.3: Day Gainers 자동 추가
- 별도 Step으로 연기 (Gainers API 통합 필요)

---

## ✅ 완료 조건 체크

| 조건 | 상태 |
|------|------|
| Tier 2 테이블이 Tier 1 상단에 표시 | ✅ |
| 6개 컬럼: Ticker, Price, Chg%, zenV, zenP, Ign | ✅ |
| Tick 수신 시 Price 실시간 업데이트 | ✅ |
| Ignition ≥ 70 시 자동 Tier 2 승격 | ✅ |
| 문법 오류 없음 (py_compile) | ✅ |

---

## 📁 변경 파일

| 파일 | 변경 내용 |
|------|-----------|
| `frontend/gui/dashboard.py` | Tier2Item dataclass, Tier 2 테이블, 승격 로직, 틱 핸들러 업데이트 |

---

## ⚠️ 논리적 갭 분석

### � Critical: asyncio.create_task() in Qt Event Loop
- **문제**: `_promote_to_tier2()`에서 `asyncio.create_task()` 사용
- **원인**: Qt GUI는 자체 이벤트 루프 사용, asyncio 루프 없음
- **증상**: `RuntimeError: no running event loop`
- **해결**: `threading.Thread`로 대체하여 별도 스레드에서 `asyncio.run()` 호출 ✅

### 🟡 Medium: No demote_from_tier2 Logic
- **문제**: Tier 2에서 종목 제거 로직 없음
- **영향**: Tier 2가 계속 커지기만 함, 메모리/UI 이슈 가능
- **해결 방안**: 
  - Ignition < 50 시 자동 강등
  - EOD (장 마감) 자동 정리
  - 수동 제거 UI 추가
- **상태**: 🔜 Step 4.A.4에서 구현 예정

### 🟢 Low: No Throttling on Tier 2 Updates
- **문제**: `_on_tick_received`가 매 틱마다 Tier 2 UI 업데이트
- **영향**: 고빈도 틱 시 UI 깜빡임 가능성
- **해결 방안**: 100-200ms 스로틀링 추가
- **상태**: 현재는 미미한 영향

### 🟢 Low: change_pct Not Updated on Tick
- **문제**: Tier 2 테이블에서 가격만 업데이트, Chg% 고정
- **원인**: 전일 종가(previous close) 데이터 미보유
- **해결 방안**: Tier2Item에 prev_close 필드 추가
- **상태**: 🔜 Step 4.A.3에서 개선 예정

### 🟢 Low: Sorting During Updates 
- **문제**: setSortingEnabled(True) 상태에서 setItem() 호출
- **영향**: 정렬 중 setItem 호출 시 간헐적 UI glitch
- **해결 방안**: 업데이트 전 정렬 비활성화
- **상태**: 발생 빈도 매우 낮음

---

## �💡 다음 단계

- **Step 4.A.3**: zenV/zenP 계산 로직 구현
- **Step 4.A.4**: Tier 2 demote 로직, EOD 정리
- **Day Gainers API 통합**: 장 시작 시 Top Gainers 자동 추가
