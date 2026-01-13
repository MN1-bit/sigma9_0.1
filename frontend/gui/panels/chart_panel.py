# ==============================================================================
# chart_panel.py - 차트 영역 패널
# ==============================================================================
# 📌 이 파일의 역할:
#    Sigma9 Dashboard의 CENTER PANEL (차트 영역)입니다.
#    finplot 기반 차트 위젯을 래핑하고, 샘플 데이터 로딩 기능을 제공합니다.
#
# 📌 ELI5:
#    주식 차트를 보여주는 패널이에요. 캔들스틱, 거래량, 이동평균선 등을
#    모두 이 패널에서 표시합니다.
# ==============================================================================
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import pyqtSignal

if TYPE_CHECKING:
    from ..chart.finplot_chart import FinplotChartWidget


class ChartPanel(QFrame):
    """
    차트 영역 패널 - PyQtGraph 래퍼

    ═══════════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════════
    이건 주식 차트를 보여주는 패널이에요.

    - 캔들스틱 차트 (빨간색/초록색 막대)
    - 거래량 바
    - 이동평균선 (SMA, EMA)
    - 매수/손절/익절 가격선
    - Ignition 마커 (🔥 표시)

    PyQtGraph라는 빠른 차트 라이브러리를 사용해서 실시간 업데이트도 부드럽게!
    ═══════════════════════════════════════════════════════════════════════════
    """

    # =========================================================================
    # 시그널 (Signal) - 이벤트 발생 시 외부에 알림
    # =========================================================================
    # 타임프레임 변경 시 (1D, 1h, 5m 등)
    timeframe_changed = pyqtSignal(str)

    # 뷰포트에서 더 많은 데이터가 필요할 때
    # [FIX 13-001] PyQtGraphChartWidget과 시그니처 일치 (int, int)
    viewport_data_needed = pyqtSignal(int, int)

    # 📌 [09-009] 차트 로드 요청 시그널 (ticker, source)
    # Dashboard에서 이 시그널을 받아 실제 차트 데이터 로딩 수행
    chart_load_requested = pyqtSignal(str, str)

    def __init__(self, theme=None, state=None):
        """
        차트 패널 초기화

        Args:
            theme: 테마 매니저 (기본값: 전역 theme 사용)
            state: DashboardState 인스턴스 (선택, Event Bus 연결용)
        """
        super().__init__()

        from ..theme import theme as global_theme

        self._theme = theme or global_theme
        self._chart_widget: FinplotChartWidget | None = None
        self._state = state

        self._setup_ui()

        # 📌 [09-009] Event Bus 연결
        if self._state:
            self._state.ticker_changed.connect(self._on_ticker_changed)

    def _on_ticker_changed(self, ticker: str, source: str) -> None:
        """
        [09-009] 티커 변경 시 차트 로드 요청

        Dashboard에서 chart_load_requested 시그널을 받아 실제 로딩 수행
        """
        self.chart_load_requested.emit(ticker, source)

    def _setup_ui(self) -> None:
        """UI 구성"""
        from ..chart.finplot_chart import FinplotChartWidget

        c = self._theme.colors

        # 프레임 스타일
        self.setStyleSheet(self._theme.get_stylesheet("panel"))

        # 레이아웃
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        # 제목 라벨
        title_label = QLabel("📈 Chart")
        title_label.setStyleSheet(f"""
            color: {c["text_secondary"]}; 
            font-size: 12px; 
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        layout.addWidget(title_label)

        # =====================================================================
        # PyQtGraph 기반 차트 위젯
        # Acrylic 효과와 완전히 호환됩니다.
        # =====================================================================
        self._chart_widget = FinplotChartWidget()
        self._chart_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # 차트 위젯의 시그널을 패널 시그널로 전달
        self._chart_widget.timeframe_changed.connect(self.timeframe_changed.emit)
        self._chart_widget.viewport_data_needed.connect(self.viewport_data_needed.emit)

        layout.addWidget(self._chart_widget)

    @property
    def chart_widget(self) -> FinplotChartWidget:
        """
        차트 위젯 반환 (호환성용)

        기존 코드에서 self.chart_widget으로 접근하던 것을 지원합니다.
        """
        return self._chart_widget

    def load_sample_data(self) -> None:
        """
        샘플 차트 데이터 로드

        차트 위젯이 정상적으로 표시되는지 확인을 위한 테스트 데이터입니다.
        100개의 일봉 캔들 + Volume + VWAP + SMA + EMA를 생성합니다.
        """
        import numpy as np
        import time as time_module

        # =====================================================================
        # 100개 캔들 생성 (일봉 기준)
        # 시작 가격 $10에서 약간 상승 편향으로 랜덤 워크
        # =====================================================================
        base_time = time_module.time() - 86400 * 100  # 100일 전부터
        candles = []
        volumes = []
        price = 10.0

        for i in range(100):
            o = price  # Open = 이전 Close
            delta = np.random.uniform(-0.3, 0.35)  # 약간 상승 편향
            c = price + delta  # Close
            h = max(o, c) + np.random.uniform(0, 0.2)  # High
            low_val = min(o, c) - np.random.uniform(0, 0.2)  # Low
            vol = int(np.random.uniform(100000, 500000))  # Volume
            is_up = c >= o  # 상승 봉인지 여부

            timestamp = base_time + i * 86400  # 하루씩 증가

            candles.append(
                {
                    "time": timestamp,
                    "open": round(o, 2),
                    "high": round(h, 2),
                    "low": round(low_val, 2),
                    "close": round(c, 2),
                }
            )
            volumes.append(
                {
                    "time": timestamp,
                    "volume": vol,
                    "is_up": is_up,
                }
            )
            price = c  # 다음 봉의 시작 가격

        # =====================================================================
        # 차트 위젯에 데이터 설정
        # =====================================================================

        # 캔들스틱 설정
        self._chart_widget.set_candlestick_data(candles)

        # Volume 설정
        self._chart_widget.set_volume_data(volumes)

        # =====================================================================
        # VWAP (Volume Weighted Average Price) 간이 계산
        # 실제로는 정확한 공식을 사용하지만, 여기서는 간이 버전
        # =====================================================================
        vwap_data = []
        cumulative = 0
        for i, c in enumerate(candles):
            tp = (c["high"] + c["low"] + c["close"]) / 3  # Typical Price
            cumulative = (cumulative * i + tp) / (i + 1) if i > 0 else tp
            vwap_data.append({"time": c["time"], "value": cumulative})
        self._chart_widget.set_vwap_data(vwap_data)

        # =====================================================================
        # SMA 20 (Simple Moving Average, 20일)
        # 최근 20개 종가의 평균
        # =====================================================================
        closes = [c["close"] for c in candles]
        sma_data = []
        for i in range(19, len(candles)):  # 20번째 캔들부터 계산 가능
            sma = sum(closes[i - 19 : i + 1]) / 20
            sma_data.append({"time": candles[i]["time"], "value": sma})
        self._chart_widget.set_ma_data(sma_data, period=20, color="#3b82f6")  # 파란색

        # =====================================================================
        # EMA 9 (Exponential Moving Average, 9일)
        # 최근 값에 더 큰 가중치를 주는 이동평균
        # =====================================================================
        ema = closes[0]
        mult = 2 / 10  # EMA 승수 = 2 / (period + 1)
        ema_data = []
        for i, c in enumerate(candles):
            ema = (closes[i] - ema) * mult + ema
            if i >= 8:  # 9번째 캔들부터 표시
                ema_data.append({"time": c["time"], "value": ema})
        self._chart_widget.set_ma_data(ema_data, period=9, color="#a855f7")  # 보라색

        # =====================================================================
        # 진입/손절/익절 레벨
        # 현재 가격 기준 ±5%, ±10%
        # =====================================================================
        current_price = candles[-1]["close"]
        self._chart_widget.set_price_levels(
            entry=current_price,
            stop_loss=current_price * 0.95,  # -5%
            take_profit=current_price * 1.10,  # +10%
        )

        # =====================================================================
        # Ignition 마커 (80번째 캔들에 표시)
        # 폭발 신호 감지 시 표시되는 마커
        # =====================================================================
        self._chart_widget.add_ignition_marker(
            candles[80]["time"], candles[80]["high"], score=85
        )

    def schedule_sample_load(self, delay_ms: int = 1500) -> None:
        """
        지연 후 샘플 데이터 로드 예약

        Args:
            delay_ms: 지연 시간 (밀리초)
        """
        from PyQt6.QtCore import QTimer

        QTimer.singleShot(delay_ms, self.load_sample_data)
