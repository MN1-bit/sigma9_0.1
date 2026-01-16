# test_risk_manager.py

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `tests/test_risk_manager.py` |
| **역할** | RiskManager, RiskConfig, DailyPnL 단위 테스트 |
| **라인 수** | 390 |

## 테스트 클래스

### `TestRiskConfig`
> RiskConfig 데이터클래스 테스트

| 테스트 | 설명 |
|--------|------|
| `test_default_config` | 기본 설정 확인 |
| `test_custom_config` | 커스텀 설정 |
| `test_to_dict` | to_dict() 직렬화 |

### `TestDailyPnL`
> DailyPnL 데이터클래스 테스트

| 테스트 | 설명 |
|--------|------|
| `test_daily_pnl_creation` | 생성 테스트 |
| `test_total_pnl` | total_pnl 계산 (realized + unrealized) |

### `TestRiskManager`
> RiskManager 클래스 테스트

| 테스트 | 설명 |
|--------|------|
| `test_initialization` | 초기화 테스트 |
| `test_set_starting_balance` | 시작 잔고 설정 |

### `TestPositionSizing`
> 포지션 사이징 테스트

| 테스트 | 설명 |
|--------|------|
| `test_fixed_position_size` | 고정비율 (10%) 테스트 |
| `test_position_size_with_low_balance` | 잔고 대비 가격 높음 |
| `test_position_size_zero_price` | 가격 0 시 |
| `test_position_size_zero_balance` | 잔고 0 시 |

### `TestLossLimits`
> 손실 한도 테스트

| 테스트 | 설명 |
|--------|------|
| `test_daily_pnl_calculation` | 일일 손익률 계산 |
| `test_daily_limit_not_reached` | 한도 미도달 |
| `test_daily_limit_reached` | 한도 도달 |

### `TestTradingAllowed`
> 거래 가능 여부 테스트

| 테스트 | 설명 |
|--------|------|
| `test_trading_allowed_normal` | 정상 상태 |
| `test_trading_not_allowed_after_kill` | Kill 후 |
| `test_trading_allowed_after_reset` | Reset 후 |
| `test_trading_disabled_manually` | 수동 비활성화 |

### `TestKillSwitch`
> Kill Switch 테스트

| 테스트 | 설명 |
|--------|------|
| `test_kill_switch_execution` | 실행 테스트 |
| `test_kill_switch_without_connector` | Connector 없이 |
| `test_kill_switch_status` | 상태 확인 |

### `TestTradeRecording`
> 거래 기록 테스트

| 테스트 | 설명 |
|--------|------|
| `test_record_trade` | 거래 기록 추가 |

### `TestKellyCriterion`
> Kelly Criterion 테스트

| 테스트 | 설명 |
|--------|------|
| `test_kelly_with_insufficient_trades` | 거래 부족 시 기본 비율 |
| `test_kelly_calculation` | Kelly 계산 |

## 🔗 외부 연결 (Connections)

### Tests (테스트 대상)
| 파일 | 테스트 항목 |
|------|------------|
| `backend/core/risk_manager.py` | `RiskManager`, `DailyPnL` |
| `backend/core/risk_config.py` | `RiskConfig` |

## 외부 의존성
- `pytest`
- `unittest.mock`
