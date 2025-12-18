# PyQtGraph Chart 대안 조사 리포트

**날짜**: 2025-12-18  
**목적**: QWebEngineView의 Acrylic 충돌 문제를 해결하기 위한 PyQtGraph 평가

---

## 1. 요약 (Executive Summary)

| 항목 | PyQtGraph | TradingView (QWebEngineView) |
|:-----|:----------|:-----------------------------|
| **Acrylic 호환** | ✅ 완전 지원 | ❌ Windows DWM 충돌 |
| **캔들스틱 차트** | ⚠️ 커스텀 구현 필요 | ✅ 내장 지원 |
| **타임프레임** | ✅ DateAxisItem | ✅ 내장 지원 |
| **지표 오버레이** | ✅ 다중 PlotItem | ✅ 내장 지원 |
| **성능** | ⚡ OpenGL 가속 | ⚡ 브라우저 렌더링 |
| **스타일링** | Qt StyleSheet | CSS/HTML |

**결론**: PyQtGraph는 Acrylic과 완전 호환되며, 필요한 모든 기능 구현 가능. 단, 캔들스틱은 커스텀 GraphicsItem으로 직접 구현 필요.

---

## 2. 기능별 상세 분석

### 2.1 투명 배경 (Acrylic 호환)

```python
# PyQtGraph는 Qt 네이티브이므로 투명 배경 완전 지원
from pyqtgraph import PlotWidget
chart = PlotWidget(background=None)  # 투명 배경!
```

- **DWM 충돌 없음**: QWebEngineView와 달리 별도 GPU 프로세스 없음
- `WA_TranslucentBackground` 속성과 완벽 호환

### 2.2 캔들스틱 차트 (OHLC)

```python
# 커스텀 CandlestickItem 예시 (공식 예제 기반)
class CandlestickItem(pg.GraphicsObject):
    def __init__(self, data):
        pg.GraphicsObject.__init__(self)
        self.data = data  # [(timestamp, open, high, low, close), ...]
        self.generatePicture()
    
    def generatePicture(self):
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)
        w = 0.3  # 캔들 너비
        for t, o, h, l, c in self.data:
            if c > o:
                p.setPen(pg.mkPen('g'))
                p.setBrush(pg.mkBrush('g'))
            else:
                p.setPen(pg.mkPen('r'))
                p.setBrush(pg.mkBrush('r'))
            p.drawLine(QtCore.QPointF(t, l), QtCore.QPointF(t, h))
            p.drawRect(QtCore.QRectF(t - w, o, w * 2, c - o))
        p.end()
```

- **구현 난이도**: 중간 (공식 예제 존재)
- **참조**: `pyqtgraph/examples/customGraphicsItem.py`

### 2.3 타임프레임 (1m, 5m, 15m, 1h, 4h, 1d, 1w)

```python
from pyqtgraph import DateAxisItem

# X축에 DateAxisItem 적용
date_axis = DateAxisItem(orientation='bottom')
plot = pg.PlotWidget(axisItems={'bottom': date_axis})

# 데이터는 Unix timestamp로 전달
timestamps = [candle['time'].timestamp() for candle in candles]
```

- **DateAxisItem**: 줌 레벨에 따라 자동으로 날짜 포맷 조정
- **타임프레임 변경**: 백엔드에서 데이터 리샘플링 후 `setData()` 호출

### 2.4 기술적 지표 오버레이 (ATR, VWAP)

```python
# 메인 차트에 VWAP 라인 추가
plot = pg.PlotWidget()

# 캔들스틱
candle_item = CandlestickItem(ohlc_data)
plot.addItem(candle_item)

# VWAP 라인 (별도 시리즈)
vwap_line = plot.plot(timestamps, vwap_values, pen=pg.mkPen('y', width=2))

# ATR 밴드
atr_upper = plot.plot(timestamps, upper_band, pen=pg.mkPen('g', style=Qt.DashLine))
atr_lower = plot.plot(timestamps, lower_band, pen=pg.mkPen('r', style=Qt.DashLine))
```

- **지표 계산**: PyQtGraph는 순수 시각화 라이브러리. 지표는 NumPy/Pandas로 계산
- **기존 백엔드 호환**: `backend/data/technical.py`의 `calculate_vwap()`, `calculate_atr()` 그대로 사용 가능

---

## 3. 구현 가능 여부 요약

| HTS 기능 | PyQtGraph 구현 | 난이도 |
|:---------|:--------------|:-------|
| 캔들스틱 차트 | ✅ 커스텀 GraphicsItem | ⭐⭐ |
| VWAP 라인 | ✅ `plot()` 메서드 | ⭐ |
| ATR 밴드 | ✅ `plot()` 메서드 | ⭐ |
| 타임프레임 전환 | ✅ 데이터 리샘플링 + setData | ⭐⭐ |
| 줌/팬 | ✅ 내장 (마우스 휠/드래그) | ⭐ |
| 크로스헤어 | ✅ `CrosshairItem` | ⭐ |
| 트레이드 마커 | ✅ `ScatterPlotItem` 또는 TextItem | ⭐ |
| 실시간 업데이트 | ✅ `setData()` 호출 | ⭐ |

---

## 4. 장단점 비교

### 장점
1. **Acrylic 완전 호환** - DWM 충돌 없음
2. **Qt 네이티브** - 기존 PyQt6 코드와 자연스럽게 통합
3. **성능** - OpenGL 가속, 대량 데이터 처리 가능
4. **의존성 감소** - 브라우저 엔진 불필요

### 단점
1. **캔들스틱 직접 구현** - TradingView처럼 턴키 솔루션 아님
2. **스타일링 제한** - CSS만큼 유연하지 않음
3. **학습 곡선** - GraphicsItem 커스터마이징 필요

---

## 5. 다음 단계 권장사항

1. **pyqtgraph 설치**: `pip install pyqtgraph`
2. **CandlestickItem 프로토타입** 작성
3. **기존 ChartWidget 대체** 테스트
4. **Acrylic 호환 확인**

