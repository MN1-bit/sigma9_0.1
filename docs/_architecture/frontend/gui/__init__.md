# __init__.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `frontend/gui/__init__.py` |
| **역할** | Frontend GUI 패키지 초기화 및 공개 인터페이스 정의 |
| **라인 수** | 34 |
| **바이트** | 1,198 |

---

## 패키지 개요

PyQt6 기반의 GUI 컴포넌트들을 담당하는 패키지입니다.

### 디자인 원칙
- **Glassmorphism / Acrylic Effect** 스타일
- **5-Panel 레이아웃** (Top, Left, Center, Right, Bottom)

---

## 공개 인터페이스 (Exports)

| 클래스 | 소스 파일 | 설명 |
|--------|----------|------|
| `Sigma9Dashboard` | `dashboard.py` | 메인 대시보드 윈도우 |
| `CustomWindow` | `custom_window.py` | Acrylic 프레임리스 윈도우 |
| `ParticleSystem` | `particle_effects.py` | 트레이딩 파티클 이펙트 |

---

## 🔗 외부 연결 (Connections)

### Imports From (이 파일이 가져오는 것)

| 파일 | 가져오는 항목 |
|------|--------------|
| `frontend/gui/dashboard.py` | `Sigma9Dashboard` |
| `frontend/gui/custom_window.py` | `CustomWindow` |
| `frontend/gui/particle_effects.py` | `ParticleSystem` |

### Imported By (이 파일을 가져가는 것)

| 파일 | 사용 목적 |
|------|----------|
| `frontend/main.py` | GUI 패키지 로딩 |

---

## 포함 모듈

| 모듈 | 설명 |
|------|------|
| `dashboard.py` | 메인 대시보드 윈도우 |
| `custom_window.py` | Acrylic 프레임리스 윈도우 |
| `window_effects.py` | Windows DWM API 래퍼 |
| `particle_effects.py` | 트레이딩 파티클 이펙트 |
| `chart_widget.py` | TradingView Lightweight Charts 위젯 |
| `control_panel.py` | 컨트롤 패널 |
| `theme.py` | 테마 설정 |
| `watchlist_model.py` | Watchlist 모델 |
