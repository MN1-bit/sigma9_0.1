# chart/__init__.py

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `frontend/gui/chart/__init__.py` |
| **역할** | Chart 모듈 패키지 초기화 및 공개 인터페이스 |
| **라인 수** | 8 |

## 공개 인터페이스 (Exports)

| 클래스 | 소스 파일 | 설명 |
|--------|----------|------|
| `ChartDataManager` | `chart_data_manager.py` | 2-Tier 캐시 데이터 로딩 관리자 |
| `FinplotChartWidget` | `finplot_chart.py` | finplot 기반 트레이딩 차트 위젯 |

## 🔗 외부 연결 (Connections)

### Imports From
| 파일 | 가져오는 항목 |
|------|--------------|
| `frontend/gui/chart/chart_data_manager.py` | `ChartDataManager` |
| `frontend/gui/chart/finplot_chart.py` | `FinplotChartWidget` |

### Imported By
| 파일 | 사용 목적 |
|------|----------|
| `frontend/gui/panels/chart_panel.py` | 차트 위젯 사용 |
