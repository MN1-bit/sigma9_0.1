# ==============================================================================
# Finplot Chart Widget - finplot 기반 트레이딩 차트
# ==============================================================================
# 📌 이 파일의 역할:
#    finplot 라이브러리를 PyQt6 위젯으로 래핑하여 캔들스틱 차트 표시
#    기존 PyQtGraphChartWidget과 동일한 인터페이스 유지
#
# 📌 ELI5:
#    TradingView 스타일 차트를 쉽게 그려주는 finplot을 사용해서
#    캔들, 볼륨, 지표를 한번에 표시하는 위젯이에요.
# ==============================================================================
from __future__ import annotations

import os
from typing import Dict, List, Optional

import pandas as pd

# finplot은 PyQt6를 사용하도록 환경변수 설정 (import 전에!)
os.environ["QT_API"] = "pyqt6"
import finplot as fplt

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ..theme import theme


class FinplotChartWidget(QWidget):
    """
    finplot 기반 트레이딩 차트 위젯

    ═══════════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════════
    이 위젯은 주식 차트를 그려주는 도화지입니다.

    위쪽 큰 패널: 캔들스틱 (가격 움직임)
    아래쪽 작은 패널: 볼륨 바 차트 (거래량)

    finplot 라이브러리가 대부분의 작업을 알아서 해줍니다!

    Signals:
        timeframe_changed: 타임프레임 변경 시 발생 (str)
        viewport_data_needed: 뷰포트 밖 데이터 필요 시 발생 (int, int)
    ═══════════════════════════════════════════════════════════════════════════
    """

    # 시그널 정의 (기존 인터페이스 호환)
    timeframe_changed = pyqtSignal(str)
    chart_clicked = pyqtSignal(float, float)
    viewport_data_needed = pyqtSignal(int, int)

    # 지원하는 타임프레임
    TIMEFRAMES = ["1m", "5m", "15m", "1h", "1D"]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # 투명 배경 설정 (Acrylic 호환)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        # 내부 상태
        self._current_timeframe = "1D"
        self._candle_data: List[Dict] = []
        self._volume_data: List[Dict] = []

        # finplot 아이템 참조
        self._candlestick_plot = None
        self._volume_plot = None
        self._vwap_line = None
        self._ma_lines: Dict[int, object] = {}
        self._price_levels: Dict[str, object] = {}

        # finplot 테마 설정
        self._setup_finplot_theme()

        # UI 초기화
        self._setup_ui()

    def _setup_finplot_theme(self) -> None:
        """finplot 테마 색상 설정"""
        c = theme.colors

        # 캔들 색상
        fplt.candle_bull_color = c["chart_up"]
        fplt.candle_bear_color = c["chart_down"]
        fplt.candle_bull_body_color = c["chart_up"]
        fplt.candle_bear_body_color = c["chart_down"]

        # 볼륨 색상
        fplt.volume_bull_color = c["chart_up"]
        fplt.volume_bear_color = c["chart_down"]

        # 배경/축 색상 (투명)
        # NOTE: finplot은 rgba() 형식을 지원하지 않으므로 hex만 사용
        fplt.background = "#00000000"  # 투명
        fplt.foreground = "#FFFFFF"  # 흰색 (c["text"]가 rgba일 수 있음)
        fplt.cross_hair_color = "#999999"  # 회색

        # 그리드
        fplt.display_timezone = None  # 로컬 시간 사용

    def _setup_ui(self) -> None:
        """UI 구성"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # ═══════════════════════════════════════════════════════════════════
        # 1. 상단 툴바 (타임프레임 버튼 그룹)
        # ═══════════════════════════════════════════════════════════════════
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(4, 4, 4, 0)
        toolbar.setSpacing(2)

        self._tf_buttons: Dict[str, QPushButton] = {}
        for tf in self.TIMEFRAMES:
            btn = QPushButton(tf)
            btn.setCheckable(True)
            btn.setChecked(tf == self._current_timeframe)
            btn.setFixedHeight(24)
            btn.setMinimumWidth(36)
            btn.clicked.connect(
                lambda checked, timeframe=tf: self._on_tf_button_clicked(timeframe)
            )
            self._tf_buttons[tf] = btn
            toolbar.addWidget(btn)

        self._update_tf_button_styles()
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # ═══════════════════════════════════════════════════════════════════
        # 2. finplot 차트 영역
        # ═══════════════════════════════════════════════════════════════════
        # 공식 finplot 임베딩 방법 (finplot/examples/embed.py 참조):
        # 1. fplt.create_plot() 사용 (not create_plot_widget)
        # 2. self.axs = [ax, ...] 설정 (finplot 요구사항)
        # 3. ax.vb.win을 레이아웃에 추가
        # 4. fplt.show(qt_exec=False) 호출

        # 메인 차트 (캔들스틱)
        self.ax = fplt.create_plot(init_zoom_periods=100)
        
        # 볼륨 차트 (오버레이)
        self.ax_volume = self.ax.overlay()
        
        # finplot 요구사항: 위젯에 axs 속성 설정
        self.axs = [self.ax, self.ax_volume]
        
        # ax.vb.win (ViewBox의 윈도우)을 레이아웃에 추가
        layout.addWidget(self.ax.vb.win, stretch=1)

        # Qt 이벤트 루프와 분리 (부모 앱이 이벤트 루프 관리)
        fplt.show(qt_exec=False)

    def _on_tf_button_clicked(self, timeframe: str) -> None:
        """타임프레임 버튼 클릭 핸들러"""
        if timeframe == self._current_timeframe:
            self._tf_buttons[timeframe].setChecked(True)
            return

        self._current_timeframe = timeframe
        self._update_tf_button_styles()
        self.timeframe_changed.emit(timeframe)

    def _update_tf_button_styles(self) -> None:
        """타임프레임 버튼 스타일 업데이트"""
        for tf, btn in self._tf_buttons.items():
            is_selected = tf == self._current_timeframe
            btn.setChecked(is_selected)

            if is_selected:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {theme.get_color("primary")};
                        border: none;
                        border-radius: 4px;
                        padding: 2px 8px;
                        color: white;
                        font-size: 11px;
                        font-weight: bold;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        border: 1px solid {theme.get_color("border")};
                        border-radius: 4px;
                        padding: 2px 8px;
                        color: {theme.get_color("text_secondary")};
                        font-size: 11px;
                    }}
                    QPushButton:hover {{
                        background-color: {theme.get_color("surface")};
                        color: {theme.get_color("text")};
                    }}
                """)

    # ═══════════════════════════════════════════════════════════════════════════
    # 데이터 설정 메서드 (기존 인터페이스 호환)
    # ═══════════════════════════════════════════════════════════════════════════

    def set_candlestick_data(self, candles: List[Dict]) -> None:
        """
        캔들스틱 데이터 설정

        Args:
            candles: [{"time": timestamp, "open": float, "high": float,
                      "low": float, "close": float}, ...]
        """
        if not candles:
            return

        self._candle_data = candles

        # Dict 리스트를 DataFrame으로 변환
        df = self._convert_to_dataframe(candles)

        # 기존 플롯 제거 후 새로 그리기
        self.ax.reset()

        # 캔들스틱 플롯
        self._candlestick_plot = fplt.candlestick_ochl(
            df[["Open", "Close", "High", "Low"]], ax=self.ax
        )

        # 자동 스케일링
        fplt.refresh()

    def set_volume_data(self, volume_data: List[Dict]) -> None:
        """
        Volume 바 차트 설정

        Args:
            volume_data: [{"time": timestamp, "volume": int, "is_up": bool}, ...]
        """
        if not volume_data:
            return

        self._volume_data = volume_data

        # DataFrame 변환
        df = pd.DataFrame(volume_data)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df.set_index("time")
        df = df.rename(columns={"volume": "Volume"})

        # finplot volume_ocv는 Open, Close, Volume 3개 컬럼 필요 (ocv = Open, Close, Volume)
        # is_up 기반으로 Open, Close 더미 값 생성
        if "is_up" in df.columns:
            df["Open"] = 0
            df["Close"] = df["is_up"].apply(lambda x: 1 if x else -1)
        else:
            df["Open"] = 0
            df["Close"] = 1

        # 기존 볼륨 플롯 제거
        self.ax_volume.reset()

        # 볼륨 플롯 (Open, Close, Volume 순서)
        self._volume_plot = fplt.volume_ocv(
            df[["Open", "Close", "Volume"]], ax=self.ax_volume
        )

        fplt.refresh()

    def set_vwap_data(self, vwap_data: List[Dict]) -> None:
        """
        VWAP 라인 데이터 설정

        Args:
            vwap_data: [{"time": timestamp, "value": float}, ...]
        """
        if not vwap_data:
            return

        df = pd.DataFrame(vwap_data)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df.set_index("time")

        self._vwap_line = fplt.plot(
            df["value"],
            ax=self.ax,
            color=theme.colors["warning"],  # 노란색 VWAP
            width=2,
            legend="VWAP",
        )

    def set_ma_data(
        self, ma_data: List[Dict], period: int = 20, color: str = "#3b82f6"
    ) -> None:
        """
        MA (이동평균) 라인 설정

        Args:
            ma_data: [{"time": timestamp, "value": float}, ...]
            period: MA 기간 (라벨용)
            color: 라인 색상
        """
        if not ma_data:
            return

        df = pd.DataFrame(ma_data)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df.set_index("time")

        self._ma_lines[period] = fplt.plot(
            df["value"],
            ax=self.ax,
            color=color,
            width=1,
            legend=f"MA{period}",
        )

    def set_atr_bands(
        self, upper_data: List[Dict], lower_data: List[Dict]
    ) -> None:
        """ATR 밴드 설정 (상단/하단)"""
        if upper_data:
            df_upper = pd.DataFrame(upper_data)
            df_upper["time"] = pd.to_datetime(df_upper["time"], unit="s")
            df_upper = df_upper.set_index("time")
            fplt.plot(
                df_upper["value"],
                ax=self.ax,
                color=theme.colors["chart_up"],
                style="--",
                legend="ATR+",
            )

        if lower_data:
            df_lower = pd.DataFrame(lower_data)
            df_lower["time"] = pd.to_datetime(df_lower["time"], unit="s")
            df_lower = df_lower.set_index("time")
            fplt.plot(
                df_lower["value"],
                ax=self.ax,
                color=theme.colors["chart_down"],
                style="--",
                legend="ATR-",
            )

    def set_price_levels(
        self,
        entry: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> None:
        """
        수평선 레벨 설정 (Entry, Stop Loss, Take Profit)

        Args:
            entry: 진입 가격 (파란색 실선)
            stop_loss: 손절 가격 (빨간색 점선)
            take_profit: 익절 가격 (녹색 점선)
        """
        if entry is not None:
            fplt.add_line(
                (0, entry),
                (1, entry),
                ax=self.ax,
                color=theme.colors["primary"],
                width=2,
            )

        if stop_loss is not None:
            fplt.add_line(
                (0, stop_loss),
                (1, stop_loss),
                ax=self.ax,
                color=theme.colors["chart_down"],
                style="--",
            )

        if take_profit is not None:
            fplt.add_line(
                (0, take_profit),
                (1, take_profit),
                ax=self.ax,
                color=theme.colors["chart_up"],
                style="--",
            )

    def add_ignition_marker(
        self, timestamp: float, price: float, score: int = 0
    ) -> None:
        """
        Ignition 마커 추가 (🔥 표시)

        Args:
            timestamp: 마커 위치 (타임스탬프)
            price: 마커 가격 위치
            score: 점수 (라벨용)
        """
        from datetime import datetime

        dt = datetime.fromtimestamp(timestamp)
        fplt.add_text(
            (dt, price * 1.02),  # 캔들 위에 표시
            f"🔥 {score}",
            ax=self.ax,
            color=theme.colors["warning"],
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # 헬퍼 메서드
    # ═══════════════════════════════════════════════════════════════════════════

    def _convert_to_dataframe(self, candles: List[Dict]) -> pd.DataFrame:
        """
        Dict 리스트를 finplot용 DataFrame으로 변환

        Returns:
            DataFrame with columns: Open, Close, High, Low (DatetimeIndex)
        """
        df = pd.DataFrame(candles)

        # 타임스탬프 → datetime 변환
        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"], unit="s")
            df = df.set_index("time")

        # 컬럼명 표준화 (finplot은 대문자 컬럼 기대)
        rename_map = {
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
        df = df.rename(columns=rename_map)

        return df

    def clear(self) -> None:
        """차트 초기화"""
        self.ax.reset()
        self.ax_volume.reset()
        self._candle_data = []
        self._volume_data = []
        self._ma_lines.clear()
        fplt.refresh()
