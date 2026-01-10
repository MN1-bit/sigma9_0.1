# 05-002: dashboard.py 분리 Phase 3-4 리팩터링 계획서

> **작성일**: 2026-01-08 15:34
> **우선순위**: 5 | **예상 소요**: 4-6h | **위험도**: 중간
> **선행 작업**: [05-001](./05-001_dashboard_split.md) Phase 1-2 완료

## 1. 목표

`dashboard.py` (현재 2,585줄) → **≤500줄** 목표 달성

**현재 상태 (Phase 2 완료)**:
| 항목 | 상태 |
|------|------|
| LogPanel 분리/통합 | ✅ 완료 |
| WatchlistPanel 분리/통합 | ✅ 완료 |
| Tier2Panel 분리 | ✅ 완료 |
| DashboardState 생성 | ✅ 완료 |
| 중복 클래스 제거 | 📋 Phase 3 |
| ChartPanel/RightPanel 분리 | 📋 Phase 4 |

---

## 2. 영향 분석

### 중복 클래스 현황

| 클래스 | dashboard.py | 중복 위치 | 조치 |
|--------|-------------|----------|------|
| `Tier2Item` | L98-113 | `state/dashboard_state.py` | 삭제 → import |
| `NumericTableWidgetItem` | L119-145 | `panels/tier2_panel.py` | 삭제 → import |

### 추출 대상 (Phase 4)

| 대상 | 라인 | 신규 파일 |
|------|------|----------|
| Chart | ~90 | `panels/chart_panel.py` |
| Position | ~75 | `panels/position_panel.py` |
| Oracle (LLM) | ~80 | `panels/oracle_panel.py` |

---

## 3. 실행 계획

### Phase 3: 중복 클래스 제거

#### Step 3-1: Tier2Item 제거
```diff
- from dataclasses import dataclass
- @dataclass
- class Tier2Item:
-     ...
+ from .state.dashboard_state import Tier2Item
```

#### Step 3-2: NumericTableWidgetItem 제거
```diff
- class NumericTableWidgetItem(QTableWidgetItem):
-     ...
+ from .panels.tier2_panel import NumericTableWidgetItem
```

### Phase 4: 패널 분리 (별도 PR 권장)

#### Step 4-1: ChartPanel 분리
- `_create_center_panel()`, `_load_sample_chart_data()` 추출

#### Step 4-2: PositionPanel 분리
- Trading Section (L968-1023): P&L 요약, Active Positions 리스트

#### Step 4-3: OraclePanel 분리
- Oracle Section (L1025-1085): LLM 분석 버튼, 결과 표시 영역
- `_get_oracle_btn_style()` (L1090-1106)

---

## 4. 목표 라인 수

| 파일 | Phase 3 후 | Phase 4 후 |
|------|-----------|-----------|
| `dashboard.py` | ~2,540 | ~1,700 |
| `chart_panel.py` | - | ~90 |
| `position_panel.py` | - | ~75 |
| `oracle_panel.py` | - | ~80 |

---

## 5. 검증 계획

```bash
# Lint
ruff format --check frontend/gui/ && ruff check frontend/gui/

# Import 테스트
python -c "from frontend.gui.dashboard import Sigma9Dashboard; print('OK')"

# 순환 의존성
pydeps frontend.gui --only frontend.gui --show-cycles --no-output
```

- [ ] GUI 정상 실행
- [ ] Watchlist/Tier2 동작
- [ ] 차트 표시

---

## 6. 롤백 계획

```bash
git checkout HEAD -- frontend/gui/dashboard.py
```
