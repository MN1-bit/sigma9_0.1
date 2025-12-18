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
from .candlestick_item import CandlestickItem
from ..theme import theme


class IndexDateAxis(pg.AxisItem):
    """
    인덱스 기반 날짜 X축 (Gap 제거용)
    0, 1, 2... 인덱스를 받아서 해당 인덱스의 날짜 문자열(MM-DD)로 표시
    """
    def __init__(self, orientation='bottom'):
        super().__init__(orientation)
        self.timestamps = {}  # {index: timestamp}
        self.time_strs = {}   # {index: "MM-DD"}
        
    def update_ticks(self, timestamps: List[float]):
        """타임스탬프 매핑 업데이트"""
        self.timestamps = {i: t for i, t in enumerate(timestamps)}
        from datetime import datetime
        self.time_strs = {
            i: datetime.fromtimestamp(t).strftime('%m-%d')
            for i, t in enumerate(timestamps)
        }
    
    def tickStrings(self, values, scale, spacing):
        """인덱스를 날짜 문자열로 변환"""
        strings = []
        for v in values:
            idx = int(round(v))
            if idx in self.time_strs:
                strings.append(self.time_strs[idx])
            else:
                strings.append("")
        return strings



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
    
    # 지원하는 타임프레임 (Step 2.7)
    TIMEFRAMES = ['1m', '5m', '15m', '1h', '1D']
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 투명 배경 설정 (Acrylic 호환)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        
        # 데이터 시리즈 저장
        self._candle_item: Optional[CandlestickItem] = None
        self._volume_bars = None
        self._vwap_line = None
        self._atr_upper_line = None
        self._atr_lower_line = None
        self._ma_lines = {}  # {period: PlotDataItem}
        self._price_levels = {}  # {'entry': InfiniteLine, 'sl': ..., 'tp': ...}
        self._markers = []
        
        # 데이터 캐시 (툴팁용)
        self._candle_data = []
        self._volume_data = []
        
        # UI 초기화 (plots 생성)
        self._setup_ui()
        
        # 툴팁 설정 (plots 생성 후!!)
        self._setup_tooltips()
    
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
        # ─────────────────────────────────────────────────────────────
        # 2A. 캔들스틱 플롯 (상단, 70%)
        # ─────────────────────────────────────────────────────────────
        # [Gap 제거] 커스텀 축 사용
        self.date_axis = IndexDateAxis(orientation='bottom')
        self.price_plot = self.graphics_layout.addPlot(
            row=0, col=0,
            axisItems={'bottom': self.date_axis}
        )
        self.price_plot.showAxis('left', False)
        self.price_plot.showAxis('right', True)
        self._style_plot(self.price_plot, axis_side='right')
        
        # [New] X축 범위 변경 시 Y축 수동 자동 스케일링 연결
        self.price_plot.getViewBox().sigXRangeChanged.connect(self._update_y_range)
        
        # X축 숨김 (아래 Volume과 공유)
        self.price_plot.hideAxis('bottom')
        
        # ─────────────────────────────────────────────────────────────
        # 2B. Volume 플롯 (하단, 30%)
        # ─────────────────────────────────────────────────────────────
        # ─────────────────────────────────────────────────────────────
        # 2B. Volume 플롯 (하단, 30%)
        # ─────────────────────────────────────────────────────────────
        # [Gap 제거] 커스텀 축 사용 (Price 축과 공유하지만 인스턴스는 별도 필요할 수 있음. 
        # 하지만 여기서는 Price 축을 메인으로 쓰고 Volume 축은 숨기거나 연동)
        self.volume_date_axis = IndexDateAxis(orientation='bottom')
        self.volume_plot = self.graphics_layout.addPlot(
            row=1, col=0,
            axisItems={'bottom': self.volume_date_axis}
        )
        # [User Request] Volume 축은 다시 왼쪽으로 이동
        self.volume_plot.showAxis('left', True)
        self.volume_plot.showAxis('right', False)
        self._style_plot(self.volume_plot, axis_side='left')
        
        # 높이 비율 설정 (Price:Volume = 3:1)
        self.graphics_layout.ci.layout.setRowStretchFactor(0, 3)
        self.graphics_layout.ci.layout.setRowStretchFactor(1, 1)
        
        # X축 연동 (줌/팬 동기화)
        self.volume_plot.setXLink(self.price_plot)
        
        layout.addWidget(self.graphics_layout)
    
    def _style_plot(self, plot, axis_side='right'):
        """플롯 스타일 설정"""
        # 축 색상 설정
        axis_color = QColor(255, 255, 255, 150)  # 반투명 흰색
        
        # 지정된 방향의 축과 하단 축 스타일링
        axes_to_style = ['bottom', axis_side]
        
        for axis_name in axes_to_style:
            axis = plot.getAxis(axis_name)
            axis.setPen(pg.mkPen(axis_color, width=1))
            axis.setTextPen(pg.mkPen(axis_color))
        
        # 불필요한 쪽 축 숨기기 (안전장치)
        opposite_side = 'left' if axis_side == 'right' else 'right'
        plot.showAxis(opposite_side, False)
        plot.showAxis(axis_side, True)
        
        # 그리드 설정 (반투명)
        plot.showGrid(x=True, y=True, alpha=0.1)
        
        # [FIX] Y축 자동 스케일링 설정 제거 (수동 제어로 변경)
        # plot.enableAutoRange(axis='y', enable=True)
        # plot.setAutoVisible(y=True)
        plot.enableAutoRange(axis='y', enable=False)
        plot.setAutoVisible(y=False)
        
        # 마우스 인터랙션 활성화
        plot.setMouseEnabled(x=True, y=True)
    
    def _on_timeframe_changed(self, timeframe: str):
        """타임프레임 변경 핸들러"""
        self.timeframe_changed.emit(timeframe)
    
    def _format_volume_axis(self):
        """
        Volume Y축을 자연수 포맷으로 설정
        
        1,000,000 → 1M, 500,000 → 500K 형식으로 표시
        """
        # [User Request] Volume은 다시 왼쪽 축 사용
        axis = self.volume_plot.getAxis('left')
        
        def format_volume(value):
            if abs(value) >= 1_000_000_000:
                return f"{value / 1_000_000_000:.1f}B"
            elif abs(value) >= 1_000_000:
                return f"{value / 1_000_000:.1f}M"
            elif abs(value) >= 1_000:
                return f"{value / 1_000:.0f}K"
            else:
                return f"{int(value)}"
        
        # 커스텀 틱 문자열 생성
        axis.setTicks(None)  # 자동 틱 사용
        axis.enableAutoSIPrefix(False)  # SI 접두사 비활성화
        axis.setTickSpacing()  # 기본 간격
        
        # Y축 라벨 포맷터 설정
        axis.tickStrings = lambda values, scale, spacing: [format_volume(v) for v in values]
    
    def _setup_tooltips(self):
        """
        호버 툴팁 설정
        
        캔들스틱 위에 마우스를 올리면 OHLCV + 시간 표시
        Volume 바 위에 마우스를 올리면 거래량 + 시간 표시
        """
        # 프록시 아이템으로 마우스 이벤트 감지
        self._price_proxy = pg.SignalProxy(
            self.price_plot.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._on_price_mouse_moved
        )
        self._volume_proxy = pg.SignalProxy(
            self.volume_plot.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._on_volume_mouse_moved
        )
        
        # 툴팁 텍스트 아이템
        self._price_tooltip = pg.TextItem(
            text="",
            color='white',
            fill=pg.mkBrush(0, 0, 0, 180),
            anchor=(0, 1)
        )
        self._price_tooltip.setZValue(100)
        self.price_plot.addItem(self._price_tooltip)
        self._price_tooltip.hide()
        
        self._volume_tooltip = pg.TextItem(
            text="",
            color='white',
            fill=pg.mkBrush(0, 0, 0, 180),
            anchor=(0, 1)
        )
        self._volume_tooltip.setZValue(100)
        self.volume_plot.addItem(self._volume_tooltip)
        self._volume_tooltip.hide()
    
    def _on_price_mouse_moved(self, evt):
        """캔들스틱 호버 이벤트"""
        pos = evt[0]
        if not self.price_plot.sceneBoundingRect().contains(pos):
            self._price_tooltip.hide()
            return
        
        mouse_point = self.price_plot.getViewBox().mapSceneToView(pos)
        x = mouse_point.x()
        
        # 인덱스 기반으로 캔들 찾기
        idx = int(round(x))
        if 0 <= idx < len(self._candle_data):
            closest = self._candle_data[idx]
            from datetime import datetime
            time_str = datetime.fromtimestamp(closest['time']).strftime('%Y-%m-%d')
            
            text = (
                f"📅 {time_str}\n"
                f"O: {closest['open']:.2f}  H: {closest['high']:.2f}\n"
                f"L: {closest['low']:.2f}  C: {closest['close']:.2f}"
            )
            self._price_tooltip.setText(text)
            self._price_tooltip.setPos(x, closest['high'])
            self._price_tooltip.show()
        else:
            self._price_tooltip.hide()
    
    def _update_y_range(self):
        """X축 범위 변경 시 Y축 자동 스케일링 (TradingView 스타일)"""
        if not hasattr(self, '_candle_data') or not self._candle_data:
            return
            
        # 현재 보이는 X축 범위 (인덱스) 가져오기
        view_box = self.price_plot.getViewBox()
        view_range = view_box.viewRange()
        x_min, x_max = view_range[0]
        
        # 범위 내 캔들 필터링
        min_price = float('inf')
        max_price = float('-inf')
        found = False
        
        # 인덱스 기반으로 빠르게 필터링 가능
        start_idx = max(0, int(x_min))
        end_idx = min(len(self._candle_data) - 1, int(x_max) + 1)
        
        if start_idx <= end_idx:
            subset = self._candle_data[start_idx:end_idx+1]
            for c in subset:
                if c['low'] < min_price: min_price = c['low']
                if c['high'] > max_price: max_price = c['high']
                found = True
        
        # 범위 내 데이터가 있으면 Y축 조정
        if found and min_price < max_price:
            padding = (max_price - min_price) * 0.1  # 상하 10% 여유
            view_box.setYRange(min_price - padding, max_price + padding, padding=0)

    def _on_volume_mouse_moved(self, evt):
        """Volume 바 호버 이벤트"""
        pos = evt[0]
        if not self.volume_plot.sceneBoundingRect().contains(pos):
            self._volume_tooltip.hide()
            return
        
        mouse_point = self.volume_plot.getViewBox().mapSceneToView(pos)
        x = mouse_point.x()
        
        # 가장 가까운 Volume 찾기
        idx = int(round(x))
        if 0 <= idx < len(self._volume_data):
            v = self._volume_data[idx]
            from datetime import datetime
            time_str = datetime.fromtimestamp(v['time']).strftime('%Y-%m-%d')
            
            vol = v['volume']
            text = f"📅 {time_str}\n📊 Volume: {vol:,}"
            self._volume_tooltip.setText(text)
            self._volume_tooltip.setPos(x, vol)
            self._volume_tooltip.show()
        else:
            self._volume_tooltip.hide()
    
    # ═══════════════════════════════════════════════════════════════════
    # 데이터 설정 메서드
    # ═══════════════════════════════════════════════════════════════════
    
    def set_candlestick_data(self, candles: List[Dict]):
        """
        캔들스틱 데이터 설정 (Gap 제거 적용)
        
        Args:
            candles: [{"time": timestamp, "open": float, ...}, ...]
        """
        # Dict 리스트를 튜플 리스트로 변환
        data = []
        timestamps = []  # [Gap 제거] 축 매핑용
        
        # [New] 저장용 데이터 초기화
        self._candle_data = []
        
        # 타임스탬프 -> 인덱스 매핑 생성
        self._timestamp_map = {} 
        
        
        
        for i, c in enumerate(candles):
            t = c['time']
            if isinstance(t, str):
                from datetime import datetime
                t = datetime.fromisoformat(t.replace('Z', '+00:00')).timestamp()
            timestamps.append(t)
            
            # [Gap 제거] X좌표는 타임스탬프 대신 인덱스(i) 사용
            data.append((i, c['open'], c['high'], c['low'], c['close']))
            
            self._timestamp_map[t] = i
            
            # 데이터 캐시 저장 (인덱스 포함)
            self._candle_data.append({
                'index': i,
                'time': t,
                'open': c['open'],
                'high': c['high'],
                'low': c['low'],
                'close': c['close']
            })
            
        # [Gap 제거] 축 업데이트
        if hasattr(self, 'date_axis'):
            self.date_axis.update_ticks(timestamps)
        if hasattr(self, 'volume_date_axis'):
            self.volume_date_axis.update_ticks(timestamps)
        
        # 기존 캔들 제거
        if self._candle_item:
            self.price_plot.removeItem(self._candle_item)
        
        # 새 캔들 추가
        self._candle_item = CandlestickItem(data)
        self.price_plot.addItem(self._candle_item)
        
        # 뷰 범위 자동 조정 (처음 로드 시)
        self.price_plot.autoRange()
        # 이후에는 X축 변경 시 자동으로 _update_y_range가 호출됨
        self._update_y_range()
    
    def set_volume_data(self, volume_data: List[Dict]):
        """
        Volume 바 차트 설정
        
        Args:
            volume_data: [{"time": timestamp, "volume": int, "is_up": bool}, ...]
        """
        # 기존 Volume 제거
        if self._volume_bars:
            self.volume_plot.removeItem(self._volume_bars)
        
        # self._candle_data가 먼저 설정되어야 매핑 가능
        # 보통 candles와 volume 데이터 길이가 같다고 가정하거나,
        # volume_data의 time을 이용해 인덱스를 찾아야 함.
        
        times = [] # 인덱스 리스트
        volumes = []
        colors = []
        
        self._volume_data = [] # 인덱스 포함해서 재저장
        
        for i, v in enumerate(volume_data):
            t = v['time']
            if isinstance(t, str):
                from datetime import datetime
                t = datetime.fromisoformat(t.replace('Z', '+00:00')).timestamp()
            
            # 매핑된 인덱스 찾기 (없으면 순서대로)
            idx = self._timestamp_map.get(t, i)
            
            times.append(idx)
            volumes.append(v['volume'])
            
            is_up = v.get('is_up', True)
            colors.append('#22c55e' if is_up else '#ef4444')
            
            self._volume_data.append({
                'index': idx,
                'time': t,
                'volume': v['volume']
            })
        
        # 바 너비 (인덱스 간격은 1이므로 0.8로 고정)
        bar_width = 0.8
        
        # BarGraphItem으로 Volume 바 생성
        brushes = [pg.mkBrush(c) for c in colors]
        self._volume_bars = pg.BarGraphItem(
            x=times, height=volumes, width=bar_width,
            brushes=brushes,
            pen=pg.mkPen(None)  # 테두리 없음
        )
        self.volume_plot.addItem(self._volume_bars)
        
        # [NEW] Volume Y축 자연수 포맷터 (과학 표기법 대신)
        self._format_volume_axis()
        
        self.volume_plot.autoRange()
    
    def set_vwap_data(self, vwap_data: List[Dict]):
        """
        VWAP 라인 데이터 설정
        
        Args:
            vwap_data: [{"time": timestamp, "value": float}, ...]
        """
        if self._vwap_line:
            self.price_plot.removeItem(self._vwap_line)
        
        if not hasattr(self, '_timestamp_map'):
            return

        times = []
        values = []
        for v in vwap_data:
            t = v['time']
            if isinstance(t, str):
                from datetime import datetime
                t = datetime.fromisoformat(t.replace('Z', '+00:00')).timestamp()
            
            # 매핑된 인덱스 찾기
            if t in self._timestamp_map:
                times.append(self._timestamp_map[t])
                values.append(v['value'])
        
        if times:
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
        
        if not hasattr(self, '_timestamp_map'):
            return

        times = []
        values = []
        for d in ma_data:
            t = d['time']
            if isinstance(t, str):
                from datetime import datetime
                t = datetime.fromisoformat(t.replace('Z', '+00:00')).timestamp()
            
            # 매핑된 인덱스 찾기
            if t in self._timestamp_map:
                times.append(self._timestamp_map[t])
                values.append(d['value'])
        
        if times:
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
        
        if not hasattr(self, '_timestamp_map'):
            return

        # 상단 ATR
        upper_times = []
        upper_values = []
        for d in upper_data:
            t = d['time']
            if isinstance(t, str):
                from datetime import datetime
                t = datetime.fromisoformat(t.replace('Z', '+00:00')).timestamp()
            
            if t in self._timestamp_map:
                upper_times.append(self._timestamp_map[t])
                upper_values.append(d['value'])
        
        if upper_times:
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
            
            if t in self._timestamp_map:
                lower_times.append(self._timestamp_map[t])
                lower_values.append(d['value'])
        
        if lower_times:
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
        
        # [Map] 타임스탬프를 인덱스로 변환
        x_pos = time
        if hasattr(self, '_timestamp_map') and time in self._timestamp_map:
            x_pos = self._timestamp_map[time]
        else:
            # 매핑에 없는 경우(예: 장외 거래?) - 추가하거나 무시해야 함
            # 여기선 무시하거나 근사값 처리. 일단 예외 처리 없이 리턴
            # return 
            pass
        
        # ScatterPlotItem으로 마커 추가
        scatter = pg.ScatterPlotItem(
            [x_pos], [price],
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
            label.setPos(x_pos, price)  # 인덱스 좌표 사용
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
        # [FIX] self.price_plot.clear() 대신 항목별 제거로 변경
        # 이렇게 해야 툴팁(TextItem)과 Grid, Axis 설정이 유지됨
        
        # 1. 캔들 제거
        if self._candle_item:
            self.price_plot.removeItem(self._candle_item)
            self._candle_item = None
            
        # 2. Volume 바 제거
        if self._volume_bars:
            self.volume_plot.removeItem(self._volume_bars)
            self._volume_bars = None
            
        # 3. 보조지표 제거
        if self._vwap_line:
            self.price_plot.removeItem(self._vwap_line)
            self._vwap_line = None
            
        if self._atr_upper_line:
            self.price_plot.removeItem(self._atr_upper_line)
            self._atr_upper_line = None
        
        if self._atr_lower_line:
            self.price_plot.removeItem(self._atr_lower_line)
            self._atr_lower_line = None
            
        for line in self._ma_lines.values():
            self.price_plot.removeItem(line)
        self._ma_lines.clear()
        
        for line in self._price_levels.values():
            self.price_plot.removeItem(line)
        self._price_levels.clear()
        
        self.clear_markers()
        
        # 데이터 캐시 초기화
        self._candle_data = []
        self._volume_data = []
        
        
        # 뷰 범위 자동 조정 활성화 (수동 모드이므로 autoRange 비활성화 유지)
        self.price_plot.enableAutoRange(axis='y', enable=False)
        self.volume_plot.enableAutoRange(axis='y', enable=False)
        
        self.price_plot.autoRange()
        self.volume_plot.autoRange()


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
