import sys
import os

# 고DPI 스케일링 문제 해결을 위한 환경변수
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

try:
    from PyQt6.QtGui import QIcon, QColor
    from PyQt6.QtWidgets import (
        QApplication,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QFrame,
        QSlider,
        QPushButton,
        QColorDialog,
        QGridLayout,
    )
    from PyQt6.QtCore import Qt
except ModuleNotFoundError:
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import (
        QApplication,
        QVBoxLayout,
        QHBoxLayout,
        QLabel,
        QFrame,
        QSlider,
        QPushButton,
        QColorDialog,
        QGridLayout,
    )
    from PySide6.QtCore import Qt

from custom_window import CustomWindow
from particle_effects import ParticleSystem


class AcrylicDashboard(CustomWindow):
    def __init__(self):
        # 초기 색상 설정
        self.tint_r = 0x20
        self.tint_g = 0x20
        self.tint_b = 0x20
        self.alpha = 0x60

        super().__init__(use_mica="false", theme="dark", color=self._get_color_string())
        self.resize(900, 750)
        self.setWindowTitle("Project Omnissiah - Trading Effects Demo")

        self.init_dashboard()

        # 파티클 시스템 오버레이 추가
        self.particle_system = ParticleSystem(self)
        self.particle_system.setGeometry(0, 0, self.width(), self.height())
        self.particle_system.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "particle_system"):
            self.particle_system.setGeometry(0, 0, self.width(), self.height())

    def _get_color_string(self):
        return f"{self.tint_r:02X}{self.tint_g:02X}{self.tint_b:02X}{self.alpha:02X}"

    def _update_acrylic(self):
        color = self._get_color_string()
        self.acrylic_color = color
        self.win_effects.add_acrylic_effect(self.winId(), color)
        self._update_preview()

    def _update_preview(self):
        self.color_preview.setStyleSheet(f"""
            background-color: rgba({self.tint_r}, {self.tint_g}, {self.tint_b}, {self.alpha});
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 8px;
        """)
        self.color_value_label.setText(f"#{self._get_color_string()}")
        self.alpha_value_label.setText(f"{self.alpha} ({int(self.alpha / 255 * 100)}%)")

    def _on_alpha_changed(self, value):
        self.alpha = value
        self._update_acrylic()

    def _on_color_picker(self):
        current = QColor(self.tint_r, self.tint_g, self.tint_b)
        color = QColorDialog.getColor(current, self, "Tint Color 선택")
        if color.isValid():
            self.tint_r = color.red()
            self.tint_g = color.green()
            self.tint_b = color.blue()
            self._update_acrylic()
            self.color_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgb({self.tint_r}, {self.tint_g}, {self.tint_b});
                    border: 1px solid rgba(255, 255, 255, 0.3);
                    border-radius: 6px;
                    padding: 8px 16px;
                    color: {"white" if (self.tint_r + self.tint_g + self.tint_b) < 400 else "black"};
                }}
                QPushButton:hover {{ border: 2px solid white; }}
            """)

    def _on_particle_alpha_changed(self, value):
        """파티클 투명도 슬라이더 변경"""
        self.particle_system.global_alpha = value / 100.0
        self.particle_alpha_value.setText(f"{value}%")

    def _create_effect_button(self, text: str, color: str, callback) -> QPushButton:
        """이펙트 버튼 생성 헬퍼"""
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                color: white;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {color};
                border: 2px solid white;
            }}
            QPushButton:pressed {{
                background-color: {color};
                opacity: 0.8;
            }}
        """)
        btn.clicked.connect(callback)
        return btn

    def init_dashboard(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 50, 20, 20)
        layout.setSpacing(12)

        # 타이틀
        title = QLabel("Trading Particle Effects Demo")
        title.setStyleSheet("""
            font-size: 22px; 
            font-weight: bold; 
            color: white;
            background: transparent;
        """)
        layout.addWidget(title)

        # === 트레이딩 이펙트 버튼 ===
        effects_group = QFrame()
        effects_group.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.08); 
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
            }
            QLabel { background: transparent; border: none; color: white; }
        """)
        effects_layout = QVBoxLayout(effects_group)
        effects_layout.setContentsMargins(15, 15, 15, 15)

        effects_title = QLabel("🎯 Trading Events")
        effects_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #aaa;")
        effects_layout.addWidget(effects_title)

        # 버튼 그리드
        grid = QGridLayout()
        grid.setSpacing(10)

        # Row 1: 주문 관련
        grid.addWidget(
            self._create_effect_button(
                "📝 주문 생성", "#2196F3", lambda: self.particle_system.order_created()
            ),
            0,
            0,
        )
        grid.addWidget(
            self._create_effect_button(
                "✅ 주문 체결", "#FF9800", lambda: self.particle_system.order_filled()
            ),
            0,
            1,
        )

        # Row 2: 포지션 상태
        grid.addWidget(
            self._create_effect_button(
                "📈 수익중 시작",
                "#4CAF50",
                lambda: self.particle_system.start_profit_effect(),
            ),
            1,
            0,
        )
        grid.addWidget(
            self._create_effect_button(
                "📉 손실중 시작",
                "#f44336",
                lambda: self.particle_system.start_loss_effect(),
            ),
            1,
            1,
        )

        # Row 3: 청산
        grid.addWidget(
            self._create_effect_button(
                "💰 익절 (Take Profit)",
                "#00C853",
                lambda: self.particle_system.take_profit(),
            ),
            2,
            0,
        )
        grid.addWidget(
            self._create_effect_button(
                "🛑 손절 (Stop Loss)",
                "#D32F2F",
                lambda: self.particle_system.stop_loss(),
            ),
            2,
            1,
        )

        # Row 4: 파티클 투명도 슬라이더
        particle_alpha_row = QHBoxLayout()
        particle_alpha_label = QLabel("✨ 파티클 Alpha:")
        particle_alpha_label.setStyleSheet(
            "color: white; background: transparent; border: none;"
        )
        particle_alpha_label.setFixedWidth(110)

        self.particle_alpha_slider = QSlider(Qt.Orientation.Horizontal)
        self.particle_alpha_slider.setMinimum(0)
        self.particle_alpha_slider.setMaximum(100)
        self.particle_alpha_slider.setValue(100)
        self.particle_alpha_slider.setStyleSheet("""
            QSlider::groove:horizontal { background: rgba(255,255,255,0.2); height: 6px; border-radius: 3px; }
            QSlider::handle:horizontal { background: #9C27B0; width: 14px; margin: -4px 0; border-radius: 7px; }
        """)
        self.particle_alpha_slider.valueChanged.connect(self._on_particle_alpha_changed)

        self.particle_alpha_value = QLabel("100%")
        self.particle_alpha_value.setStyleSheet(
            "color: white; background: transparent; border: none;"
        )
        self.particle_alpha_value.setFixedWidth(50)

        particle_alpha_row.addWidget(particle_alpha_label)
        particle_alpha_row.addWidget(self.particle_alpha_slider)
        particle_alpha_row.addWidget(self.particle_alpha_value)
        effects_layout.addLayout(particle_alpha_row)

        # Row 5: 컨트롤
        clear_btn = self._create_effect_button(
            "🧹 이펙트 정리", "#607D8B", lambda: self.particle_system.clear_all()
        )
        grid.addWidget(clear_btn, 3, 0, 1, 2)

        effects_layout.addLayout(grid)
        layout.addWidget(effects_group)

        # === Acrylic 컨트롤 (축소) ===
        control_group = QFrame()
        control_group.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05); 
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
            QLabel { background: transparent; border: none; color: white; }
        """)
        control_layout = QVBoxLayout(control_group)
        control_layout.setContentsMargins(15, 15, 15, 15)
        control_layout.setSpacing(10)

        control_title = QLabel("🎨 Acrylic Settings")
        control_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #aaa;")
        control_layout.addWidget(control_title)

        # 투명도 + 색상 한 줄에
        settings_row = QHBoxLayout()

        # 투명도
        alpha_label = QLabel("Alpha:")
        alpha_label.setFixedWidth(50)
        self.alpha_slider = QSlider(Qt.Orientation.Horizontal)
        self.alpha_slider.setMinimum(0)
        self.alpha_slider.setMaximum(255)
        self.alpha_slider.setValue(self.alpha)
        self.alpha_slider.setStyleSheet("""
            QSlider::groove:horizontal { background: rgba(255,255,255,0.2); height: 6px; border-radius: 3px; }
            QSlider::handle:horizontal { background: #0078D4; width: 14px; margin: -4px 0; border-radius: 7px; }
        """)
        self.alpha_slider.valueChanged.connect(self._on_alpha_changed)
        self.alpha_value_label = QLabel(f"{self.alpha}")
        self.alpha_value_label.setFixedWidth(60)

        settings_row.addWidget(alpha_label)
        settings_row.addWidget(self.alpha_slider)
        settings_row.addWidget(self.alpha_value_label)

        # 색상 버튼
        self.color_btn = QPushButton("Color")
        self.color_btn.setFixedWidth(80)
        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb({self.tint_r}, {self.tint_g}, {self.tint_b});
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 6px;
                padding: 6px;
                color: white;
            }}
        """)
        self.color_btn.clicked.connect(self._on_color_picker)
        settings_row.addWidget(self.color_btn)

        self.color_value_label = QLabel(f"#{self._get_color_string()}")
        self.color_value_label.setFixedWidth(90)
        settings_row.addWidget(self.color_value_label)

        control_layout.addLayout(settings_row)

        # 미리보기
        self.color_preview = QFrame()
        self.color_preview.setFixedHeight(40)
        control_layout.addWidget(self.color_preview)

        layout.addWidget(control_group)

        # 안내
        info = QLabel(
            "💡 창 뒤에 다른 앱을 두고 블러 효과 + 파티클 이펙트를 확인하세요!"
        )
        info.setStyleSheet("color: #666; font-size: 11px; background: transparent;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        layout.addStretch(1)
        self.setLayout(layout)
        self._update_preview()


if __name__ == "__main__":
    if hasattr(Qt, "HighDpiScaleFactorRoundingPolicy"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    app = QApplication(sys.argv)
    window = AcrylicDashboard()
    window.show()
    sys.exit(app.exec())
