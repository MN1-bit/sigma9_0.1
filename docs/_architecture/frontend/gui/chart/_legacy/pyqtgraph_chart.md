# _legacy/pyqtgraph_chart.py

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `frontend/gui/chart/_legacy/pyqtgraph_chart.py` |
| **역할** | PyQtGraph 기반 트레이딩 차트 위젯 (레거시) |
| **라인 수** | 1,192 |
| **상태** | ⚠️ 레거시 - finplot_chart.py로 교체됨 |

## 클래스

### `IndexDateAxis(pg.AxisItem)`
> 인덱스 기반 날짜 X축 (Gap 제거용)

| 메서드 | 설명 |
|--------|------|
| `update_ticks` | 타임스탬프 매핑 업데이트 |
| `tickStrings` | 인덱스를 MM-DD 문자열로 변환 |

---

### `PyQtGraphChartWidget(QWidget)`
> PyQtGraph 기반 트레이딩 차트

#### Features
- 캔들스틱 + Volume 서브차트
- VWAP/MA/ATR 밴드 인디케이터
- 트레이드 마커 (매수/매도/Ignition)
- 마우스 줌/팬 + 툴팁

#### Signals
| Signal | 타입 | 설명 |
|--------|------|------|
| `timeframe_changed` | `pyqtSignal(str)` | 타임프레임 변경 |
| `viewport_data_needed` | `pyqtSignal(int, int)` | 추가 데이터 필요 |

#### 주요 메서드
| 메서드 | 시그니처 | 설명 |
|--------|----------|------|
| `set_candlestick_data` | `(candles: List[Dict])` | 캔들스틱 데이터 설정 |
| `set_volume_data` | `(volume_data)` | Volume 바 설정 |
| `set_vwap_data` | `(vwap_data)` | VWAP 라인 설정 |
| `set_ma_data` | `(ma_data, period, color)` | MA 라인 설정 |
| `set_atr_bands` | `(upper, lower)` | ATR 밴드 설정 |

## 🔗 외부 연결 (Connections)

### Imports From
| 파일 | 가져오는 항목 |
|------|--------------|
| `_legacy/candlestick_item.py` | `CandlestickItem` |
| `frontend/gui/theme.py` | `theme` |

### Imported By
| 파일 | 사용 목적 |
|------|----------|
| (레거시 - 현재 미사용) | - |

## 외부 의존성
- `pyqtgraph`
- `numpy`
- `PyQt6`
