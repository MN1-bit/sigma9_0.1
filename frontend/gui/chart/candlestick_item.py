# ============================================================================
# CandlestickItem - PyQtGraph용 캔들스틱 그래픽 아이템
# ============================================================================
# 📌 이 파일의 역할:
#   - OHLC(시가/고가/저가/종가) 캔들스틱 차트를 PyQtGraph에서 렌더링
#   - QWebEngineView 없이 Qt 네이티브로 구현 (Acrylic 호환)
#
# 📖 참조: pyqtgraph/examples/customGraphicsItem.py
# ============================================================================

"""
CandlestickItem - OHLC 캔들스틱 그래픽 아이템

PyQtGraph의 GraphicsObject를 상속받아 캔들스틱 차트를 구현합니다.
QPainter를 사용하여 직접 렌더링하므로 Acrylic 효과와 완벽 호환됩니다.

Example:
    >>> data = [(timestamp1, open, high, low, close), ...]
    >>> candles = CandlestickItem(data)
    >>> plot.addItem(candles)
"""

import pyqtgraph as pg
from PyQt6 import QtCore, QtGui
from typing import List, Tuple
import numpy as np


class CandlestickItem(pg.GraphicsObject):
    """
    캔들스틱 차트 아이템
    
    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    캔들스틱은 주식 가격을 시각화하는 방법입니다.
    
    각 캔들은 4가지 정보를 담고 있어요:
    - Open (시가): 기간 시작 시 가격
    - High (고가): 기간 중 최고 가격
    - Low (저가): 기간 중 최저 가격  
    - Close (종가): 기간 종료 시 가격
    
    가격이 올랐으면 녹색, 내렸으면 빨간색으로 표시합니다.
    
    Attributes:
        data: OHLC 데이터 리스트 [(time, open, high, low, close), ...]
        up_color: 상승 캔들 색상 (기본: 녹색)
        down_color: 하락 캔들 색상 (기본: 빨간색)
        candle_width: 캔들 너비 (기본: 0.6)
    """
    
    def __init__(
        self, 
        data: List[Tuple[float, float, float, float, float]] = None,
        up_color: str = '#22c55e',
        down_color: str = '#ef4444',
        candle_width: float = 0.6
    ):
        """
        CandlestickItem 초기화
        
        Args:
            data: OHLC 데이터 [(time, open, high, low, close), ...]
                  time은 Unix timestamp (float) 또는 인덱스
            up_color: 상승 캔들 색상 (hex)
            down_color: 하락 캔들 색상 (hex)
            candle_width: 캔들 너비 (0~1, 기본 0.6)
        """
        super().__init__()
        
        self.data = data or []
        self.up_color = up_color
        self.down_color = down_color
        self.candle_width = candle_width
        
        # QPicture로 캔들 미리 렌더링 (성능 최적화)
        self.picture = QtGui.QPicture()
        # [FIX] 도지 캔들은 별도 저장 (paint()에서 픽셀 기반으로 그림)
        self._doji_candles = []  # [(t, o, w), ...]
        self._generatePicture()
    
    def setData(self, data: List[Tuple[float, float, float, float, float]]):
        """
        새로운 데이터로 캔들스틱 업데이트
        
        Args:
            data: OHLC 데이터 [(time, open, high, low, close), ...]
        """
        self.data = data
        self._generatePicture()
        self.informViewBoundsChanged()
        self.update()
    
    def _generatePicture(self):
        """
        캔들스틱을 QPicture에 미리 렌더링
        
        QPicture는 QPainter 명령을 저장하는 객체입니다.
        한 번 그려두면 paint() 호출 시 빠르게 재사용할 수 있습니다.
        """
        self.picture = QtGui.QPicture()
        self._doji_candles = []  # 도지 캔들 데이터 초기화
        
        if not self.data:
            return
        
        p = QtGui.QPainter(self.picture)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        
        # 캔들 너비 계산 (데이터 간격 기준)
        if len(self.data) >= 2:
            w = (self.data[1][0] - self.data[0][0]) * self.candle_width / 2
        else:
            w = 0.3
        
        for candle in self.data:
            t, o, h, l, c = candle
            
            # 상승/하락에 따른 색상 결정
            if c >= o:
                color = QtGui.QColor(self.up_color)
            else:
                color = QtGui.QColor(self.down_color)
            
            # 펜과 브러시 설정
            # [FIX] 펜을 cosmetic으로 설정하여 두께가 픽셀 단위로 고정됨
            pen = pg.mkPen(color)
            pen.setCosmetic(True)
            p.setPen(pen)
            p.setBrush(pg.mkBrush(color))
            
            # [FIX] QPicture에서 drawLine/drawRect의 길이가 0에 가까우면
            # 펜 두께가 데이터 좌표($1.00)로 렌더링되는 버그 발생.
            # 해결: 길이가 매우 작은 선/사각형은 그리지 않음
            
            wick_height = h - l
            body_height = c - o
            
            # Wick (심지) 그리기 - 고가에서 저가까지의 수직선
            # 심지 길이가 충분할 때만 그림
            if wick_height > 0.01:
                p.drawLine(
                    QtCore.QPointF(t, l),
                    QtCore.QPointF(t, h)
                )
            
            # Body (몸통) 그리기
            if abs(body_height) > 0.001:  # 0.1센트 초과면 일반 캔들
                # 일반 캔들: 사각형으로 그림
                p.drawRect(QtCore.QRectF(t - w, o, w * 2, body_height))
            else:
                # Doji: paint()에서 픽셀 기반으로 그림 (데이터만 저장)
                self._doji_candles.append((t, o, w))
        
        p.end()
    
    def paint(self, p: QtGui.QPainter, *args):
        """
        화면에 캔들스틱 렌더링
        
        이 메서드는 PyQtGraph가 자동으로 호출합니다.
        일반 캔들: 미리 생성해둔 QPicture를 재생
        도지 캔들: 픽셀 기반 최소 높이로 직접 그림
        """
        # 일반 캔들 그리기 (QPicture)
        p.drawPicture(0, 0, self.picture)
        
        # 도지 캔들 그리기 (픽셀 기반 최소 높이)
        if self._doji_candles:
            # 뷰 정보를 사용해 픽셀-데이터 변환 비율 계산
            view = self.getViewBox()
            if view is not None:
                view_rect = view.viewRect()
                pixel_height_view = view.height()
                data_height = view_rect.height()
                
                if pixel_height_view > 0 and data_height > 0:
                    # 1픽셀을 데이터 좌표로 변환
                    min_height = (1.0 / pixel_height_view) * data_height
                else:
                    min_height = 0.001
            else:
                min_height = 0.001
            
            # 도지 캔들 그리기 (NoPen + 흰색 브러시)
            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(pg.mkBrush('#FFFFFF'))
            
            for t, o, w in self._doji_candles:
                p.drawRect(QtCore.QRectF(t - w, o - min_height/2, w * 2, min_height))
    
    def boundingRect(self) -> QtCore.QRectF:
        """
        캔들스틱의 경계 영역 반환
        
        PyQtGraph가 뷰 범위를 계산할 때 사용합니다.
        """
        if not self.data:
            return QtCore.QRectF()
        
        times = [d[0] for d in self.data]
        highs = [d[2] for d in self.data]
        lows = [d[3] for d in self.data]
        
        # 데이터 범위 계산
        min_t = min(times)
        max_t = max(times)
        min_price = min(lows)
        max_price = max(highs)
        
        # 약간의 여백 추가
        padding = (max_price - min_price) * 0.05 if max_price != min_price else 1
        
        return QtCore.QRectF(
            min_t,
            min_price - padding,
            max_t - min_t,
            (max_price - min_price) + padding * 2
        )
