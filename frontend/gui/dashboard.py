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
from datetime import datetime

# 고DPI 스케일링 문제 해결을 위한 환경변수
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

try:
    from PyQt6.QtGui import QColor
    from PyQt6.QtWidgets import (
        QApplication,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QFrame,
        QPushButton,
        QSplitter,
        QTextEdit,
        QListWidget,
        QSizePolicy,
        QComboBox,
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSlot
except ModuleNotFoundError:
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import (
        QApplication,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QFrame,
        QPushButton,
        QSplitter,
        QComboBox,
    )
    from PySide6.QtCore import Qt, QTimer

from .custom_window import CustomWindow
from .particle_effects import ParticleSystem
from .theme import theme  # [REFAC] 테마 매니저 임포트
from .settings_dialog import SettingsDialog

# from .chart_widget import ChartWidget  # Step 2.4.7: 차트 위젯 (Backup) - REMOVED due to missing dependency
# [REFAC Phase 4] PyQtGraphChartWidget 제거됨 → ChartPanel 내부에서 import
from .control_panel import (
    ControlPanel,
)  # [NEW] Step 3.4
from .panels.log_panel import LogPanel  # [REFAC Phase 2] 로그 패널 분리
from .panels.watchlist_panel import (
    WatchlistPanel,
)  # [REFAC Phase 2] 워치리스트 패널 분리
from .panels.chart_panel import ChartPanel  # [REFAC Phase 4] 차트 패널 분리
from .panels.position_panel import PositionPanel  # [REFAC Phase 4] 포지션 패널 분리
from .panels.oracle_panel import OraclePanel  # [REFAC Phase 4] Oracle 패널 분리
from ..config.loader import load_settings, save_settings
from ..services.backend_client import (
    BackendClient,
    ConnectionState,
    WatchlistItem,
)  # [NEW] Step 3.4

# [REFAC Phase 4] Tier2Item, NumericTableWidgetItem → 정식 위치에서 import
from .panels.tier2_panel import Tier2Item, NumericTableWidgetItem


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
            use_mica="false",
            theme=theme.mode,  # [REFAC] 설정된 테마 모드 사용
            color=self._get_color_string(),
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
        self.particle_system.global_alpha = (
            theme.particle_alpha
        )  # [NEW] 초기 투명도 적용
        self.particle_system.set_background_effect(
            theme.background_effect
        )  # [NEW] 초기 배경 이펙트 적용
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

        # Phase 4.A.0: 실시간 바 업데이트 (차트용)
        if hasattr(self.backend_client, "bar_received"):
            self.backend_client.bar_received.connect(self._on_bar_received)

        # Phase 4.A.0.b: 실시간 틱 업데이트 (Tier 2 가격 표시용)
        if hasattr(self.backend_client, "tick_received"):
            self.backend_client.tick_received.connect(self._on_tick_received)

        # [08-001] Heartbeat 업데이트 (TimeDisplayWidget용)
        if hasattr(self.backend_client, "heartbeat_received"):
            self.backend_client.heartbeat_received.connect(self.on_heartbeat_received)

        # Ignition Score 캐시 초기화 (ticker -> score)
        self._ignition_cache: dict = {}

        # 실시간 가격 캐시 (ticker -> price)
        self._price_cache: dict = {}

        # Phase 4.A.0.d: 틱 기반 차트 업데이트용
        self._current_chart_ticker: str = None  # 현재 차트에 표시 중인 종목
        self._pending_tick: dict = None  # 스로틀링 대기 중인 틱
        self._tick_throttle_timer = QTimer()
        self._tick_throttle_timer.setSingleShot(True)
        self._tick_throttle_timer.setInterval(300)  # 300ms 스로틀링
        self._tick_throttle_timer.timeout.connect(self._apply_tick_to_chart)

    def _auto_connect_backend(self):
        """
        Step 3.4.6: GUI 시작 시 Backend 자동 연결 (Non-blocking)

        500ms 후에 호출되어 Backend에 자동으로 연결을 시도합니다.
        연결 성공 시 현재 선택된 전략으로 Scanner를 자동 실행합니다.

        [BUGFIX] GUI freeze 방지: 백그라운드 스레드에서 연결 시도
        """
        self.log("[INFO] Auto-connecting to backend...")

        # [BUGFIX] Non-blocking 연결: 별도 스레드에서 실행
        import threading

        def connect_in_background():
            try:
                if self.backend_client.connect_sync():
                    # 연결 성공 시 Scanner 자동 실행 (GUI 스레드에서)
                    from PyQt6.QtCore import QTimer

                    def run_scanner():
                        current_strategy = self.control_panel.get_selected_strategy()
                        if current_strategy:
                            self._run_scanner_for_strategy(current_strategy)

                    QTimer.singleShot(0, run_scanner)
            except Exception:
                from PyQt6.QtCore import QTimer

                QTimer.singleShot(
                    0, lambda: self.log(f"[WARN] Auto-connect failed: {e}")
                )

        thread = threading.Thread(target=connect_in_background, daemon=True)
        thread.start()

    def resizeEvent(self, event):
        """윈도우 크기 변경 시 파티클 시스템 크기도 조절"""
        super().resizeEvent(event)
        if hasattr(self, "particle_system"):
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
            QSplitter::handle {{ background: {theme.get_color("border")}; }}
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
            color: {theme.get_color("text_secondary")}; 
            font-size: 12px; 
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        layout.addWidget(title_label)

        return frame, layout

    def _create_control_button(
        self, text: str, color_key: str, callback=None
    ) -> QPushButton:
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
                background-color: {theme.get_color("surface")}; 
                border: 1px solid {theme.get_color("border")};
                border-radius: 8px;
            }}
        """)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(10)

        # 로고/타이틀
        logo = QLabel("⚡ Sigma9")
        logo.setStyleSheet(f"""
            color: {theme.get_color("text")}; 
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

        self.stop_btn = self._create_control_button("🔴 Stop", "warning", self._on_stop)
        layout.addWidget(self.stop_btn)

        # ═══════════════════════════════════════════════════════════════
        # Step 2.5.4: 전략 선택 드롭다운
        # ═══════════════════════════════════════════════════════════════
        layout.addWidget(QLabel("|"))  # 구분자

        strategy_label = QLabel("Strategy:")
        strategy_label.setStyleSheet(f"""
            color: {theme.get_color("text_secondary")}; 
            font-size: 11px;
            background: transparent;
            border: none;
        """)
        layout.addWidget(strategy_label)

        self.strategy_combo = QComboBox()
        self.strategy_combo.setMinimumWidth(120)
        self.strategy_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {theme.get_color("surface")};
                border: 1px solid {theme.get_color("border")};
                border-radius: 4px;
                color: {theme.get_color("text")};
                padding: 4px 8px;
                font-size: 11px;
            }}
            QComboBox:hover {{
                border: 1px solid {theme.get_color("primary")};
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
                background-color: {theme.get_color("surface")};
                border: 1px solid {theme.get_color("border")};
                color: {theme.get_color("text")};
                selection-background-color: {theme.get_color("primary")};
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
                color: {theme.get_color("text_secondary")};
                font-size: 14px;
                padding: 4px;
            }}
            QPushButton:hover {{
                color: {theme.get_color("primary")};
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
        self.kill_btn.setStyleSheet(
            self.kill_btn.styleSheet()
            + """
            QPushButton {
                padding: 8px 20px;
            }
        """
        )
        layout.addWidget(self.kill_btn)

        # 연결 상태
        self.status_label = QLabel("🔴 Disconnected")
        self.status_label.setStyleSheet(f"""
            color: {theme.get_color("danger")}; 
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
                color: {theme.get_color("text_secondary")};
                font-size: 16px;
            }}
            QPushButton:hover {{
                color: {theme.get_color("text")};
            }}
        """)
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self._on_settings)
        layout.addWidget(self.settings_btn)

        return frame

    def _create_left_panel(self) -> QFrame:
        """
        LEFT PANEL - Tier 2 Hot Zone + Tier 1 Watchlist

        [REFAC Phase 2] WatchlistPanel 모듈 사용으로 교체
        약 250줄 → 40줄로 감소

        [Step 4.A.2] 레이아웃:
        ┌─────────────────┐
        │  🔥 Hot Zone    │  ← Tier 2 테이블 (상단, 고정 높이 150px)
        │  [Tier 2 Table] │
        ├─────────────────┤
        │  📋 Watchlist   │  ← Tier 1 테이블 (하단, 확장)
        │  [Tier 1 Table] │
        └─────────────────┘
        """
        from PyQt6.QtCore import QTimer

        # WatchlistPanel 생성 (panels/watchlist_panel.py)
        self._watchlist_panel = WatchlistPanel(
            theme=theme, on_save_column_widths=self._save_column_widths
        )

        # ═══════════════════════════════════════════════════════════════════
        # 호환성을 위한 속성 포워딩 (기존 코드가 self.xxx로 접근)
        # ═══════════════════════════════════════════════════════════════════

        # Tier 2 관련 속성
        self._tier2_cache: dict[str, Tier2Item] = {}  # 캐시는 dashboard에서 관리
        self.tier2_table = self._watchlist_panel.tier2_table

        # Tier 1 Watchlist 관련 속성
        self.watchlist_model = self._watchlist_panel.watchlist_model
        self.watchlist_proxy = self._watchlist_panel.watchlist_proxy
        self.watchlist_table = self._watchlist_panel.watchlist_table

        # Score V3 UI 속성
        self._score_v2_updated_label = self._watchlist_panel._score_updated_label
        self._refresh_score_v2_btn = self._watchlist_panel._refresh_score_btn

        # ═══════════════════════════════════════════════════════════════════
        # 시그널 연결
        # ═══════════════════════════════════════════════════════════════════

        # Tier 2 클릭 시 차트 로드
        self._watchlist_panel.tier2_row_clicked.connect(self._on_tier2_table_clicked)

        # Tier 1 Watchlist 클릭 시 차트 로드
        self._watchlist_panel.tier1_row_clicked.connect(
            self._on_watchlist_table_clicked
        )

        # Score V3 Refresh 버튼 클릭
        self._watchlist_panel.refresh_score_clicked.connect(self._on_refresh_score_v2)

        # Watchlist 초기화
        self._add_watchlist_sample_data()

        # [Step 4.A.1.3] 1분 자동 갱신 타이머
        self._watchlist_refresh_timer = QTimer()
        self._watchlist_refresh_timer.timeout.connect(self._refresh_watchlist)
        self._watchlist_refresh_timer.start(60_000)  # 60초

        return self._watchlist_panel

    def _on_tier2_table_clicked(self, row: int, column: int):
        """Tier 2 테이블 클릭 핸들러"""
        ticker_item = self.tier2_table.item(row, 0)
        if ticker_item:
            ticker = ticker_item.text()
            self.log(f"[ACTION] Hot Zone selected: {ticker}")
            self._load_chart_for_ticker(ticker)

    def _on_watchlist_table_clicked(self, proxy_index):
        """
        [Issue 01-004 Phase 4] Tier 1 Watchlist 테이블 클릭 핸들러

        ProxyModel 인덱스를 SourceModel 인덱스로 변환하여 ticker 조회
        """
        # Proxy 인덱스 → Source 인덱스 변환
        source_index = self.watchlist_proxy.mapToSource(proxy_index)
        ticker_index = self.watchlist_model.index(source_index.row(), 0)
        ticker = self.watchlist_model.data(ticker_index)
        if ticker:
            self.log(f"[ACTION] Watchlist selected: {ticker}")
            self._load_chart_for_ticker(ticker)

    def _load_chart_for_ticker(self, ticker: str):
        """
        특정 종목의 차트 데이터 로드 (공통 메서드)

        Tier 1, Tier 2 모두에서 사용됩니다.
        """
        self.log(f"[INFO] Loading chart for {ticker}...")

        # 비동기 데이터 로드 (별도 스레드에서 실행)
        import threading
        from PyQt6.QtCore import QTimer

        def load_in_thread():
            try:
                from frontend.services.chart_data_service import get_chart_data_sync

                # 현재 타임프레임 사용 (없으면 1D 기본)
                timeframe = getattr(self, "_current_timeframe", "1D")
                days = 100 if timeframe == "1D" else 5
                data = get_chart_data_sync(ticker, days=days)

                # 결과를 인스턴스 변수에 저장 후 메인 스레드에서 업데이트
                self._pending_chart_data = (ticker, data)
                QTimer.singleShot(0, self._apply_pending_chart_data)
            except Exception as e:
                self.log(f"[ERROR] Failed to load {ticker}: {e}")

        thread = threading.Thread(target=load_in_thread, daemon=True)
        thread.start()

    def _add_watchlist_sample_data(self):
        """
        [Issue 01-004] Watchlist 초기화 (빈 상태로 시작, 백엔드 연결 시 업데이트됨)

        Model/View 아키텍처: 모델 초기화
        """
        # Model 기반: clear_all() 호출
        self.watchlist_model.clear_all()
        self.log("[INFO] Watchlist ready - waiting for scanner results")

    def _format_dollar_volume(self, value: float) -> str:
        """Dollar Volume K/M/B 포맷팅 (4.A.1.1)"""
        if value >= 1_000_000_000:
            return f"${value / 1e9:.1f}B"
        elif value >= 1_000_000:
            return f"${value / 1e6:.0f}M"
        elif value >= 1_000:
            return f"${value / 1e3:.0f}K"
        return f"${value:.0f}"

    def _save_column_widths(self, table_name: str, column: int, width: int):
        """
        컬럼 너비 변경 시 settings.yaml에 저장

        Args:
            table_name: "tier1" 또는 "tier2"
            column: 변경된 컬럼 인덱스
            width: 새 너비 (픽셀)
        """
        from frontend.config.loader import load_settings, save_setting

        # 0번 컬럼(Ticker)은 Stretch 모드이므로 저장하지 않음
        if column == 0:
            return

        key = f"tables.{table_name}_column_widths"
        current = (
            load_settings().get("tables", {}).get(f"{table_name}_column_widths", [])
        )

        # 리스트 확장 필요 시
        while len(current) <= column:
            current.append(0)

        current[column] = width
        save_setting(key, current)

    # [Issue 01-004] 중복 함수 제거 - 위의 _on_watchlist_table_clicked 사용

    def _refresh_watchlist(self):
        """[Step 4.A.1.3] Watchlist 자동 갱신 (1분 주기)"""
        if hasattr(self, "backend_client") and self.backend_client.is_connected():
            self.backend_client.run_scanner_sync()
            self.log("[INFO] Watchlist auto-refreshed")

    def _on_refresh_score_v2(self):
        """
        [Phase 9] Score V3 재계산 버튼 클릭 핸들러

        Watchlist 전체가 아닌 Score V3만 재계산합니다.
        API 호출: POST /api/watchlist/recalculate
        """
        import threading

        if (
            not hasattr(self, "backend_client")
            or not self.backend_client.is_connected()
        ):
            self.log("[WARN] Backend 미연결 - Score V3 재계산 불가")
            return

        self.log("[INFO] Score V3 재계산 시작...")
        self._refresh_score_v2_btn.setEnabled(False)
        self._refresh_score_v2_btn.setText("⏳")

        # [Phase 9 FIX] 스레드 안전 UI 업데이트를 위한 인스턴스 변수
        self._pending_score_v2_result = None

        def recalculate_in_background():
            try:
                import requests
                from datetime import datetime

                # 백엔드 API 호출
                base_url = self.backend_client._base_url or "http://localhost:8000"
                response = requests.post(
                    f"{base_url}/api/watchlist/recalculate", timeout=120
                )

                if response.status_code == 200:
                    result = response.json()
                    self._pending_score_v2_result = {
                        "success": True,
                        "timestamp": result.get(
                            "timestamp", datetime.now().strftime("%H:%M:%S")
                        ),
                        "count_success": result.get("success", 0),
                        "count_failed": result.get("failed", 0),
                    }
                else:
                    self._pending_score_v2_result = {
                        "success": False,
                        "error": f"HTTP {response.status_code}",
                    }
            except Exception as e:
                self._pending_score_v2_result = {"success": False, "error": str(e)}

            # GUI 스레드에서 업데이트 실행
            from PyQt6.QtCore import QMetaObject, Qt

            QMetaObject.invokeMethod(
                self, "_apply_score_v2_result", Qt.ConnectionType.QueuedConnection
            )

        thread = threading.Thread(target=recalculate_in_background, daemon=True)
        thread.start()

    @pyqtSlot()
    def _apply_score_v2_result(self):
        """[Phase 9] 스레드 안전 UI 업데이트"""
        result = getattr(self, "_pending_score_v2_result", None)
        if result is None:
            return

        self._refresh_score_v2_btn.setEnabled(True)
        self._refresh_score_v2_btn.setText("🔄")

        if result.get("success"):
            timestamp = result.get("timestamp", "--:--:--")
            self._score_v2_updated_label.setText(f"Score V3: {timestamp}")
            self.log(
                f"[INFO] Score V3 재계산 완료: {result.get('count_success', 0)}개 성공, {result.get('count_failed', 0)}개 실패"
            )
        else:
            self.log(f"[ERROR] Score V3 재계산 실패: {result.get('error', 'Unknown')}")

    def _create_center_panel(self) -> QFrame:
        """
        CENTER PANEL - Chart Area (차트 영역)

        [REFAC Phase 4] ChartPanel 모듈 사용으로 교체
        """
        # ChartPanel 생성 (panels/chart_panel.py)
        self._chart_panel = ChartPanel(theme=theme)

        # 시그널 연결
        self._chart_panel.timeframe_changed.connect(self._on_timeframe_changed)
        self._chart_panel.viewport_data_needed.connect(self._on_viewport_data_needed)

        # 호환성을 위한 속성 포워딩
        self.chart_widget = self._chart_panel.chart_widget

        # 시작 시 샘플 데이터 로드 (1.5초 후)
        self._chart_panel.schedule_sample_load(1500)

        return self._chart_panel

    # [REFAC Phase 4] _load_sample_chart_data() 제거됨 → ChartPanel.load_sample_data()로 이동

    def _create_right_panel(self) -> QFrame:
        """
        RIGHT PANEL - Positions & P&L + Oracle

        [REFAC Phase 4] PositionPanel + OraclePanel 모듈 사용으로 교체
        두 패널이 세로로 배치됩니다.
        """
        frame = QFrame()
        frame.setStyleSheet(theme.get_stylesheet("panel"))
        frame.setMinimumWidth(200)
        frame.setMaximumWidth(350)

        main_layout = QVBoxLayout(frame)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # ═══════════════════════════════════════════════════════════
        # 1. PositionPanel (Positions & P&L)
        # ═══════════════════════════════════════════════════════════
        self._position_panel = PositionPanel(theme=theme)
        main_layout.addWidget(self._position_panel)

        # 호환성을 위한 속성 포워딩
        self.pnl_value = self._position_panel.pnl_value
        self.positions_list = self._position_panel.positions_list

        # ═══════════════════════════════════════════════════════════
        # 2. OraclePanel (LLM 분석)
        # ═══════════════════════════════════════════════════════════
        self._oracle_panel = OraclePanel(theme=theme)
        main_layout.addWidget(self._oracle_panel)

        # 호환성을 위한 속성 포워딩
        self.oracle_why_btn = self._oracle_panel.oracle_why_btn
        self.oracle_fundamental_btn = self._oracle_panel.oracle_fundamental_btn
        self.oracle_reflection_btn = self._oracle_panel.oracle_reflection_btn
        self.oracle_result = self._oracle_panel.oracle_result

        main_layout.addStretch()

        return frame

    # [REFAC Phase 4] _get_oracle_btn_style() 제거됨 → OraclePanel._get_btn_style()로 이동

    def _create_bottom_panel(self) -> QFrame:
        """
        BOTTOM PANEL - Log Console (로그 콘솔)

        [REFAC Phase 2] LogPanel 모듈 사용으로 교체
        """
        # LogPanel 생성 (panels/log_panel.py)
        self._log_panel = LogPanel(theme=theme)

        # 호환성을 위해 log_console 속성 유지
        self.log_console = self._log_panel.log_console

        return self._log_panel

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
        Connect 버튼 클릭 - 스마트 자동 연결 (Non-blocking)

        순서:
        1. AWS 서버 연결 시도
        2. 실패 시 → 로컬 서버 연결 시도
        3. 로컬 서버도 없으면 → 자동으로 로컬 서버 시작
        4. 연결 성공 시 → 엔진 자동 시작

        [BUGFIX] GUI freeze 방지: 전체 로직을 백그라운드 스레드에서 실행
        """
        self.log("[ACTION] 🔌 Smart Connect initiated...")
        self.particle_system.order_created()

        # [BUGFIX] 전체 연결 로직을 백그라운드에서 실행
        import threading

        def connect_in_background():
            import httpx
            import subprocess
            import os
            import time
            from PyQt6.QtCore import QTimer

            def log_safe(msg):
                """스레드 안전 로그"""
                QTimer.singleShot(0, lambda: self.log(msg))

            # 설정에서 서버 정보 가져오기
            settings = load_settings()
            aws_host = settings.get("server", {}).get("aws_host", "")
            local_host = "localhost"
            port = settings.get("server", {}).get("port", 8000)

            # ═══════════════════════════════════════════════════════════
            # Step 1: AWS 서버 연결 시도
            # ═══════════════════════════════════════════════════════════
            if (
                aws_host
                and aws_host != "localhost"
                and aws_host != "ec2-xxx.amazonaws.com"
            ):
                log_safe(f"[INFO] 1️⃣ Trying AWS server: {aws_host}:{port}...")
                try:
                    resp = httpx.get(f"http://{aws_host}:{port}/health", timeout=5.0)
                    if resp.status_code == 200:
                        log_safe("[INFO] ✅ AWS server found!")
                        self.backend_client.set_server(aws_host, port)
                        if self.backend_client.connect_sync():
                            QTimer.singleShot(0, self._auto_start_engine)
                            return
                except Exception as e:
                    log_safe(f"[WARN] AWS connection failed: {e}")

            # ═══════════════════════════════════════════════════════════
            # Step 2: 로컬 서버 연결 시도
            # ═══════════════════════════════════════════════════════════
            log_safe(f"[INFO] 2️⃣ Trying local server: {local_host}:{port}...")
            try:
                resp = httpx.get(f"http://{local_host}:{port}/health", timeout=3.0)
                if resp.status_code == 200:
                    log_safe("[INFO] ✅ Local server found!")
                    self.backend_client.set_server(local_host, port)
                    if self.backend_client.connect_sync():
                        QTimer.singleShot(0, self._auto_start_engine)
                        return
            except httpx.ConnectError:
                log_safe("[WARN] Local server not running")
            except Exception as e:
                log_safe(f"[WARN] Local server check failed: {e}")

            # ═══════════════════════════════════════════════════════════
            # Step 3: 로컬 서버 자동 시작
            # ═══════════════════════════════════════════════════════════
            log_safe("[INFO] 3️⃣ Starting local server automatically...")

            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            venv_python = os.path.join(project_root, ".venv", "Scripts", "python.exe")

            if not os.path.exists(venv_python):
                log_safe("[ERROR] ❌ Python not found in .venv")
                return

            try:
                # 새 콘솔 창에서 서버 실행 (cmd /k로 창 유지 - 에러 디버깅용)
                self._local_server_process = subprocess.Popen(
                    ["cmd", "/k", venv_python, "-m", "backend"],
                    cwd=project_root,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
                log_safe(
                    f"[INFO] 🖥️ Local server started (PID: {self._local_server_process.pid})"
                )

                # 서버 시작 대기 (최대 10초)
                for i in range(20):
                    time.sleep(0.5)
                    try:
                        resp = httpx.get(
                            f"http://{local_host}:{port}/health", timeout=2.0
                        )
                        if resp.status_code == 200:
                            log_safe("[INFO] ✅ Local server is now ready!")
                            break
                    except:
                        pass
                    if i % 4 == 0:
                        log_safe(f"[INFO] Waiting for server... ({i // 2}s)")

                # ═══════════════════════════════════════════════════════════
                # Step 4: 연결 및 엔진 시작
                # ═══════════════════════════════════════════════════════════
                self.backend_client.set_server(local_host, port)
                if self.backend_client.connect_sync():
                    QTimer.singleShot(0, self._auto_start_engine)
                else:
                    log_safe("[ERROR] ❌ Failed to connect after starting server")

            except Exception as e:
                log_safe(f"[ERROR] ❌ Failed to start local server: {e}")

        thread = threading.Thread(target=connect_in_background, daemon=True)
        thread.start()

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
        self.backend_client.run_scanner_sync(strategy_name)

    def _update_watchlist_panel(self, items: list):
        """
        [Issue 01-004] Watchlist 패널 업데이트 (Model/View 아키텍처)

        Scanner 결과가 도착하면 WatchlistModel을 통해 업데이트합니다.
        QTableView + QStandardItemModel 조합으로 정렬 상태와 무관하게
        안정적인 데이터 업데이트를 보장합니다.

        [Issue 01-003] Transparency Protocol:
        - 데이터 누락 시 ⚠️ 경고 아이콘 표시
        - 사용자가 데이터 품질 문제를 인지할 수 있도록 함

        Args:
            items: List[WatchlistItem] - Scanner 결과
        """
        if not items:
            self.watchlist_model.clear_all()
            self.log("[INFO] Watchlist updated: 0 stocks")
            return

        # [Issue 6.3 Fix] Watchlist 캐시 저장 (ticker -> item dict)
        self._watchlist_data = {}

        # Model 업데이트 (현재 정렬 상태에 영향 없음)
        for item in items:
            if isinstance(item, WatchlistItem):
                ticker = item.ticker
                change_pct = item.change_pct
                score = item.score
                score_v3 = getattr(
                    item, "score_v3", None
                )  # [03-001] v3 점수 (없으면 None)
                dollar_volume = getattr(item, "dollar_volume", 0) or getattr(
                    item, "avg_volume", 0
                ) * getattr(item, "last_close", 0)
            else:
                ticker = item.get("ticker", "UNKNOWN")
                change_pct = item.get("change_pct", 0.0)
                score = item.get("score", 0)
                score_v3 = item.get("score_v3")  # [03-001] v3 점수 (없으면 None)
                dollar_volume = item.get("dollar_volume", 0) or item.get(
                    "avg_volume", 0
                ) * item.get("last_close", 0)

            # [Issue 6.3 Fix] Watchlist 캐시에 저장
            self._watchlist_data[ticker] = (
                item
                if isinstance(item, dict)
                else {
                    "ticker": ticker,
                    "change_pct": change_pct,
                    "score": score,
                    "stage_number": getattr(item, "stage_number", 0),
                    "source": getattr(item, "source", ""),
                }
            )

            # Ignition Score (캐시에서)
            ignition_score = self._ignition_cache.get(ticker, 0.0)

            # [02-001c FIX] intensities 추출
            if isinstance(item, WatchlistItem):
                intensities = getattr(item, "intensities", {})
            else:
                intensities = item.get("intensities", {})

            # Model 업데이트 (WatchlistModel이 정렬/색상/포맷 처리)
            item_data = {
                "ticker": ticker,
                "change_pct": change_pct,
                "dollar_volume": dollar_volume,
                "score": score,
                "score_v3": score_v3,  # [03-001] v3 점수 추가
                "ignition": ignition_score,
                "intensities": intensities,  # [02-001c] 신호 강도 추가
            }
            self.watchlist_model.update_item(item_data)

        self.log(f"[INFO] Watchlist updated: {len(items)} stocks")
        self.particle_system.order_created()

    def _on_ignition_update(self, data: dict):
        """
        Ignition Score 실시간 업데이트 핸들러 (Phase 2 + 4.A.1 + 4.A.2.2)

        WebSocket으로 수신된 Ignition Score를 캐시에 저장하고
        해당 종목의 Watchlist 테이블을 업데이트합니다.

        [Step 4.A.2.2] 자동 Tier 2 승격 조건:
        - Ignition ≥ 70 (기존)
        - Stage 4 VCP (신규)
        - zenV-zenP Divergence (신규)
        - High Score Gainer (신규)

        Args:
            data: {"ticker": str, "score": float, "passed_filter": bool, "reason": str}
        """
        from PyQt6.QtWidgets import QTableWidgetItem
        from PyQt6.QtCore import Qt

        ticker = data.get("ticker", "")
        score = data.get("score", 0.0)
        passed_filter = data.get("passed_filter", True)

        if not ticker:
            return

        # Ignition 모니터링 활성화 플래그 설정
        self._ignition_monitoring = True

        # 캐시 업데이트
        self._ignition_cache[ticker] = score

        # Watchlist 테이블에서 해당 종목 찾아서 업데이트
        for row in range(self.watchlist_table.rowCount()):
            ticker_item = self.watchlist_table.item(row, 0)
            if ticker_item and ticker_item.text() == ticker:
                # Ignition 컬럼 업데이트
                if score > 0:
                    ign_item = QTableWidgetItem(f"🔥{int(score)}")
                    ign_item.setData(Qt.ItemDataRole.UserRole, score)
                    if score >= 70:
                        ign_item.setBackground(QColor(255, 193, 7, 80))
                else:
                    ign_item = QTableWidgetItem("-")
                    ign_item.setData(Qt.ItemDataRole.UserRole, 0)

                self.watchlist_table.setItem(row, 4, ign_item)
                break

        # [Issue 6.3 Fix] 새로운 복합 승격 조건 검사
        should_promote, reason = self._check_tier2_promotion(
            ticker, score, passed_filter, data
        )
        if should_promote:
            self.particle_system.take_profit()
            self._play_ignition_sound()
            self.log(f"[TIER2] {reason}: {ticker} (Ign={score:.0f})")
            self._promote_to_tier2(ticker, score)

    def _check_tier2_promotion(
        self, ticker: str, ignition_score: float, passed_filter: bool, data: dict = None
    ) -> tuple:
        """
        [05-004] Hot Zone 승격 조건 검사 (Backend API 위임)

        승격 조건 판단은 Backend에서 수행하고, Frontend는 결과만 받아 처리합니다.

        Returns:
            (should_promote: bool, reason: str)
        """
        # 이미 Tier 2에 있으면 건너뛰기 (로컬 캐시 확인 - 빠른 리턴)
        if hasattr(self, "_tier2_cache") and ticker in self._tier2_cache:
            return False, ""

        # Watchlist 캐시에서 컨텍스트 조회
        watchlist_entry = {}
        if hasattr(self, "_watchlist_data"):
            watchlist_entry = self._watchlist_data.get(ticker, {})

        # Tier 2 캐시에서 Z-Score 조회
        zenV = 0.0
        zenP = 0.0
        if hasattr(self, "_tier2_cache") and ticker in self._tier2_cache:
            item = self._tier2_cache[ticker]
            zenV = getattr(item, "zenV", 0.0)
            zenP = getattr(item, "zenP", 0.0)

        # Backend API 호출
        resp = self.backend_client.check_tier2_promotion_sync(
            ticker=ticker,
            ignition_score=ignition_score,
            passed_filter=passed_filter,
            stage_number=watchlist_entry.get("stage_number", 0)
            if isinstance(watchlist_entry, dict)
            else 0,
            acc_score=watchlist_entry.get("score", 0)
            if isinstance(watchlist_entry, dict)
            else 0,
            source=watchlist_entry.get("source", "")
            if isinstance(watchlist_entry, dict)
            else "",
            zenV=zenV,
            zenP=zenP,
        )

        return resp.get("should_promote", False), resp.get("reason", "")

    def _promote_to_tier2(self, ticker: str, ignition_score: float = 0.0):
        """
        종목을 Tier 2 Hot Zone으로 승격 (Step 4.A.2.2)

        Args:
            ticker: 종목 코드
            ignition_score: Ignition Score (optional)
        """
        from PyQt6.QtCore import Qt

        # 이미 Tier 2에 있는지 확인
        if ticker in self._tier2_cache:
            # 이미 존재하면 Ignition만 업데이트
            self._tier2_cache[ticker].ignition = ignition_score
            self._update_tier2_row(ticker)
            return

        # Tier 2 캐시에 추가
        change_pct = 0.0
        price = self._price_cache.get(ticker, 0.0)

        # Tier 1에서 change_pct 가져오기
        for row in range(self.watchlist_table.rowCount()):
            item = self.watchlist_table.item(row, 0)
            if item and item.text() == ticker:
                change_item = self.watchlist_table.item(row, 1)
                if change_item:
                    change_pct = change_item.data(Qt.ItemDataRole.UserRole) or 0.0
                break

        tier2_item = Tier2Item(
            ticker=ticker, price=price, change_pct=change_pct, ignition=ignition_score
        )
        self._tier2_cache[ticker] = tier2_item

        # Tier 2 테이블에 행 추가
        row = self.tier2_table.rowCount()
        self.tier2_table.insertRow(row)
        self._set_tier2_row(row, tier2_item)

        self.log(f"[TIER2] 🔥 {ticker} promoted to Hot Zone (Ign={ignition_score:.0f})")

        # [Step 4.A.3] Z-Score API 호출 (비동기)
        def fetch_zscore():
            try:
                import requests
                from frontend.config.loader import load_settings

                settings = load_settings()
                host = settings.get("backend_host", "127.0.0.1")
                port = settings.get("backend_port", 8000)
                resp = requests.get(
                    f"http://{host}:{port}/api/zscore/{ticker}", timeout=10
                )
                if resp.status_code == 200:
                    data = resp.json()
                    # GUI 업데이트는 메인 스레드에서
                    from PyQt6.QtCore import QTimer

                    def update_zscore():
                        if ticker in self._tier2_cache:
                            zenV = data.get("zenV", 0.0)
                            zenP = data.get("zenP", 0.0)
                            self._tier2_cache[ticker].zenV = zenV
                            self._tier2_cache[ticker].zenP = zenP

                            # [4.A.4] Divergence Signal 탐지
                            if zenV >= 2.0 and zenP < 0.5:
                                self._tier2_cache[ticker].signal = "🔥"  # Divergence
                                self.log(
                                    f"[DIVERGENCE] 🔥 {ticker} zenV={zenV:.2f}, zenP={zenP:.2f}"
                                )
                            elif self._tier2_cache[ticker].ignition >= 70:
                                self._tier2_cache[ticker].signal = "🎯"  # Strike ready

                            self._update_tier2_row(ticker)
                            self.log(
                                f"[TIER2] 📊 {ticker} Z-Score: zenV={zenV:.2f}, zenP={zenP:.2f}"
                            )

                    QTimer.singleShot(0, update_zscore)
            except Exception:
                from PyQt6.QtCore import QTimer

                QTimer.singleShot(
                    0, lambda: self.log(f"[WARN] Z-Score fetch failed: {e}")
                )

        import threading

        threading.Thread(target=fetch_zscore, daemon=True).start()

        # Backend API 호출 (T채널 구독) - Qt 이벤트 루프에선 asyncio 사용 불가
        def call_tier2_api():
            try:
                import asyncio

                asyncio.run(self.backend_client.rest.promote_to_tier2([ticker]))
            except Exception:
                # GUI 스레드에서 로그 출력
                from PyQt6.QtCore import QTimer

                QTimer.singleShot(
                    0, lambda: self.log(f"[WARN] Tier 2 API call failed: {e}")
                )

        try:
            if hasattr(self, "backend_client") and self.backend_client.is_connected():
                import threading

                threading.Thread(target=call_tier2_api, daemon=True).start()
        except Exception as e:
            self.log(f"[WARN] Tier 2 API call failed: {e}")

    def _set_tier2_row(self, row: int, item: Tier2Item):
        """Tier 2 테이블 행 데이터 설정"""
        from PyQt6.QtWidgets import QTableWidgetItem

        # Ticker (텍스트 - 일반 QTableWidgetItem 사용)
        self.tier2_table.setItem(row, 0, QTableWidgetItem(item.ticker))

        # Price (숫자 - NumericTableWidgetItem 사용)
        price_text = f"${item.price:.2f}" if item.price > 0 else "-"
        price_item = NumericTableWidgetItem(price_text, item.price)
        self.tier2_table.setItem(row, 1, price_item)

        # Chg% (숫자)
        sign = "+" if item.change_pct >= 0 else ""
        chg_item = NumericTableWidgetItem(
            f"{sign}{item.change_pct:.1f}%", item.change_pct
        )
        if item.change_pct >= 0:
            chg_item.setForeground(QColor(theme.get_color("success")))
        else:
            chg_item.setForeground(QColor(theme.get_color("danger")))
        self.tier2_table.setItem(row, 2, chg_item)

        # zenV with color coding (숫자)
        zenV_text = f"{item.zenV:.1f}" if item.zenV != 0 else "-"
        zenV_item = NumericTableWidgetItem(zenV_text, item.zenV)
        if item.zenV >= 2.0:
            zenV_item.setForeground(QColor("#ff9800"))  # Orange (High)
        elif item.zenV >= 1.0:
            zenV_item.setForeground(QColor("#4caf50"))  # Green
        else:
            zenV_item.setForeground(QColor("#9e9e9e"))  # Gray
        self.tier2_table.setItem(row, 3, zenV_item)

        # zenP with color coding (숫자)
        zenP_text = f"{item.zenP:.1f}" if item.zenP != 0 else "-"
        zenP_item = NumericTableWidgetItem(zenP_text, item.zenP)
        if item.zenP >= 2.0:
            zenP_item.setForeground(QColor("#ff9800"))  # Orange (High)
        elif item.zenP >= 1.0:
            zenP_item.setForeground(QColor("#4caf50"))  # Green
        else:
            zenP_item.setForeground(QColor("#9e9e9e"))  # Gray
        self.tier2_table.setItem(row, 4, zenP_item)

        # Ign (숫자)
        if item.ignition > 0:
            ign_item = NumericTableWidgetItem(f"{int(item.ignition)}", item.ignition)
            if item.ignition >= 70:
                ign_item.setBackground(QColor(255, 193, 7, 80))
        else:
            ign_item = NumericTableWidgetItem("-", 0)
        self.tier2_table.setItem(row, 5, ign_item)

        # Signal [4.A.4] - 🔥 (Divergence) or 🎯 (Ignition>=70) (텍스트)
        sig_item = QTableWidgetItem(item.signal if item.signal else "")
        if item.signal == "🔥":
            sig_item.setForeground(QColor("#ff5722"))  # Deep Orange for Divergence
        elif item.signal == "🎯":
            sig_item.setForeground(QColor("#e91e63"))  # Pink for Strike
        self.tier2_table.setItem(row, 6, sig_item)

    def _update_tier2_row(self, ticker: str):
        """특정 Tier 2 종목의 행 업데이트"""
        if ticker not in self._tier2_cache:
            return

        item = self._tier2_cache[ticker]
        for row in range(self.tier2_table.rowCount()):
            ticker_item = self.tier2_table.item(row, 0)
            if ticker_item and ticker_item.text() == ticker:
                self._set_tier2_row(row, item)
                break

    def _demote_from_tier2(self, ticker: str):
        """
        [Step 4.A.4] 종목을 Tier 2에서 강등

        Ignition < 50 지속 시 호출됨
        """
        if ticker not in self._tier2_cache:
            return

        # 캐시에서 제거
        del self._tier2_cache[ticker]

        # 테이블에서 행 제거
        for row in range(self.tier2_table.rowCount()):
            ticker_item = self.tier2_table.item(row, 0)
            if ticker_item and ticker_item.text() == ticker:
                self.tier2_table.removeRow(row)
                self.log(f"[TIER2] ⬇️ {ticker} demoted from Hot Zone")
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

        # 현재 선택된 종목 가져오기 (QTableWidget)
        selected_row = self.watchlist_table.currentRow()
        if selected_row < 0:
            self.log("[WARN] No stock selected")
            return

        ticker_item = self.watchlist_table.item(selected_row, 0)
        if not ticker_item:
            return
        ticker = ticker_item.text()
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
                    data = await service.get_chart_data(
                        ticker, timeframe=timeframe, days=days
                    )
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
        if not hasattr(self, "_pending_chart_data"):
            return

        ticker, data = self._pending_chart_data
        delattr(self, "_pending_chart_data")

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
            self.chart_widget.set_ma_data(data["sma_20"], period=20, color="#3b82f6")

        # EMA 9
        if data.get("ema_9"):
            self.chart_widget.set_ma_data(data["ema_9"], period=9, color="#a855f7")

        self.log(f"[INFO] Chart updated for {ticker} ({len(data['candles'])} bars)")

        # Phase 4.A.0.d: 현재 차트 종목 저장 (틱 업데이트용)
        self._current_chart_ticker = ticker

    # ═══════════════════════════════════════════════════════════════════════
    # Phase 4.A.0.d: 틱 기반 실시간 캔들 업데이트
    # ═══════════════════════════════════════════════════════════════════════

    def _on_tick_received(self, tick: dict):
        """
        실시간 틱 수신 핸들러 (Phase 4.A.0.d + Step 4.A.2.5)

        Args:
            tick: {
                "ticker": str,
                "price": float,
                "volume": int
            }

        📌 동작:
        - 가격 캐시 업데이트 (모든 종목)
        - Tier 2 종목이면 테이블 Price 컬럼 업데이트 (4.A.2.5)
        - 현재 차트 종목이면 300ms 스로틀링 후 캔들 업데이트
        """
        from PyQt6.QtWidgets import QTableWidgetItem
        from PyQt6.QtCore import Qt

        ticker = tick.get("ticker")
        price = tick.get("price", 0)
        volume = tick.get("volume", 0)

        if not ticker or price <= 0:
            return

        # 가격 캐시 업데이트 (Tier 2 등에서 사용)
        self._price_cache[ticker] = price

        # [Step 4.A.2.5] Tier 2 종목이면 실시간 가격 업데이트
        if hasattr(self, "_tier2_cache") and ticker in self._tier2_cache:
            self._tier2_cache[ticker].price = price
            self._tier2_cache[ticker].last_update = datetime.now()

            # 테이블에서 해당 행 찾아 Price 컬럼만 업데이트
            for row in range(self.tier2_table.rowCount()):
                ticker_item = self.tier2_table.item(row, 0)
                if ticker_item and ticker_item.text() == ticker:
                    price_item = QTableWidgetItem(f"${price:.2f}")
                    price_item.setData(Qt.ItemDataRole.UserRole, price)
                    self.tier2_table.setItem(row, 1, price_item)
                    break

        # 현재 차트 종목이면 캔들 업데이트 예약
        if self._current_chart_ticker and ticker == self._current_chart_ticker:
            self._pending_tick = {"ticker": ticker, "price": price, "volume": volume}

            # 300ms 스로틀링: 타이머가 이미 실행 중이면 대기
            if not self._tick_throttle_timer.isActive():
                self._tick_throttle_timer.start()

    def _apply_tick_to_chart(self):
        """
        300ms마다 호출 - 현재 캔들 업데이트

        스로틀 타이머가 만료되면 대기 중인 틱으로 차트 업데이트
        """
        if self._pending_tick and hasattr(self, "chart_widget"):
            # [FIX] 틱 종목이 현재 차트 종목과 일치하는지 검증 (race condition 방지)
            if self._pending_tick.get("ticker") == self._current_chart_ticker:
                self.chart_widget.update_current_candle(
                    self._pending_tick["price"], self._pending_tick.get("volume", 0)
                )
            self._pending_tick = None

    def log(self, message: str):
        """로그 콘솔에 메시지 추가 (다이나믹 스크롤)"""
        # Safety check: log_console may not exist during initialization
        if not hasattr(self, "log_console") or self.log_console is None:
            print(f"[LOG] {message}")
            return

        from datetime import datetime

        # 스크롤 위치 저장 (메시지 추가 전)
        scrollbar = self.log_console.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - 20  # 20px 여유

        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_console.append(f"[{timestamp}] {message}")

        # 사용자가 맨 아래에 있었을 때만 자동 스크롤
        if at_bottom:
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

    # [REFAC Cleanup] 중복 _on_strategy_changed 제거됨 → L1066 사용

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
                if "gui" not in s:
                    s["gui"] = {}

            s["gui"]["opacity"] = dlg.opacity_slider.value() / 100.0
            s["gui"]["acrylic_map_alpha"] = dlg.alpha_slider.value()
            s["gui"]["particle_alpha"] = dlg.particle_slider.value() / 100.0
            s["gui"]["tint_color"] = dlg.initial_tint_color
            s["gui"]["theme"] = "light" if dlg.radio_light.isChecked() else "dark"
            s["gui"]["background_effect"] = dlg.effect_combo.currentText().lower()

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
                if theme.mode != s["gui"]["theme"]:
                    self.log(
                        "[INFO] Theme changed. Restart recommended for full effect."
                    )

            else:
                # Revert preview
                print("[DEBUG] Dialog Cancelled")
                self.setWindowOpacity(theme.opacity)
                self.alpha = theme.acrylic_map_alpha
                self.particle_system.global_alpha = theme.particle_alpha  # [NEW] Revert

        except Exception as e:
            print(f"[ERROR] Settings Dialog Crashed: {e}")
            self.log(f"[ERROR] Settings Dialog Crashed: {e}")
            import traceback

            traceback.print_exc()
            self.particle_system.set_background_effect(
                theme.background_effect
            )  # [NEW] Revert
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
        if self._viewport_loading or getattr(self, "_updating_chart", False):
            return

        # 1D(Daily)는 이미 전체 로드됨, Intraday만 동적 로딩
        if not hasattr(self, "_current_timeframe") or self._current_timeframe == "1D":
            return

        # 현재 선택된 종목 확인 (QTableWidget)
        selected_row = self.watchlist_table.currentRow()
        if selected_row < 0:
            return

        ticker_item = self.watchlist_table.item(selected_row, 0)
        if not ticker_item:
            return
        ticker = ticker_item.text()
        timeframe = self._current_timeframe

        # 차트의 현재 첫 번째 타임스탬프 가져오기
        before_timestamp = None
        if (
            hasattr(self.chart_widget, "_candle_data")
            and self.chart_widget._candle_data
        ):
            first_time = self.chart_widget._candle_data[0].get("time", 0)
            if first_time > 0:
                before_timestamp = int(first_time * 1000)  # seconds → ms

        self.log(f"[INFO] 📊 Loading more data: {ticker} {timeframe} (idx={start_idx})")
        self._viewport_loading = True

        # 비동기 데이터 로드 (별도 스레드)
        import threading

        def load_in_thread():
            try:
                self._fetch_historical_bars(
                    ticker, timeframe, abs(start_idx) + 100, before_timestamp
                )
            finally:
                self._viewport_loading = False

        thread = threading.Thread(target=load_in_thread, daemon=True)
        thread.start()

    def _fetch_historical_bars(
        self, ticker: str, timeframe: str, extra_bars: int, before_timestamp: int = None
    ):
        """
        과거 Bar 데이터 조회 (Backend API 호출)

        [REFAC Phase 5] L2→L3 캐시 로직은 Backend로 이동됨.
        Frontend는 단순히 API를 호출하고 결과를 받기만 함.

        Args:
            ticker: 종목 심볼
            timeframe: 타임프레임 (1m, 5m, 15m, 1h)
            extra_bars: 추가로 필요한 바 수
            before_timestamp: 이 시점 이전 데이터를 가져옴 (ms)
        """
        import requests

        try:
            # Backend API 호출
            params = {
                "ticker": ticker,
                "timeframe": timeframe,
                "limit": extra_bars,
            }
            if before_timestamp:
                params["before"] = before_timestamp

            response = requests.get(
                f"{self.backend_client.base_url}/api/chart/bars",
                params=params,
                timeout=30,
            )

            if response.status_code != 200:
                self.log(f"[WARN] Historical bars API failed: {response.status_code}")
                return

            data = response.json()
            bars = data.get("candles", [])

            if bars:
                # 차트에 적용할 데이터 준비
                self._pending_prepend_data = bars
                # Worker thread에서 main thread로 안전하게 호출
                from PyQt6.QtCore import QMetaObject, Qt

                QMetaObject.invokeMethod(
                    self, "_apply_prepend_data", Qt.ConnectionType.QueuedConnection
                )

                self.log(
                    f"[INFO] Loaded {len(bars)} historical bars from {data.get('source', 'API')}"
                )

        except Exception as e:
            self.log(f"[ERROR] Historical data fetch failed: {e}")

    from PyQt6.QtCore import pyqtSlot

    @pyqtSlot()
    def _apply_prepend_data(self):
        """과거 데이터를 차트에 prepend (메인 스레드)"""
        if not hasattr(self, "_pending_prepend_data") or not self._pending_prepend_data:
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
            candle_data.append(
                {
                    "time": ts,
                    "open": bar["open"],
                    "high": bar["high"],
                    "low": bar["low"],
                    "close": bar["close"],
                }
            )
            volume_data.append(
                {
                    "time": ts,
                    "volume": bar["volume"],
                    "is_up": bar["close"] >= bar["open"],
                }
            )

        # 기존 데이터 앞에 추가 (prepend)
        if (
            hasattr(self.chart_widget, "_candle_data")
            and self.chart_widget._candle_data
        ):
            first_existing_time = self.chart_widget._candle_data[0].get("time", 0)
            self.log(
                f"[DEBUG] First existing time: {first_existing_time}, new data range: {candle_data[0]['time']} ~ {candle_data[-1]['time']}"
            )

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
                    if hasattr(self.chart_widget, "_last_requested_start"):
                        self.chart_widget._last_requested_start = 0
                finally:
                    self._updating_chart = False

                self.log(f"[INFO] ✅ {prepend_count} bars prepended, viewport shifted")
            else:
                self.log(
                    "[INFO] No new data to prepend (already loaded or same timerange)"
                )
        else:
            # 기존 데이터 없으면 그냥 설정
            self._updating_chart = True
            try:
                self.chart_widget.set_candlestick_data(candle_data)
                self.chart_widget.set_volume_data(volume_data)
            finally:
                self._updating_chart = False
            self.log(f"[INFO] ✅ {len(candle_data)} bars loaded (no existing data)")

    # ═══════════════════════════════════════════════════════════════════
    # Phase 4.A.0: 실시간 바 수신 핸들러
    # ═══════════════════════════════════════════════════════════════════

    def _on_bar_received(self, data: dict):
        """
        실시간 바 데이터 수신 핸들러 (Phase 4.A.0)

        Massive WebSocket에서 AM (1분봉) 데이터가 도착하면
        현재 표시 중인 차트를 업데이트합니다.

        Args:
            data: {
                "ticker": str,
                "timeframe": str,
                "bar": {
                    "time": float,
                    "open": float,
                    "high": float,
                    "low": float,
                    "close": float,
                    "volume": int
                }
            }
        """
        try:
            ticker = data.get("ticker", "")
            bar = data.get("bar", {})

            # 현재 차트에 표시 중인 종목이 아니면 무시
            if not hasattr(self, "_current_ticker") or self._current_ticker != ticker:
                return

            # 차트 업데이트
            if hasattr(self, "chart_widget") and self.chart_widget:
                self.chart_widget.update_realtime_bar(bar)

        except Exception as e:
            self.log(f"[WARN] Bar update error: {e}")

    # [REFAC Cleanup] 중복 _on_tick_received 제거됨 → L1625 사용

    def on_heartbeat_received(self, data: dict):
        """
        [08-001] Heartbeat 수신 핸들러

        control_panel.update_time에 위임 (정책: dashboard는 연결만)
        """
        if hasattr(self, "control_panel"):
            self.control_panel.update_time(data)


# ═══════════════════════════════════════════════════════════════════════════
# 직접 실행 시 테스트
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    app = QApplication(sys.argv)
    window = Sigma9Dashboard()
    window.show()
    sys.exit(app.exec())
