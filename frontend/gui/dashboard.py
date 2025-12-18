# ============================================================================
# Sigma9 Dashboard - 메인 대시보드 윈도우
# ============================================================================
# 📌 이 파일의 역할:
#   Sigma9 트레이딩 시스템의 메인 GUI 대시보드입니다.
#   Acrylic(Glassmorphism) 효과가 적용된 모던한 디자인을 제공합니다.
#
# 📌 레이아웃 구조 (5-Panel):
#   ┌─────────────────────────────────────────────────────┐
#   │                  TOP (Control Panel)                │
#   ├────────┬──────────────────────────────┬─────────────┤
#   │  LEFT  │           CENTER             │    RIGHT    │
#   │Watchlist│           Chart             │  Positions  │
#   ├────────┴──────────────────────────────┴─────────────┤
#   │                  BOTTOM (Log)                       │
#   └─────────────────────────────────────────────────────┘
#
# 📌 기반 코드: docs/references/GUI-demo/demo.py
# ============================================================================

"""
Sigma9 Dashboard

PyQt6 기반의 트레이딩 대시보드 메인 윈도우입니다.
Acrylic 효과와 파티클 이펙트를 지원합니다.
"""

import sys
import os

# 고DPI 스케일링 문제 해결을 위한 환경변수
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

try:
    from PyQt6.QtGui import QIcon, QColor, QFont
    from PyQt6.QtWidgets import (
        QApplication, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
        QSlider, QPushButton, QSplitter, QTextEdit, QListWidget,
        QWidget, QSizePolicy, QComboBox
    )
    from PyQt6.QtCore import Qt, QTimer
except ModuleNotFoundError:
    from PySide6.QtGui import QIcon, QColor, QFont
    from PySide6.QtWidgets import (
        QApplication, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
        QSlider, QPushButton, QSplitter, QTextEdit, QListWidget,
        QWidget, QSizePolicy, QComboBox
    )
    from PySide6.QtCore import Qt, QTimer

from .custom_window import CustomWindow
from .particle_effects import ParticleSystem
from .theme import theme  # [REFAC] 테마 매니저 임포트
from .settings_dialog import SettingsDialog
# from .chart_widget import ChartWidget  # Step 2.4.7: 차트 위젯 (Backup) - REMOVED due to missing dependency
from .chart.pyqtgraph_chart import PyQtGraphChartWidget  # [NEW] PyQtGraph 기반 차트
from .control_panel import ControlPanel, StatusIndicator, LoadingOverlay  # [NEW] Step 3.4
from ..config.loader import load_settings, save_settings
from ..services.backend_client import BackendClient, ConnectionState, WatchlistItem  # [NEW] Step 3.4


class Sigma9Dashboard(CustomWindow):
    """
    Sigma9 메인 대시보드 윈도우
    
    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    이 클래스는 Sigma9 트레이딩 시스템의 "조종석(Control Room)"입니다.
    
    조종석을 5개 구역으로 나눴어요:
    1. TOP: 연결/시작/정지 버튼들
    2. LEFT: 감시 중인 종목 리스트 (Watchlist)
    3. CENTER: 주가 차트
    4. RIGHT: 현재 보유 포지션과 수익
    5. BOTTOM: 실시간 로그
    
    그리고 창 뒤가 살짝 비치는 "Acrylic" 효과로 멋있게 꾸몄습니다!
    """
    
    def __init__(self):
        """
        대시보드 초기화
        
        - Acrylic 효과 설정
        - 5-Panel 레이아웃 구성
        - 파티클 시스템 오버레이 추가
        """
        # [REFAC] 테마 매니저에서 초기 색상 가져오기
        self.tint_r = theme.tint_r
        self.tint_g = theme.tint_g
        self.tint_b = theme.tint_b
        self.alpha = theme.acrylic_map_alpha
        
        super().__init__(
            use_mica='false',
            theme=theme.mode,  # [REFAC] 설정된 테마 모드 사용
            color=self._get_color_string()
        )
        
        # 윈도우 설정
        self.resize(1400, 900)
        self.setWindowTitle("Sigma9 Trading Dashboard")
        self.setMinimumSize(1000, 700)
        self.setWindowOpacity(theme.opacity)
        
        # 5-Panel 레이아웃 구성
        self._init_dashboard()
        
        # 파티클 시스템 오버레이 추가 (트레이딩 이펙트용)
        self.particle_system = ParticleSystem(self)
        self.particle_system.setGeometry(0, 0, self.width(), self.height())
        self.particle_system.global_alpha = theme.particle_alpha # [NEW] 초기 투명도 적용
        self.particle_system.set_background_effect(theme.background_effect) # [NEW] 초기 배경 이펙트 적용
        self.particle_system.raise_()
        
        # ═══════════════════════════════════════════════════════════════════
        # Step 3.4: BackendClient 초기화
        # ═══════════════════════════════════════════════════════════════════
        self.backend_client = BackendClient.instance()
        self._connect_backend_signals()
        
        # Step 2.5: StrategyLoader 초기화 및 전략 목록 로드
        self._init_strategy_loader()
        
        # Step 3.4.6: GUI 시작 시 자동 연결 (500ms 후)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(500, self._auto_connect_backend)

    def _connect_backend_signals(self):
        """
        BackendClient Signal 연결
        
        Step 3.4: BackendClient의 시그널을 GUI 핸들러에 연결합니다.
        """
        # 연결 상태 변경
        self.backend_client.state_changed.connect(self._on_backend_state_changed)
        
        # Watchlist 업데이트 (Step 3.4.8)
        self.backend_client.watchlist_updated.connect(self._update_watchlist_panel)
        
        # Ignition Score 업데이트 (Phase 2)
        self.backend_client.ignition_updated.connect(self._on_ignition_update)
        
        # 에러 발생
        self.backend_client.error_occurred.connect(
            lambda msg: self.log(f"[ERROR] {msg}")
        )
        
        # 로그 메시지
        self.backend_client.log_message.connect(self.log)
        
        # Ignition Score 캐시 초기화 (ticker -> score)
        self._ignition_cache: dict = {}
    
    def _auto_connect_backend(self):
        """
        Step 3.4.6: GUI 시작 시 Backend 자동 연결
        
        500ms 후에 호출되어 Backend에 자동으로 연결을 시도합니다.
        연결 성공 시 현재 선택된 전략으로 Scanner를 자동 실행합니다.
        """
        self.log("[INFO] Auto-connecting to backend...")
        # [FIX] async → sync 래퍼 사용
        if self.backend_client.connect_sync():
            # 연결 성공 시 Scanner 자동 실행 (Step 3.4.7)
            current_strategy = self.control_panel.get_selected_strategy()
            if current_strategy:
                self._run_scanner_for_strategy(current_strategy)

    def resizeEvent(self, event):
        """윈도우 크기 변경 시 파티클 시스템 크기도 조절"""
        super().resizeEvent(event)
        if hasattr(self, 'particle_system'):
            self.particle_system.setGeometry(0, 0, self.width(), self.height())

    def _get_color_string(self) -> str:
        """Acrylic 색상 문자열 생성 (RRGGBBAA 형식)"""
        return f"{self.tint_r:02X}{self.tint_g:02X}{self.tint_b:02X}{self.alpha:02X}"

    def _init_dashboard(self):
        """
        5-Panel 대시보드 레이아웃 구성
        
        ┌──────────────────────────────────────────────────────────┐
        │                    TOP PANEL (Control)                    │
        ├──────────┬──────────────────────────────┬────────────────┤
        │   LEFT   │           CENTER             │     RIGHT      │
        │ (200px)  │         (stretch)            │   (250px)      │
        ├──────────┴──────────────────────────────┴────────────────┤
        │                  BOTTOM PANEL (Log)                       │
        │                      (120px)                              │
        └──────────────────────────────────────────────────────────┘
        """
        # 메인 레이아웃 (세로 배치)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 45, 10, 10)  # 타이틀바 공간 확보
        main_layout.setSpacing(8)
        
        # ═══════════════════════════════════════════════════════════
        # 1. TOP PANEL - 컨트롤 패널 (Step 3.4)
        # ═══════════════════════════════════════════════════════════
        self.control_panel = ControlPanel()
        self._connect_control_panel_signals()
        main_layout.addWidget(self.control_panel)
        
        # ═══════════════════════════════════════════════════════════
        # 2. MIDDLE AREA - Left, Center, Right (Splitter 사용)
        # ═══════════════════════════════════════════════════════════
        middle_splitter = QSplitter(Qt.Orientation.Horizontal)
        middle_splitter.setStyleSheet(f"""
            QSplitter {{ background: transparent; }}
            QSplitter::handle {{ background: {theme.get_color('border')}; }}
        """)
        
        # LEFT PANEL - Watchlist
        left_panel = self._create_left_panel()
        middle_splitter.addWidget(left_panel)
        
        # CENTER PANEL - Chart
        center_panel = self._create_center_panel()
        middle_splitter.addWidget(center_panel)
        
        # RIGHT PANEL - Positions & P&L
        right_panel = self._create_right_panel()
        middle_splitter.addWidget(right_panel)
        
        # 크기 비율 설정 (Left:Center:Right = 1:4:1.5)
        middle_splitter.setSizes([200, 800, 250])
        middle_splitter.setStretchFactor(0, 0)  # Left 고정
        middle_splitter.setStretchFactor(1, 1)  # Center 확장
        middle_splitter.setStretchFactor(2, 0)  # Right 고정
        
        main_layout.addWidget(middle_splitter, stretch=1)
        
        # ═══════════════════════════════════════════════════════════
        # 3. BOTTOM PANEL - Log Console
        # ═══════════════════════════════════════════════════════════
        bottom_panel = self._create_bottom_panel()
        main_layout.addWidget(bottom_panel)
        
        self.setLayout(main_layout)

    def _create_panel_frame(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        """
        공통 패널 프레임 생성 헬퍼
        """
        frame = QFrame()
        # [REFAC] 테마 매니저에서 패널 스타일 가져오기
        frame.setStyleSheet(theme.get_stylesheet("panel"))
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # 제목 라벨
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            color: {theme.get_color('text_secondary')}; 
            font-size: 12px; 
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        layout.addWidget(title_label)
        
        return frame, layout

    def _create_control_button(self, text: str, color_key: str, callback=None) -> QPushButton:
        """
        컨트롤 버튼 생성 헬퍼
        """
        btn = QPushButton(text)
        
        # [REFAC] 테마 매니저를 통해 완전히 중앙화된 스타일 적용
        btn.setStyleSheet(theme.get_button_style(color_key))
        
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if callback:
            btn.clicked.connect(callback)
        return btn

    def _create_top_panel(self) -> QFrame:
        """
        TOP PANEL - 컨트롤 버튼 패널
        """
        frame = QFrame()
        frame.setFixedHeight(50)
        # [REFAC] 테마 적용 (반투명 Surface)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.get_color('surface')}; 
                border: 1px solid {theme.get_color('border')};
                border-radius: 8px;
            }}
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(10)
        
        # 로고/타이틀
        logo = QLabel("⚡ Sigma9")
        logo.setStyleSheet(f"""
            color: {theme.get_color('text')}; 
            font-size: 16px; 
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        layout.addWidget(logo)
        
        layout.addStretch(1)
        
        # 컨트롤 버튼들
        # [REFAC] 색상 코드 대신 테마 키 사용
        self.connect_btn = self._create_control_button(
            "🔌 Connect", "primary", self._on_connect
        )
        layout.addWidget(self.connect_btn)
        
        self.start_btn = self._create_control_button(
            "🚀 Start Engine", "success", self._on_start
        )
        layout.addWidget(self.start_btn)
        
        self.stop_btn = self._create_control_button(
            "🔴 Stop", "warning", self._on_stop
        )
        layout.addWidget(self.stop_btn)
        
        # ═══════════════════════════════════════════════════════════════
        # Step 2.5.4: 전략 선택 드롭다운
        # ═══════════════════════════════════════════════════════════════
        layout.addWidget(QLabel("|"))  # 구분자
        
        strategy_label = QLabel("Strategy:")
        strategy_label.setStyleSheet(f"""
            color: {theme.get_color('text_secondary')}; 
            font-size: 11px;
            background: transparent;
            border: none;
        """)
        layout.addWidget(strategy_label)
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.setMinimumWidth(120)
        self.strategy_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {theme.get_color('surface')};
                border: 1px solid {theme.get_color('border')};
                border-radius: 4px;
                color: {theme.get_color('text')};
                padding: 4px 8px;
                font-size: 11px;
            }}
            QComboBox:hover {{
                border: 1px solid {theme.get_color('primary')};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                width: 12px;
                height: 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme.get_color('surface')};
                border: 1px solid {theme.get_color('border')};
                color: {theme.get_color('text')};
                selection-background-color: {theme.get_color('primary')};
            }}
        """)
        self.strategy_combo.currentTextChanged.connect(self._on_strategy_changed)
        layout.addWidget(self.strategy_combo)
        
        # 리로드 버튼
        self.reload_strategy_btn = QPushButton("🔄")
        self.reload_strategy_btn.setToolTip("Reload Strategy (Hot Reload)")
        self.reload_strategy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {theme.get_color('text_secondary')};
                font-size: 14px;
                padding: 4px;
            }}
            QPushButton:hover {{
                color: {theme.get_color('primary')};
            }}
        """)
        self.reload_strategy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reload_strategy_btn.clicked.connect(self._on_reload_strategy)
        layout.addWidget(self.reload_strategy_btn)
        
        layout.addWidget(QLabel("|"))  # 구분자
        
        # Kill Switch는 빨간색으로 강조
        self.kill_btn = self._create_control_button(
            "⚡ KILL SWITCH", "danger", self._on_kill
        )
        self.kill_btn.setStyleSheet(self.kill_btn.styleSheet() + """
            QPushButton {
                padding: 8px 20px;
            }
        """)
        layout.addWidget(self.kill_btn)
        
        # 연결 상태
        self.status_label = QLabel("🔴 Disconnected")
        self.status_label.setStyleSheet(f"""
            color: {theme.get_color('danger')}; 
            font-size: 11px;
            background: transparent;
            border: none;
            padding-left: 10px;
        """)
        layout.addWidget(self.status_label)
        
        # Settings Button
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {theme.get_color('text_secondary')};
                font-size: 16px;
            }}
            QPushButton:hover {{
                color: {theme.get_color('text')};
            }}
        """)
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self._on_settings)
        layout.addWidget(self.settings_btn)

        return frame

    def _create_left_panel(self) -> QFrame:
        """
        LEFT PANEL - Watchlist (감시 종목 리스트)
        """
        frame, layout = self._create_panel_frame("📋 Watchlist")
        frame.setMinimumWidth(180)
        frame.setMaximumWidth(300)
        
        # 종목 리스트
        self.watchlist = QListWidget()
        # [REFAC] 테마 매니저 List 스타일 사용
        styles = theme.get_stylesheet("list")
        # [FIX] 배경을 투명하게 하고 패널 배경을 사용 (Surface on Surface 방지)
        # 만약 두 겹이면 너무 밝아질 수 있으므로, ListWidget 자체는 투명하게 설정
        styles += "QListWidget { background-color: transparent; }"
        self.watchlist.setStyleSheet(styles)
        
        # [NEW] Watchlist 클릭 시 차트 로드
        self.watchlist.itemClicked.connect(self._on_watchlist_clicked)
        
        # 샘플 데이터 (실제로는 DB에서 로드)
        # TODO: 실제 워치리스트 연동 시 Scanner에서 가져오기
        sample_tickers = [
            "AAPL  +2.3%  [85]",
            "TSLA  +1.8%  [78]",
            "NVDA  +3.1%  [92]",
            "AMD   +0.9%  [71]",
            "MSFT  +1.5%  [76]",
        ]
        self.watchlist.addItems(sample_tickers)
        
        layout.addWidget(self.watchlist)
        
        return frame

    def _create_center_panel(self) -> QFrame:
        """
        CENTER PANEL - Chart Area (차트 영역)
        
        [REFAC] PyQtGraph 기반 차트로 전환 (Acrylic 호환)
        """
        frame, layout = self._create_panel_frame("📈 Chart")
        
        # [NEW] PyQtGraph 기반 차트 위젯 (Acrylic 완전 호환)
        self.chart_widget = PyQtGraphChartWidget()
        self.chart_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.Expanding
        )
        
        # 타임프레임 변경 시그널 연결
        self.chart_widget.timeframe_changed.connect(self._on_timeframe_changed)
        
        # [Step 2.7.4] Viewport 변경 시 동적 데이터 로딩 시그널 연결
        self.chart_widget.viewport_data_needed.connect(self._on_viewport_data_needed)
        
        layout.addWidget(self.chart_widget)
        
        # 시작 시 샘플 데이터 로드 (1.5초 후)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1500, self._load_sample_chart_data)
        
        return frame
    
    def _load_sample_chart_data(self):
        """
        Step 2.4.8: 샘플 차트 데이터 로드 (Volume, MA 포함)
        
        차트 위젯이 정상적으로 표시되는지 확인을 위한 테스트 데이터
        """
        import numpy as np
        import time as time_module
        
        # 100개 캔들 생성 (일봉)
        base_time = time_module.time() - 86400 * 100
        candles = []
        volumes = []
        price = 10.0
        
        for i in range(100):
            o = price
            delta = np.random.uniform(-0.3, 0.35)  # 약간 상승 편향
            c = price + delta
            h = max(o, c) + np.random.uniform(0, 0.2)
            l = min(o, c) - np.random.uniform(0, 0.2)
            vol = int(np.random.uniform(100000, 500000))
            is_up = c >= o
            
            timestamp = base_time + i * 86400
            candles.append({
                "time": timestamp,
                "open": round(o, 2),
                "high": round(h, 2),
                "low": round(l, 2),
                "close": round(c, 2),
            })
            volumes.append({
                "time": timestamp,
                "volume": vol,
                "is_up": is_up,
            })
            price = c
        
        # 캔들스틱 설정
        self.chart_widget.set_candlestick_data(candles)
        
        # Volume 설정
        self.chart_widget.set_volume_data(volumes)
        
        # VWAP (간이 계산)
        vwap_data = []
        cumulative = 0
        for i, c in enumerate(candles):
            tp = (c["high"] + c["low"] + c["close"]) / 3
            cumulative = (cumulative * i + tp) / (i + 1) if i > 0 else tp
            vwap_data.append({"time": c["time"], "value": cumulative})
        self.chart_widget.set_vwap_data(vwap_data)
        
        # SMA 20 (간이 계산)
        closes = [c["close"] for c in candles]
        sma_data = []
        for i in range(19, len(candles)):
            sma = sum(closes[i-19:i+1]) / 20
            sma_data.append({"time": candles[i]["time"], "value": sma})
        self.chart_widget.set_ma_data(sma_data, period=20, color='#3b82f6')
        
        # EMA 9 (간이 계산)
        ema = closes[0]
        mult = 2 / 10
        ema_data = []
        for i, c in enumerate(candles):
            ema = (closes[i] - ema) * mult + ema
            if i >= 8:
                ema_data.append({"time": c["time"], "value": ema})
        self.chart_widget.set_ma_data(ema_data, period=9, color='#a855f7')
        
        # 진입/손절/익절 레벨
        current_price = candles[-1]["close"]
        self.chart_widget.set_price_levels(
            entry=current_price,
            stop_loss=current_price * 0.95,  # -5%
            take_profit=current_price * 1.10  # +10%
        )
        
        # Ignition 마커 (80번째 캔들)
        self.chart_widget.add_ignition_marker(
            candles[80]["time"], 
            candles[80]["high"], 
            score=85
        )
        
        self.log("[INFO] Chart loaded with sample data (Volume, MA, SL/TP)")

    def _create_right_panel(self) -> QFrame:
        """
        RIGHT PANEL - Positions & P&L + Oracle (Step 4.2.5)
        
        두 섹션이 세로로 배치됩니다:
        1. Trading (Positions & P&L) - 상단
        2. Oracle (분석 요청) - 하단
        """
        frame = QFrame()
        frame.setStyleSheet(theme.get_stylesheet("panel"))
        frame.setMinimumWidth(200)
        frame.setMaximumWidth(350)
        
        main_layout = QVBoxLayout(frame)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        
        # ═══════════════════════════════════════════════════════════
        # 1. Trading Section (Positions & P&L)
        # ═══════════════════════════════════════════════════════════
        trading_label = QLabel("💰 Positions & P&L")
        trading_label.setStyleSheet(f"""
            color: {theme.get_color('text_secondary')}; 
            font-size: 12px; 
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        main_layout.addWidget(trading_label)
        
        # P&L 요약
        pnl_frame = QFrame()
        c = theme.colors
        pnl_frame.setStyleSheet(f"""
            background-color: {c['surface']};
            border: 1px solid {c['success']};
            border-radius: 8px;
        """)
        pnl_layout = QVBoxLayout(pnl_frame)
        pnl_layout.setContentsMargins(8, 8, 8, 8)
        
        pnl_label = QLabel("Today's P&L")
        pnl_label.setStyleSheet(f"color: {c['text_secondary']}; font-size: 11px; background: transparent; border: none;")
        pnl_layout.addWidget(pnl_label)
        
        self.pnl_value = QLabel("+ $0.00")
        self.pnl_value.setStyleSheet(f"""
            color: {c['success']}; 
            font-size: 20px; 
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        pnl_layout.addWidget(self.pnl_value)
        
        main_layout.addWidget(pnl_frame)
        
        # 포지션 리스트 (축소)
        positions_label = QLabel("Active Positions")
        positions_label.setStyleSheet(f"color: {c['text_secondary']}; font-size: 11px; background: transparent; border: none;")
        main_layout.addWidget(positions_label)
        
        self.positions_list = QListWidget()
        styles = theme.get_stylesheet("list")
        styles += "QListWidget { background-color: transparent; max-height: 80px; }"
        self.positions_list.setStyleSheet(styles)
        self.positions_list.setMaximumHeight(80)
        self.positions_list.addItem("No active positions")
        main_layout.addWidget(self.positions_list)
        
        # ═══════════════════════════════════════════════════════════
        # 2. Oracle Section (Step 4.2.5)
        # ═══════════════════════════════════════════════════════════
        oracle_label = QLabel("🔮 Oracle")
        oracle_label.setStyleSheet(f"""
            color: {theme.get_color('text_secondary')}; 
            font-size: 12px; 
            font-weight: bold;
            background: transparent;
            border: none;
            margin-top: 8px;
        """)
        main_layout.addWidget(oracle_label)
        
        # Oracle 프레임
        oracle_frame = QFrame()
        oracle_frame.setStyleSheet(f"""
            background-color: {c['surface']};
            border: 1px solid {theme.get_color('primary')};
            border-radius: 8px;
        """)
        oracle_layout = QVBoxLayout(oracle_frame)
        oracle_layout.setContentsMargins(8, 8, 8, 8)
        oracle_layout.setSpacing(6)
        
        # 분석 버튼들
        self.oracle_why_btn = QPushButton("❓ Why?")
        self.oracle_why_btn.setToolTip("선택된 종목이 왜 신호를 발생했는지 분석")
        self.oracle_why_btn.setStyleSheet(self._get_oracle_btn_style())
        self.oracle_why_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        oracle_layout.addWidget(self.oracle_why_btn)
        
        self.oracle_fundamental_btn = QPushButton("📊 Fundamental")
        self.oracle_fundamental_btn.setToolTip("종목 펀더멘털 분석")
        self.oracle_fundamental_btn.setStyleSheet(self._get_oracle_btn_style())
        self.oracle_fundamental_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        oracle_layout.addWidget(self.oracle_fundamental_btn)
        
        self.oracle_reflection_btn = QPushButton("💭 Reflection")
        self.oracle_reflection_btn.setToolTip("거래 복기 및 교훈 분석")
        self.oracle_reflection_btn.setStyleSheet(self._get_oracle_btn_style())
        self.oracle_reflection_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        oracle_layout.addWidget(self.oracle_reflection_btn)
        
        # 결과 표시 영역
        self.oracle_result = QTextEdit()
        self.oracle_result.setReadOnly(True)
        self.oracle_result.setPlaceholderText("Select a stock and click a button...")
        self.oracle_result.setStyleSheet(f"""
            QTextEdit {{
                background-color: rgba(0,0,0,0.3);
                border: 1px solid {c['border']};
                border-radius: 4px;
                color: {c['text']};
                font-size: 11px;
            }}
        """)
        self.oracle_result.setMaximumHeight(100)
        oracle_layout.addWidget(self.oracle_result)
        
        main_layout.addWidget(oracle_frame)
        main_layout.addStretch()
        
        return frame
    
    def _get_oracle_btn_style(self) -> str:
        """Oracle 버튼 스타일"""
        c = theme.colors
        return f"""
            QPushButton {{
                background-color: rgba(33, 150, 243, 0.2);
                border: 1px solid {theme.get_color('primary')};
                border-radius: 4px;
                color: {c['text']};
                padding: 6px 12px;
                font-size: 11px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: rgba(33, 150, 243, 0.4);
            }}
        """


    def _create_bottom_panel(self) -> QFrame:
        """
        BOTTOM PANEL - Log Console (로그 콘솔)
        """
        frame, layout = self._create_panel_frame("📝 Log")
        frame.setFixedHeight(140)
        
        # 로그 텍스트 영역
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        c = theme.colors
        self.log_console.setStyleSheet(f"""
            QTextEdit {{
                background-color: {c['surface']};
                border: 1px solid {c['border']};
                border-radius: 6px;
                color: {c['primary']};  /* 콘솔 텍스트는 primary 컬러 사용 */
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
            }}
        """)
        
        # 샘플 로그
        self.log_console.append("[INFO] Sigma9 Dashboard initialized")
        self.log_console.append(f"[INFO] Theme loaded: {theme.mode}")
        self.log_console.append("[INFO] Waiting for connection...")
        
        layout.addWidget(self.log_console)
        
        return frame

    # ═══════════════════════════════════════════════════════════════════════
    # Step 3.4: Control Panel & Backend 이벤트 핸들러
    # ═══════════════════════════════════════════════════════════════════════
    
    def _connect_control_panel_signals(self):
        """
        ControlPanel Signal 연결
        
        Step 3.4: ControlPanel의 버튼 시그널을 핸들러에 연결합니다.
        """
        self.control_panel.connect_clicked.connect(self._on_connect)
        self.control_panel.disconnect_clicked.connect(self._on_disconnect)
        self.control_panel.start_clicked.connect(self._on_start)
        self.control_panel.stop_clicked.connect(self._on_stop)
        self.control_panel.kill_clicked.connect(self._on_kill)
        self.control_panel.strategy_selected.connect(self._on_strategy_changed)
        self.control_panel.strategy_reload_clicked.connect(self._on_reload_strategy)
        self.control_panel.settings_clicked.connect(self._on_settings)
    
    # ═══════════════════════════════════════════════════════════════════════
    # 로컬 서버 프로세스 관리
    # ═══════════════════════════════════════════════════════════════════════
    _local_server_process = None

    def _on_connect(self):
        """
        Connect 버튼 클릭 - 스마트 자동 연결
        
        순서:
        1. AWS 서버 연결 시도
        2. 실패 시 → 로컬 서버 연결 시도
        3. 로컬 서버도 없으면 → 자동으로 로컬 서버 시작
        4. 연결 성공 시 → 엔진 자동 시작
        """
        self.log("[ACTION] 🔌 Smart Connect initiated...")
        self.particle_system.order_created()
        
        import httpx
        import subprocess
        import os
        import time
        
        # 설정에서 서버 정보 가져오기
        settings = load_settings()
        aws_host = settings.get("server", {}).get("aws_host", "")
        local_host = "localhost"
        port = settings.get("server", {}).get("port", 8000)
        
        # ═══════════════════════════════════════════════════════════
        # Step 1: AWS 서버 연결 시도
        # ═══════════════════════════════════════════════════════════
        if aws_host and aws_host != "localhost" and aws_host != "ec2-xxx.amazonaws.com":
            self.log(f"[INFO] 1️⃣ Trying AWS server: {aws_host}:{port}...")
            try:
                resp = httpx.get(f"http://{aws_host}:{port}/health", timeout=5.0)
                if resp.status_code == 200:
                    self.log(f"[INFO] ✅ AWS server found!")
                    self.backend_client.set_server(aws_host, port)
                    if self.backend_client.connect_sync():
                        self._auto_start_engine()
                        return
            except Exception as e:
                self.log(f"[WARN] AWS connection failed: {e}")
        
        # ═══════════════════════════════════════════════════════════
        # Step 2: 로컬 서버 연결 시도
        # ═══════════════════════════════════════════════════════════
        self.log(f"[INFO] 2️⃣ Trying local server: {local_host}:{port}...")
        try:
            resp = httpx.get(f"http://{local_host}:{port}/health", timeout=3.0)
            if resp.status_code == 200:
                self.log(f"[INFO] ✅ Local server found!")
                self.backend_client.set_server(local_host, port)
                if self.backend_client.connect_sync():
                    self._auto_start_engine()
                    return
        except httpx.ConnectError:
            self.log("[WARN] Local server not running")
        except Exception as e:
            self.log(f"[WARN] Local server check failed: {e}")
        
        # ═══════════════════════════════════════════════════════════
        # Step 3: 로컬 서버 자동 시작
        # ═══════════════════════════════════════════════════════════
        self.log("[INFO] 3️⃣ Starting local server automatically...")
        
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        venv_python = os.path.join(project_root, ".venv", "Scripts", "python.exe")
        
        if not os.path.exists(venv_python):
            self.log("[ERROR] ❌ Python not found in .venv")
            return
        
        try:
            # 새 콘솔 창에서 서버 실행
            self._local_server_process = subprocess.Popen(
                [venv_python, "-m", "backend"],
                cwd=project_root,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            self.log(f"[INFO] 🖥️ Local server started (PID: {self._local_server_process.pid})")
            
            # 서버 시작 대기 (최대 10초)
            for i in range(20):
                time.sleep(0.5)
                try:
                    resp = httpx.get(f"http://{local_host}:{port}/health", timeout=2.0)
                    if resp.status_code == 200:
                        self.log("[INFO] ✅ Local server is now ready!")
                        break
                except:
                    pass
                if i % 4 == 0:
                    self.log(f"[INFO] Waiting for server... ({i//2}s)")
            
            # ═══════════════════════════════════════════════════════════
            # Step 4: 연결 및 엔진 시작
            # ═══════════════════════════════════════════════════════════
            self.backend_client.set_server(local_host, port)
            if self.backend_client.connect_sync():
                self._auto_start_engine()
            else:
                self.log("[ERROR] ❌ Failed to connect after starting server")
                
        except Exception as e:
            self.log(f"[ERROR] ❌ Failed to start local server: {e}")
    
    def _auto_start_engine(self):
        """연결 후 자동으로 엔진 시작"""
        self.log("[INFO] 4️⃣ Auto-starting engine...")
        self.backend_client.start_engine_sync()
        
        # Scanner 자동 실행
        current_strategy = self.control_panel.get_selected_strategy()
        if current_strategy:
            self.log(f"[INFO] 5️⃣ Running scanner with strategy: {current_strategy}")
            self._run_scanner_for_strategy(current_strategy)
    
    def _on_disconnect(self):
        """Disconnect 버튼 클릭 (Step 3.4.1)"""
        self.log("[ACTION] Disconnect button clicked")
        self.backend_client.disconnect_sync()

    def _on_start(self):
        """Start Engine 버튼 클릭 (Step 3.4.2)"""
        self.log("[ACTION] Start Engine clicked")
        self.particle_system.order_filled()
        self.backend_client.start_engine_sync()

    def _on_stop(self):
        """Stop 버튼 클릭 (Step 3.4.2)"""
        self.log("[ACTION] Stop clicked")
        self.particle_system.stop_loss()
        self.backend_client.stop_engine_sync()  # [FIX] async → sync

    def _on_kill(self):
        """Kill Switch 버튼 클릭 (Step 3.2.4 연동)"""
        self.log("[EMERGENCY] ⚡ KILL SWITCH ACTIVATED!")
        self.particle_system.stop_loss()
        self.backend_client.kill_switch_sync()  # [FIX] async → sync
    
    def _on_backend_state_changed(self, state: ConnectionState):
        """
        Backend 상태 변경 핸들러
        
        Step 3.4.4: 상태 인디케이터 업데이트
        """
        # 연결 상태 업데이트
        if state == ConnectionState.CONNECTED:
            self.control_panel.update_connection_status(True)
            self.particle_system.order_created()
        elif state == ConnectionState.RUNNING:
            # RUNNING은 파란색으로 별도 표시
            self.control_panel.update_engine_status(True)
            self.particle_system.order_filled()
        elif state == ConnectionState.DISCONNECTED or state == ConnectionState.ERROR:
            self.control_panel.update_connection_status(False)
        elif state == ConnectionState.STOPPING:
            self.control_panel.update_engine_status(False)

    def _on_strategy_changed(self, strategy_name: str):
        """
        전략 드롭다운 변경 이벤트
        
        Step 3.4.7: 전략 변경 시 Scanner 자동 실행
        """
        if not strategy_name:
            return
        self.log(f"[ACTION] Strategy selected: {strategy_name}")
        self._load_selected_strategy(strategy_name)
        
        # Step 3.4.7: Scanner 자동 실행
        if self.backend_client.is_connected:
            self._run_scanner_for_strategy(strategy_name)
    
    def _run_scanner_for_strategy(self, strategy_name: str):
        """
        Step 3.4.7: 전략에 대한 Scanner 실행
        
        BackendClient를 통해 Scanner를 비동기로 실행합니다.
        결과는 watchlist_updated 시그널로 전달됩니다.
        """
        self.log(f"[INFO] Starting scanner for {strategy_name}...")
        self.backend_client.run_scanner(strategy_name)
    
    def _update_watchlist_panel(self, items: list):
        """
        Step 3.4.8: Watchlist 패널 자동 업데이트
        
        Scanner 결과가 도착하면 Watchlist 위젯을 업데이트합니다.
        
        Args:
            items: List[WatchlistItem] - Scanner 결과
        """
        self.watchlist.clear()
        
        if not items:
            self.watchlist.addItem("No stocks found")
            self.log("[INFO] Watchlist updated: 0 stocks")
            return
        
        for item in items:
            if isinstance(item, WatchlistItem):
                ticker = item.ticker
                change_pct = item.change_pct
                score = item.score
            else:
                # dict 형태인 경우
                ticker = item.get("ticker", "UNKNOWN")
                change_pct = item.get("change_pct", 0.0)
                score = item.get("score", 0)
            
            # Ignition Score 조회 (캐시에서)
            ignition_score = self._ignition_cache.get(ticker, 0.0)
            
            # 표시 형식: "AAPL  +2.3%  [85] 🔥72" 또는 "AAPL  +2.3%  [85]  -"
            sign = "+" if change_pct >= 0 else ""
            
            # Ignition 칸럼 항상 표시 (값이 있으면 표시, 없으면 빈칸)
            if ignition_score > 0:
                display_text = f"{ticker:6s} {sign}{change_pct:.1f}%  [{score:.0f}] 🔥{ignition_score:.0f}"
            else:
                display_text = f"{ticker:6s} {sign}{change_pct:.1f}%  [{score:.0f}]  -"
            
            list_item = self.watchlist.addItem(display_text)
            
            # Score ≥ 70 강조 표시 (노란색)
            if ignition_score >= 70:
                idx = self.watchlist.count() - 1
                widget_item = self.watchlist.item(idx)
                if widget_item:
                    widget_item.setBackground(QColor(255, 193, 7, 80))  # 노란색 반투명
        
        self.log(f"[INFO] Watchlist updated: {len(items)} stocks")
        self.particle_system.order_created()  # 시각적 피드백
    
    def _on_ignition_update(self, data: dict):
        """
        Ignition Score 실시간 업데이트 핸들러 (Phase 2)
        
        WebSocket으로 수신된 Ignition Score를 캐시에 저장하고
        해당 종목의 Watchlist 표시를 업데이트합니다.
        
        Args:
            data: {"ticker": str, "score": float, "passed_filter": bool, "reason": str}
        """
        ticker = data.get("ticker", "")
        score = data.get("score", 0.0)
        passed_filter = data.get("passed_filter", True)
        
        if not ticker:
            return
        
        # Ignition 모니터링 활성화 플래그 설정
        self._ignition_monitoring = True
        
        # 캐시 업데이트
        self._ignition_cache[ticker] = score
        
        # Watchlist에서 해당 종목 찾아서 업데이트
        for i in range(self.watchlist.count()):
            item = self.watchlist.item(i)
            if item and item.text().split()[0] == ticker:
                # 기존 텍스트 파싱 후 Ignition Score 업데이트
                text = item.text()
                parts = text.split()
                if len(parts) >= 3:
                    # 새 텍스트 생성 (🔥 이모지 사용)
                    base_text = " ".join(parts[:3])  # "AAPL +2.3% [85]"
                    new_text = f"{base_text} 🔥{score:.0f}"
                    item.setText(new_text)
                    
                    # 70점 이상 강조 + 사운드 + 파티클
                    if score >= 70:
                        item.setBackground(QColor(255, 193, 7, 80))
                        if passed_filter:
                            # 파티클 이펙트
                            self.particle_system.take_profit()
                            # 사운드 알림
                            self._play_ignition_sound()
                            self.log(f"[IGNITION] 🔥 {ticker} Score={score:.0f} - READY!")
                    else:
                        item.setBackground(QColor(0, 0, 0, 0))  # 투명
                break
    
    def _play_ignition_sound(self):
        """Ignition Alert 사운드 재생"""
        try:
            import winsound
            # 시스템 알림음 (비프음)
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass  # 사운드 재생 실패 시 무시

    def _on_timeframe_changed(self, timeframe: str):
        """
        차트 타임프레임 변경 핸들러 (Step 2.7)
        
        타임프레임 변경 시 해당 타임프레임의 데이터를 로드합니다.
        - 1D: DB에서 Daily bar 로드
        - 1m/5m/15m/1h: Massive API에서 Intraday bar 로드
        """
        self.log(f"[INFO] Timeframe changed to: {timeframe}")
        
        # 현재 타임프레임 저장
        self._current_timeframe = timeframe
        
        # 현재 선택된 종목 가져오기
        current_item = self.watchlist.currentItem()
        if not current_item:
            self.log("[WARN] No stock selected")
            return
        
        ticker = current_item.text().split()[0].strip()
        self.log(f"[INFO] Reloading {ticker} data for {timeframe}...")
        
        # 비동기 데이터 로드
        import threading
        from PyQt6.QtCore import QTimer
        
        def load_in_thread():
            try:
                from frontend.services.chart_data_service import ChartDataService
                import asyncio
                
                async def fetch():
                    service = ChartDataService()
                    # timeframe 전달: "1D", "5m", "1h" 등
                    days = 100 if timeframe == "1D" else 5  # Intraday는 5일
                    data = await service.get_chart_data(ticker, timeframe=timeframe, days=days)
                    await service.close()
                    return data
                
                data = asyncio.run(fetch())
                self._pending_chart_data = (ticker, data)
                QTimer.singleShot(0, self._apply_pending_chart_data)
                
            except Exception as e:
                self.log(f"[ERROR] Failed to load {ticker} ({timeframe}): {e}")
        
        thread = threading.Thread(target=load_in_thread, daemon=True)
        thread.start()

    def _on_watchlist_clicked(self, item):
        """
        Watchlist 종목 클릭 시 차트 데이터 로드
        
        워치리스트 아이템 형식: "AAPL  +2.3%  [85]"
        → 첫 번째 단어(티커)를 추출하여 DB에서 데이터 조회
        """
        # 티커 추출 (첫 번째 단어)
        text = item.text()
        ticker = text.split()[0].strip()
        
        self.log(f"[INFO] Loading chart for {ticker}...")
        
        # 비동기 데이터 로드 (별도 스레드에서 실행)
        import threading
        from PyQt6.QtCore import QTimer
        
        def load_in_thread():
            try:
                from frontend.services.chart_data_service import get_chart_data_sync
                data = get_chart_data_sync(ticker, days=100)
                
                # 결과를 인스턴스 변수에 저장 후 메인 스레드에서 업데이트
                self._pending_chart_data = (ticker, data)
                QTimer.singleShot(0, self._apply_pending_chart_data)
            except Exception as e:
                self.log(f"[ERROR] Failed to load {ticker}: {e}")
        
        thread = threading.Thread(target=load_in_thread, daemon=True)
        thread.start()
    
    def _apply_pending_chart_data(self):
        """
        대기 중인 차트 데이터 적용 (메인 스레드에서 호출)
        
        _on_watchlist_clicked에서 별도 스레드로 데이터를 로드한 후
        _pending_chart_data에 저장하고, 이 메서드가 메인 스레드에서 차트 업데이트
        """
        if not hasattr(self, '_pending_chart_data'):
            return
        
        ticker, data = self._pending_chart_data
        delattr(self, '_pending_chart_data')
        
        if not data.get("candles"):
            self.log(f"[WARN] No data available for {ticker}")
            return
        
        # 차트 초기화
        self.chart_widget.clear()
        
        # 캔들스틱
        self.chart_widget.set_candlestick_data(data["candles"])
        
        # Volume
        if data.get("volume"):
            self.chart_widget.set_volume_data(data["volume"])
        
        # VWAP
        if data.get("vwap"):
            self.chart_widget.set_vwap_data(data["vwap"])
        
        # SMA 20
        if data.get("sma_20"):
            self.chart_widget.set_ma_data(data["sma_20"], period=20, color='#3b82f6')
        
        # EMA 9
        if data.get("ema_9"):
            self.chart_widget.set_ma_data(data["ema_9"], period=9, color='#a855f7')
        
        self.log(f"[INFO] Chart updated for {ticker} ({len(data['candles'])} bars)")

    def log(self, message: str):
        """로그 콘솔에 메시지 추가 (자동 스크롤)"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_console.append(f"[{timestamp}] {message}")
        # 자동 스크롤 (맨 아래로)
        scrollbar = self.log_console.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    # ═══════════════════════════════════════════════════════════════════════
    # Step 2.5: Strategy Loader 관련 메서드
    # ═══════════════════════════════════════════════════════════════════════
    
    def _init_strategy_loader(self):
        """
        StrategyLoader 초기화 및 전략 목록 로드
        
        Step 2.5: 전략 플러그인 시스템 GUI 연동
        """
        import sys
        from pathlib import Path
        
        # backend 경로를 sys.path에 추가
        backend_path = Path(__file__).parent.parent.parent / "backend"
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))
        
        try:
            from core.strategy_loader import StrategyLoader
            self.strategy_loader = StrategyLoader()
            
            # 사용 가능한 전략 목록 로드
            strategies = self.strategy_loader.discover_strategies()
            
            # Step 3.4: ControlPanel 드롭다운에 전략 목록 추가
            self.control_panel.set_strategies(strategies)
            
            self.log(f"[INFO] Found {len(strategies)} strategies: {strategies}")
            
            # 첫 번째 전략 자동 로드
            if strategies:
                self._load_selected_strategy(strategies[0])

        except Exception as e:
            self.log(f"[ERROR] Failed to init StrategyLoader: {e}")
            self.strategy_loader = None
    
    def _load_selected_strategy(self, strategy_name: str):
        """선택된 전략 로드"""
        if not self.strategy_loader:
            return
        
        try:
            strategy = self.strategy_loader.load_strategy(strategy_name)
            self.current_strategy = strategy
            self.log(f"[INFO] Loaded: {strategy.name} v{strategy.version}")
        except Exception as e:
            self.log(f"[ERROR] Failed to load {strategy_name}: {e}")
    
    def _on_strategy_changed(self, strategy_name: str):
        """전략 드롭다운 변경 이벤트"""
        if not strategy_name:
            return
        self.log(f"[ACTION] Strategy selected: {strategy_name}")
        self._load_selected_strategy(strategy_name)
    
    def _on_reload_strategy(self):
        """전략 리로드 버튼 클릭"""
        if not self.strategy_loader:
            self.log("[ERROR] StrategyLoader not initialized")
            return
        
        strategy_name = self.strategy_combo.currentText()
        if not strategy_name:
            self.log("[WARNING] No strategy selected")
            return
        
        try:
            strategy = self.strategy_loader.reload_strategy(strategy_name)
            self.current_strategy = strategy
            self.log(f"[INFO] Hot-reloaded: {strategy.name} v{strategy.version}")
            self.particle_system.order_created()  # 리로드 성공 시각 피드백
        except Exception as e:
            self.log(f"[ERROR] Failed to reload {strategy_name}: {e}")

    def _on_settings(self):
        """설정 버튼 클릭"""
        print("[DEBUG] Dashboard: _on_settings called!")
        self.log("[ACTION] Settings button clicked")
        current_settings = load_settings()
        try:
            # [FIX] Parent를 None으로 설정하여 Top-level 윈도우로 띄움 (부모의 효과 간섭 방지)
            dlg = SettingsDialog(None, current_settings)
            dlg.sig_settings_changed.connect(self._on_settings_preview)
            
            print("[DEBUG] Executing Settings Dialog...")
            if dlg.exec():
                # Save Setting
                # Note: For complex nested settings, better to use recursive update or specialized manager
                # Here we manually update what we support
                s = current_settings
                if 'gui' not in s: s['gui'] = {}
            
            s['gui']['opacity'] = dlg.opacity_slider.value() / 100.0
            s['gui']['acrylic_map_alpha'] = dlg.alpha_slider.value()
            s['gui']['particle_alpha'] = dlg.particle_slider.value() / 100.0
            s['gui']['tint_color'] = dlg.initial_tint_color
            s['gui']['theme'] = 'light' if dlg.radio_light.isChecked() else 'dark'
            s['gui']['background_effect'] = dlg.effect_combo.currentText().lower()
                
            if save_settings(s):
                self.log("[INFO] Settings saved.")
                theme.reload()
                
                # Apply changes safely
                self.tint_r = theme.tint_r
                self.tint_g = theme.tint_g
                self.tint_b = theme.tint_b
                self.alpha = theme.acrylic_map_alpha
                self.particle_system.global_alpha = theme.particle_alpha
                self.particle_system.set_background_effect(theme.background_effect)
                
                self.setWindowOpacity(theme.opacity)
                self.update_acrylic_color(self._get_color_string())
                
                # Theme reload notice
                if theme.mode != s['gui']['theme']:
                     self.log("[INFO] Theme changed. Restart recommended for full effect.")

            else:
                # Revert preview
                print("[DEBUG] Dialog Cancelled")
                self.setWindowOpacity(theme.opacity)
                self.alpha = theme.acrylic_map_alpha
                self.particle_system.global_alpha = theme.particle_alpha # [NEW] Revert
                
        except Exception as e:
            print(f"[ERROR] Settings Dialog Crashed: {e}")
            self.log(f"[ERROR] Settings Dialog Crashed: {e}")
            import traceback
            traceback.print_exc()
            self.particle_system.set_background_effect(theme.background_effect) # [NEW] Revert
            self.update_acrylic_color(self._get_color_string())

    def _on_settings_preview(self, changes: dict):
        """설정 변경 미리보기"""
        if "opacity" in changes:
            self.setWindowOpacity(changes["opacity"])
        
        # Color & Alpha update handled together usually
        update_color = False
        if "acrylic_map_alpha" in changes:
            self.alpha = int(changes["acrylic_map_alpha"])
            update_color = True
        
        if "tint_color" in changes:
            c = changes["tint_color"].lstrip("#")
            self.tint_r = int(c[0:2], 16)
            self.tint_g = int(c[2:4], 16)
            self.tint_b = int(c[4:6], 16)
            update_color = True
            
        if update_color:
            self.update_acrylic_color(self._get_color_string())
            
        if "particle_alpha" in changes:
            self.particle_system.global_alpha = changes["particle_alpha"]

        if "background_effect" in changes:
            self.particle_system.set_background_effect(changes["background_effect"])
    
    # ═══════════════════════════════════════════════════════════════════════
    # Step 2.7.4: Dynamic Data Loading on Pan/Zoom
    # ═══════════════════════════════════════════════════════════════════════
    
    _viewport_loading = False  # 중복 로딩 방지 플래그
    
    def _on_viewport_data_needed(self, start_idx: int, end_idx: int):
        """
        차트 Pan/Zoom 시 추가 데이터 필요 핸들러
        
        왼쪽(과거) 방향으로 스크롤하여 현재 로드된 데이터 범위를 벗어났을 때 호출됩니다.
        
        Data Flow:
            1. L2(SQLite) 먼저 조회
            2. L2 Miss → L3(API) 호출
            3. API 데이터 → L2 저장
            4. chart_widget에 prepend
        """
        # 중복 요청 방지 / 차트 업데이트 중 시그널 무시
        if self._viewport_loading or getattr(self, '_updating_chart', False):
            return
        
        # 1D(Daily)는 이미 전체 로드됨, Intraday만 동적 로딩
        if not hasattr(self, '_current_timeframe') or self._current_timeframe == "1D":
            return
        
        # 현재 선택된 종목 확인
        current_item = self.watchlist.currentItem()
        if not current_item:
            return
        
        ticker = current_item.text().split()[0].strip()
        timeframe = self._current_timeframe
        
        # 차트의 현재 첫 번째 타임스탬프 가져오기
        before_timestamp = None
        if hasattr(self.chart_widget, '_candle_data') and self.chart_widget._candle_data:
            first_time = self.chart_widget._candle_data[0].get("time", 0)
            if first_time > 0:
                before_timestamp = int(first_time * 1000)  # seconds → ms
        
        self.log(f"[INFO] 📊 Loading more data: {ticker} {timeframe} (idx={start_idx})")
        self._viewport_loading = True
        
        # 비동기 데이터 로드 (별도 스레드)
        import threading
        from PyQt6.QtCore import QTimer
        
        def load_in_thread():
            try:
                self._fetch_historical_bars(ticker, timeframe, abs(start_idx) + 100, before_timestamp)
            finally:
                self._viewport_loading = False
        
        thread = threading.Thread(target=load_in_thread, daemon=True)
        thread.start()
    
    def _fetch_historical_bars(self, ticker: str, timeframe: str, extra_bars: int, before_timestamp: int = None):
        """
        과거 Bar 데이터 조회 (L2 → L3)
        
        Args:
            ticker: 종목 심볼
            timeframe: 타임프레임 (1m, 5m, 15m, 1h)
            extra_bars: 추가로 필요한 바 수
            before_timestamp: 이 시점 이전 데이터를 가져옴 (ms, None이면 현재 시간 기준)
        """
        import asyncio
        from datetime import datetime, timedelta
        from PyQt6.QtCore import QTimer
        
        async def fetch_async():
            from backend.data.database import MarketDB
            from backend.data.polygon_client import PolygonClient
            from loguru import logger
            
            # 타임프레임 → multiplier 변환
            tf_map = {"1m": 1, "5m": 5, "15m": 15, "1h": 60}
            multiplier = tf_map.get(timeframe.lower(), 5)
            
            # ═══════════════════════════════════════════════════════════
            # 날짜 범위 계산 (차트의 첫 타임스탬프 기준으로 더 과거)
            # ═══════════════════════════════════════════════════════════
            if before_timestamp:
                # 차트의 첫 타임스탬프 이전 데이터를 가져옴
                ref_time = datetime.fromtimestamp(before_timestamp / 1000)
            else:
                # 기준 없으면 현재 시간
                ref_time = datetime.now()
            
            days_back = max(5, extra_bars // (78 // multiplier) + 2)  # 하루 78개 1분봉 기준
            from_date = (ref_time - timedelta(days=days_back)).strftime("%Y-%m-%d")
            to_date = (ref_time - timedelta(days=1)).strftime("%Y-%m-%d")  # ref_time 하루 전까지
            
            # 타임스탬프 범위 (ms)
            start_ts = int((ref_time - timedelta(days=days_back)).timestamp() * 1000)
            end_ts = int((ref_time - timedelta(days=1)).timestamp() * 1000)
            
            logger.debug(f"📆 Date range: {from_date} ~ {to_date} (before {ref_time.strftime('%Y-%m-%d %H:%M')})")
            
            # ═══════════════════════════════════════════════════════════
            # L2: SQLite 조회
            # ═══════════════════════════════════════════════════════════
            db = MarketDB()
            await db.initialize()
            
            db_bars = await db.get_intraday_bars(
                ticker=ticker,
                timeframe=timeframe.lower(),
                start_timestamp=start_ts,
                end_timestamp=end_ts
            )
            
            if db_bars and len(db_bars) >= extra_bars * 0.8:
                # L2 Hit - DB에서 충분한 데이터 발견
                logger.info(f"📥 L2 Hit: {len(db_bars)} bars from SQLite")
                return [bar.to_dict() for bar in db_bars]
            
            # ═══════════════════════════════════════════════════════════
            # L3: API 호출 (청크 기반 순차 요청)
            # ═══════════════════════════════════════════════════════════
            import os
            from dotenv import load_dotenv
            load_dotenv()
            
            api_key = os.getenv("MASSIVE_API_KEY", "")
            if not api_key:
                logger.error("MASSIVE_API_KEY not set in environment")
                return []
            
            MAX_BARS_PER_CHUNK = 500
            all_api_bars = []
            current_end_ts = end_ts  # 시작: before_timestamp 기준
            chunk_count = 0
            max_chunks = 10  # 무한 루프 방지
            
            client = PolygonClient(api_key=api_key)
            
            try:
                while len(all_api_bars) < extra_bars and chunk_count < max_chunks:
                    chunk_count += 1
                    
                    # 타임스탬프 → 날짜 변환
                    chunk_end_date = datetime.fromtimestamp(current_end_ts / 1000).strftime("%Y-%m-%d")
                    
                    # 청크 날짜 범위 계산 (타임프레임별 바 개수 추정)
                    # 1분봉: 하루 390개, 5분봉: 78개, 15분봉: 26개, 1시간봉: 6.5개
                    bars_per_day = {1: 390, 5: 78, 15: 26, 60: 7}.get(multiplier, 78)
                    chunk_days = max(3, MAX_BARS_PER_CHUNK // bars_per_day + 1)
                    chunk_start_date = (datetime.fromtimestamp(current_end_ts / 1000) - timedelta(days=chunk_days)).strftime("%Y-%m-%d")
                    
                    logger.info(f"📡 L3 Chunk {chunk_count}: {chunk_start_date} ~ {chunk_end_date}")
                    
                    chunk_bars = await client.fetch_intraday_bars(
                        ticker=ticker,
                        multiplier=multiplier,
                        from_date=chunk_start_date,
                        to_date=chunk_end_date,
                        limit=MAX_BARS_PER_CHUNK
                    )
                    
                    if not chunk_bars:
                        logger.info(f"📭 No more data available (chunk {chunk_count})")
                        break
                    
                    # 청크 데이터를 앞에 추가 (과거 → 현재 순서 유지)
                    all_api_bars = chunk_bars + all_api_bars
                    logger.info(f"📦 Chunk {chunk_count}: {len(chunk_bars)} bars (total: {len(all_api_bars)})")
                    
                    # 다음 청크의 끝점 = 이 청크의 첫 번째 타임스탬프
                    current_end_ts = chunk_bars[0]["timestamp"]
            finally:
                await client.close()
            
            if not all_api_bars:
                logger.warning(f"No historical data from API")
                return []
            
            api_bars = all_api_bars
            
            # ═══════════════════════════════════════════════════════════
            # L2에 저장 (완성된 Bar만)
            # ═══════════════════════════════════════════════════════════
            bars_to_save = []
            for bar in api_bars:
                bars_to_save.append({
                    "ticker": ticker,
                    "timeframe": timeframe.lower(),
                    "timestamp": bar["timestamp"],
                    "open": bar["open"],
                    "high": bar["high"],
                    "low": bar["low"],
                    "close": bar["close"],
                    "volume": bar["volume"],
                    "vwap": bar.get("vwap", 0),
                })
            
            if bars_to_save:
                saved_count = await db.upsert_intraday_bulk(bars_to_save)
                logger.info(f"💾 {saved_count} bars saved to L2 (SQLite)")
            
            return api_bars
        
        try:
            bars = asyncio.run(fetch_async())
            
            if bars:
                # 차트에 적용할 데이터 준비
                self._pending_prepend_data = bars
                # Worker thread에서 main thread로 안전하게 호출
                from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
                QMetaObject.invokeMethod(
                    self, "_apply_prepend_data",
                    Qt.ConnectionType.QueuedConnection
                )
                
        except Exception as e:
            self.log(f"[ERROR] Historical data fetch failed: {e}")
    
    from PyQt6.QtCore import pyqtSlot
    @pyqtSlot()
    def _apply_prepend_data(self):
        """과거 데이터를 차트에 prepend (메인 스레드)"""
        if not hasattr(self, '_pending_prepend_data') or not self._pending_prepend_data:
            self.log("[DEBUG] No pending prepend data")
            return
        
        bars = self._pending_prepend_data
        self._pending_prepend_data = None
        
        self.log(f"[DEBUG] _apply_prepend_data called with {len(bars)} bars")
        
        # 기존 데이터와 병합
        candle_data = []
        volume_data = []
        
        for bar in bars:
            # timestamp(ms) 또는 time(sec) 둘 다 지원
            ts = bar.get("time") or (bar.get("timestamp", 0) / 1000)
            candle_data.append({
                "time": ts,
                "open": bar["open"],
                "high": bar["high"],
                "low": bar["low"],
                "close": bar["close"],
            })
            volume_data.append({
                "time": ts,
                "volume": bar["volume"],
                "is_up": bar["close"] >= bar["open"],
            })
        
        # 기존 데이터 앞에 추가 (prepend)
        if hasattr(self.chart_widget, '_candle_data') and self.chart_widget._candle_data:
            first_existing_time = self.chart_widget._candle_data[0].get("time", 0)
            self.log(f"[DEBUG] First existing time: {first_existing_time}, new data range: {candle_data[0]['time']} ~ {candle_data[-1]['time']}")
            
            # 중복 제거: 기존 첫 타임스탬프보다 작은 것만 추가
            new_candles = [c for c in candle_data if c["time"] < first_existing_time]
            new_volumes = [v for v in volume_data if v["time"] < first_existing_time]
            
            self.log(f"[DEBUG] New candles to prepend: {len(new_candles)}")
            
            if new_candles:
                prepend_count = len(new_candles)
                combined_candles = new_candles + self.chart_widget._candle_data
                combined_volumes = new_volumes + self.chart_widget._volume_data
                
                # 현재 뷰포트 범위 저장
                vb = self.chart_widget.price_plot.getViewBox()
                current_x_range = vb.viewRange()[0]
                
                # 차트 업데이트 (viewport 시그널 차단)
                self._updating_chart = True
                try:
                    self.chart_widget.set_candlestick_data(combined_candles)
                    self.chart_widget.set_volume_data(combined_volumes)
                    
                    # 뷰포트 X 범위를 prepend된 수만큼 이동 (기존 위치 유지)
                    new_x_min = current_x_range[0] + prepend_count
                    new_x_max = current_x_range[1] + prepend_count
                    vb.setXRange(new_x_min, new_x_max, padding=0)
                    
                    # _last_requested_start도 리셋 (새 인덱스 체계)
                    if hasattr(self.chart_widget, '_last_requested_start'):
                        self.chart_widget._last_requested_start = 0
                finally:
                    self._updating_chart = False
                
                self.log(f"[INFO] ✅ {prepend_count} bars prepended, viewport shifted")
            else:
                self.log(f"[INFO] No new data to prepend (already loaded or same timerange)")
        else:
            # 기존 데이터 없으면 그냥 설정
            self._updating_chart = True
            try:
                self.chart_widget.set_candlestick_data(candle_data)
                self.chart_widget.set_volume_data(volume_data)
            finally:
                self._updating_chart = False
            self.log(f"[INFO] ✅ {len(candle_data)} bars loaded (no existing data)")



# ═══════════════════════════════════════════════════════════════════════════
# 직접 실행 시 테스트
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    window = Sigma9Dashboard()
    window.show()
    sys.exit(app.exec())
