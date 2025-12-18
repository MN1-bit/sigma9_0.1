# ============================================================================
# PyQtGraph Chart Widget - 투명 배경 지원 캔들스틱 차트
# ============================================================================
# 📌 이 파일의 역할:
#   - PyQtGraph 기반 트레이딩 차트 위젯
#   - QWebEngineView 대신 Qt 네이티브로 구현 (Acrylic 호환)
#   - 캔들스틱, Volume, VWAP, ATR, MA 라인, 트레이드 마커 지원
#
# 📖 장점:
#   - Windows DWM 투명 효과와 충돌 없음
#   - OpenGL 가속으로 빠른 렌더링
#   - PyQt6 코드와 자연스럽게 통합
#
# 🔄 업데이트 (2025-12-18):
#   - Volume 서브차트 추가 (연동 X축)
#   - MA (SMA/EMA) 라인 지원
#   - Stop Loss / Take Profit 수평선
# ============================================================================

"""
PyQtGraph Chart Widget

투명 배경을 지원하는 PyQtGraph 기반 트레이딩 차트입니다.
Acrylic 효과와 완벽 호환되며, TradingView를 대체합니다.

Features:
    - 캔들스틱 차트 (OHLC)
    - Volume 서브차트 (연동 X축)
    - VWAP/ATR/MA 지표 오버레이
    - Stop Loss / Take Profit 수평선
    - 트레이드 마커 (매수/매도/Ignition)
    - DateAxisItem으로 타임프레임 표시
    - 마우스 줌/팬 지원
"""

import pyqtgraph as pg
from pyqtgraph import DateAxisItem
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from typing import List, Dict, Optional
import numpy as np

from .candlestick_item import CandlestickItem
from ..theme import theme


class PyQtGraphChartWidget(QWidget):
    """
    PyQtGraph 기반 트레이딩 차트 위젯 (Volume 서브차트 포함)
    
    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    이 위젯은 주식 차트를 그려주는 도화지입니다.
    
    위쪽 큰 패널: 캔들스틱 (가격 움직임)
    아래쪽 작은 패널: 볼륨 바 차트 (거래량)
    
    두 패널은 X축이 연동되어 함께 줌/팬됩니다.
    
    Signals:
        timeframe_changed: 타임프레임 변경 시 발생 (str)
        chart_clicked: 차트 클릭 시 발생 (float, float) - (time, price)
    """
    
    # 시그널 정의
    timeframe_changed = pyqtSignal(str)
    chart_clicked = pyqtSignal(float, float)
    
    # 지원하는 타임프레임
    TIMEFRAMES = ['1m', '3m', '5m', '15m', '1h', '4h', '1d', '1w']
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 투명 배경 설정 (Acrylic 호환)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        
        # UI 초기화
        self._setup_ui()
        
        # 데이터 시리즈 저장
        self._candle_item: Optional[CandlestickItem] = None
        self._volume_bars = None
        self._vwap_line = None
        self._atr_upper_line = None
        self._atr_lower_line = None
        self._ma_lines = {}  # {period: PlotDataItem}
        self._price_levels = {}  # {'entry': InfiniteLine, 'sl': ..., 'tp': ...}
        self._markers = []
    
    def _setup_ui(self):
        """UI 구성"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # ═══════════════════════════════════════════════════════════════
        # 1. 상단 툴바 (타임프레임 선택)
        # ═══════════════════════════════════════════════════════════════
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(4, 4, 4, 0)
        
        # 타임프레임 라벨
        tf_label = QLabel("Timeframe:")
        tf_label.setStyleSheet(f"color: {theme.get_color('text_secondary')}; font-size: 11px;")
        toolbar.addWidget(tf_label)
        
        # 타임프레임 콤보박스
        self.tf_combo = QComboBox()
        self.tf_combo.addItems(self.TIMEFRAMES)
        self.tf_combo.setCurrentText('1d')  # 일봉 기본
        self.tf_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {theme.get_color('surface')};
                border: 1px solid {theme.get_color('border')};
                border-radius: 4px;
                padding: 4px 8px;
                color: {theme.get_color('text')};
                min-width: 60px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme.get_color('surface')};
                border: 1px solid {theme.get_color('border')};
                color: {theme.get_color('text')};
            }}
        """)
        self.tf_combo.currentTextChanged.connect(self._on_timeframe_changed)
        toolbar.addWidget(self.tf_combo)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # ═══════════════════════════════════════════════════════════════
        # 2. 메인 차트 영역 (GraphicsLayoutWidget)
        # ═══════════════════════════════════════════════════════════════
        
        # GraphicsLayoutWidget으로 멀티 패널 구성
        self.graphics_layout = pg.GraphicsLayoutWidget()
        self.graphics_layout.setBackground(None)  # 투명 배경 (Acrylic 호환)
        
        # ─────────────────────────────────────────────────────────────
        # 2A. 캔들스틱 플롯 (상단, 70%)
        # ─────────────────────────────────────────────────────────────
        date_axis = DateAxisItem(orientation='bottom')
        self.price_plot = self.graphics_layout.addPlot(
            row=0, col=0,
            axisItems={'bottom': date_axis}
        )
        self._style_plot(self.price_plot)
        
        # X축 숨김 (아래 Volume과 공유)
        self.price_plot.hideAxis('bottom')
        
        # ─────────────────────────────────────────────────────────────
        # 2B. Volume 플롯 (하단, 30%)
        # ─────────────────────────────────────────────────────────────
        volume_date_axis = DateAxisItem(orientation='bottom')
        self.volume_plot = self.graphics_layout.addPlot(
            row=1, col=0,
            axisItems={'bottom': volume_date_axis}
        )
        self._style_plot(self.volume_plot)
        
        # 높이 비율 설정 (Price:Volume = 3:1)
        self.graphics_layout.ci.layout.setRowStretchFactor(0, 3)
        self.graphics_layout.ci.layout.setRowStretchFactor(1, 1)
        
        # X축 연동 (줌/팬 동기화)
        self.volume_plot.setXLink(self.price_plot)
        
        layout.addWidget(self.graphics_layout)
    
    def _style_plot(self, plot):
        """플롯 스타일 설정"""
        # 축 색상 설정 - PyQtGraph는 CSS rgba()를 파싱하지 못하므로 QColor 사용
        axis_color = QColor(255, 255, 255, 150)  # 반투명 흰색
        for axis_name in ['left', 'bottom']:
            axis = plot.getAxis(axis_name)
            axis.setPen(pg.mkPen(axis_color, width=1))
            axis.setTextPen(pg.mkPen(axis_color))
        
        # 그리드 설정 (반투명)
        plot.showGrid(x=True, y=True, alpha=0.1)
        
        # 마우스 인터랙션 활성화
        plot.setMouseEnabled(x=True, y=True)
    
    def _on_timeframe_changed(self, timeframe: str):
        """타임프레임 변경 핸들러"""
        self.timeframe_changed.emit(timeframe)
    
    # ═══════════════════════════════════════════════════════════════════
    # 데이터 설정 메서드
    # ═══════════════════════════════════════════════════════════════════
    
    def set_candlestick_data(self, candles: List[Dict]):
        """
        캔들스틱 데이터 설정
        
        Args:
            candles: [{"time": timestamp, "open": float, "high": float, 
                      "low": float, "close": float, "volume": int}, ...]
        """
        # Dict 리스트를 튜플 리스트로 변환
        data = []
        for c in candles:
            t = c['time']
            # time이 문자열이면 timestamp로 변환
            if isinstance(t, str):
                from datetime import datetime
                t = datetime.fromisoformat(t.replace('Z', '+00:00')).timestamp()
            data.append((t, c['open'], c['high'], c['low'], c['close']))
        
        # 기존 캔들 제거
        if self._candle_item:
            self.price_plot.removeItem(self._candle_item)
        
        # 새 캔들 추가
        self._candle_item = CandlestickItem(data)
        self.price_plot.addItem(self._candle_item)
        
        # 뷰 범위 자동 조정
        self.price_plot.autoRange()
    
    def set_volume_data(self, volume_data: List[Dict]):
        """
        Volume 바 차트 설정
        
        Args:
            volume_data: [{"time": timestamp, "volume": int, "is_up": bool}, ...]
        """
        # 기존 Volume 제거
        if self._volume_bars:
            self.volume_plot.removeItem(self._volume_bars)
        
        times = []
        volumes = []
        colors = []
        
        for v in volume_data:
            t = v['time']
            if isinstance(t, str):
                from datetime import datetime
                t = datetime.fromisoformat(t.replace('Z', '+00:00')).timestamp()
            times.append(t)
            volumes.append(v['volume'])
            # 상승봉 녹색, 하락봉 빨간색
            is_up = v.get('is_up', True)
            colors.append('#22c55e' if is_up else '#ef4444')
        
        # 바 너비 계산
        if len(times) >= 2:
            bar_width = (times[1] - times[0]) * 0.8
        else:
            bar_width = 86400 * 0.8  # 1일
        
        # BarGraphItem으로 Volume 바 생성
        brushes = [pg.mkBrush(c) for c in colors]
        self._volume_bars = pg.BarGraphItem(
            x=times, height=volumes, width=bar_width,
            brushes=brushes,
            pen=pg.mkPen(None)  # 테두리 없음
        )
        self.volume_plot.addItem(self._volume_bars)
        self.volume_plot.autoRange()
    
    def set_vwap_data(self, vwap_data: List[Dict]):
        """
        VWAP 라인 데이터 설정
        
        Args:
            vwap_data: [{"time": timestamp, "value": float}, ...]
        """
        if self._vwap_line:
            self.price_plot.removeItem(self._vwap_line)
        
        times = []
        values = []
        for v in vwap_data:
            t = v['time']
            if isinstance(t, str):
                from datetime import datetime
                t = datetime.fromisoformat(t.replace('Z', '+00:00')).timestamp()
            times.append(t)
            values.append(v['value'])
        
        self._vwap_line = self.price_plot.plot(
            times, values,
            pen=pg.mkPen('#eab308', width=2),  # 노란색 VWAP
            name='VWAP'
        )
    
    def set_ma_data(self, ma_data: List[Dict], period: int = 20, color: str = '#3b82f6'):
        """
        MA (이동평균) 라인 설정
        
        Args:
            ma_data: [{"time": timestamp, "value": float}, ...]
            period: MA 기간 (라벨용)
            color: 라인 색상
        """
        # 기존 라인 제거
        if period in self._ma_lines:
            self.price_plot.removeItem(self._ma_lines[period])
        
        times = []
        values = []
        for d in ma_data:
            t = d['time']
            if isinstance(t, str):
                from datetime import datetime
                t = datetime.fromisoformat(t.replace('Z', '+00:00')).timestamp()
            times.append(t)
            values.append(d['value'])
        
        line = self.price_plot.plot(
            times, values,
            pen=pg.mkPen(color, width=1),
            name=f'MA{period}'
        )
        self._ma_lines[period] = line
    
    def set_atr_bands(self, upper_data: List[Dict], lower_data: List[Dict]):
        """
        ATR 밴드 설정 (상단/하단)
        
        Args:
            upper_data: [{"time": timestamp, "value": float}, ...]
            lower_data: [{"time": timestamp, "value": float}, ...]
        """
        # 기존 라인 제거
        if self._atr_upper_line:
            self.price_plot.removeItem(self._atr_upper_line)
        if self._atr_lower_line:
            self.price_plot.removeItem(self._atr_lower_line)
        
        # 상단 ATR
        upper_times = []
        upper_values = []
        for d in upper_data:
            t = d['time']
            if isinstance(t, str):
                from datetime import datetime
                t = datetime.fromisoformat(t.replace('Z', '+00:00')).timestamp()
            upper_times.append(t)
            upper_values.append(d['value'])
        
        self._atr_upper_line = self.price_plot.plot(
            upper_times, upper_values,
            pen=pg.mkPen('#22c55e', width=1, style=Qt.PenStyle.DashLine),
            name='ATR+'
        )
        
        # 하단 ATR
        lower_times = []
        lower_values = []
        for d in lower_data:
            t = d['time']
            if isinstance(t, str):
                from datetime import datetime
                t = datetime.fromisoformat(t.replace('Z', '+00:00')).timestamp()
            lower_times.append(t)
            lower_values.append(d['value'])
        
        self._atr_lower_line = self.price_plot.plot(
            lower_times, lower_values,
            pen=pg.mkPen('#ef4444', width=1, style=Qt.PenStyle.DashLine),
            name='ATR-'
        )
    
    def set_price_levels(self, entry: float = None, stop_loss: float = None, take_profit: float = None):
        """
        수평선 레벨 설정 (Entry, Stop Loss, Take Profit)
        
        Args:
            entry: 진입 가격 (파란색 실선)
            stop_loss: 손절 가격 (빨간색 점선)
            take_profit: 익절 가격 (녹색 점선)
        """
        # 기존 라인 제거
        for key in list(self._price_levels.keys()):
            self.price_plot.removeItem(self._price_levels[key])
        self._price_levels.clear()
        
        if entry:
            line = pg.InfiniteLine(
                pos=entry, angle=0,
                pen=pg.mkPen('#3b82f6', width=2, style=Qt.PenStyle.SolidLine),
                label=f'Entry ${entry:.2f}',
                labelOpts={'color': '#3b82f6', 'position': 0.98}
            )
            self.price_plot.addItem(line)
            self._price_levels['entry'] = line
        
        if stop_loss:
            line = pg.InfiniteLine(
                pos=stop_loss, angle=0,
                pen=pg.mkPen('#ef4444', width=1, style=Qt.PenStyle.DashLine),
                label=f'SL ${stop_loss:.2f}',
                labelOpts={'color': '#ef4444', 'position': 0.98}
            )
            self.price_plot.addItem(line)
            self._price_levels['sl'] = line
        
        if take_profit:
            line = pg.InfiniteLine(
                pos=take_profit, angle=0,
                pen=pg.mkPen('#22c55e', width=1, style=Qt.PenStyle.DashLine),
                label=f'TP ${take_profit:.2f}',
                labelOpts={'color': '#22c55e', 'position': 0.98}
            )
            self.price_plot.addItem(line)
            self._price_levels['tp'] = line
    
    # ═══════════════════════════════════════════════════════════════════
    # 마커 메서드
    # ═══════════════════════════════════════════════════════════════════
    
    def add_marker(
        self,
        time: float,
        price: float,
        text: str = "",
        color: str = "#2196F3",
        symbol: str = 'o'
    ):
        """
        차트에 마커 추가
        
        Args:
            time: Unix timestamp
            price: 가격
            text: 마커 텍스트
            color: 색상 (hex)
            symbol: 마커 모양 ('o', 't', 'd', 's', '+')
        """
        if isinstance(time, str):
            from datetime import datetime
            time = datetime.fromisoformat(time.replace('Z', '+00:00')).timestamp()
        
        # ScatterPlotItem으로 마커 추가
        scatter = pg.ScatterPlotItem(
            [time], [price],
            symbol=symbol,
            size=12,
            pen=pg.mkPen(color, width=2),
            brush=pg.mkBrush(color)
        )
        self.price_plot.addItem(scatter)
        self._markers.append(scatter)
        
        # 텍스트 라벨 추가
        if text:
            label = pg.TextItem(text, color=color, anchor=(0.5, 1))
            label.setPos(time, price)
            self.price_plot.addItem(label)
            self._markers.append(label)
    
    def add_buy_marker(self, time, price: float = None):
        """매수 마커 추가"""
        text = f"BUY ${price:.2f}" if price else "BUY"
        self.add_marker(time, price or 0, text, "#22c55e", 't')  # 삼각형 위
    
    def add_sell_marker(self, time, price: float = None):
        """매도 마커 추가"""
        text = f"SELL ${price:.2f}" if price else "SELL"
        self.add_marker(time, price or 0, text, "#ef4444", 't')  # 삼각형 아래
    
    def add_ignition_marker(self, time, price: float, score: float = None):
        """
        Ignition 포인트 마커 추가
        
        Args:
            time: 타임스탬프
            price: 캔들 고가 위에 표시할 가격
            score: Ignition 스코어
        """
        text = f"🔥{score:.0f}" if score else "🔥"
        if isinstance(time, str):
            from datetime import datetime
            time = datetime.fromisoformat(time.replace('Z', '+00:00')).timestamp()
        
        label = pg.TextItem(text, color='#f97316', anchor=(0.5, 1.5))
        label.setPos(time, price)
        self.price_plot.addItem(label)
        self._markers.append(label)
    
    def clear_markers(self):
        """모든 마커 제거"""
        for marker in self._markers:
            self.price_plot.removeItem(marker)
        self._markers.clear()
    
    def clear(self):
        """차트 초기화"""
        self.price_plot.clear()
        self.volume_plot.clear()
        self._candle_item = None
        self._volume_bars = None
        self._vwap_line = None
        self._atr_upper_line = None
        self._atr_lower_line = None
        self._ma_lines.clear()
        self._price_levels.clear()
        self._markers.clear()


# ═══════════════════════════════════════════════════════════════════════════
# 테스트
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """독립 실행 테스트"""
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    chart = PyQtGraphChartWidget()
    chart.resize(1000, 700)
    chart.setWindowTitle("PyQtGraph Chart Test")
    chart.show()
    
    # 테스트 데이터
    import time as time_module
    base_time = time_module.time() - 86400 * 100  # 100일 전부터
    
    test_candles = []
    test_volumes = []
    price = 10.0
    for i in range(100):
        o = price
        delta = np.random.uniform(-0.5, 0.5)
        c = price + delta
        h = max(o, c) + np.random.uniform(0, 0.3)
        l = min(o, c) - np.random.uniform(0, 0.3)
        vol = int(np.random.uniform(100000, 500000))
        is_up = c >= o
        
        test_candles.append({
            "time": base_time + i * 86400,  # 일봉
            "open": o, "high": h, "low": l, "close": c, "volume": vol
        })
        test_volumes.append({
            "time": base_time + i * 86400,
            "volume": vol,
            "is_up": is_up
        })
        price = c
    
    chart.set_candlestick_data(test_candles)
    chart.set_volume_data(test_volumes)
    
    # VWAP 테스트
    test_vwap = [{"time": c["time"], "value": c["close"] * 0.99} for c in test_candles]
    chart.set_vwap_data(test_vwap)
    
    # MA 테스트
    test_ma20 = [{"time": c["time"], "value": c["close"] * 1.01} for c in test_candles]
    chart.set_ma_data(test_ma20, period=20, color='#3b82f6')
    
    # Entry/SL/TP 테스트
    chart.set_price_levels(entry=10.0, stop_loss=9.5, take_profit=11.0)
    
    # Ignition 마커 테스트
    chart.add_ignition_marker(test_candles[50]["time"], test_candles[50]["high"], score=85)
    
    sys.exit(app.exec())
