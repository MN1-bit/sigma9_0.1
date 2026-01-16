# Frontend GUI Overview

> 📍 **Location**: `frontend/gui/`  
> **Role**: PyQt6 GUI 컴포넌트 - 대시보드, 패널, 차트, 위젯

---

## 구조

```
gui/
├── __init__.py
├── dashboard.py          # 메인 대시보드 (99KB!)
├── chart_widget.py       # 차트 위젯
├── control_panel.py      # 컨트롤 패널
├── custom_window.py      # 커스텀 윈도우
├── particle_effects.py   # 파티클 효과
├── settings_dialog.py    # 설정 다이얼로그
├── theme.py              # 테마 설정
├── ticker_info_window.py # 티커 정보 윈도우
├── watchlist_model.py    # 워치리스트 모델
├── window_effects.py     # 윈도우 효과
│
├── panels/               # UI 패널
├── chart/                # 차트 모듈
├── state/                # 상태 관리
├── widgets/              # 재사용 위젯
└── assets/               # 에셋 파일
```

---

## 메인 파일 목록

| 파일 | 역할 |
|------|------|
| [dashboard.py](./dashboard.md) | 메인 대시보드 |
| [chart_widget.py](./chart_widget.md) | 차트 위젯 |
| [control_panel.py](./control_panel.md) | 컨트롤 패널 |
| [custom_window.py](./custom_window.md) | 커스텀 윈도우 |
| [particle_effects.py](./particle_effects.md) | 파티클 효과 |
| [settings_dialog.py](./settings_dialog.md) | 설정 다이얼로그 |
| [theme.py](./theme.md) | 테마 설정 |
| [ticker_info_window.py](./ticker_info_window.md) | 티커 정보 윈도우 |
| [watchlist_model.py](./watchlist_model.md) | 워치리스트 모델 |
| [window_effects.py](./window_effects.md) | 윈도우 효과 |

---

## 하위 모듈

| 모듈 | 설명 |
|------|------|
| [panels/](./panels/_overview.md) | UI 패널 (7 files) |
| [chart/](./chart/_overview.md) | 차트 모듈 |
| [state/](./state/_overview.md) | 상태 관리 |
