# _legacy/candlestick_item.py

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `frontend/gui/chart/_legacy/candlestick_item.py` |
| **역할** | PyQtGraph용 캔들스틱 그래픽 아이템 (레거시) |
| **라인 수** | 269 |
| **상태** | ⚠️ 레거시 - finplot으로 교체됨 |

## 클래스

### `CandlestickItem(pg.GraphicsObject)`
> PyQtGraph 캔들스틱 차트 아이템

#### 주요 메서드
| 메서드 | 시그니처 | 설명 |
|--------|----------|------|
| `setData` | `(data: List[Tuple])` | OHLC 데이터 설정 |
| `update_bar` | `(index, open_, high, low, close)` | 마지막 캔들 업데이트 |
| `add_bar` | `(index, open_, high, low, close)` | 새 캔들 추가 |
| `_generatePicture` | `()` | QPicture에 미리 렌더링 |
| `paint` | `(p: QPainter, *args)` | 화면 렌더링 |
| `boundingRect` | `() -> QRectF` | 경계 영역 반환 |

## 🔗 외부 연결 (Connections)

### Imports From
| 파일/모듈 | 가져오는 항목 |
|----------|--------------|
| `pyqtgraph` | `pg.GraphicsObject` |
| `PyQt6.QtGui` | `QPainter`, `QPicture` |

### Imported By
| 파일 | 사용 목적 |
|------|----------|
| `_legacy/pyqtgraph_chart.py` | 캔들스틱 렌더링 |

## 외부 의존성
- `pyqtgraph`
- `PyQt6`
