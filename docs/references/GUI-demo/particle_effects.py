"""
Trading Particle Effects System
퀀트 트레이딩 봇용 파티클 이펙트 시스템
"""
import random
import math
import os
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

try:
    from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
    from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QPixmap, QTransform
    from PyQt6.QtWidgets import QWidget
except ModuleNotFoundError:
    from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
    from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QPixmap, QTransform
    from PySide6.QtWidgets import QWidget


@dataclass
class Particle:
    """개별 파티클"""
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    ax: float = 0.0  # 가속도 x
    ay: float = 0.0  # 가속도 y (중력)
    size: float = 5.0
    color: Tuple[int, int, int] = (255, 255, 255)
    alpha: float = 1.0
    life: float = 1.0  # 남은 수명 (0~1)
    decay: float = 0.02  # 수명 감소율
    size_decay: float = 0.0  # 크기 감소율
    rotation: float = 0.0  # 회전 각도
    rotation_speed: float = 0.0  # 회전 속도
    is_image: bool = False  # 이미지 파티클 여부
    
    def update(self):
        """파티클 상태 업데이트"""
        self.vx += self.ax
        self.vy += self.ay
        self.x += self.vx
        self.y += self.vy
        self.life -= self.decay
        self.alpha = max(0, self.life)
        self.size = max(0, self.size - self.size_decay)
        self.rotation += self.rotation_speed
        
    @property
    def is_alive(self) -> bool:
        return self.life > 0 and self.size > 0


class ParticleSystem(QWidget):
    """파티클 시스템 오버레이"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.particles: List[Particle] = []
        self.global_alpha: float = 1.0  # 전역 투명도 (0.0 ~ 1.0)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        
        # 코인 이미지 로드
        self.coin_pixmap: Optional[QPixmap] = None
        self._load_coin_image()
        
        # 업데이트 타이머 (60fps)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_particles)
        self.timer.start(16)  # ~60fps
        
        # 연속 이펙트용 타이머
        self.effect_timer = QTimer(self)
        self.effect_timer.timeout.connect(self._continuous_effect)
        self.current_effect: Optional[str] = None
    
    def _load_coin_image(self):
        """코인 이미지 로드"""
        # 현재 파일 디렉토리 기준으로 이미지 찾기
        current_dir = os.path.dirname(os.path.abspath(__file__))
        coin_path = os.path.join(current_dir, "gold_coin-Photoroom.png")
        
        if os.path.exists(coin_path):
            self.coin_pixmap = QPixmap(coin_path)
            if self.coin_pixmap.isNull():
                self.coin_pixmap = None
    
    def _update_particles(self):
        """모든 파티클 업데이트"""
        for p in self.particles:
            p.update()
        # 죽은 파티클 제거
        self.particles = [p for p in self.particles if p.is_alive]
        self.update()  # repaint
    
    def _continuous_effect(self):
        """연속 이펙트 생성"""
        if self.current_effect == "profit":
            self._emit_profit_particles()
        elif self.current_effect == "loss":
            self._emit_loss_particles()
    
    def paintEvent(self, event):
        """파티클 렌더링"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        for p in self.particles:
            final_alpha = p.alpha * self.global_alpha
            
            if p.is_image and self.coin_pixmap:
                # 이미지 파티클 렌더링
                painter.save()
                painter.setOpacity(final_alpha)
                
                # 크기에 맞게 스케일링
                size = int(p.size)
                scaled = self.coin_pixmap.scaled(
                    size, size, 
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                # 회전 적용
                painter.translate(p.x, p.y)
                painter.rotate(p.rotation)
                painter.translate(-size/2, -size/2)
                
                painter.drawPixmap(0, 0, scaled)
                painter.restore()
            else:
                # 원형 파티클 렌더링
                color = QColor(p.color[0], p.color[1], p.color[2], int(final_alpha * 255))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(color))
                painter.drawEllipse(QPointF(p.x, p.y), p.size, p.size)
    
    # ========== 트레이딩 이펙트 ==========
    
    def order_created(self, x: float = None, y: float = None):
        """주문 생성 - 펄스/리플 효과 (파란색)"""
        x = x or self.width() / 2
        y = y or self.height() / 2
        
        for i in range(20):
            angle = (i / 20) * 2 * math.pi
            speed = random.uniform(3, 6)
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                size=random.uniform(3, 6),
                color=(66, 165, 245),  # 파란색
                decay=0.03,
                size_decay=0.1
            ))
    
    def order_filled(self, x: float = None, y: float = None):
        """주문 체결 - 버스트/스파클 효과 (흰색+노란색)"""
        x = x or self.width() / 2
        y = y or self.height() / 2
        
        # 중심 폭발
        for _ in range(30):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(5, 12)
            color = random.choice([
                (255, 255, 255),  # 흰색
                (255, 235, 59),   # 노란색
                (255, 193, 7)     # 금색
            ])
            self.particles.append(Particle(
                x=x, y=y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                size=random.uniform(2, 5),
                color=color,
                decay=0.025,
                size_decay=0.05
            ))
    
    def start_profit_effect(self):
        """수익중 - 위로 올라가는 녹색 파티클 (연속)"""
        self.current_effect = "profit"
        self.effect_timer.start(50)
    
    def stop_profit_effect(self):
        """수익 이펙트 중지"""
        if self.current_effect == "profit":
            self.current_effect = None
            self.effect_timer.stop()
    
    def _emit_profit_particles(self):
        """수익 파티클 방출"""
        for _ in range(3):
            x = random.uniform(0, self.width())
            self.particles.append(Particle(
                x=x, y=self.height() + 10,
                vx=random.uniform(-0.5, 0.5),
                vy=random.uniform(-4, -2),
                size=random.uniform(3, 7),
                color=(76, 175, 80),  # 녹색
                decay=0.008,
                size_decay=0.02
            ))
    
    def start_loss_effect(self):
        """손실중 - 아래로 떨어지는 빨간 파티클 (연속)"""
        self.current_effect = "loss"
        self.effect_timer.start(50)
    
    def stop_loss_effect(self):
        """손실 이펙트 중지"""
        if self.current_effect == "loss":
            self.current_effect = None
            self.effect_timer.stop()
    
    def _emit_loss_particles(self):
        """손실 파티클 방출"""
        for _ in range(3):
            x = random.uniform(0, self.width())
            self.particles.append(Particle(
                x=x, y=-10,
                vx=random.uniform(-0.5, 0.5),
                vy=random.uniform(2, 4),
                ay=0.1,  # 중력
                size=random.uniform(3, 7),
                color=(244, 67, 54),  # 빨간색
                decay=0.008,
                size_decay=0.02
            ))
    
    def take_profit(self):
        """익절 - 🪙 골드 코인 폭발!"""
        cx, cy = self.width() / 2, self.height() / 2
        
        # 코인 이미지 파티클
        for _ in range(25):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(5, 15)
            self.particles.append(Particle(
                x=cx, y=cy,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed - 3,  # 약간 위로
                ay=0.3,  # 중력
                size=random.uniform(60, 100),  # 코인 크기 2배 (30~50 -> 60~100)
                decay=0.012,
                size_decay=0.2,
                rotation=random.uniform(0, 360),
                rotation_speed=random.uniform(-15, 15),
                is_image=True
            ))
    
    def stop_loss(self):
        """손절 - 빨간 경고 플래시 + 떨어지는 파티클"""
        # 화면 가장자리에서 빨간 파티클
        for _ in range(50):
            # 위에서 떨어짐
            x = random.uniform(0, self.width())
            self.particles.append(Particle(
                x=x, y=0,
                vx=random.uniform(-1, 1),
                vy=random.uniform(5, 10),
                ay=0.2,
                size=random.uniform(4, 10),
                color=random.choice([
                    (244, 67, 54),   # 빨간색
                    (229, 57, 53),   # 진한 빨강
                    (239, 154, 154), # 연한 빨강
                ]),
                decay=0.012,
                size_decay=0.05
            ))
        
        # 중심에서 빨간 펄스
        cx, cy = self.width() / 2, self.height() / 2
        for i in range(30):
            angle = (i / 30) * 2 * math.pi
            speed = random.uniform(8, 15)
            self.particles.append(Particle(
                x=cx, y=cy,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                size=random.uniform(5, 12),
                color=(244, 67, 54),
                decay=0.04,
                size_decay=0.15
            ))
    
    def clear_all(self):
        """모든 파티클 제거"""
        self.particles.clear()
        self.current_effect = None
        self.effect_timer.stop()
