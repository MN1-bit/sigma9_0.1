
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QPushButton, QLabel, QComboBox, 
    QSizePolicy, QWidget, QVBoxLayout, QGraphicsOpacityEffect
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
import os
from .theme import theme

class StatusIndicator(QWidget):
    """연결 상태 표시기 (🔴🟡🟢)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.dot = QLabel("🔴")
        self.dot.setStyleSheet("background: transparent; border: none; font-size: 10px;")
        
        self.text = QLabel("Disconnected")
        self.text.setStyleSheet(f"color: {theme.get_color('text_secondary')}; background: transparent; border: none; font-size: 11px;")
        
        self.layout.addWidget(self.dot)
        self.layout.addWidget(self.text)
        
    def set_status(self, color_key: str, text: str):
        color = theme.get_color(color_key)
        
        # Dot 색상/아이콘 변경
        if color_key == 'success': icon = "🟢"
        elif color_key == 'warning': icon = "🟡"
        elif color_key == 'danger': icon = "🔴"
        elif color_key == 'primary': icon = "🔵"  # RUNNING 상태
        else: icon = "⚪"
        
        self.dot.setText(icon)
        self.text.setText(text)
        self.text.setStyleSheet(f"color: {color}; background: transparent; border: none; font-size: 11px;")

class LoadingOverlay(QWidget):
    """로딩 오버레이"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hide()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents) # 클릭 통과
        
        layout = QHBoxLayout(self)
        self.label = QLabel("Loading...")
        self.label.setStyleSheet(f"color: {theme.get_color('primary')}; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.label)
        
    def show_loading(self, show=True):
        self.setVisible(show)

class ControlPanel(QFrame):
    """
    트레이딩 제어 패널 (Top Panel)
    """
    
    # Signals (Dashboard 호환)
    connect_clicked = pyqtSignal()
    disconnect_clicked = pyqtSignal()
    start_clicked = pyqtSignal()
    stop_clicked = pyqtSignal()
    kill_clicked = pyqtSignal()
    strategy_selected = pyqtSignal(str)
    strategy_selection_changed = pyqtSignal(str) # Renaming alias if needed
    # strategy_selected = pyqtSignal(str) # Kept above
    strategy_reload_clicked = pyqtSignal()
    settings_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self._init_ui()
        
    def _init_ui(self):
        # 스타일 적용
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.get_color('surface')}; 
                border: 1px solid {theme.get_color('border')};
                border-radius: 8px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(10)
        
        # 1. 로고
        # 1. 로고 (Icon + Text)
        logo_container = QWidget()
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(8) # Icon과 Text 사이 간격

        # Icon
        icon_label = QLabel()
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "assets", "ico01.ico")
            icon_pixmap = QIcon(icon_path).pixmap(24, 24)
            icon_label.setPixmap(icon_pixmap)
        except Exception as e:
            icon_label.setText("⚡") # Fallback
            
        icon_label.setStyleSheet("border: none; background: transparent;")
        logo_layout.addWidget(icon_label)

        # Text
        text_label = QLabel("Sigma9")
        text_label.setStyleSheet(f"""
            color: {theme.get_color('text')}; font-size: 16px; font-weight: bold; border: none; background: transparent;
        """)
        logo_layout.addWidget(text_label)
        
        layout.addWidget(logo_container)
        
        layout.addStretch(1)
        
        # 2. Connection Controls
        self.connect_btn = self._create_button("🔌 Connect", "primary", self._on_connect_clicked)
        self.disconnect_btn = self._create_button("⏏️ Disconnect", "text_secondary", self._on_disconnect_clicked)
        self.disconnect_btn.hide()
        layout.addWidget(self.connect_btn)
        layout.addWidget(self.disconnect_btn)
        
        # 3. Engine Controls
        self.start_btn = self._create_button("🚀 Start Engine", "success", self.start_clicked.emit)
        self.stop_btn = self._create_button("⏹ Stop Engine", "warning", self.stop_clicked.emit)
        self.start_btn.setEnabled(False)
        self.stop_btn.hide()
        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        
        layout.addWidget(self._create_separator())
        
        # 4. Strategy Controls
        self._init_strategy_ui(layout)
        
        layout.addWidget(self._create_separator())
        
        # 5. Emergency
        self.kill_btn = self._create_button("⚡ KILL SWITCH", "danger", self.kill_clicked.emit)
        layout.addWidget(self.kill_btn)
        
        # 6. Status Indicator (Custom Widget)
        self.status_indicator = StatusIndicator()
        layout.addWidget(self.status_indicator)
        
        # 7. Settings
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.setStyleSheet(f"""
            QPushButton {{ color: {theme.get_color('text_secondary')}; background: transparent; border: none; font-size: 16px; }}
            QPushButton:hover {{ color: {theme.get_color('text')}; }}
        """)
        self.settings_btn.clicked.connect(lambda: print("[DEBUG] ControlPanel: Settings Button Clicked!"))
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self.settings_btn)

    def _init_strategy_ui(self, layout):
        label = QLabel("Strategy:")
        label.setStyleSheet(f"color: {theme.get_color('text_secondary')}; font-size: 11px; border: none; background: transparent;")
        layout.addWidget(label)
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.setMinimumWidth(120)
        self.strategy_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {theme.get_color('surface')};
                border: 1px solid {theme.get_color('border')};
                color: {theme.get_color('text')};
                padding: 4px;
                border-radius: 4px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background-color: {theme.get_color('background')};
                color: {theme.get_color('text')};
                selection-background-color: {theme.get_color('primary')};
            }}
        """)
        self.strategy_combo.currentTextChanged.connect(self.strategy_selected.emit)
        layout.addWidget(self.strategy_combo)
        
        self.reload_btn = QPushButton("🔄")
        self.reload_btn.setToolTip("Reload Strategy")
        self.reload_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reload_btn.setStyleSheet(f"""
            QPushButton {{ color: {theme.get_color('text_secondary')}; background: transparent; border: none; font-size: 14px; }}
            QPushButton:hover {{ color: {theme.get_color('primary')}; }}
        """)
        self.reload_btn.clicked.connect(self.strategy_reload_clicked.emit)
        layout.addWidget(self.reload_btn)

    def _create_button(self, text, color_key, callback):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(theme.get_button_style(color_key))
        btn.clicked.connect(callback)
        return btn
        
    def _create_separator(self):
        lbl = QLabel("|")
        lbl.setStyleSheet(f"color: {theme.get_color('border')}; border: none; background: transparent;")
        return lbl

    def _on_connect_clicked(self):
        self.connect_clicked.emit()
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Connecting...")

    def _on_disconnect_clicked(self):
        self.disconnect_clicked.emit()

        
    def update_connection_status(self, connected: bool):
        """연결 상태 업데이트"""
        if connected:
            self.connect_btn.hide()
            self.disconnect_btn.show()
            self.start_btn.setEnabled(True)
            self.status_indicator.set_status('success', "Connected")
        else:
            self.connect_btn.show()
            self.disconnect_btn.hide()
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText("🔌 Connect")
            self.start_btn.setEnabled(False)
            self.stop_btn.hide()
            self.start_btn.show()
            self.status_indicator.set_status('danger', "Disconnected")
    
    def update_engine_status(self, running: bool):
        """엔진 상태 업데이트 (파란색 Running)"""
        if running:
            self.start_btn.hide()
            self.stop_btn.show()
            self.status_indicator.set_status('primary', "Running")
        else:
            self.stop_btn.hide()
            self.start_btn.show()
            self.start_btn.setEnabled(True)
            self.status_indicator.set_status('success', "Connected")

    def set_strategies(self, strategies: list):
        self.strategy_combo.clear()
        self.strategy_combo.addItems(strategies)
        
    def get_selected_strategy(self) -> str:
        """현재 선택된 전략 반환"""
        return self.strategy_combo.currentText()
