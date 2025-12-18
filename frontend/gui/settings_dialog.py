# ============================================================================
# Sigma9 Settings Dialog
# ============================================================================
try:
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, 
        QRadioButton, QPushButton, QGroupBox, QFrame, QColorDialog,
        QSpinBox, QDoubleSpinBox
    )
    from PyQt6.QtGui import QColor
except ModuleNotFoundError:
    from PySide6.QtCore import Qt, Signal as pyqtSignal
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
        QRadioButton, QPushButton, QGroupBox, QFrame, QColorDialog,
        QSpinBox, QDoubleSpinBox
    )
    from PySide6.QtGui import QColor

from .theme import theme
from .window_effects import WindowsEffects # Acrylic Effect

class SettingsDialog(QDialog):
    # 설정 변경 시그널 (preview 용)
    # dict: {ikey: value}
    sig_settings_changed = pyqtSignal(dict)

    def __init__(self, parent=None, current_settings=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedWidth(400)
        self.settings = current_settings or {}
        
        # 기본값 설정
        self.initial_opacity = self.settings.get("opacity", 1.0)
        self.initial_alpha = self.settings.get("acrylic_map_alpha", 150)
        self.initial_theme = self.settings.get("theme", "dark")
        
        # [NEW] Acrylic Effect & Frameless
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._init_ui()
        self._apply_theme()
        
        # Apply Acrylic
        self.window_effects = WindowsEffects()
        # Use tint color from settings or theme
        tint_color = self.settings.get("tint_color")
        if not tint_color:
             tint_color = f"{theme.tint_r:02X}{theme.tint_g:02X}{theme.tint_b:02X}"
        else:
            tint_color = tint_color.lstrip("#")
            
        # Add alpha to color string for acrylic
        # Note: SettingsDialog opacity might be separate from acrylic tint
        # Here we use a fixed high alpha for the dialog background itself to ensure readability
        self.window_effects.add_acrylic_effect(self.winId(), f"{tint_color}CC") # CC = 80% opacity for dialog bg

    def _init_ui(self):
        # Create a main frame to hold content and sensitive borders if needed
        # For simple dialog, just layout on self is fine but we need to ensure text is readable
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title Bar (Custom since frameless)
        title_layout = QHBoxLayout()
        title_label = QLabel("Settings")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # 1. Appearance Group
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QVBoxLayout(appearance_group)
        appearance_layout.setSpacing(15)
        
        # Theme Selection
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Theme Mode:")
        self.radio_dark = QRadioButton("Dark")
        self.radio_light = QRadioButton("Light")
        
        if self.initial_theme == "light":
            self.radio_light.setChecked(True)
        else:
            self.radio_dark.setChecked(True)
            
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.radio_dark)
        theme_layout.addWidget(self.radio_light)
        theme_layout.addStretch()
        appearance_layout.addLayout(theme_layout)
        
        # ════════════════════════════════════════════════════════════════════
        # Sliders Group (Opacity, Acrylic Alpha, Particle Alpha)
        # ════════════════════════════════════════════════════════════════════
        
        # A. Window Opacity
        self.opacity_slider, self.opacity_spin = self._create_slider_row(
            appearance_layout, "Window Opacity:", 20, 100, int(self.initial_opacity * 100), "%",
            color="#00BCD4"
        )
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        self.opacity_spin.valueChanged.connect(lambda v: self.opacity_slider.setValue(v))

        # B. Acrylic Tint Alpha
        self.alpha_slider, self.alpha_spin = self._create_slider_row(
            appearance_layout, "Acrylic Alpha:", 0, 255, self.initial_alpha, "",
            color="#2196F3"
        )
        self.alpha_slider.valueChanged.connect(self._on_alpha_changed)
        self.alpha_spin.valueChanged.connect(lambda v: self.alpha_slider.setValue(v))

        # C. Particle Opacity
        self.initial_particle_alpha = self.settings.get("particle_alpha", 1.0)
        self.particle_slider, self.particle_spin = self._create_slider_row(
            appearance_layout, "Particle Opacity:", 0, 100, int(self.initial_particle_alpha * 100), "%",
            color="#9C27B0"
        )
        self.particle_slider.valueChanged.connect(self._on_particle_changed)
        self.particle_spin.valueChanged.connect(lambda v: self.particle_slider.setValue(v))
        
        layout.addWidget(appearance_group)

        # ════════════════════════════════════════════════════════════════════
        # Acrylic Color Section (Bottom)
        # ════════════════════════════════════════════════════════════════════
        color_group = QGroupBox("Acrylic Tint Color")
        color_layout = QHBoxLayout(color_group)
        
        self.initial_tint_color = self.settings.get("tint_color")
        if not self.initial_tint_color:
             self.initial_tint_color = f"#{theme.tint_r:02X}{theme.tint_g:02X}{theme.tint_b:02X}"
        
        c = self.initial_tint_color.lstrip("#")
        self.current_tint_r = int(c[0:2], 16)
        self.current_tint_g = int(c[2:4], 16)
        self.current_tint_b = int(c[4:6], 16)

        # Color Button
        self.color_btn = QPushButton("Select Color")
        self.color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color_btn.setFixedHeight(30)
        self.color_btn.clicked.connect(self._on_color_picker)
        self._update_color_btn_style()
        
        # Hex Label
        self.color_hex_label = QLabel(self.initial_tint_color)
        self.color_hex_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.color_hex_label.setFixedWidth(80)
        self.color_hex_label.setStyleSheet("color: white; font-family: monospace; font-weight: bold;")
        
        # Preview
        self.color_preview = QFrame()
        self.color_preview.setFixedSize(30, 30)
        self._update_preview()
        
        color_layout.addWidget(self.color_preview)
        color_layout.addWidget(self.color_hex_label)
        color_layout.addWidget(self.color_btn)
        
        layout.addWidget(color_group)

        # 2. Action Buttons (Save/Cancel)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton("Save")
        self.btn_save.clicked.connect(self.accept)
        
        # Custom button style for Acrylic Dialog
        style_base = """
            QPushButton {
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: bold;
            }
        """
        self.btn_save.setStyleSheet(style_base + "QPushButton { background-color: #2196F3; color: white; } QPushButton:hover { background-color: #1976D2; }")
        self.btn_cancel.setStyleSheet(style_base + "QPushButton { background-color: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.2); } QPushButton:hover { background-color: rgba(255,255,255,0.2); }")
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        
        layout.addLayout(btn_layout)

    def _create_slider_row(self, parent_layout, label_text, min_val, max_val, init_val, suffix, color):
        """Helper to create a unified slider row with SpinBox"""
        row_layout = QHBoxLayout()
        
        # Label
        label = QLabel(label_text)
        label.setFixedWidth(100)
        label.setStyleSheet("color: #DDD;")
        
        # Slider
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(init_val)
        slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{ background: rgba(255,255,255,0.2); height: 6px; border-radius: 3px; }}
            QSlider::handle:horizontal {{ background: {color}; width: 14px; margin: -4px 0; border-radius: 7px; }}
        """)
        
        # SpinBox (Editable Value)
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(init_val)
        spin.setSuffix(suffix)
        spin.setFixedWidth(70)
        spin.setStyleSheet("""
            QSpinBox {
                background: rgba(0,0,0,0.3);
                color: white;
                border: 1px solid rgba(255,255,255,0.2);
                border-radius: 4px;
                padding: 4px;
            }
        """)
        
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
                background-color: {c['background']};
                color: {c['text']};
            }}
            QGroupBox {{
                color: {c['primary']};
                font-weight: bold;
                border: 1px solid {c['border']};
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 15px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                left: 10px;
            }}
            QLabel {{
                color: {c['text']};
            }}
            QRadioButton {{
                color: {c['text']};
            }}
            QRadioButton::indicator:checked {{
                background-color: {c['primary']};
                border: 2px solid {c['primary']};
                border-radius: 6px;
                width: 8px;
                height: 8px;
            }}
            QRadioButton::indicator:unchecked {{
                border: 2px solid {c['text_secondary']};
                border-radius: 6px;
                width: 8px;
                height: 8px;
            }}
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
        self.sig_settings_changed.emit({
            "acrylic_map_alpha": value,
            "tint_color": self.initial_tint_color
        })

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
            self.initial_tint_color = new_color.name().upper() # #RRGGBB
            self.color_hex_label.setText(self.initial_tint_color)
            
            # Update internal RGB
            self.current_tint_r = new_color.red()
            self.current_tint_g = new_color.green()
            self.current_tint_b = new_color.blue()

            self._update_color_btn_style()
            self._update_preview()

            self.sig_settings_changed.emit({
                "tint_color": self.initial_tint_color,
                "acrylic_map_alpha": self.alpha_slider.value()
            })

    def _update_preview(self):
        alpha = self.alpha_slider.value()
        self.color_preview.setStyleSheet(f"""
            QFrame {{
                background-color: rgba({self.current_tint_r}, {self.current_tint_g}, {self.current_tint_b}, {alpha});
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 4px;
            }}
        """)

    def _update_color_btn_style(self):
         self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.initial_tint_color};
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 6px;
                color: {'white' if (self.current_tint_r + self.current_tint_g + self.current_tint_b) < 400 else 'black'};
                font-weight: bold;
            }}
            QPushButton:hover {{
                border: 2px solid white;
            }}
         """)
