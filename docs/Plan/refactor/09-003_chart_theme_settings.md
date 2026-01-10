# Finplot 차트 UI 개선 (타임프레임 + 테마)

> **상태**: 📋 **구현 계획** (09-002 완료 후 진행)
> **작성일**: 2026-01-10
> **예상 작업 시간**: 4h
> **선행 작업**: [09-002_finplot_chart_enhancements.md](./09-002_finplot_chart_enhancements.md)
> **레이어**: Frontend

---

## 1. 목표

1. **타임프레임 버튼** - 1m/3m/5m/15m/1h/4h/1D/1W 지원
2. **차트 색상 GUI** - Settings Window에서 직접 조작
3. **Hot Reload** - 설정 변경 즉시 반영

---

## 2. 타임프레임 UI

### 2.1 버튼 확장

```python
# finplot_chart.py
TIMEFRAMES = ["1m", "3m", "5m", "15m", "1h", "4h", "1D", "1W"]
```

### 2.2 ChartDataService 수정

```python
async def get_chart_data(self, ticker: str, timeframe: str):
    # 09-002에서 생성된 Parquet 직접 로드
    df = self._get_repo().get_intraday_bars(ticker, timeframe)
    return self._df_to_chart_format(df)
```

---

## 3. 차트 테마 GUI

### 3.1 settings.yaml 확장

```yaml
chart:
  colors:
    candle_bull: "#22c55e"
    candle_bear: "#ef4444"
    volume_bull: "#22c55e"
    volume_bear: "#ef4444"
    crosshair: "#999999"
```

### 3.2 Hot Reload 연결

```python
# FinplotChartWidget
theme.theme_changed.connect(self._apply_chart_theme)
```

### 3.3 Settings Window Chart 탭

- ColorPicker 위젯 (캔들/볼륨/Crosshair)
- 변경 시 `save_setting()` + `theme.reload()`

---

## 4. 변경 파일

| 파일 | 설명 |
|------|------|
| `frontend/gui/chart/finplot_chart.py` | 버튼 확장 + Hot Reload |
| `frontend/services/chart_data_service.py` | 타임프레임 로드 |
| `frontend/gui/panels/settings_panel.py` | Chart 탭 + ColorPicker |
| `frontend/gui/theme.py` | `get_chart_colors()` |
| `frontend/config/settings.yaml` | `chart.colors` 추가 |

---

## 5. 실행 단계

### Step 1: 타임프레임 버튼 확장 (0.5h)
### Step 2: ChartDataService 수정 (0.5h)
### Step 3: settings.yaml 확장 (0.3h)
### Step 4: ThemeManager 확장 (0.5h)
### Step 5: FinplotChartWidget Hot Reload (0.7h)
### Step 6: Settings Window Chart 탭 (1h)
### Step 7: 검증 (0.5h)

---

## 6. 검증

| # | 항목 | 예상 결과 |
|---|------|----------|
| 1 | 5m 버튼 | 5분봉 차트 표시 |
| 2 | GUI 색상 변경 | 즉시 차트 반영 |
| 3 | 앱 재시작 | 변경 유지 |

---

## 7. 다음 단계

- [ ] 09-002 완료 후 진행
- [ ] `/IMP-execution`
