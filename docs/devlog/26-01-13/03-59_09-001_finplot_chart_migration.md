# Finplot Chart Migration Devlog

> **작성일**: 2026-01-10
> **상태**: ✅ **완료**
> **계획서**: [09-001_finplot_chart_migration.md](../../Plan/refactor/09-001_finplot_chart_migration.md)

## 최종 결과

| 지표 | 변경 전 | 변경 후 |
|-----|--------|--------|
| 차트 코드 라인 수 | 1,461줄 | ~350줄 |
| 코드 감소율 | - | **~76%** |
| 라이브러리 | PyQtGraph (수동 구현) | finplot (내장 기능) |
| Step 0: 아카이빙 | ✅ | 08:31 |
| Step 2: 핵심 구현 | ✅ | 08:35 |
| Step 3: 패널 통합 | ✅ | 08:38 |
| Step 4: 검증 | ✅ | 08:40 |

---

## Step 0: 기존 차트 아카이빙

### 변경 사항
- `frontend/gui/chart/_legacy/` 디렉토리 생성
- `pyqtgraph_chart.py` (1,192줄) → `_legacy/` 이동
- `candlestick_item.py` (269줄) → `_legacy/` 이동

### 검증
- 롤백 필요 시 `_legacy/` 파일로 즉시 복원 가능

---

## Step 2: 핵심 위젯 구현

### 변경 사항
- `frontend/gui/chart/finplot_chart.py` 신규 생성 (~350줄)

### 주요 구현
- `FinplotChartWidget` 클래스 - finplot 기반 차트 위젯
- 기존 `PyQtGraphChartWidget`과 동일한 시그널/메서드 인터페이스 유지:
  - `timeframe_changed`, `chart_clicked`, `viewport_data_needed` 시그널
  - `set_candlestick_data()`, `set_volume_data()`, `set_vwap_data()`
  - `set_ma_data()`, `set_atr_bands()`, `set_price_levels()`
  - `add_ignition_marker()`
- 테마 연동: `theme.colors["chart_up"]`, `chart_down` 등 사용
- Acrylic 투명 배경 설정: `WA_TranslucentBackground`

### 검증
- ruff check: ✅ All checks passed

---

## Step 3: 패널 통합

### 변경 사항
- `frontend/gui/chart/__init__.py`: `PyQtGraphChartWidget` → `FinplotChartWidget` 익스포트
- `frontend/gui/panels/chart_panel.py`:
  - import 변경: `from ..chart.finplot_chart import FinplotChartWidget`
  - 타입 힌트 변경: `_chart_widget: FinplotChartWidget`
  - E741 린트 오류 수정: 변수명 `l` → `low_val`

### 검증
- ruff check: ✅ All checks passed
- lint-imports: ✅ 통과

---

## Step 4: 최종 검증

### 자동화 검증
```bash
ruff check frontend/gui/chart/finplot_chart.py frontend/gui/chart/__init__.py \
           frontend/gui/chart/chart_data_manager.py frontend/gui/panels/chart_panel.py
# Result: All checks passed!

lint-imports
# Result: 통과 (ASCII art 출력)
```

### 수동 GUI 테스트 (필요)
```bash
# 1. 백엔드 서버 실행
python -m backend

# 2. 프론트엔드 GUI 실행
python -m frontend

# 3. 워치리스트에서 종목 클릭 → 차트 패널 확인
```

---

## 요약

| 지표 | 변경 전 | 변경 후 |
|-----|--------|--------|
| 차트 코드 라인 수 | 1,461줄 | ~350줄 |
| 코드 감소율 | - | **~76%** |
| 라이브러리 | PyQtGraph (수동 구현) | finplot (내장 기능) |
| Acrylic 호환 | ✅ | ✅ (유지) |

### 롤백 방법
1. `chart_panel.py`에서 import를 `_legacy/pyqtgraph_chart`로 변경
2. `__init__.py` 익스포트 복원
3. GUI 재시작

---

## 트러블슈팅: 실패 원인 및 최종 해결

### ❌ 시도 1: `create_plot_widget` + `fplt.windows[-1]`

```python
# 잘못된 방식
axes = fplt.create_plot_widget(master=dummy, rows=2)
layout.addWidget(fplt.windows[-1])  # ← 윈도우와 axes가 분리됨
```

**실패 원인**: 
- `create_plot_widget`은 axes만 반환
- `fplt.windows[-1]`은 별도 윈도우 객체
- 두 객체가 **연결되지 않아** 차트 미표시

---

### ❌ 시도 2: `create_plot_widget` + master에 직접 임베딩

```python
# 잘못된 방식
axes = fplt.create_plot_widget(master=self._chart_container, rows=2)
layout.addWidget(self._chart_container)
```

**실패 원인**:
- finplot이 master에 자식 위젯을 **자동 추가하지 않음**
- `self._chart_container.children() == []` (비어있음)

---

### ❌ 시도 3: `volume_ocv` 잘못된 컬럼

```python
# 잘못된 방식
fplt.volume_ocv(df[["Volume"]], ax=self.ax_volume)
```

**실패 원인**:
- **AssertionError: too few columns supplied**
- `volume_ocv`는 Open, Close, Volume **3개 컬럼 필요** (ocv = Open, Close, Volume)

---

### ✅ 최종 해결: 공식 `embed.py` 예제 패턴

> **참조**: [finplot/examples/embed.py](https://github.com/highfestiva/finplot/blob/master/finplot/examples/embed.py)

```python
# 올바른 방식
# 1. create_plot() 사용 (not create_plot_widget!)
self.ax = fplt.create_plot(init_zoom_periods=100)

# 2. overlay()로 볼륨 차트 생성 (별도 axes 아님)
self.ax_volume = self.ax.overlay()

# 3. 위젯에 axs 속성 설정 (finplot 요구사항)
self.axs = [self.ax, self.ax_volume]

# 4. ax.vb.win을 레이아웃에 추가 (핵심!)
layout.addWidget(self.ax.vb.win, stretch=1)

# 5. Qt 이벤트 루프 분리
fplt.show(qt_exec=False)
```

**성공 이유**:
- `ax.vb.win`은 실제 렌더링되는 **ViewBox의 윈도우**
- `overlay()`는 같은 윈도우 내에서 볼륨을 오버레이
- axes와 윈도우가 **올바르게 연결**됨

---

## 핵심 교훈

1. **공식 예제 먼저 확인**: `create_plot_widget` 문서가 불완전, 공식 예제가 정답
2. **API 함수명 주의**: `candlestick_ochl`, `volume_ocv` 등 컬럼 순서가 함수명에 포함
3. **디버깅 시 객체 관계 확인**: `axes`, `fplt.windows`, `ax.vb.win` 간 관계 파악 중요
