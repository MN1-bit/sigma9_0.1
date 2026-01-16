# Finplot 기능 레퍼런스

> **목적**: 차트 마이그레이션 계획 수립을 위한 finplot 라이브러리 기능 목록
> **작성일**: 2026-01-09
> **출처**: [GitHub Wiki](https://github.com/highfestiva/finplot/wiki)

---

## 1. 개요

**finplot**은 PyQtGraph 기반의 고성능 금융 차트 라이브러리.
- 설치: `pip install finplot`
- 라이센스: MIT
- 월간 다운로드: 5,000+

---

## 2. 차트 타입

| 차트 타입 | API | 설명 |
|:----------|:----|:-----|
| **캔들스틱** | `fplt.candlestick_ochl(df)` | OHLC 데이터로 캔들스틱 생성 |
| **렌코 차트** | `fplt.renko(df)` | 변동폭 기반 렌코 박스 |
| **볼륨 바** | `fplt.volume_ocv(df)` | 가격 방향 색상 볼륨 |
| **히트맵** | `fplt.heatmap(df)` | 가격/시간 밀도 시각화 |
| **바 차트** | `fplt.bar(x, y)` | 일반 바 차트 |
| **히스토그램** | `fplt.hist(x, bins)` | 분포 히스토그램 |
| **라인 플롯** | `fplt.plot(x, y)` | 라인/지표 플롯 |
| **수평 볼륨** | `fplt.horiz_time_volume(df)` | Volume Profile |

---

## 3. 보조지표 (Indicators)

> finplot 자체는 **시각화 전용**. 지표 계산은 `pandas`/`numpy`로 수행 후 `fplt.plot()`으로 표시.

### 3.1 내장 예제가 있는 지표

| 지표 | 예제 파일 | 구현 방식 |
|:-----|:---------|:---------|
| **SMA** | 기본 | `df['Close'].rolling(20).mean()` |
| **EMA** | 기본 | `df['Close'].ewm(span=9).mean()` |
| **MACD** | `analyze.py` | EMA(12) - EMA(26) + Signal(9) |
| **RSI** | `analyze.py` | 14일 RS 기반 계산 |
| **Bollinger Bands** | `analyze.py` | SMA(20) ± 2.5×σ |
| **VWAP** | 예제 | 누적(P×V) / 누적(V) |
| **Volume Profile** | `volume-profile.py` | 가격 구간별 거래량 분포 |
| **Parabolic SAR** | 예제 | 추세 추적 포물선 |
| **TD Sequential** | 예제 | 9/13 카운트 패턴 |
| **Heikin Ashi** | `analyze.py` | 평활화 캔들스틱 |
| **ATR** | 커스텀 | True Range 평균 |
| **OBV** | `analyze.py` | On-Balance Volume |
| **Accumulation/Distribution** | `analyze.py` | CLV × Volume 누적 |

### 3.2 지표 표시 방식

```python
# 메인 차트에 오버레이
sma = df['Close'].rolling(20).mean()
fplt.plot(sma, ax=ax, legend='SMA(20)', color='#2196F3')

# 별도 서브차트 (RSI 등)
ax_rsi = fplt.create_plot(rows=2)[1]  # 두 번째 행
fplt.plot(rsi, ax=ax_rsi, legend='RSI')
fplt.add_band(30, 70, ax=ax_rsi)  # 과매수/과매도 밴드
```

---

## 4. 멀티 차트 (Sub-charts / Rows)

```python
# 여러 행의 차트 생성 (예: 가격, 볼륨, RSI)
ax_price, ax_vol, ax_rsi = fplt.create_plot('Title', rows=3)

# 각 차트에 데이터 할당
fplt.candlestick_ochl(df, ax=ax_price)
fplt.volume_ocv(df, ax=ax_vol)
fplt.plot(rsi, ax=ax_rsi)
```

**특징:**
- ✅ 모든 차트가 **동일 시간축 동기화**
- ✅ 줌/팬 시 모든 차트 동시 반응
- ✅ 행 높이 비율 조정 가능 (`fplt.winx`, `fplt.winh`)

---

## 5. 실시간 업데이트

```python
def update():
    # 새 데이터 가져오기
    new_data = fetch_latest_bar()
    
    # 차트 업데이트
    candle_item.update_data(new_data)
    fplt.refresh()

# 1초마다 업데이트
fplt.timer_callback(update, seconds=1.0)
```

**API:**
- `fplt.timer_callback(func, seconds)` - 주기적 업데이트
- `fplt.refresh()` - 차트 강제 갱신
- `fplt.autoviewrestore()` - 줌 위치 저장/복원

---

## 6. 인터랙티브 기능

| 기능 | 지원 | 설명 |
|:-----|:----:|:-----|
| **줌/팬** | ✅ | 마우스 휠/드래그 |
| **크로스헤어** | ✅ | 자동 표시, 커스텀 가능 |
| **범례** | ✅ | `legend='Name'` |
| **라인 그리기** | ✅ | `Ctrl+드래그` |
| **타원 그리기** | ✅ | `Ctrl+중버튼` |
| **ROI 마커** | ✅ | `fplt.add_rect()`, `fplt.add_line()` |
| **텍스트 주석** | ✅ | `fplt.add_text(pos, text)` |
| **스크린샷** | ✅ | `fplt.screenshot(file)` |

---

## 7. 커스터마이징

### 7.1 색상 설정

```python
# 배경색
fplt.background = '#1a1a2e'
fplt.odd_plot_background = '#1f1f3d'

# 캔들 색상
fplt.candle_bull_color = '#22c55e'  # 상승
fplt.candle_bear_color = '#ef4444'  # 하락

# 볼륨 색상
fplt.volume_bull_color = '#22c55e80'
fplt.volume_bear_color = '#ef444480'

# 크로스헤어 색상
fplt.cross_hair_color = '#ffffff50'

# 전경색 (축, 텍스트)
fplt.foreground = '#e0e0e0'
```

### 7.2 기타 설정

```python
# 초기 줌 범위
fplt.create_plot(init_zoom_periods=100)

# 윈도우 크기
fplt.winw = 1200
fplt.winh = 800

# 시간대 설정
from dateutil.tz import gettz
fplt.display_timezone = gettz('Asia/Seoul')

# 타임스탬프 포맷
fplt.timestamp_format = '%Y-%m-%d %H:%M'
```

---

## 8. PyQt 통합

### 8.1 위젯 임베딩

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout
import finplot as fplt

class ChartWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        
        # finplot 차트 생성
        ax = fplt.create_plot(init_zoom_periods=100)
        
        # 내부 윈도우를 레이아웃에 추가
        win = fplt.windows[0]
        layout.addWidget(win)
```

### 8.2 별도 위젯 API

```python
# QWidget에 직접 임베딩하는 API
chart = fplt.create_plot_widget(master=parent_widget, rows=2)
```

---

## 9. Sigma9 통합 시 필요한 기능 매핑

| Sigma9 요구사항 | finplot 대응 |
|:---------------|:-------------|
| 타임프레임 버튼 (1m~1w) | 데이터 교체 후 `fplt.refresh()` |
| 캔들스틱 차트 | `fplt.candlestick_ochl()` |
| 볼륨 서브차트 | `fplt.volume_ocv()` 별도 row |
| VWAP 오버레이 | `fplt.plot(vwap, legend='VWAP')` |
| SMA/EMA | `fplt.plot()` |
| RSI 서브차트 | 별도 row + `fplt.add_band()` |
| MACD 서브차트 | 별도 row + 계산 로직 |
| 실시간 업데이트 | `fplt.timer_callback()` |
| 트레이드 마커 | `fplt.labels()` 또는 `scatter` |
| Acrylic 투명 배경 | `fplt.background = None` + Qt 설정 |

---

## 10. 제한사항

| 항목 | 상태 |
|:-----|:-----|
| Jupyter 지원 | ❌ 미지원 |
| 웹앱 | ❌ 미지원 |
| 선 그리기 도구 저장 | ⚠️ 수동 구현 필요 |
| 지표 자동 계산 | ❌ 직접 계산 필요 (pandas) |

---

## 11. 참조 링크

- [GitHub Repo](https://github.com/highfestiva/finplot)
- [Wiki - Home](https://github.com/highfestiva/finplot/wiki)
- [Wiki - API](https://github.com/highfestiva/finplot/wiki/API)
- [Wiki - Snippets](https://github.com/highfestiva/finplot/wiki/Snippets)
- [Examples](https://github.com/highfestiva/finplot/tree/master/finplot/examples)
