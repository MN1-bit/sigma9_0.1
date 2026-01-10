# ============================================================================
# Chart Widget - TradingView Lightweight Charts 통합
# ============================================================================
# 📌 이 파일의 역할:
#   - TradingView Lightweight Charts를 PyQt6에 통합
#   - QWebEngineView 기반 차트 렌더링
#   - 실시간 캔들스틱, VWAP, ATR 라인, Trade Markers 표시
#
# 📖 사용 예시:
#   >>> from frontend.gui.chart_widget import ChartWidget
#   >>> chart = ChartWidget()
#   >>> chart.add_candlestick_data(candles)
#   >>> chart.add_vwap_line(vwap_data)
# ============================================================================

"""
TradingView Lightweight Charts Widget

PyQt6 QWebEngineView를 사용하여 TradingView Lightweight Charts를 렌더링합니다.

Features:
    - 캔들스틱 차트 (1분봉, 5분봉, 일봉)
    - VWAP & ATR 라인
    - Trade Markers (진입/청산 포인트)
    - Ignition Points 시각화
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import pyqtSlot, pyqtSignal, QObject
from typing import List, Dict
import json


# ═══════════════════════════════════════════════════════════════════════════
# JavaScript Bridge
# ═══════════════════════════════════════════════════════════════════════════


class ChartBridge(QObject):
    """
    Python ↔ JavaScript 통신 브릿지

    QWebChannel을 통해 Python에서 JavaScript 함수 호출 및
    JavaScript에서 Python 함수 호출을 가능하게 합니다.
    """

    # 차트에서 Python으로 보내는 시그널
    chart_clicked = pyqtSignal(float, float)  # (time, price)
    crosshair_moved = pyqtSignal(float, float)  # (time, price)

    @pyqtSlot(float, float)
    def on_chart_click(self, time: float, price: float):
        """JavaScript에서 차트 클릭 시 호출"""
        self.chart_clicked.emit(time, price)

    @pyqtSlot(float, float)
    def on_crosshair_move(self, time: float, price: float):
        """JavaScript에서 크로스헤어 이동 시 호출"""
        self.crosshair_moved.emit(time, price)


# ═══════════════════════════════════════════════════════════════════════════
# ChartWidget 클래스
# ═══════════════════════════════════════════════════════════════════════════


class ChartWidget(QWidget):
    """
    TradingView Lightweight Charts 위젯

    PyQt6에서 실시간 차트를 렌더링하는 위젯입니다.

    Features:
        - 캔들스틱 차트 (OHLC)
        - 라인 시리즈 (VWAP, SMA, EMA)
        - 마커 (진입점, 청산점, Ignition)
        - 다크 테마 (acrylic 스타일 호환)

    Example:
        >>> chart = ChartWidget()
        >>> layout.addWidget(chart)
        >>> chart.set_candlestick_data([
        ...     {"time": "2024-01-01", "open": 10, "high": 11, "low": 9, "close": 10.5}
        ... ])
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # [FIX] 컨테이너 투명 속성 제거 (단색 배경 사용)
        # self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # self.setStyleSheet("background: transparent;")

        self._setup_ui()
        self._setup_bridge()
        self._load_chart()

    def _setup_ui(self):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView()
        # [FIX] 투명 배경 제거 (전체 Acrylic 깨짐 방지) -> 단색 배경 사용
        # WebEngineView의 투명 모드는 Windows DWM과 충돌하여 전체 윈도우를 검게 만들 수 있음
        # self.web_view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        # self.web_view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.web_view.setStyleSheet("background: #151520;")
        layout.addWidget(self.web_view)

    def _setup_bridge(self):
        """QWebChannel 브릿지 설정"""
        self.bridge = ChartBridge()
        self.channel = QWebChannel()
        self.channel.registerObject("bridge", self.bridge)
        self.web_view.page().setWebChannel(self.channel)

    def _load_chart(self):
        """차트 HTML 로드"""
        html = self._get_chart_html()
        self.web_view.setHtml(html)

    def _get_chart_html(self) -> str:
        """
        TradingView Lightweight Charts HTML 생성

        CDN에서 lightweight-charts 라이브러리를 로드하고
        다크 테마 차트를 초기화합니다.
        """
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            background: #151520; 
            overflow: hidden;
        }
        #chart-container { 
            width: 100%; 
            height: 100vh; 
        }
    </style>
</head>
<body>
    <div id="chart-container"></div>
    
    <script>
        // ═══════════════════════════════════════════════════════════════
        // 글로벌 변수
        // ═══════════════════════════════════════════════════════════════
        
        let chart = null;
        let candleSeries = null;
        let vwapSeries = null;
        let atrUpperSeries = null;
        let atrLowerSeries = null;
        let markers = [];
        let bridge = null;
        
        // ═══════════════════════════════════════════════════════════════
        // 차트 초기화
        // ═══════════════════════════════════════════════════════════════
        
        function initChart() {
            const container = document.getElementById('chart-container');
            
            chart = LightweightCharts.createChart(container, {
                layout: {
                    background: { type: 'solid', color: 'transparent' },
                    textColor: '#d1d5db',
                },
                grid: {
                    vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                    horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
                },
                crosshair: {
                    mode: LightweightCharts.CrosshairMode.Normal,
                    vertLine: { color: '#6366f1', width: 1, style: 2 },
                    horzLine: { color: '#6366f1', width: 1, style: 2 },
                },
                rightPriceScale: {
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                },
                timeScale: {
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    timeVisible: true,
                },
            });
            
            // 캔들스틱 시리즈
            candleSeries = chart.addCandlestickSeries({
                upColor: '#22c55e',
                downColor: '#ef4444',
                borderDownColor: '#ef4444',
                borderUpColor: '#22c55e',
                wickDownColor: '#ef4444',
                wickUpColor: '#22c55e',
            });
            
            // VWAP 라인
            vwapSeries = chart.addLineSeries({
                color: '#eab308',
                lineWidth: 2,
                title: 'VWAP',
            });
            
            // ATR 상단 (SL/TP용)
            atrUpperSeries = chart.addLineSeries({
                color: 'rgba(34, 197, 94, 0.5)',
                lineWidth: 1,
                lineStyle: 2,
                title: 'ATR+',
            });
            
            // ATR 하단 (SL용)
            atrLowerSeries = chart.addLineSeries({
                color: 'rgba(239, 68, 68, 0.5)',
                lineWidth: 1,
                lineStyle: 2,
                title: 'ATR-',
            });
            
            // 리사이즈 처리
            window.addEventListener('resize', () => {
                chart.applyOptions({ 
                    width: container.clientWidth, 
                    height: container.clientHeight 
                });
            });
            
            // 크로스헤어 이벤트
            chart.subscribeCrosshairMove((param) => {
                if (bridge && param.time && param.point) {
                    const price = candleSeries.coordinateToPrice(param.point.y);
                    bridge.on_crosshair_move(param.time, price || 0);
                }
            });
            
            // 클릭 이벤트
            chart.subscribeClick((param) => {
                if (bridge && param.time) {
                    const price = candleSeries.coordinateToPrice(param.point.y);
                    bridge.on_chart_click(param.time, price || 0);
                }
            });
        }
        
        // ═══════════════════════════════════════════════════════════════
        // Python에서 호출하는 함수들
        // ═══════════════════════════════════════════════════════════════
        
        function setCandlestickData(dataJson) {
            const data = JSON.parse(dataJson);
            candleSeries.setData(data);
            chart.timeScale().fitContent();
        }
        
        function updateCandlestick(barJson) {
            const bar = JSON.parse(barJson);
            candleSeries.update(bar);
        }
        
        function setVwapData(dataJson) {
            const data = JSON.parse(dataJson);
            vwapSeries.setData(data);
        }
        
        function setAtrBands(upperJson, lowerJson) {
            const upper = JSON.parse(upperJson);
            const lower = JSON.parse(lowerJson);
            atrUpperSeries.setData(upper);
            atrLowerSeries.setData(lower);
        }
        
        function addMarker(markerJson) {
            const m = JSON.parse(markerJson);
            markers.push({
                time: m.time,
                position: m.position || 'belowBar',
                color: m.color || '#2196F3',
                shape: m.shape || 'circle',
                text: m.text || '',
            });
            candleSeries.setMarkers(markers);
        }
        
        function clearMarkers() {
            markers = [];
            candleSeries.setMarkers([]);
        }
        
        // ═══════════════════════════════════════════════════════════════
        // QWebChannel 연결
        // ═══════════════════════════════════════════════════════════════
        
        new QWebChannel(qt.webChannelTransport, function(channel) {
            bridge = channel.objects.bridge;
        });
        
        // 차트 초기화
        initChart();
    </script>
</body>
</html>
        """

    # ═══════════════════════════════════════════════════════════════════
    # 데이터 설정 메서드
    # ═══════════════════════════════════════════════════════════════════

    def set_candlestick_data(self, candles: List[Dict]):
        """
        캔들스틱 데이터 설정

        Args:
            candles: [{"time": "2024-01-01", "open": 10, "high": 11, "low": 9, "close": 10.5}]
        """
        data_json = json.dumps(candles)
        self._run_js(f"setCandlestickData('{data_json}')")

    def update_candlestick(self, bar: Dict):
        """
        단일 캔들 업데이트 (실시간)

        Args:
            bar: {"time": 1704067200, "open": 10, "high": 11, "low": 9, "close": 10.5}
        """
        bar_json = json.dumps(bar)
        self._run_js(f"updateCandlestick('{bar_json}')")

    def set_vwap_data(self, vwap_data: List[Dict]):
        """
        VWAP 라인 데이터 설정

        Args:
            vwap_data: [{"time": "2024-01-01", "value": 10.5}]
        """
        data_json = json.dumps(vwap_data)
        self._run_js(f"setVwapData('{data_json}')")

    def set_atr_bands(self, upper_data: List[Dict], lower_data: List[Dict]):
        """
        ATR 밴드 설정 (상단/하단 라인)

        Args:
            upper_data: [{"time": "2024-01-01", "value": 11.0}]
            lower_data: [{"time": "2024-01-01", "value": 9.0}]
        """
        upper_json = json.dumps(upper_data)
        lower_json = json.dumps(lower_data)
        self._run_js(f"setAtrBands('{upper_json}', '{lower_json}')")

    def add_marker(
        self,
        time: str,
        text: str = "",
        color: str = "#2196F3",
        position: str = "belowBar",
        shape: str = "circle",
    ):
        """
        마커 추가 (Trade Entry/Exit, Ignition)

        Args:
            time: 시간 (ISO format 또는 Unix timestamp)
            text: 마커 텍스트
            color: 색상 (#hex)
            position: "aboveBar" | "belowBar" | "inBar"
            shape: "circle" | "square" | "arrowUp" | "arrowDown"
        """
        marker = {
            "time": time,
            "text": text,
            "color": color,
            "position": position,
            "shape": shape,
        }
        marker_json = json.dumps(marker)
        self._run_js(f"addMarker('{marker_json}')")

    def add_buy_marker(self, time: str, price: float = None):
        """매수 마커 추가"""
        text = f"BUY ${price:.2f}" if price else "BUY"
        self.add_marker(time, text, "#22c55e", "belowBar", "arrowUp")

    def add_sell_marker(self, time: str, price: float = None):
        """매도 마커 추가"""
        text = f"SELL ${price:.2f}" if price else "SELL"
        self.add_marker(time, text, "#ef4444", "aboveBar", "arrowDown")

    def add_ignition_marker(self, time: str, score: float = None):
        """Ignition 포인트 마커 추가"""
        text = f"🔥 {score:.0f}" if score else "🔥"
        self.add_marker(time, text, "#f97316", "belowBar", "circle")

    def clear_markers(self):
        """모든 마커 제거"""
        self._run_js("clearMarkers()")

    # ═══════════════════════════════════════════════════════════════════
    # 유틸리티
    # ═══════════════════════════════════════════════════════════════════

    def _run_js(self, script: str):
        """JavaScript 실행"""
        self.web_view.page().runJavaScript(script)


# ═══════════════════════════════════════════════════════════════════════════
# 테스트
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """독립 실행 테스트"""
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    # 테스트 윈도우
    chart = ChartWidget()
    chart.resize(800, 600)
    chart.setWindowTitle("TradingView Chart Test")
    chart.show()

    # 테스트 데이터 (지연 로드)
    from PyQt6.QtCore import QTimer

    def load_test_data():
        test_candles = [
            {
                "time": "2024-01-01",
                "open": 10.0,
                "high": 10.5,
                "low": 9.5,
                "close": 10.2,
            },
            {
                "time": "2024-01-02",
                "open": 10.2,
                "high": 10.8,
                "low": 10.0,
                "close": 10.6,
            },
            {
                "time": "2024-01-03",
                "open": 10.6,
                "high": 11.0,
                "low": 10.4,
                "close": 10.8,
            },
            {
                "time": "2024-01-04",
                "open": 10.8,
                "high": 11.5,
                "low": 10.7,
                "close": 11.3,
            },
            {
                "time": "2024-01-05",
                "open": 11.3,
                "high": 12.0,
                "low": 11.0,
                "close": 11.8,
            },
        ]
        chart.set_candlestick_data(test_candles)

        test_vwap = [
            {"time": "2024-01-01", "value": 10.1},
            {"time": "2024-01-02", "value": 10.4},
            {"time": "2024-01-03", "value": 10.6},
            {"time": "2024-01-04", "value": 10.9},
            {"time": "2024-01-05", "value": 11.2},
        ]
        chart.set_vwap_data(test_vwap)

        chart.add_buy_marker("2024-01-03", 10.8)
        chart.add_ignition_marker("2024-01-03", 85)

    QTimer.singleShot(1000, load_test_data)

    sys.exit(app.exec())
