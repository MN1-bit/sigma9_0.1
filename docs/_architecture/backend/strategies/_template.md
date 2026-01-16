# _template.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `backend/strategies/_template.py` |
| **역할** | 새 전략 개발용 템플릿 - StrategyBase 상속 클래스 보일러플레이트 |
| **라인 수** | 195 |
| **바이트** | 8,664 |

> ⚠️ 파일명이 `_`로 시작하므로 StrategyLoader가 무시함 (템플릿 전용)

## 클래스

### `TemplateStrategy(StrategyBase)`
> 전략 템플릿 클래스 - 복사하여 새 전략 구현

#### 메타정보
| 속성 | 값 | 설명 |
|------|---|------|
| `name` | `"Template Strategy"` | GUI 표시용 |
| `version` | `"1.0.0"` | 버전 |
| `description` | `"새 전략 개발 템플릿"` | 설명 |

#### Scanning Layer 메서드
| 메서드 | 시그니처 | 설명 |
|--------|----------|------|
| `get_universe_filter` | `() -> dict` | Universe 필터 조건 (가격, 시총, 거래량) |
| `calculate_watchlist_score` | `(ticker, daily_data) -> float` | 일봉 기반 Watchlist 점수 (0~100) |
| `calculate_trigger_score` | `(ticker, tick_data, bar_data) -> float` | 실시간 Trigger 점수 (0~100) |
| `get_anti_trap_filter` | `() -> dict` | Anti-Trap 필터 조건 |

#### Trading Layer 메서드
| 메서드 | 시그니처 | 설명 |
|--------|----------|------|
| `initialize` | `() -> None` | 전략 초기화 (로드 시 1회) |
| `on_tick` | `(ticker, price, volume, timestamp) -> Signal?` | 틱 처리 → Signal |
| `on_bar` | `(ticker, ohlcv) -> Signal?` | 분봉/일봉 처리 → Signal |
| `on_order_filled` | `(order) -> None` | 주문 체결 콜백 |

#### Configuration Layer 메서드
| 메서드 | 시그니처 | 설명 |
|--------|----------|------|
| `get_config` | `() -> dict` | 전략 설정값 반환 (GUI 표시용) |
| `set_config` | `(config) -> None` | 전략 설정값 변경 (런타임) |

## 🔗 외부 연결 (Connections)

### Imports From (이 파일이 가져오는 것)
| 파일 | 가져오는 항목 |
|------|--------------|
| `backend/core/strategy_base.py` | `StrategyBase`, `Signal` |

### Imported By (이 파일을 가져가는 것)
| 파일 | 사용 목적 |
|------|----------|
| (없음) | 템플릿 파일 - 복사하여 사용 |

## 사용법

```bash
# 1. 템플릿 복사
cp _template.py my_strategy.py

# 2. 클래스명/메타정보 수정
# 3. 모든 abstractmethod 구현
# 4. GUI에서 전략 선택!
```

## 외부 의존성
- (없음 - backend 내부 모듈만 사용)
