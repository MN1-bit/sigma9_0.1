# 05-003: dashboard.py 분리 Phase 4 리팩터링 계획서

> **작성일**: 2026-01-08 16:00  
> **수정일**: 2026-01-08 16:05  
> **우선순위**: 5 | **예상 소요**: 2-3h | **위험도**: 중간  
> **선행 작업**: [05-002](./05-002_dashboard_split_phase3.md) Phase 3 완료

---

## 1. 목표

`dashboard.py` (현재 2,532줄) → **~2,200줄** 목표 (약 300줄 감소)

> [!NOTE]
> Phase 4에서는 ChartPanel, RightPanel(Position+Oracle) 분리를 통해 중간 규모 감소를 달성합니다.
> 500줄 이하 도달은 Phase 5 (데이터/비즈니스 로직 Backend 이전)에서 진행 예정.

---

## 2. 현재 상태 분석

### 2.1 완료된 작업

| 작업 | 상태 | 비고 |
|------|------|------|
| Step 4-0: Tier2Item 위치 이동 | ✅ 완료 | `tier2_panel.py:L38`에 정의, `dashboard_state.py:L21`에서 import |
| Tier2Item 하위호환 export | ✅ 완료 | `dashboard_state.py:L27` `__all__` |
| Tier2Panel 사용 | ✅ 완료 | `watchlist_panel.py`에서 인스턴스화 |

### 2.2 추출 대상 (정확한 라인 범위)

| 메서드 | 라인 범위 | 라인 수 | 대상 파일 |
|--------|-----------|---------|-----------|
| `_create_center_panel()` | L778-805 | 28 | `panels/chart_panel.py` |
| `_load_sample_chart_data()` | L807-896 | 90 | `panels/chart_panel.py` |
| `_create_right_panel()` | L898-1035 | 138 | `panels/right_panel.py` |
| `_get_oracle_btn_style()` | L1037-1053 | 17 | `panels/right_panel.py` |

**예상 감소**: ~270줄 (교체/import 코드 추가로 순감소 ~250줄)

---

## 3. 실행 계획

### Step 4-1: ChartPanel 분리 (~120줄 감소)

#### [NEW] `panels/chart_panel.py`

```python
class ChartPanel(QFrame):
    """차트 영역 패널 - PyQtGraph 래퍼"""
    
    timeframe_changed = pyqtSignal(str)
    viewport_data_needed = pyqtSignal(str, str, int, int)
    
    def __init__(self, theme=None):
        ...
    
    def load_sample_data(self):
        """샘플 데이터 로드"""
        ...
    
    @property
    def chart_widget(self) -> PyQtGraphChartWidget:
        """차트 위젯 접근자"""
        ...
```

#### [MODIFY] `dashboard.py`

```diff
- def _create_center_panel(self) -> QFrame:
-     ... (28줄)
-
- def _load_sample_chart_data(self):
-     ... (90줄)

+ from .panels.chart_panel import ChartPanel
+ 
+ def _create_center_panel(self) -> QFrame:
+     self._chart_panel = ChartPanel(theme=theme)
+     self._chart_panel.timeframe_changed.connect(self._on_timeframe_changed)
+     self._chart_panel.viewport_data_needed.connect(self._on_viewport_data_needed)
+     # 호환성
+     self.chart_widget = self._chart_panel.chart_widget
+     return self._chart_panel
```

---

### Step 4-2: RightPanel 분리 (~155줄 감소)

#### [NEW] `panels/right_panel.py`

```python
class RightPanel(QFrame):
    """오른쪽 패널 - Positions & P&L + Oracle"""
    
    oracle_why_clicked = pyqtSignal()
    oracle_fundamental_clicked = pyqtSignal()
    oracle_reflection_clicked = pyqtSignal()
    
    def __init__(self, theme=None):
        ...
    
    @property
    def pnl_value(self) -> QLabel:
        ...
    
    @property
    def positions_list(self) -> QListWidget:
        ...
    
    @property
    def oracle_result(self) -> QTextEdit:
        ...
```

#### [MODIFY] `dashboard.py`

```diff
- def _create_right_panel(self) -> QFrame:
-     ... (138줄)
-
- def _get_oracle_btn_style(self) -> str:
-     ... (17줄)

+ from .panels.right_panel import RightPanel
+ 
+ def _create_right_panel(self) -> QFrame:
+     self._right_panel = RightPanel(theme=theme)
+     # 호환성 포워딩
+     self.pnl_value = self._right_panel.pnl_value
+     self.positions_list = self._right_panel.positions_list
+     self.oracle_result = self._right_panel.oracle_result
+     self.oracle_why_btn = self._right_panel.oracle_why_btn
+     self.oracle_fundamental_btn = self._right_panel.oracle_fundamental_btn
+     self.oracle_reflection_btn = self._right_panel.oracle_reflection_btn
+     return self._right_panel
```

---

### Step 4-3: `panels/__init__.py` 업데이트

```python
# panels/__init__.py
from .chart_panel import ChartPanel
from .right_panel import RightPanel
from .tier2_panel import Tier2Item, NumericTableWidgetItem, Tier2Panel
from .watchlist_panel import WatchlistPanel
from .log_panel import LogPanel

__all__ = [
    "ChartPanel",
    "RightPanel",
    "Tier2Item",
    "NumericTableWidgetItem",
    "Tier2Panel",
    "WatchlistPanel",
    "LogPanel",
]
```

---

## 4. 영향 분석

### 4.1 변경 파일

| 파일 | 변경 유형 | 영향도 |
|------|----------|--------|
| `panels/chart_panel.py` | NEW | 낮음 |
| `panels/right_panel.py` | NEW | 낮음 |
| `panels/__init__.py` | MODIFY | 낮음 |
| `dashboard.py` | MODIFY | 중간 |

### 4.2 의존성

- `ChartPanel` → `PyQtGraphChartWidget` (기존)
- `RightPanel` → `theme`, `QListWidget`, `QTextEdit` (기존)
- 순환 의존성: 없음

---

## 5. 검증 계획

```bash
# 1. Lint 검사
ruff check frontend/gui/ --select=F401,F811

# 2. Import 검증
python -c "from frontend.gui.dashboard import Sigma9Dashboard; print('OK')"
python -c "from frontend.gui.panels import ChartPanel, RightPanel; print('OK')"

# 3. 파일 라인 수 확인
python -c "print(len(open('frontend/gui/dashboard.py').readlines()), 'lines')"
```

### 5.1 수동 검증 (선택)

1. `python -m frontend` 실행
2. 차트 영역 정상 표시 확인
3. Right Panel (P&L, Oracle) 정상 표시 확인
4. Oracle 버튼 스타일 확인

---

## 6. 롤백 계획

```bash
git checkout HEAD -- frontend/gui/
```

---

## 7. 향후 계획 (Phase 5)

> [!IMPORTANT]
> Phase 4 완료 후에도 dashboard.py는 ~2,200줄 (목표 500줄 미달).
> 근본적인 원인은 **데이터 로딩/비즈니스 로직이 Frontend에 내장**되어 있기 때문.

Phase 5 계획 ([05-004](./05-004_frontend_backend_separation.md)):
- `_load_chart_for_ticker()` → Backend API 이동
- `_check_tier2_promotion()` → Backend 로직 이동
- Historical bar 페칭 → Backend 전담

---

## Appendix: 라인 범위 검증 기록

```
# 2026-01-08 16:00 검증
dashboard.py 총 라인: 2,532

_create_center_panel: L778-805 (28줄)
_load_sample_chart_data: L807-896 (90줄)
_create_right_panel: L898-1035 (138줄)
_get_oracle_btn_style: L1037-1053 (17줄)
```
