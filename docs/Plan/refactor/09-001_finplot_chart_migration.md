# Finplot 차트 마이그레이션 리팩터링 계획서

> **작성일**: 2026-01-10 02:22  
> **우선순위**: 09 (GUI 개선) | **예상 소요**: 8-12h | **위험도**: 중간

---

## 1. 목표

현재 PyQtGraph 기반 수동 구현 차트(~2,003줄)를 **finplot** 라이브러리로 교체하여:

1. **코드 복잡도 80% 이상 감소** - 1,500줄 → ~200줄 목표
2. **안정성 향상** - 검증된 오픈소스 라이브러리 활용
3. **기능 확장 용이성** - 내장 RSI, MACD, Bollinger 등 즉시 사용 가능
4. **유지보수 비용 절감** - 커스텀 캔들스틱 렌더링 로직 제거

---

## 2. 영향 분석

### 2.1 변경 대상 파일

| 파일 | 라인수 | 변경 유형 | 비고 |
|:-----|:------:|:----------|:-----|
| `frontend/gui/chart/pyqtgraph_chart.py` | 1,192 | **DELETE** | finplot 위젯으로 대체 |
| `frontend/gui/chart/candlestick_item.py` | 269 | **DELETE** | finplot 내장 캔들 사용 |
| `frontend/gui/chart/chart_data_manager.py` | 307 | **MODIFY** | DataFrame 출력 지원 |
| `frontend/gui/chart/__init__.py` | 10 | **MODIFY** | export 변경 |
| `frontend/gui/panels/chart_panel.py` | 235 | **MODIFY** | finplot 위젯 래핑 |
| `frontend/gui/chart/finplot_chart.py` | - | **NEW** | 신규 차트 위젯 (~200줄) |

**총 예상 변경**: -1,461줄 (삭제) + 200줄 (신규) = **~1,261줄 순감**

### 2.2 영향받는 모듈

| 모듈 | 영향 범위 | 필요 조치 |
|:-----|:---------|:----------|
| `frontend/gui/panels/chart_panel.py` | import 경로 | `PyQtGraphChartWidget` → `FinplotChartWidget` |
| `frontend/gui/dashboard.py` | 간접 (chart_panel 통해) | 변경 없음 |
| `frontend/services/chart_data_service.py` | 데이터 포맷 | DataFrame 출력 메서드 추가 |

### 2.3 순환 의존성 현황

- ✅ 순환 의존성 없음 (`pydeps --show-cycles` 확인)
- 차트 모듈은 독립적 UI 레이어로 다른 모듈과 순환 없음

---

## 3. 실행 계획

### Step 1: 인프라 준비 (예상 2h)

#### 1.1 환경 설정 확인
```python
# finplot이 PyQt6를 사용하도록 환경 변수 설정 확인
os.environ['QT_API'] = 'pyqt6'
```

#### 1.2 chart_data_service DataFrame 출력 지원
- `ChartDataService.get_chart_data()` 반환값에 pandas DataFrame 옵션 추가
- 기존 dict 반환은 호환성 유지

---

### Step 2: 핵심 위젯 구현 (예상 4h)

#### 2.1 `finplot_chart.py` 신규 생성

```python
# frontend/gui/chart/finplot_chart.py (~200줄 예상)
class FinplotChartWidget(QWidget):
    """finplot 기반 차트 위젯"""
    
    timeframe_changed = pyqtSignal(str)  # 기존 시그널 유지
    more_data_needed = pyqtSignal(int, int)  # 스크롤 시 추가 데이터 요청
    
    def __init__(self, parent=None):
        # finplot 윈도우를 PyQt6에 임베딩
        self.ax, self.ax_volume = fplt.create_plot(rows=2)
        self.plot_widget = fplt.pg.PlotWidget(plotItem=self.ax.vb)
        
    def set_candlestick_data(self, df: pd.DataFrame):
        fplt.candlestick_ochl(df)
        fplt.volume_ocv(df)
        
    def set_vwap_data(self, df: pd.DataFrame):
        fplt.plot(df['vwap'], legend='VWAP')
```

#### 2.2 기존 인터페이스 호환
- `set_candlestick_data()`, `set_volume_data()`, `set_vwap_data()` 등 기존 메서드 시그니처 유지
- `timeframe_changed` 시그널 유지로 dashboard.py 변경 최소화

---

### Step 3: 패널 통합 및 테마 적용 (예상 3h)

#### 3.1 chart_panel.py 수정
```python
# 기존
from ..chart.pyqtgraph_chart import PyQtGraphChartWidget

# 변경
from ..chart.finplot_chart import FinplotChartWidget
```

#### 3.2 Acrylic 투명 배경 적용
```python
# finplot PlotWidget에 투명 배경 설정
self.plot_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
self.plot_widget.setBackground(QColor(0, 0, 0, 0))
```

#### 3.3 테마 색상 적용
```python
fplt.candle_bull_color = theme.get('success')  # #22c55e
fplt.candle_bear_color = theme.get('error')    # #ef4444
fplt.background = theme.get('surface')
```

---

### Step 4: 레거시 정리 및 검증 (예상 2h)

#### 4.1 삭제 대상
- `frontend/gui/chart/pyqtgraph_chart.py` (1,192줄)
- `frontend/gui/chart/candlestick_item.py` (269줄)

#### 4.2 import 경로 정리
- `frontend/gui/chart/__init__.py` 업데이트

---

## 4. 검증 계획

### 4.1 수동 테스트 (필수)

> [!IMPORTANT]  
> 차트 테스트는 시각적 검증이 필수이므로 자동화 테스트 외 수동 확인 필요

| 테스트 항목 | 검증 방법 | 예상 결과 |
|:-----------|:---------|:----------|
| 캔들스틱 렌더링 | GUI 실행 후 종목 선택 | OHLC 캔들 정상 표시 |
| 볼륨 차트 | 하단 서브차트 확인 | 볼륨 바 정상 표시 |
| VWAP 오버레이 | 차트 위 라인 확인 | 보라색 VWAP 라인 표시 |
| 타임프레임 전환 | 1m/5m/1h/1d 버튼 클릭 | 데이터 갱신, UI 반응 |
| 줌/팬 | 마우스 휠/드래그 | 부드러운 인터랙션 |
| Acrylic 투명도 | 윈도우 뒤 배경 확인 | 반투명 효과 유지 |

**수동 테스트 실행 방법**:
```bash
# 1. 백엔드 서버 실행
python -m backend

# 2. 프론트엔드 GUI 실행
python -m frontend

# 3. 워치리스트에서 종목 클릭 → 차트 패널 확인
```

### 4.2 린트 및 타입 검사

```bash
# 필수 검증 명령어
ruff check frontend/gui/chart/
mypy frontend/gui/chart/ --ignore-missing-imports
lint-imports
```

### 4.3 (선택) 단위 테스트 추가

> 현재 차트 관련 테스트가 없으므로, 기본 테스트 추가 권장

```python
# tests/test_finplot_chart.py
def test_chart_widget_import():
    """Import 경로 검증"""
    from frontend.gui.chart import FinplotChartWidget
    assert FinplotChartWidget is not None

def test_chart_data_format():
    """DataFrame 출력 검증"""
    from frontend.services.chart_data_service import ChartDataService
    service = ChartDataService()
    data = service.get_chart_data("AAPL", as_dataframe=True)
    assert hasattr(data, 'columns')
```

---

## 5. 롤백 계획

### 5.1 즉시 롤백
삭제 예정 파일들은 마이그레이션 완료 전까지 `/frontend/gui/chart/_legacy/`로 이동:
```
frontend/gui/chart/
├── _legacy/                     # 롤백용 백업
│   ├── pyqtgraph_chart.py
│   └── candlestick_item.py
├── finplot_chart.py             # 신규
└── chart_data_manager.py        # 수정
```

### 5.2 롤백 절차
1. `chart_panel.py`에서 import를 `_legacy/pyqtgraph_chart`로 변경
2. GUI 재시작 후 정상 동작 확인
3. 문제 해결 후 다시 finplot으로 전환

---

## 6. 위험 요소 및 대응

| 위험 | 확률 | 대응 |
|:----|:----:|:-----|
| Acrylic 플리커링 | 중간 | `WA_TranslucentBackground` 수동 전파, PoC에서 해결책 확인됨 |
| 실시간 업데이트 지연 | 낮음 | `fplt.timer_callback` + 마지막 캔들 직접 업데이트 |
| 기존 API 호환성 | 낮음 | 메서드 시그니처 동일하게 유지 |
| 타임프레임 버튼 UI | 낮음 | 기존 버튼 로직 그대로 재사용 |

---

## 7. 참조 문서

- [PoC 결과](../../references/research/003_finplot_feature_reference.md)
- [Draft 계획](./09-001_finplot_chart_migration_draft.md)
- [KI: Trading Visualization](C:/Users/USER/.gemini/antigravity/knowledge/trading_visualization_and_charting/overview.md)
