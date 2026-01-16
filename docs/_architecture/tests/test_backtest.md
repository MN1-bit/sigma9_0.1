# test_backtest.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `tests/test_backtest.py` |
| **역할** | 백테스트 엔진 단위 테스트 |
| **라인 수** | 485 |
| **바이트** | 17,730 |

## 테스트 클래스

### `TestTrade`
> Trade 데이터클래스 테스트

| 테스트 | 설명 |
|-------|------|
| `test_trade_creation` | 객체 정상 생성 |
| `test_trade_close_profit` | 수익 청산 |
| `test_trade_close_loss` | 손실 청산 |
| `test_trade_to_dict` | 직렬화 |

### `TestBacktestReport`
> 백테스트 리포트 테스트

| 테스트 | 설명 |
|-------|------|
| `test_total_trades` | 총 거래 수 |
| `test_win_rate` | 승률 계산 |
| `test_profit_factor` | Profit Factor |
| `test_max_drawdown_calculation` | MDD 계산 |
| `test_get_summary` | 요약 생성 |

### `TestBacktestConfig`
> 설정 클래스 테스트

### `TestBacktestEngine`
> 엔진 통합 테스트

## 🔗 외부 연결 (Connections)

### Imports From (이 파일이 가져오는 것)
| 파일 | 가져오는 항목 |
|------|--------------|
| `backend/core/backtest.py` | `Trade`, `BacktestReport`, `BacktestConfig`, `BacktestEngine` |

## 외부 의존성
- `pytest`
