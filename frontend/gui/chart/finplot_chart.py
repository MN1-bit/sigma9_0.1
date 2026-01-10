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

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
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
    TIMEFRAMES = ["1m", "3m", "5m", "15m", "1h", "4h", "1D", "1W"]

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

        # [09-003] Viewport 데이터 로딩을 위한 디바운스 타이머
        self._viewport_debounce = QTimer()
        self._viewport_debounce.setSingleShot(True)
        self._viewport_debounce.setInterval(150)  # 150ms 디바운스
        self._viewport_debounce.timeout.connect(self._emit_viewport_data_needed)
        self._pending_viewport_range: tuple = (0, 0)
        self._data_start_ts: int = 0  # 현재 로드된 데이터의 최소 타임스탬프

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

        # [09-003] finplot autoviewrestore 비활성화 (스크롤 후 자동 리셋 방지)
        fplt.autoviewrestore()  # 현재 뷰 저장

        # [09-003] Viewport 경계 제한 해제 (데이터 범위 밖으로 스크롤 허용)
        # NOTE: 데이터 로드 후에도 _disable_viewport_limits() 재호출 필요
        self._disable_viewport_limits()

        # [09-003] Viewport 변경 감지 (pyqtgraph sigXRangeChanged)
        self.ax.vb.sigXRangeChanged.connect(self._on_viewport_changed)

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

    def set_ticker(self, ticker: str) -> None:
        """
        현재 티커 설정

        [09-003] Historical data loading에 필요.

        Args:
            ticker: 종목 심볼 (예: "AAPL", "SMX")
        """
        self._current_ticker = ticker

    def set_candlestick_data(self, candles: List[Dict], ticker: str = None) -> None:
        """
        캔들스틱 데이터 설정

        Args:
            candles: [{"time": timestamp, "open": float, "high": float,
                      "low": float, "close": float}, ...]
            ticker: 종목 심볼 (선택적, 설정 시 _current_ticker 갱신)
        """
        if not candles:
            return

        self._candle_data = candles

        # [09-003] 티커 저장 (historical data loading에 필요)
        if ticker:
            self._current_ticker = ticker

        # [09-003] 데이터 시작 타임스탬프 저장 (viewport 스크롤 감지용)
        self._data_start_ts = min(c.get("time", 0) for c in candles)

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

        # [09-003] 데이터 로드 후 ViewBox 제한 다시 해제 (스크롤 허용)
        self._disable_viewport_limits()

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

    def set_atr_bands(self, upper_data: List[Dict], lower_data: List[Dict]) -> None:
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
        self._data_start_ts = 0
        fplt.refresh()

    def _disable_viewport_limits(self) -> None:
        """
        ViewBox 제한 해제 (데이터 범위 밖으로 스크롤 허용)

        [09-003] finplot/pyqtgraph는 기본적으로 데이터 범위 내로 스크롤을 제한합니다.
        이 메서드는 그 제한을 해제하여 과거 데이터 영역으로 스크롤할 수 있게 합니다.

        NOTE: fplt.refresh() 후에 호출해야 합니다 (refresh가 제한을 다시 설정할 수 있음).
        """
        try:
            # AutoRange 비활성화 (자동 확대/축소 방지)
            self.ax.vb.disableAutoRange()

            # X/Y축 경계 제한 해제 (None = 무제한)
            self.ax.vb.setLimits(xMin=None, xMax=None, yMin=None, yMax=None)

            # 자동 가시성 조정 비활성화
            self.ax.vb.setAutoVisible(x=False, y=False)

            # Volume 차트도 동일하게 적용
            if hasattr(self, "ax_volume") and self.ax_volume:
                self.ax_volume.vb.disableAutoRange()
                self.ax_volume.vb.setLimits(xMin=None, xMax=None, yMin=None, yMax=None)
        except Exception as e:
            print(f"[CHART] ViewBox limit disable failed: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # [09-003] Viewport 스크롤 감지 및 데이터 로딩
    # ═══════════════════════════════════════════════════════════════════════════

    def _on_viewport_changed(self, vb, range_) -> None:
        """
        Viewport 변경 시 호출 (pyqtgraph sigXRangeChanged)

        [09-003] Edge Trigger: 첫 번째 캔들이 뷰포트에 보이면 과거 데이터 로드
        NOTE: finplot/pyqtgraph의 range_는 **캔들 인덱스 기반** (0, 1, 2, ...)
        """
        if not range_ or len(range_) < 2:
            return

        # range_ = [x_min, x_max] (캔들 인덱스 기반, 0 = 첫 번째 캔들)
        x_min, x_max = range_[0], range_[1]

        # 로딩 중이거나 데이터가 없으면 무시
        if getattr(self, "_is_loading_historical", False):
            return
        if not self._candle_data:
            return

        # Edge Trigger: x_min이 5 이하면 첫 번째 캔들이 뷰포트에 가까이 있음
        # (약간의 여유를 두어 미리 로드 시작)
        TRIGGER_THRESHOLD = 5  # 5개 캔들 이하로 스크롤하면 트리거

        if x_min <= TRIGGER_THRESHOLD:
            print(f"[CHART] 🎯 Edge trigger fired! x_min={x_min:.1f}")
            self._pending_viewport_range = (int(self._data_start_ts), int(x_max))
            self._viewport_debounce.start()

    def _emit_viewport_data_needed(self) -> None:
        """
        디바운스 타이머 만료 시 과거 데이터 로드

        [09-003] 100 bars 통일 정책 (타임프레임별 조정):
        - m 단위 (1m/3m/5m/15m): 80 bars
        - h 단위 (1h/4h): 50 bars
        - D 단위 (1D/1W): 30 bars
        """
        # 중복 로드 방지
        if getattr(self, "_is_loading_historical", False):
            return

        start_ts, end_ts = self._pending_viewport_range
        if start_ts <= 0:
            return

        # 현재 티커와 타임프레임 확인
        ticker = getattr(self, "_current_ticker", None)
        timeframe = self._current_timeframe
        if not ticker:
            return

        # 타임프레임별 로드 수량 결정
        load_bars = self._get_load_bars_for_timeframe(timeframe)

        print(
            f"[CHART] 📊 Loading {load_bars} historical bars: {ticker} {timeframe} before {start_ts}"
        )

        # 로딩 플래그 설정
        self._is_loading_historical = True

        # 별도 스레드에서 데이터 로드
        import threading
        from PyQt6.QtCore import QMetaObject, Qt

        def load_in_thread():
            try:
                from backend.data.parquet_manager import ParquetManager

                pm = ParquetManager()

                # 소스 타임프레임과 소스 요청량 계산
                source_tf, source_bars = self._get_source_request(timeframe, load_bars)

                # Daily vs Intraday 분기
                if source_tf in ("1D", "1W"):
                    # Daily 데이터는 read_daily 사용
                    df = pm.read_daily(ticker=ticker, days=365)  # 1년치
                    ts_col = "date"  # read_daily는 date 컬럼 사용
                else:
                    # Intraday 데이터는 get_intraday_bars 사용
                    df = pm.get_intraday_bars(ticker=ticker, tf=source_tf, days=60)
                    ts_col = "timestamp"

                if df.empty:
                    print(f"[CHART] ⚠️ No historical data for {ticker}/{source_tf}")
                    return

                # 현재 데이터보다 이전 데이터만 필터링
                if ts_col == "date":
                    # date 컬럼은 string "YYYY-MM-DD" 또는 datetime
                    import pandas as pd
                    from datetime import datetime

                    cutoff_date = datetime.fromtimestamp(start_ts).strftime("%Y-%m-%d")
                    df = df[df["date"] < cutoff_date]
                else:
                    # timestamp 컬럼은 ms 단위
                    df = df[df["timestamp"] < start_ts * 1000]

                if df.empty:
                    print(f"[CHART] ⚠️ No older data for {ticker}/{source_tf}")
                    return

                # 소스와 타겟이 다르면 리샘플링 필요
                if source_tf != timeframe:
                    df = self._resample_df(df, timeframe)

                # 최신 N개만 사용
                if len(df) > load_bars:
                    df = df.tail(load_bars)

                # DataFrame → candles 변환
                candles = []
                for _, row in df.iterrows():
                    if ts_col == "date":
                        # date 컬럼을 epoch seconds로 변환
                        import pandas as pd

                        date_val = row["date"]
                        if isinstance(date_val, str):
                            time_val = pd.Timestamp(date_val).timestamp()
                        else:
                            time_val = date_val.timestamp()
                    else:
                        ts = row["timestamp"]
                        time_val = ts / 1000 if ts > 1e12 else ts

                    candles.append(
                        {
                            "time": time_val,
                            "open": float(row["open"]),
                            "high": float(row["high"]),
                            "low": float(row["low"]),
                            "close": float(row["close"]),
                            "volume": int(row.get("volume", 0)),
                        }
                    )

                if candles:
                    self._pending_prepend_candles = candles
                    QMetaObject.invokeMethod(
                        self,
                        "_apply_prepend_candles",
                        Qt.ConnectionType.QueuedConnection,
                    )
                    print(f"[CHART] ✅ Loaded {len(candles)} historical bars")

            except Exception as e:
                print(f"[CHART] ❌ Historical load error: {e}")
                import traceback

                traceback.print_exc()
            finally:
                self._is_loading_historical = False

        thread = threading.Thread(target=load_in_thread, daemon=True)
        thread.start()

    def _get_load_bars_for_timeframe(self, tf: str) -> int:
        """타임프레임별 로드할 바 수량 반환"""
        if tf.endswith("m"):
            return 80  # 분 단위: 80 bars
        elif tf.endswith("h"):
            return 50  # 시간 단위: 50 bars
        else:  # D, W
            return 30  # 일 단위: 30 bars

    def _get_source_request(self, target_tf: str, target_bars: int) -> tuple[str, int]:
        """
        타겟 타임프레임에 맞는 소스 타임프레임과 요청량 계산

        Returns:
            (source_tf, source_bars)
        """
        # 소스 타임프레임과 배수 정의
        resample_map = {
            "1m": ("1m", 1),
            "3m": ("1m", 3),
            "5m": ("1m", 5),
            "15m": ("1m", 15),
            "1h": ("1h", 1),
            "4h": ("1h", 4),
            "1D": ("1D", 1),
            "1W": ("1D", 7),
        }

        source_tf, multiplier = resample_map.get(target_tf, (target_tf, 1))
        source_bars = target_bars * multiplier
        return source_tf, source_bars

    def _resample_df(self, df, target_tf: str):
        """DataFrame을 타겟 타임프레임으로 리샘플링"""
        import pandas as pd

        # pandas resample 규칙
        resample_rules = {
            "3m": "3min",
            "5m": "5min",
            "15m": "15min",
            "4h": "4h",
            "1W": "W-MON",
        }

        rule = resample_rules.get(target_tf)
        if not rule:
            return df

        # timestamp를 datetime으로 변환
        df = df.copy()
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("datetime")

        # OHLCV 리샘플링
        resampled = (
            df.resample(rule)
            .agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                    "timestamp": "first",
                }
            )
            .dropna()
        )

        return resampled.reset_index(drop=True)

    from PyQt6.QtCore import pyqtSlot

    @pyqtSlot()
    def _apply_prepend_candles(self) -> None:
        """메인 스레드에서 과거 데이터 prepend"""
        candles = getattr(self, "_pending_prepend_candles", None)
        if candles:
            self.prepend_candlestick_data(candles)
            self._pending_prepend_candles = None

    def prepend_candlestick_data(self, candles: List[Dict]) -> None:
        """
        기존 캔들 데이터 앞에 과거 데이터 추가

        [09-003] 좌측 스크롤 시 호출되어 과거 데이터를 병합합니다.

        Args:
            candles: 과거 캔들 데이터 [{time, open, high, low, close}, ...]
        """
        if not candles:
            return

        # 기존 데이터 앞에 추가
        self._candle_data = candles + self._candle_data

        # 시작 타임스탬프 업데이트
        if candles:
            self._data_start_ts = min(c.get("time", 0) for c in candles)

        # 전체 데이터로 차트 다시 그리기
        df = self._convert_to_dataframe(self._candle_data)
        self.ax.reset()
        self._candlestick_plot = fplt.candlestick_ochl(
            df[["Open", "Close", "High", "Low"]], ax=self.ax
        )
        fplt.refresh()
