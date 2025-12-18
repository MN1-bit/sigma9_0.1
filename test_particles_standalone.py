
import sys
import os

# Ensure we can import from frontend
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QFrame
from PyQt6.QtCore import Qt
from frontend.gui.particle_effects import ParticleSystem
from frontend.gui.theme import theme
from frontend.gui.custom_window import CustomWindow

class ParticleTestWindow(CustomWindow):
    def __init__(self):
        super().__init__(use_mica='false', theme='dark', color=f"{theme.tint_r:02X}{theme.tint_g:02X}{theme.tint_b:02X}FF")
        self.setWindowTitle("Sigma9 Particle Effect Tester")
        self.resize(1000, 800)
        
        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Particle System (Background)
        self.particle_system = ParticleSystem(self)
        self.particle_system.setGeometry(0, 0, self.width(), self.height())
        self.particle_system.global_alpha = 1.0
        self.particle_system.lower() # Send to back
        
        # 2. UI Overlay (Buttons)
        # Use a container to centering
        overlay_container = QWidget(self)
        overlay_layout = QVBoxLayout(overlay_container)
        overlay_layout.addStretch()
        
        # Button Panel
        btn_panel = QFrame()
        btn_panel.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(0, 0, 0, 0.5);
                border-radius: 15px;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}
        """)
        btn_layout = QHBoxLayout(btn_panel)
        
        effects = [
            "Constellation", 
            "Digital Dust", 
            "Bokeh", 
            "Vector Field", 
            "Matrix Rain",
            "None"
        ]
        
        for name in effects:
            btn = QPushButton(name)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: white;
                    background-color: rgba(255, 255, 255, 0.1);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    padding: 8px 16px;
                    border-radius: 5px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.2);
                    border: 1px solid #2196F3;
                    color: #2196F3;
                }}
            """)
            btn.clicked.connect(lambda checked, n=name: self.change_effect(n))
            btn_layout.addWidget(btn)
            
        overlay_layout.addWidget(btn_panel)
        overlay_layout.addStretch()
        
        main_layout.addWidget(overlay_container)
        
        # Initial Effect
        self.change_effect("Constellation")

    def change_effect(self, name):
        print(f"[ACTION] Changing effect to: {name}")
        self.particle_system.set_background_effect(name)
        if name == "None":
             self.particle_system.background_effect = None
             
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.particle_system.setGeometry(0, 0, self.width(), self.height())

if __name__ == "__main__":
    if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
            
    app = QApplication(sys.argv)
    window = ParticleTestWindow()
    window.show()
    sys.exit(app.exec())
