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
        QWidget, QSizePolicy
    )
    from PyQt6.QtCore import Qt
except ModuleNotFoundError:
    from PySide6.QtGui import QIcon, QColor, QFont
    from PySide6.QtWidgets import (
        QApplication, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
        QSlider, QPushButton, QSplitter, QTextEdit, QListWidget,
        QWidget, QSizePolicy
    )
    from PySide6.QtCore import Qt

from .custom_window import CustomWindow
from .particle_effects import ParticleSystem
from .theme import theme  # [REFAC] 테마 매니저 임포트
from .settings_dialog import SettingsDialog
from .chart_widget import ChartWidget  # Step 2.4.7: 차트 위젯
from ..config.loader import load_settings, save_settings


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
        self.particle_system.raise_()

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
        # 1. TOP PANEL - 컨트롤 버튼
        # ═══════════════════════════════════════════════════════════
        top_panel = self._create_top_panel()
        main_layout.addWidget(top_panel)
        
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
        
        # 샘플 데이터
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
        
        Step 2.4.7: TradingView Lightweight Charts 통합
        """
        frame, layout = self._create_panel_frame("📈 Chart")
        
        # [DEBUG] ChartWidget Transparency Test: Revert to placeholder (User Request)
        chart_placeholder = QLabel("TradingView Chart\n(Coming Soon)")
        chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c = theme.colors
        chart_placeholder.setStyleSheet(f"""
            color: {c['text_secondary']};
            font-size: 20px;
            background-color: transparent;
            border: 1px dashed {c['border']};
            border-radius: 8px;
        """)
        chart_placeholder.setSizePolicy(
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.Expanding
        )
        layout.addWidget(chart_placeholder)

        # Step 2.4.7: ChartWidget 통합 (TradingView Lightweight Charts)
        # self.chart_widget = ChartWidget()
        # self.chart_widget.setSizePolicy(
        #     QSizePolicy.Policy.Expanding, 
        #     QSizePolicy.Policy.Expanding
        # )
        # layout.addWidget(self.chart_widget)
        
        # Step 2.4.8: 시작 시 샘플 데이터 로드 (1초 후)
        # from PyQt6.QtCore import QTimer
        # QTimer.singleShot(1500, self._load_sample_chart_data)
        
        return frame
    
    def _load_sample_chart_data(self):
        """
        Step 2.4.8: 샘플 차트 데이터 로드
        
        차트 위젯이 정상적으로 표시되는지 확인을 위한 테스트 데이터
        """
        # 샘플 캨들 데이터
        sample_candles = [
            {"time": "2024-12-01", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.3},
            {"time": "2024-12-02", "open": 10.3, "high": 10.8, "low": 10.1, "close": 10.6},
            {"time": "2024-12-03", "open": 10.6, "high": 11.2, "low": 10.4, "close": 10.9},
            {"time": "2024-12-04", "open": 10.9, "high": 11.5, "low": 10.7, "close": 11.3},
            {"time": "2024-12-05", "open": 11.3, "high": 12.0, "low": 11.1, "close": 11.8},
            {"time": "2024-12-06", "open": 11.8, "high": 12.3, "low": 11.5, "close": 12.1},
            {"time": "2024-12-07", "open": 12.1, "high": 12.8, "low": 12.0, "close": 12.5},
            {"time": "2024-12-08", "open": 12.5, "high": 13.0, "low": 12.2, "close": 12.7},
        ]
        self.chart_widget.set_candlestick_data(sample_candles)
        
        # 샘플 VWAP
        sample_vwap = [
            {"time": "2024-12-01", "value": 10.2},
            {"time": "2024-12-02", "value": 10.5},
            {"time": "2024-12-03", "value": 10.8},
            {"time": "2024-12-04", "value": 11.1},
            {"time": "2024-12-05", "value": 11.4},
            {"time": "2024-12-06", "value": 11.8},
            {"time": "2024-12-07", "value": 12.2},
            {"time": "2024-12-08", "value": 12.5},
        ]
        self.chart_widget.set_vwap_data(sample_vwap)
        
        # 샘플 마커
        self.chart_widget.add_buy_marker("2024-12-04", 11.3)
        self.chart_widget.add_ignition_marker("2024-12-04", 85)
        
        self.log("[INFO] Chart loaded with sample data")

    def _create_right_panel(self) -> QFrame:
        """
        RIGHT PANEL - Positions & P&L (포지션 및 손익)
        """
        frame, layout = self._create_panel_frame("💰 Positions & P&L")
        frame.setMinimumWidth(200)
        frame.setMaximumWidth(350)
        
        # P&L 요약
        pnl_frame = QFrame()
        c = theme.colors # 단축 변수
        # success color 변형해서 배경색 사용 (투명도 조절은 어려우므로 일단 surface 사용)
        pnl_frame.setStyleSheet(f"""
            background-color: {c['surface']};
            border: 1px solid {c['success']};
            border-radius: 8px;
        """)
        pnl_layout = QVBoxLayout(pnl_frame)
        
        pnl_label = QLabel("Today's P&L")
        pnl_label.setStyleSheet(f"color: {c['text_secondary']}; font-size: 11px; background: transparent; border: none;")
        pnl_layout.addWidget(pnl_label)
        
        pnl_value = QLabel("+ $0.00")
        pnl_value.setStyleSheet(f"""
            color: {c['success']}; 
            font-size: 24px; 
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        pnl_layout.addWidget(pnl_value)
        
        layout.addWidget(pnl_frame)
        
        # 포지션 리스트
        positions_label = QLabel("Active Positions")
        positions_label.setStyleSheet(f"color: {c['text_secondary']}; font-size: 11px; background: transparent; border: none; margin-top: 10px;")
        layout.addWidget(positions_label)
        
        self.positions_list = QListWidget()
        # [REFAC] 테마 매니저 List 스타일 사용
        styles = theme.get_stylesheet("list")
        # [FIX] 배경을 투명하게 하고 패널 배경을 사용
        styles += "QListWidget { background-color: transparent; }"
        self.positions_list.setStyleSheet(styles)
        
        self.positions_list.addItems([
            "No active positions"
        ])
        
        layout.addWidget(self.positions_list)
        
        return frame

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
    # 버튼 이벤트 핸들러 (Placeholder)
    # ═══════════════════════════════════════════════════════════════════════

    def _on_connect(self):
        """Connect 버튼 클릭"""
        self.log("[ACTION] Connect button clicked")
        self.particle_system.order_created()
        self.status_label.setText("🟡 Connecting...")
        # primary 색상으로 변경
        self.status_label.setStyleSheet(self.status_label.styleSheet().replace(theme.get_color("danger"), theme.get_color("warning")))

    def _on_start(self):
        """Start Engine 버튼 클릭"""
        self.log("[ACTION] Start Engine clicked")
        self.particle_system.order_filled()

    def _on_stop(self):
        """Stop 버튼 클릭"""
        self.log("[ACTION] Stop clicked")
        self.particle_system.stop_loss()

    def _on_kill(self):
        """Kill Switch 버튼 클릭"""
        self.log("[EMERGENCY] ⚡ KILL SWITCH ACTIVATED!")
        self.particle_system.stop_loss()

    def log(self, message: str):
        """로그 콘솔에 메시지 추가"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_console.append(f"[{timestamp}] {message}")

    def _on_settings(self):
        """설정 버튼 클릭"""
        current_settings = load_settings()
        dlg = SettingsDialog(self, current_settings)
        dlg.sig_settings_changed.connect(self._on_settings_preview)
        
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
                
            if save_settings(s):
                self.log("[INFO] Settings saved.")
                theme.reload()
                
                # Apply changes safely
                self.tint_r = theme.tint_r
                self.tint_g = theme.tint_g
                self.tint_b = theme.tint_b
                self.alpha = theme.acrylic_map_alpha
                self.particle_system.global_alpha = theme.particle_alpha
                
                self.setWindowOpacity(theme.opacity)
                self.update_acrylic_color(self._get_color_string())
                
                # Theme reload notice
                if theme.mode != s['gui']['theme']:
                     self.log("[INFO] Theme changed. Restart recommended for full effect.")

        else:
            # Revert preview
            self.setWindowOpacity(theme.opacity)
            self.alpha = theme.acrylic_map_alpha
            self.particle_system.global_alpha = theme.particle_alpha # [NEW] Revert
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
