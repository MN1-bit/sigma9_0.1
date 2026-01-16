# particle_effects.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `frontend/gui/particle_effects.py` |
| **역할** | 퀀트 트레이딩 봇용 파티클 이펙트 시스템 |
| **라인 수** | 841 |
| **바이트** | 29,140 |

---

## 클래스

### `Particle` (dataclass)

> 개별 파티클 데이터

| 필드 | 타입 | 설명 |
|------|------|------|
| `x`, `y` | `float` | 위치 |
| `vx`, `vy` | `float` | 속도 |
| `ax`, `ay` | `float` | 가속도 |
| `size` | `float` | 크기 |
| `color` | `Tuple[int,int,int]` | RGB 색상 |
| `alpha` | `float` | 투명도 |
| `life` | `float` | 생명력 |
| `decay` | `float` | 감쇠율 |
| `char` | `str` | 텍스트 파티클용 문자 |

---

### `BackgroundEffect` (ABC)

> 배경 이펙트 추상 베이스 클래스

| 메서드 | 설명 |
|--------|------|
| `resize(w, h)` | 크기 변경 |
| `update_mouse(x, y)` | 마우스 위치 업데이트 |
| `update()` | 파티클 상태 업데이트 (추상) |
| `draw(painter)` | 렌더링 (추상) |

---

### 이펙트 클래스 (BackgroundEffect 상속)

| 클래스 | 설명 |
|--------|------|
| `ConstellationEffect` | 점들이 느리게 부유하며 연결 |
| `DigitalDustEffect` | 금색/은색 미세 입자 부유 |
| `BokehEffect` | 부드러운 빛망울 흐름 |
| `VectorFieldEffect` | 벡터장을 따라 흐르는 입자 |
| `MatrixRainEffect` | 매트릭스 코드 레인 |
| `NeuralNetworkEffect` | 노드 + 연결선 효과 |
| `FireworksEffect` | 불꽃놀이 폭발 |
| `HeartbeatEffect` | 심박수/파동 효과 |

---

### `ParticleSystem(QWidget)`

> 파티클 시스템 오버레이 위젯

#### 주요 메서드

| 메서드 | 설명 |
|--------|------|
| `__init__(parent, effect_name)` | 초기화 |
| `set_effect(effect_name)` | 이펙트 변경 |
| `start()` / `stop()` | 애니메이션 시작/정지 |
| `trigger_fireworks(x, y)` | 불꽃놀이 트리거 |
| `paintEvent(event)` | QPainter로 렌더링 |

#### 사용 가능 이펙트

| 이름 | 설명 |
|------|------|
| `constellation` | 별자리 효과 |
| `digital_dust` | 디지털 먼지 |
| `bokeh` | 보케 흐름 |
| `vector_field` | 벡터 필드 |
| `matrix` | 매트릭스 레인 |
| `neural` | 뉴럴 네트워크 |
| `fireworks` | 불꽃놀이 |
| `heartbeat` | 심박수 |

---

## 🔗 외부 연결 (Connections)

### Imports From

| 파일/모듈 | 가져오는 항목 |
|----------|--------------|
| `PyQt6.QtCore` | `Qt`, `QTimer`, `QPointF` |
| `PyQt6.QtGui` | `QPainter`, `QColor`, `QRadialGradient`, `QPixmap` |

### Imported By

| 파일 | 사용 목적 |
|------|----------|
| `frontend/gui/__init__.py` | 패키지 export |
| `frontend/gui/dashboard.py` | 대시보드 배경 효과 |

---

## 외부 의존성

- `PyQt6` / `PySide6`
- `random`, `math` (파티클 물리)
