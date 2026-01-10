# ============================================================================
# Sigma9 Settings Dialog (Tabbed Layout)
# ============================================================================
# Step 4.2.3: Settings Dialog 탭 구조 개편
#
# 📌 탭 구조:
#   - Connection: 서버 연결 설정
#   - Backend: 스케줄러 설정
#   - Theme: 외관 설정 (기존 항목)
# ============================================================================
try:
    from PyQt6.QtCore import Qt, pyqtSignal, QTime
    from PyQt6.QtWidgets import (
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QSlider,
        QRadioButton,
        QPushButton,
        QGroupBox,
        QFrame,
        QColorDialog,
        QSpinBox,
        QDoubleSpinBox,
        QComboBox,
        QTabWidget,
        QWidget,
        QFormLayout,
        QLineEdit,
        QCheckBox,
        QTimeEdit,
    )
    from PyQt6.QtGui import QColor
except ModuleNotFoundError:
    from PySide6.QtCore import Qt, Signal as pyqtSignal, QTime
    from PySide6.QtWidgets import (
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QSlider,
        QRadioButton,
        QPushButton,
        QFrame,
        QColorDialog,
        QSpinBox,
        QComboBox,
        QTabWidget,
        QWidget,
        QFormLayout,
        QLineEdit,
        QCheckBox,
        QTimeEdit,
    )
    from PySide6.QtGui import QColor

from .theme import theme
from .window_effects import WindowsEffects


class SettingsDialog(QDialog):
    """
    설정 다이얼로그 (탭 구조)

    📌 탭:
        - Connection: 서버 Host/Port, Auto-connect, Reconnect, Timeout
        - Backend: Market Open Scan, Scan Offset, Daily Data Update, Update Time
        - Theme: Opacity, Acrylic Alpha, Particle Opacity, Tint Color, Background Effect
    """

    # 설정 변경 시그널 (preview 용)
    sig_settings_changed = pyqtSignal(dict)

    def __init__(self, parent=None, current_settings=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(450, 500)
        self.settings = current_settings or {}

        # 섹션별 기본값 로드
        self.gui_settings = self.settings.get("gui", {})
        self.server_settings = self.settings.get("server", {})
        self.connection_settings = self.settings.get("connection", {})
        self.scheduler_settings = self.settings.get("scheduler", {})

        # Theme 기본값
        self.initial_opacity = self.gui_settings.get(
            "window_opacity", self.gui_settings.get("opacity", 1.0)
        )
        self.initial_alpha = self.gui_settings.get(
            "acrylic_alpha", self.gui_settings.get("acrylic_map_alpha", 150)
        )
        self.initial_theme = self.gui_settings.get("theme", "dark")
        self.initial_particle_alpha = self.gui_settings.get(
            "particle_opacity", self.gui_settings.get("particle_alpha", 1.0)
        )

        # Tint Color
        self.initial_tint_color = self.gui_settings.get("tint_color")
        if not self.initial_tint_color:
            self.initial_tint_color = (
                f"#{theme.tint_r:02X}{theme.tint_g:02X}{theme.tint_b:02X}"
            )
        c = self.initial_tint_color.lstrip("#")
        self.current_tint_r = int(c[0:2], 16) if len(c) >= 2 else 26
        self.current_tint_g = int(c[2:4], 16) if len(c) >= 4 else 26
        self.current_tint_b = int(c[4:6], 16) if len(c) >= 6 else 46

        # Frameless + Acrylic
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._init_ui()
        self._apply_theme()

        # Apply Acrylic
        self.window_effects = WindowsEffects()
        tint_hex = self.initial_tint_color.lstrip("#")
        self.window_effects.add_acrylic_effect(self.winId(), f"{tint_hex}CC")

    def _init_ui(self):
        """UI 초기화 (탭 구조)"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # 타이틀 바 (Frameless이므로 커스텀)
        title_layout = QHBoxLayout()
        title_label = QLabel("⚙️ Settings")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # ═══════════════════════════════════════════════════════════
        # QTabWidget (메인 탭)
        # ═══════════════════════════════════════════════════════════
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { 
                border: 1px solid rgba(255,255,255,0.1); 
                border-radius: 6px;
                background: rgba(0,0,0,0.2);
            }
            QTabBar::tab {
                background: rgba(255,255,255,0.1);
                color: white;
                padding: 8px 16px;
                margin: 2px;
                border-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #2196F3;
            }
            QTabBar::tab:hover:!selected {
                background: rgba(255,255,255,0.2);
            }
        """)

        # 탭 추가
        self.tab_widget.addTab(self._create_connection_tab(), "Connection")
        self.tab_widget.addTab(self._create_backend_tab(), "Backend")
        self.tab_widget.addTab(self._create_theme_tab(), "Theme")

        layout.addWidget(self.tab_widget)

        # ═══════════════════════════════════════════════════════════
        # 버튼 영역
        # ═══════════════════════════════════════════════════════════
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self.accept)

        btn_style = """
            QPushButton {
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }
        """
        self.btn_save.setStyleSheet(
            btn_style
            + "QPushButton { background-color: #2196F3; color: white; } QPushButton:hover { background-color: #1976D2; }"
        )
        self.btn_cancel.setStyleSheet(
            btn_style
            + "QPushButton { background-color: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.2); } QPushButton:hover { background-color: rgba(255,255,255,0.2); }"
        )

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    # ═══════════════════════════════════════════════════════════════════════════
    # Connection Tab (Step 4.2.3.3)
    # ═══════════════════════════════════════════════════════════════════════════

    def _create_connection_tab(self) -> QWidget:
        """Connection 탭: 서버 연결 설정"""
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)

        # ═══════════════════════════════════════════════════════════
        # 서버 프리셋 선택 (Local/AWS)
        # ═══════════════════════════════════════════════════════════
        preset_label = QLabel("🌐 Server Preset")
        preset_label.setStyleSheet(
            "color: #2196F3; font-weight: bold; font-size: 12px;"
        )
        layout.addRow(preset_label)

        self.server_preset_combo = QComboBox()
        self.server_preset_combo.addItem("🖥️ Local (localhost:8000)", "local")
        self.server_preset_combo.addItem("☁️ AWS (configure below)", "aws")
        self.server_preset_combo.addItem("🔧 Custom", "custom")
        self.server_preset_combo.setStyleSheet("""
            QComboBox {
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 4px;
                padding: 6px;
                color: white;
            }
            QComboBox:hover {
                border: 1px solid #2196F3;
            }
            QComboBox QAbstractItemView {
                background: #1e1e1e;
                border: 1px solid #333;
                color: white;
                selection-background-color: #2196F3;
            }
        """)
        self.server_preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        layout.addRow("Server:", self.server_preset_combo)

        # 구분선
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: rgba(255,255,255,0.1);")
        layout.addRow(separator)

        # ═══════════════════════════════════════════════════════════
        # 서버 주소 설정
        # ═══════════════════════════════════════════════════════════

        # Server Host
        self.host_edit = QLineEdit()
        self.host_edit.setText(self.server_settings.get("host", "localhost"))
        self.host_edit.setPlaceholderText("localhost or IP/hostname")
        self._style_input(self.host_edit)
        layout.addRow("Server Host:", self.host_edit)

        # Server Port
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(self.server_settings.get("port", 8000))
        self._style_input(self.port_spin)
        layout.addRow("Server Port:", self.port_spin)

        # Auto-connect
        self.auto_connect_check = QCheckBox("Connect on startup")
        self.auto_connect_check.setChecked(
            self.connection_settings.get("auto_connect", True)
        )
        self.auto_connect_check.setStyleSheet("color: white;")
        layout.addRow("Auto Connect:", self.auto_connect_check)

        # Reconnect Interval
        self.reconnect_spin = QSpinBox()
        self.reconnect_spin.setRange(1, 60)
        self.reconnect_spin.setValue(
            self.connection_settings.get("reconnect_interval", 5)
        )
        self.reconnect_spin.setSuffix(" sec")
        self._style_input(self.reconnect_spin)
        layout.addRow("Reconnect Interval:", self.reconnect_spin)

        # Timeout
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 120)
        self.timeout_spin.setValue(self.connection_settings.get("timeout", 30))
        self.timeout_spin.setSuffix(" sec")
        self._style_input(self.timeout_spin)
        layout.addRow("Timeout:", self.timeout_spin)

        # 연결 테스트 버튼
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background: rgba(76, 175, 80, 0.3);
                color: #4CAF50;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background: rgba(76, 175, 80, 0.5);
            }
        """)
        self.test_btn.clicked.connect(self._on_test_connection)
        layout.addRow("", self.test_btn)

        return widget

    def _on_preset_changed(self, index: int):
        """서버 프리셋 변경 시 호스트/포트 자동 설정"""
        preset = self.server_preset_combo.currentData()

        if preset == "local":
            self.host_edit.setText("localhost")
            self.port_spin.setValue(8000)
            self.host_edit.setEnabled(False)
            self.port_spin.setEnabled(False)
        elif preset == "aws":
            # AWS 기본값 (나중에 실제 EC2 주소로 변경)
            self.host_edit.setText("ec2-xxx.amazonaws.com")
            self.port_spin.setValue(8000)
            self.host_edit.setEnabled(True)
            self.port_spin.setEnabled(True)
        else:  # custom
            self.host_edit.setEnabled(True)
            self.port_spin.setEnabled(True)

    def _on_test_connection(self):
        """연결 테스트 수행"""
        import httpx

        host = self.host_edit.text()
        port = self.port_spin.value()
        url = f"http://{host}:{port}/health"

        self.test_btn.setText("Testing...")
        self.test_btn.setEnabled(False)

        try:
            # 동기 요청 (간단한 테스트)
            response = httpx.get(url, timeout=5.0)
            if response.status_code == 200:
                self.test_btn.setText("✅ Connected!")
                self.test_btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(76, 175, 80, 0.5);
                        color: white;
                        border: 1px solid #4CAF50;
                        border-radius: 4px;
                        padding: 6px 12px;
                    }
                """)
            else:
                self.test_btn.setText(f"❌ Error: {response.status_code}")
                self._reset_test_btn_error()
        except httpx.ConnectError:
            self.test_btn.setText("❌ Connection refused")
            self._reset_test_btn_error()
        except httpx.TimeoutException:
            self.test_btn.setText("❌ Timeout")
            self._reset_test_btn_error()
        except Exception as e:
            self.test_btn.setText(f"❌ {str(e)[:20]}")
            self._reset_test_btn_error()
        finally:
            self.test_btn.setEnabled(True)
            # 3초 후 버튼 텍스트 리셋
            from PyQt6.QtCore import QTimer

            QTimer.singleShot(3000, lambda: self.test_btn.setText("Test Connection"))

    def _reset_test_btn_error(self):
        """테스트 버튼 에러 스타일"""
        self.test_btn.setStyleSheet("""
            QPushButton {
                background: rgba(244, 67, 54, 0.3);
                color: #F44336;
                border: 1px solid #F44336;
                border-radius: 4px;
                padding: 6px 12px;
            }
        """)

    # ═══════════════════════════════════════════════════════════════════════════
    # Backend Tab (Step 4.2.3.4 + 4.2.6)
    # ═══════════════════════════════════════════════════════════════════════════

    def _create_backend_tab(self) -> QWidget:
        """Backend 탭: 스케줄러 설정 + 로컬 서버 구동"""
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 20, 15, 15)

        # ═══════════════════════════════════════════════════════════
        # Step 4.2.6: 로컬 서버 구동 섹션
        # ═══════════════════════════════════════════════════════════
        server_section_label = QLabel("🖥️ Local Server")
        server_section_label.setStyleSheet(
            "color: #2196F3; font-weight: bold; font-size: 12px;"
        )
        layout.addRow(server_section_label)

        # 서버 상태 표시
        self.server_status_label = QLabel("⚫ Not Running")
        self.server_status_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addRow("Server Status:", self.server_status_label)

        # 로컬 서버 구동 버튼
        server_btn_layout = QHBoxLayout()

        self.start_server_btn = QPushButton("▶️ Start Local Server")
        self.start_server_btn.setToolTip(
            "Windows에서 로컬 Backend 서버 시작 (AWS 아님)"
        )
        self.start_server_btn.setStyleSheet("""
            QPushButton {
                background: rgba(76, 175, 80, 0.3);
                color: #4CAF50;
                border: 1px solid #4CAF50;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(76, 175, 80, 0.5);
            }
            QPushButton:disabled {
                background: rgba(100, 100, 100, 0.3);
                color: #666;
                border: 1px solid #666;
            }
        """)
        self.start_server_btn.clicked.connect(self._on_start_local_server)
        server_btn_layout.addWidget(self.start_server_btn)

        self.stop_server_btn = QPushButton("⏹️ Shutdown")
        self.stop_server_btn.setToolTip("로컬 Backend 서버 종료")
        self.stop_server_btn.setEnabled(False)
        self.stop_server_btn.setStyleSheet("""
            QPushButton {
                background: rgba(244, 67, 54, 0.3);
                color: #F44336;
                border: 1px solid #F44336;
                border-radius: 4px;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background: rgba(244, 67, 54, 0.5);
            }
            QPushButton:disabled {
                background: rgba(100, 100, 100, 0.3);
                color: #666;
                border: 1px solid #666;
            }
        """)
        self.stop_server_btn.clicked.connect(self._on_stop_local_server)
        server_btn_layout.addWidget(self.stop_server_btn)

        layout.addRow("", server_btn_layout)

        # 구분선
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: rgba(255,255,255,0.1);")
        layout.addRow(separator)

        # ═══════════════════════════════════════════════════════════
        # 스케줄러 설정 섹션
        # ═══════════════════════════════════════════════════════════
        scheduler_label = QLabel("📅 Scheduler")
        scheduler_label.setStyleSheet(
            "color: #2196F3; font-weight: bold; font-size: 12px; margin-top: 8px;"
        )
        layout.addRow(scheduler_label)

        # Market Open Scan 활성화
        self.market_scan_check = QCheckBox("Enable")
        self.market_scan_check.setChecked(
            self.scheduler_settings.get("market_open_scan", True)
        )
        self.market_scan_check.setStyleSheet("color: white;")
        layout.addRow("Market Open Scan:", self.market_scan_check)

        # Scan Offset (분)
        self.scan_offset_spin = QSpinBox()
        self.scan_offset_spin.setRange(0, 60)
        self.scan_offset_spin.setValue(
            self.scheduler_settings.get("market_open_offset_minutes", 15)
        )
        self.scan_offset_spin.setSuffix(" min after open")
        self._style_input(self.scan_offset_spin)
        layout.addRow("Scan Offset:", self.scan_offset_spin)

        # Daily Data Update 활성화
        self.daily_update_check = QCheckBox("Enable")
        self.daily_update_check.setChecked(
            self.scheduler_settings.get("daily_data_update", True)
        )
        self.daily_update_check.setStyleSheet("color: white;")
        layout.addRow("Daily Data Update:", self.daily_update_check)

        # Update Time
        self.update_time_edit = QTimeEdit()
        time_str = self.scheduler_settings.get("data_update_time", "16:30")
        parts = time_str.split(":")
        hour = int(parts[0]) if parts else 16
        minute = int(parts[1]) if len(parts) > 1 else 30
        self.update_time_edit.setTime(QTime(hour, minute))
        self.update_time_edit.setDisplayFormat("HH:mm")
        self._style_input(self.update_time_edit)
        layout.addRow("Update Time (ET):", self.update_time_edit)

        # Info Label
        info_label = QLabel("⚠️ Scheduler changes require server restart")
        info_label.setStyleSheet("color: #FFA726; font-size: 10px; margin-top: 8px;")
        layout.addRow("", info_label)

        # 서버 프로세스 핸들
        self._server_process = None

        return widget

    def _on_start_local_server(self):
        """로컬 서버 시작 (Windows subprocess)"""
        import subprocess
        import os

        # 프로젝트 루트 찾기
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        venv_python = os.path.join(project_root, ".venv", "Scripts", "python.exe")

        if not os.path.exists(venv_python):
            self.server_status_label.setText("❌ Python not found")
            self.server_status_label.setStyleSheet("color: #F44336; font-size: 11px;")
            return

        try:
            # 새 콘솔 창에서 서버 실행 (CREATE_NEW_CONSOLE)
            self._server_process = subprocess.Popen(
                [venv_python, "-m", "backend"],
                cwd=project_root,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )

            self.server_status_label.setText(
                "🟢 Running (PID: {})".format(self._server_process.pid)
            )
            self.server_status_label.setStyleSheet("color: #4CAF50; font-size: 11px;")

            self.start_server_btn.setEnabled(False)
            self.stop_server_btn.setEnabled(True)

        except Exception as e:
            self.server_status_label.setText(f"❌ Error: {str(e)[:30]}")
            self.server_status_label.setStyleSheet("color: #F44336; font-size: 11px;")

    def _on_stop_local_server(self):
        """로컬 서버 중지"""
        if self._server_process:
            try:
                self._server_process.terminate()
                self._server_process.wait(timeout=5)
            except:
                self._server_process.kill()

            self._server_process = None

        self.server_status_label.setText("⚫ Not Running")
        self.server_status_label.setStyleSheet("color: #888; font-size: 11px;")

        self.start_server_btn.setEnabled(True)
        self.stop_server_btn.setEnabled(False)

    # ═══════════════════════════════════════════════════════════════════════════
    # Theme Tab (Step 4.2.3.2 - 기존 항목 마이그레이션)
    # ═══════════════════════════════════════════════════════════════════════════

    def _create_theme_tab(self) -> QWidget:
        """Theme 탭: 외관 설정 (기존 항목 마이그레이션)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 15, 10, 10)

        # Theme Selection
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Theme Mode:")
        theme_label.setStyleSheet("color: #DDD;")
        self.radio_dark = QRadioButton("Dark")
        self.radio_light = QRadioButton("Light")
        self.radio_dark.setStyleSheet("color: white;")
        self.radio_light.setStyleSheet("color: white;")

        if self.initial_theme == "light":
            self.radio_light.setChecked(True)
        else:
            self.radio_dark.setChecked(True)

        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.radio_dark)
        theme_layout.addWidget(self.radio_light)
        theme_layout.addStretch()
        layout.addLayout(theme_layout)

        # Background Effect
        effect_layout = QHBoxLayout()
        effect_label = QLabel("Background Effect:")
        effect_label.setStyleSheet("color: #DDD;")
        self.effect_combo = QComboBox()
        self.effect_combo.addItems(
            [
                "None",
                "Constellation",
                "Digital Dust",
                "Bokeh",
                "Vector Field",
                "Matrix Rain",
                "Golden Rain",
                "Rising Bubbles",
                "Falling Ember",
            ]
        )
        self._style_input(self.effect_combo)

        current_effect = self.gui_settings.get(
            "background_effect", "constellation"
        ).lower()
        for i in range(self.effect_combo.count()):
            if self.effect_combo.itemText(i).lower() == current_effect:
                self.effect_combo.setCurrentIndex(i)
                break
        self.effect_combo.currentTextChanged.connect(self._on_effect_changed)

        effect_layout.addWidget(effect_label)
        effect_layout.addWidget(self.effect_combo)
        effect_layout.addStretch()
        layout.addLayout(effect_layout)

        # Sliders
        self.opacity_slider, self.opacity_spin = self._create_slider_row(
            layout,
            "Window Opacity:",
            20,
            100,
            int(self.initial_opacity * 100),
            "%",
            "#00BCD4",
        )
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.opacity_spin.valueChanged.connect(
            lambda v: self.opacity_slider.setValue(v)
        )

        self.alpha_slider, self.alpha_spin = self._create_slider_row(
            layout, "Acrylic Alpha:", 0, 255, int(self.initial_alpha), "", "#2196F3"
        )
        self.alpha_slider.valueChanged.connect(self._on_alpha_changed)
        self.alpha_spin.valueChanged.connect(lambda v: self.alpha_slider.setValue(v))

        self.particle_slider, self.particle_spin = self._create_slider_row(
            layout,
            "Particle Opacity:",
            0,
            100,
            int(self.initial_particle_alpha * 100),
            "%",
            "#9C27B0",
        )
        self.particle_slider.valueChanged.connect(self._on_particle_changed)
        self.particle_spin.valueChanged.connect(
            lambda v: self.particle_slider.setValue(v)
        )

        # Tint Color
        color_layout = QHBoxLayout()
        color_label = QLabel("Tint Color:")
        color_label.setStyleSheet("color: #DDD;")
        color_label.setFixedWidth(100)

        self.color_preview = QFrame()
        self.color_preview.setFixedSize(24, 24)
        self._update_preview()

        self.color_hex_label = QLabel(self.initial_tint_color)
        self.color_hex_label.setStyleSheet("color: white; font-family: monospace;")
        self.color_hex_label.setFixedWidth(70)

        self.color_btn = QPushButton("Choose")
        self.color_btn.setFixedWidth(80)
        self.color_btn.clicked.connect(self._on_color_picker)
        self._update_color_btn_style()

        color_layout.addWidget(color_label)
        color_layout.addWidget(self.color_preview)
        color_layout.addWidget(self.color_hex_label)
        color_layout.addWidget(self.color_btn)
        color_layout.addStretch()
        layout.addLayout(color_layout)
        layout.addStretch()
        return widget

    # ═══════════════════════════════════════════════════════════════════════════
    # Helper Methods
    # ═══════════════════════════════════════════════════════════════════════════

    def _style_input(self, widget):
        """입력 위젯 스타일링"""
        widget.setStyleSheet("""
            background: rgba(0,0,0,0.3);
            color: white;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 4px;
            padding: 4px 8px;
        """)

    def _create_slider_row(
        self, parent_layout, label_text, min_val, max_val, init_val, suffix, color
    ):
        """슬라이더 행 생성"""
        row_layout = QHBoxLayout()

        label = QLabel(label_text)
        label.setFixedWidth(100)
        label.setStyleSheet("color: #DDD;")

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(init_val)
        slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{ background: rgba(255,255,255,0.2); height: 6px; border-radius: 3px; }}
            QSlider::handle:horizontal {{ background: {color}; width: 14px; margin: -4px 0; border-radius: 7px; }}
        """)

        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(init_val)
        spin.setSuffix(suffix)
        spin.setFixedWidth(65)
        self._style_input(spin)

        row_layout.addWidget(label)
        row_layout.addWidget(slider)
        row_layout.addWidget(spin)

        parent_layout.addLayout(row_layout)
        return slider, spin

    def _apply_theme(self):
        """다이얼로그 스타일링"""
        c = theme.colors
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {c["background"]};
                color: {c["text"]};
            }}
            QLabel {{
                color: {c["text"]};
            }}
        """)

    # ═══════════════════════════════════════════════════════════════════════════
    # Event Handlers
    # ═══════════════════════════════════════════════════════════════════════════

    def _on_test_connection(self):
        """연결 테스트"""
        self.host_edit.text()
        self.port_spin.value()
        self.test_btn.setText("Testing...")
        self.test_btn.setEnabled(False)

        # TODO: 실제 연결 테스트 구현
        from PyQt6.QtCore import QTimer

        QTimer.singleShot(1000, lambda: self._test_connection_result(True))

    def _test_connection_result(self, success: bool):
        """연결 테스트 결과"""
        self.test_btn.setEnabled(True)
        if success:
            self.test_btn.setText("✅ Connected!")
            self.test_btn.setStyleSheet("""
                QPushButton { background: rgba(76, 175, 80, 0.5); color: white; border: 1px solid #4CAF50; border-radius: 4px; padding: 6px 12px; }
            """)
        else:
            self.test_btn.setText("❌ Failed")
            self.test_btn.setStyleSheet("""
                QPushButton { background: rgba(244, 67, 54, 0.5); color: white; border: 1px solid #F44336; border-radius: 4px; padding: 6px 12px; }
            """)

    def _on_opacity_changed(self, value):
        if self.opacity_spin.value() != value:
            self.opacity_spin.blockSignals(True)
            self.opacity_spin.setValue(value)
            self.opacity_spin.blockSignals(False)
        self.sig_settings_changed.emit({"opacity": value / 100.0})

    def _on_alpha_changed(self, value):
        if self.alpha_spin.value() != value:
            self.alpha_spin.blockSignals(True)
            self.alpha_spin.setValue(value)
            self.alpha_spin.blockSignals(False)
        self._update_preview()
        self.sig_settings_changed.emit(
            {"acrylic_map_alpha": value, "tint_color": self.initial_tint_color}
        )

    def _on_particle_changed(self, value):
        if self.particle_spin.value() != value:
            self.particle_spin.blockSignals(True)
            self.particle_spin.setValue(value)
            self.particle_spin.blockSignals(False)
        self.sig_settings_changed.emit({"particle_alpha": value / 100.0})

    def _on_color_picker(self):
        color = QColor(self.initial_tint_color)
        new_color = QColorDialog.getColor(color, self, "Select Acrylic Tint Color")

        if new_color.isValid():
            self.initial_tint_color = new_color.name().upper()
            self.color_hex_label.setText(self.initial_tint_color)
            self.current_tint_r = new_color.red()
            self.current_tint_g = new_color.green()
            self.current_tint_b = new_color.blue()
            self._update_color_btn_style()
            self._update_preview()
            self.sig_settings_changed.emit(
                {
                    "tint_color": self.initial_tint_color,
                    "acrylic_map_alpha": self.alpha_slider.value(),
                }
            )

    def _update_preview(self):
        alpha = self.alpha_slider.value() if hasattr(self, "alpha_slider") else 150
        self.color_preview.setStyleSheet(f"""
            QFrame {{
                background-color: rgba({self.current_tint_r}, {self.current_tint_g}, {self.current_tint_b}, {alpha});
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 4px;
            }}
        """)

    def _update_color_btn_style(self):
        brightness = self.current_tint_r + self.current_tint_g + self.current_tint_b
        text_color = "white" if brightness < 400 else "black"
        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.initial_tint_color};
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                color: {text_color};
            }}
            QPushButton:hover {{ border: 2px solid white; }}
        """)

    def _on_effect_changed(self, text):
        self.sig_settings_changed.emit({"background_effect": text.lower()})

    # ═══════════════════════════════════════════════════════════════════════════
    # Get All Settings
    # ═══════════════════════════════════════════════════════════════════════════

    def get_all_settings(self) -> dict:
        """모든 설정값 반환"""
        return {
            # Connection
            "server_host": self.host_edit.text(),
            "server_port": self.port_spin.value(),
            "auto_connect": self.auto_connect_check.isChecked(),
            "reconnect_interval": self.reconnect_spin.value(),
            "timeout": self.timeout_spin.value(),
            # Backend (Scheduler)
            "market_open_scan": self.market_scan_check.isChecked(),
            "scan_offset_minutes": self.scan_offset_spin.value(),
            "daily_data_update": self.daily_update_check.isChecked(),
            "data_update_time": self.update_time_edit.time().toString("HH:mm"),
            # Theme
            "theme": "light" if self.radio_light.isChecked() else "dark",
            "background_effect": self.effect_combo.currentText().lower(),
            "opacity": self.opacity_slider.value() / 100.0,
            "acrylic_map_alpha": self.alpha_slider.value(),
            "particle_alpha": self.particle_slider.value() / 100.0,
            "tint_color": self.initial_tint_color,
        }
