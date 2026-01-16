# widgets/__init__.py

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `frontend/gui/widgets/__init__.py` |
| **역할** | Widgets 패키지 초기화 및 공개 인터페이스 |
| **라인 수** | 20 |

## 패키지 개요

재사용 가능한 GUI 위젯 컴포넌트를 제공합니다.

## 공개 인터페이스 (Exports)

| 클래스 | 소스 파일 | 설명 |
|--------|----------|------|
| `TimeDisplayWidget` | `time_display_widget.py` | 미국/한국 시간 + 레이턴시 표시 |

## 🔗 외부 연결 (Connections)

### Imports From
| 파일 | 가져오는 항목 |
|------|--------------|
| `frontend/gui/widgets/time_display_widget.py` | `TimeDisplayWidget` |

### Imported By
| 파일 | 사용 목적 |
|------|----------|
| `frontend/gui/control_panel.py` | 시간 표시 위젯 |

## 구조
```
widgets/
├── __init__.py              # 이 파일
├── ticker_search_bar.py     # 티커 검색 위젯
└── time_display_widget.py   # 시간 표시 위젯
```
