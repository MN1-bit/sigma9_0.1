# 📅 Step 1.3: GUI Dashboard Skeleton - 개발 계획서

> **작성일**: 2024-12-18  
> **목표**: PyQt6 기반 GUI 대시보드 골격을 구축하고 5-panel 레이아웃을 구현한다.

---

## 1. 개요 (Overview)

이 스텝은 Sigma9 GUI 대시보드의 **골격**을 구축하는 단계입니다.

**접근 방식**: 
- `docs/references/GUI-demo/` 폴더의 **검증된 데모 코드**를 활용
- 해당 코드는 현재 환경에서 테스트 완료된 상태
- 필요한 부분만 수정하여 frontend/ 폴더에 통합

**왜 이 접근 방식?**
- 이미 작동하는 Acrylic/Glassmorphism 효과
- 파티클 이펙트 시스템 포함
- Frameless 윈도우 + 커스텀 타이틀바 구현 완료

---

## 2. 파일 복사 및 수정 계획

### 2.1 직접 복사 (수정 없음)

| 원본 | 대상 | 설명 |
|------|------|------|
| `GUI-demo/custom_window.py` | `frontend/gui/custom_window.py` | Acrylic 프레임리스 윈도우 |
| `GUI-demo/window_effects.py` | `frontend/gui/window_effects.py` | Windows DWM API 래퍼 |
| `GUI-demo/particle_effects.py` | `frontend/gui/particle_effects.py` | 트레이딩 파티클 이펙트 |
| `GUI-demo/gold_coin-Photoroom.png` | `frontend/gui/assets/gold_coin.png` | 익절 이펙트 이미지 |

### 2.2 Rename + 수정

| 원본 | 대상 | 수정 내용 |
|------|------|-----------|
| `GUI-demo/demo.py` | `frontend/gui/dashboard.py` | 클래스명 변경, 5-panel 레이아웃 추가 |

### 2.3 업데이트

| 파일 | 수정 내용 |
|------|-----------|
| `frontend/main.py` | 실제 QApplication 실행 코드 활성화 |
| `frontend/gui/__init__.py` | export 추가 |

---

## 3. 상세 구현 계획

### 3.1 dashboard.py 수정 사항

**클래스 변경:**
```python
# AS-IS
class AcrylicDashboard(CustomWindow):

# TO-BE
class Sigma9Dashboard(CustomWindow):
```

**5-Panel 레이아웃 구조:**
```
┌─────────────────────────────────────────────────────────────┐
│                      TOP PANEL (Control)                     │
│  [🔌 Connect]  [🚀 Start]  [🔴 Stop]  [⚡ Kill Switch]      │
├──────────┬─────────────────────────────────┬────────────────┤
│  LEFT    │          CENTER                  │     RIGHT      │
│ PANEL    │          PANEL                   │     PANEL      │
│          │                                  │                │
│ Watchlist│     TradingView Chart           │  Positions     │
│   50     │     (Placeholder/WebView)        │    P&L         │
│          │                                  │                │
│          │                                  │                │
├──────────┴─────────────────────────────────┴────────────────┤
│                     BOTTOM PANEL (Log)                       │
│  [실시간 로그 콘솔]                                          │
└─────────────────────────────────────────────────────────────┘
```

**추가 위젯:**
- `TopControlPanel`: 연결/시작/정지/Kill Switch 버튼
- `WatchlistPanel`: 왼쪽 종목 리스트 (placeholder)
- `ChartPanel`: 중앙 차트 영역 (QWebEngineView stub)
- `PositionPanel`: 오른쪽 포지션/P&L (placeholder)
- `LogPanel`: 하단 로그 콘솔

### 3.2 main.py 활성화

```python
import sys
import os
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from gui.dashboard import Sigma9Dashboard

def main():
    if hasattr(Qt, 'HighDpiScaleFactorRoundingPolicy'):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    app = QApplication(sys.argv)
    window = Sigma9Dashboard()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

---

## 4. 검증 계획 (Verification Plan)

### Automated Tests

```powershell
# 프로젝트 루트: d:\Codes\Sigma9-0.1

# 1. Python 문법 검사
python -m py_compile frontend/gui/dashboard.py
python -m py_compile frontend/gui/custom_window.py
python -m py_compile frontend/main.py

# 2. GUI 실행 테스트 (수동)
python frontend/main.py
```

### Manual Verification

1. **윈도우 표시**: Acrylic 효과 적용된 윈도우가 나타나는지
2. **5-Panel 레이아웃**: 5개 영역이 올바르게 분할되는지
3. **타이틀바**: 최소화/최대화/닫기 버튼 동작
4. **리사이즈**: 윈도우 크기 조절 가능한지

---

## 5. 실행 순서 (Execution Order)

1. `frontend/gui/assets/` 폴더 생성
2. GUI-demo 파일들 복사 (4개 파일)
3. `dashboard.py` 생성 (demo.py 기반 + 5-panel 레이아웃)
4. `frontend/gui/__init__.py` 업데이트
5. `frontend/main.py` 활성화
6. 문법 검사 및 실행 테스트
7. devlog 작성

---

## 6. 참고 파일

- [GUI-demo README](file:///d:/Codes/Sigma9-0.1/docs/references/GUI-demo/README.md)
- [masterplan.md 7절 - GUI Dashboard](file:///d:/Codes/Sigma9-0.1/docs/Plan/masterplan.md)
