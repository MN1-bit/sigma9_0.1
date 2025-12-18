"""
Trading Particle Effects System
퀀트 트레이딩 봇용 파티클 이펙트 시스템
"""
import random
import math
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple, Optional

try:
    from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
    from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QPixmap, QPainterPath
    from PyQt6.QtWidgets import QWidget
except ModuleNotFoundError:
    from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
    from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QPixmap, QPainterPath
    from PySide6.QtWidgets import QWidget


@dataclass
class Particle:
    """개별 파티클"""
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    ax: float = 0.0
    ay: float = 0.0
    size: float = 5.0
    color: Tuple[int, int, int] = (255, 255, 255)
    alpha: float = 1.0
    life: float = 1.0
    decay: float = 0.02
    size_decay: float = 0.0
    rotation: float = 0.0
    rotation_speed: float = 0.0
    is_image: bool = False
    # Background effect specific
    target_x: float = 0.0
    target_y: float = 0.0
    original_x: float = 0.0
    original_y: float = 0.0
    phase: float = 0.0
    char: str = "" # Matrix Rain용

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


class BackgroundEffect(ABC):
    """배경 이펙트 전략 클래스 (Abstract Base Class)"""
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.particles: List[Particle] = []
        self.mouse_x = 0
        self.mouse_y = 0

    def resize(self, w: int, h: int):
        self.width = w
        self.height = h

    def update_mouse(self, x: int, y: int):
        self.mouse_x = x
        self.mouse_y = y

    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def draw(self, painter: QPainter):
        pass


class ConstellationEffect(BackgroundEffect):
    """Constellation: 점들이 느리게 부유하며 연결"""
    def __init__(self, w, h):
        super().__init__(w, h)
        self._init_particles()

    def _init_particles(self):
        count = int((self.width * self.height) / 15000) # 밀도 조절
        count = min(count, 150) # 최대 개수 제한
        for _ in range(count):
            self.particles.append(Particle(
                x=random.uniform(0, self.width),
                y=random.uniform(0, self.height),
                vx=random.uniform(-0.5, 0.5),
                vy=random.uniform(-0.5, 0.5),
                size=random.uniform(2, 4),
                color=(100, 181, 246), # Light Blue
                life=random.uniform(0.5, 1.0),
                decay=0.0
            ))

    def update(self):
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            
            # 화면 경계 반사
            if p.x < 0 or p.x > self.width: p.vx *= -1
            if p.y < 0 or p.y > self.height: p.vy *= -1
            
            # 마우스 반응 (약한 반발력)
            dx = self.mouse_x - p.x
            dy = self.mouse_y - p.y
            dist = math.hypot(dx, dy)
            if dist < 150:
                force = (150 - dist) / 150 * 0.5
                p.x -= (dx/dist) * force
                p.y -= (dy/dist) * force

    def draw(self, painter: QPainter):
        # Draw Nodes
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self.particles:
            painter.setBrush(QColor(p.color[0], p.color[1], p.color[2], int(150 * p.life)))
            painter.drawEllipse(QPointF(p.x, p.y), p.size/2, p.size/2)

        # Draw Lines
        painter.setPen(QPen(QColor(100, 181, 246, 30), 1))
        for i, p1 in enumerate(self.particles):
            for p2 in self.particles[i+1:]:
                dist = math.hypot(p1.x - p2.x, p1.y - p2.y)
                if dist < 120:
                    alpha = int((120 - dist) / 120 * 60)
                    painter.setPen(QPen(QColor(100, 181, 246, alpha), 1))
                    painter.drawLine(QPointF(p1.x, p1.y), QPointF(p2.x, p2.y))


class DigitalDustEffect(BackgroundEffect):
    """Digital Dust: 금색/은색 미세 입자가 부유"""
    def __init__(self, w, h):
        super().__init__(w, h)
        self._init_particles()

    def _init_particles(self):
        for _ in range(100):
            color = (255, 215, 0) if random.random() > 0.5 else (192, 192, 192) # Gold or Silver
            self.particles.append(Particle(
                x=random.uniform(0, self.width),
                y=random.uniform(0, self.height),
                vx=random.uniform(-0.2, 0.2),
                vy=random.uniform(-0.2, 0.2),
                size=random.uniform(1, 2),
                color=color,
                life=random.uniform(0.0, 1.0),
                decay=random.uniform(0.005, 0.01) # 깜빡임 효과를 위해 수명 감소 -> 재생성
            ))

    def update(self):
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            p.life -= p.decay
            
            if p.life <= 0 or p.x < 0 or p.x > self.width or p.y < 0 or p.y > self.height:
                # Reset
                p.x = random.uniform(0, self.width)
                p.y = random.uniform(0, self.height)
                p.life = 1.0
                p.size = random.uniform(1, 2)

    def draw(self, painter: QPainter):
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self.particles:
            # Twinkle effect: sin wave based on life
            alpha = int(abs(math.sin(p.life * math.pi)) * 200)
            painter.setBrush(QColor(p.color[0], p.color[1], p.color[2], alpha))
            painter.drawEllipse(QPointF(p.x, p.y), p.size, p.size)


class BokehEffect(BackgroundEffect):
    """Bokeh Flow: 부드러운 빛망울이 흐름"""
    def __init__(self, w, h):
        super().__init__(w, h)
        self._init_particles()

    def _init_particles(self):
        for _ in range(20):
            self.particles.append(Particle(
                x=random.uniform(0, self.width),
                y=random.uniform(0, self.height),
                vx=random.uniform(0.1, 0.5), # 오른쪽으로 천천히
                vy=random.uniform(-0.1, 0.1),
                size=random.uniform(20, 60),
                color=(144, 202, 249),
                life=random.uniform(0.2, 0.8),
                decay=0.0
            ))

    def update(self):
        for p in self.particles:
            p.x += p.vx
            p.y += p.vy
            
            # Loop around
            if p.x > self.width + 100: p.x = -100
            if p.y > self.height + 100: p.y = -100
            if p.y < -100: p.y = self.height + 100

    def draw(self, painter: QPainter):
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self.particles:
            alpha = int(40 * p.life)
            grad = QRadialGradient(p.x, p.y, p.size)
            c = QColor(p.color[0], p.color[1], p.color[2], alpha)
            grad.setColorAt(0, c)
            grad.setColorAt(1, QColor(0,0,0,0))
            painter.setBrush(QBrush(grad))
            painter.drawEllipse(QPointF(p.x, p.y), p.size, p.size)


class VectorFieldEffect(BackgroundEffect):
    """Vector Field: 벡터장을 따라 흐르는 입자 (Perlin Noise 대용)"""
    def __init__(self, w, h):
        super().__init__(w, h)
        self.rows = 20
        self.cols = 20
        self._init_particles()

    def _init_particles(self):
        for _ in range(300):
            self.particles.append(Particle(
                x=random.uniform(0, self.width),
                y=random.uniform(0, self.height),
                size=random.uniform(1, 2),
                color=(179, 136, 255), # Deep Purple
                life=random.uniform(0.5, 1.0),
                decay=0.0
            ))

    def update(self):
        for p in self.particles:
            # Simple vector field function: sin(x) * cos(y)
            angle = math.sin(p.x * 0.005) + math.cos(p.y * 0.005)
            speed = 2
            p.vx = math.cos(angle) * speed
            p.vy = math.sin(angle) * speed
            
            p.x += p.vx
            p.y += p.vy
            
            if p.x < 0: p.x = self.width
            if p.x > self.width: p.x = 0
            if p.y < 0: p.y = self.height
            if p.y > self.height: p.y = 0

    def draw(self, painter: QPainter):
        painter.setPen(Qt.PenStyle.NoPen)
        for p in self.particles:
            painter.setBrush(QColor(p.color[0], p.color[1], p.color[2], 150))
            painter.drawEllipse(QPointF(p.x, p.y), p.size, p.size)


class MatrixRainEffect(BackgroundEffect):
    """Matrix Rain: 미니멀리스트 디지털 레인"""
    def __init__(self, w, h):
        super().__init__(w, h)
        self.chars = "01"
        self._init_particles()

    def _init_particles(self):
        cols = int(self.width / 20)
        for i in range(cols):
            self.particles.append(Particle(
                x=i * 20,
                y=random.uniform(-self.height, 0),
                vy=random.uniform(2, 5),
                size=12,
                color=(0, 255, 70),
                life=1.0,
                decay=0.0,
                char=random.choice(self.chars)
            ))

    def update(self):
        for p in self.particles:
            p.y += p.vy
            if p.y > self.height:
                p.y = random.uniform(-100, 0)
                p.char = random.choice(self.chars)
            
            if random.random() < 0.05:
                p.char = random.choice(self.chars)

    def draw(self, painter: QPainter):
        painter.setPen(QColor(0, 255, 70, 150))
        font = painter.font()
        font.setFamily("Consolas")
        font.setPixelSize(12)
        painter.setFont(font)
        
        for p in self.particles:
            painter.drawText(int(p.x), int(p.y), p.char)


class ParticleSystem(QWidget):
    """파티클 시스템 오버레이"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_particles: List[Particle] = [] # Trading particles (Explosions etc)
        self.background_effect: Optional[BackgroundEffect] = None
        self.background_effect_name: str = "constellation" # Default
        
        self.global_alpha: float = 1.0
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setStyleSheet("background: transparent;")
        
        # 코인 이미지 로드
        self.coin_pixmap: Optional[QPixmap] = None
        self._load_coin_image()
        
        # 업데이트 타이머 (60fps)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_all)
        self.timer.start(16)
        
        # 연속 이펙트용
        self.effect_timer = QTimer(self)
        self.effect_timer.timeout.connect(self._continuous_effect)
        self.current_trading_effect: Optional[str] = None
        
        # 초기 배경 이펙트 설정
        self.set_background_effect("constellation")

    def _load_coin_image(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        coin_path = os.path.join(current_dir, "assets", "gold_coin.png")
        if os.path.exists(coin_path):
            self.coin_pixmap = QPixmap(coin_path)

    def set_background_effect(self, name: str):
        """배경 이펙트 변경"""
        self.background_effect_name = name.lower()
        w, h = self.width(), self.height()
        if w <= 0: w, h = 1920, 1080 # Fallback
        
        if name == "constellation":
            self.background_effect = ConstellationEffect(w, h)
        elif name == "digital dust":
            self.background_effect = DigitalDustEffect(w, h)
        elif name == "bokeh":
            self.background_effect = BokehEffect(w, h)
        elif name == "vector field":
            self.background_effect = VectorFieldEffect(w, h)
        elif name == "matrix rain":
            self.background_effect = MatrixRainEffect(w, h)
        else: # None
            self.background_effect = None

    def resizeEvent(self, event):
        if self.background_effect:
            self.background_effect.resize(self.width(), self.height())
        super().resizeEvent(event)

    def _update_all(self):
        # 1. Update Background
        if self.background_effect:
            # Mouse pos mapping (Optional, need to hook events from parent if generic)
            # For now just update animation
            self.background_effect.update()
            
        # 2. Update Active Trading Particles
        for p in self.active_particles:
            p.update()
        self.active_particles = [p for p in self.active_particles if p.is_alive]
        
        self.update()

    def _continuous_effect(self):
        if self.current_trading_effect == "profit":
            self._emit_profit_particles()
        elif self.current_trading_effect == "loss":
            self._emit_loss_particles()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # 1. Draw Background
        if self.background_effect:
            painter.save()
            # Background opacity scaling (optional)
            painter.setOpacity(0.6 * self.global_alpha) 
            self.background_effect.draw(painter)
            painter.restore()
            
        # 2. Draw Trading Particles
        for p in self.active_particles:
            final_alpha = p.alpha * self.global_alpha
            
            if p.is_image and self.coin_pixmap:
                painter.save()
                painter.setOpacity(final_alpha)
                size = int(p.size)
                scaled = self.coin_pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                painter.translate(p.x, p.y)
                painter.rotate(p.rotation)
                painter.translate(-size/2, -size/2)
                painter.drawPixmap(0, 0, scaled)
                painter.restore()
            else:
                color = QColor(p.color[0], p.color[1], p.color[2], int(final_alpha * 255))
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(p.x, p.y), p.size, p.size)

    # ========== Trading Events (Existing) ==========
    def order_created(self, x=None, y=None):
        x = x or self.width() / 2
        y = y or self.height() / 2
        for i in range(20):
            angle = (i / 20) * 2 * math.pi
            speed = random.uniform(3, 6)
            self.active_particles.append(Particle(
                x=x, y=y, vx=math.cos(angle)*speed, vy=math.sin(angle)*speed,
                size=random.uniform(3,6), color=(66,165,245), decay=0.03, size_decay=0.1
            ))
            
    def order_filled(self, x=None, y=None):
        x = x or self.width() / 2
        y = y or self.height() / 2
        for _ in range(30):
            angle = random.uniform(0, 2*math.pi)
            speed = random.uniform(5, 12)
            color = random.choice([(255,255,255), (255,235,59), (255,193,7)])
            self.active_particles.append(Particle(
                x=x, y=y, vx=math.cos(angle)*speed, vy=math.sin(angle)*speed,
                size=random.uniform(2,5), color=color, decay=0.025, size_decay=0.05
            ))
            
    def start_profit_effect(self):
        self.current_trading_effect = "profit"
        self.effect_timer.start(50)
        
    def stop_profit_effect(self):
        if self.current_trading_effect == "profit":
            self.current_trading_effect = None
            self.effect_timer.stop()
            
    def _emit_profit_particles(self):
        for _ in range(3):
            x = random.uniform(0, self.width())
            self.active_particles.append(Particle(
                x=x, y=self.height()+10, vx=random.uniform(-0.5,0.5), vy=random.uniform(-4,-2),
                size=random.uniform(3,7), color=(76,175,80), decay=0.008, size_decay=0.02
            ))
            
    def start_loss_effect(self):
        self.current_trading_effect = "loss"
        self.effect_timer.start(50)
        
    def stop_loss_effect(self):
        if self.current_trading_effect == "loss":
            self.current_trading_effect = None
            self.effect_timer.stop()
            
    def _emit_loss_particles(self):
        for _ in range(3):
            x = random.uniform(0, self.width())
            self.active_particles.append(Particle(
                x=x, y=-10, vx=random.uniform(-0.5,0.5), vy=random.uniform(2,4), ay=0.1,
                size=random.uniform(3,7), color=(244,67,54), decay=0.008, size_decay=0.02
            ))
            
    def take_profit(self):
        cx, cy = self.width()/2, self.height()/2
        for _ in range(25):
            angle = random.uniform(0, 2*math.pi)
            speed = random.uniform(5, 15)
            self.active_particles.append(Particle(
                x=cx, y=cy, vx=math.cos(angle)*speed, vy=math.sin(angle)*speed-3, ay=0.3,
                size=random.uniform(60,100), decay=0.012, size_decay=0.2,
                rotation=random.uniform(0,360), rotation_speed=random.uniform(-15,15), is_image=True
            ))
            
    def stop_loss(self):
        for _ in range(50):
            x = random.uniform(0, self.width())
            self.active_particles.append(Particle(
                x=x, y=0, vx=random.uniform(-1,1), vy=random.uniform(5,10), ay=0.2,
                size=random.uniform(4,10), color=random.choice([(244,67,54), (229,57,53), (239,154,154)]),
                decay=0.012, size_decay=0.05
            ))
            
    def clear_all(self):
        self.active_particles.clear()
        self.current_trading_effect = None
        self.effect_timer.stop()
