# ============================================================================
# Risk Manager Tests - 리스크 관리 테스트
# ============================================================================
# 📌 실행 방법:
#   pytest tests/test_risk_manager.py -v
# ============================================================================

"""
Risk Manager Tests
"""

import sys
from pathlib import Path
from datetime import date
from unittest.mock import MagicMock

import pytest

# backend 경로 추가
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from core.risk_config import RiskConfig
from core.risk_manager import RiskManager, DailyPnL


# ═══════════════════════════════════════════════════════════════════════════
# RiskConfig 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestRiskConfig:
    """RiskConfig 데이터클래스 테스트"""

    def test_default_config(self):
        """기본 설정 테스트"""
        config = RiskConfig()

        assert config.max_position_pct == 10.0
        assert config.max_positions == 3
        assert config.daily_loss_limit_pct == -3.0
        assert config.weekly_loss_limit_pct == -10.0
        assert config.max_daily_trades == 50

    def test_custom_config(self):
        """커스텀 설정 테스트"""
        config = RiskConfig(
            max_position_pct=5.0,
            daily_loss_limit_pct=-2.0,
            max_positions=5,
        )

        assert config.max_position_pct == 5.0
        assert config.daily_loss_limit_pct == -2.0
        assert config.max_positions == 5

    def test_to_dict(self):
        """to_dict() 테스트"""
        config = RiskConfig()
        result = config.to_dict()

        assert isinstance(result, dict)
        assert "max_position_pct" in result
        assert "daily_loss_limit_pct" in result


# ═══════════════════════════════════════════════════════════════════════════
# DailyPnL 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestDailyPnL:
    """DailyPnL 데이터클래스 테스트"""

    def test_daily_pnl_creation(self):
        """DailyPnL 생성 테스트"""
        pnl = DailyPnL(date="2024-01-01")

        assert pnl.date == "2024-01-01"
        assert pnl.realized_pnl == 0.0
        assert pnl.trade_count == 0

    def test_total_pnl(self):
        """total_pnl 계산 테스트"""
        pnl = DailyPnL(
            date="2024-01-01",
            realized_pnl=500.0,
            unrealized_pnl=200.0,
        )

        assert pnl.total_pnl == 700.0


# ═══════════════════════════════════════════════════════════════════════════
# RiskManager 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestRiskManager:
    """RiskManager 클래스 테스트"""

    @pytest.fixture
    def mock_connector(self):
        """Mock IBKRConnector"""
        connector = MagicMock()
        connector.get_positions.return_value = []
        connector.cancel_all_orders.return_value = 0
        connector.place_market_order.return_value = 123
        return connector

    @pytest.fixture
    def manager(self, mock_connector):
        """RiskManager with mock connector"""
        config = RiskConfig()
        manager = RiskManager(mock_connector, config)
        manager.set_starting_balance(100_000.0)
        return manager

    def test_initialization(self, mock_connector):
        """초기화 테스트"""
        manager = RiskManager(mock_connector)

        assert manager.connector == mock_connector
        assert manager.config is not None
        assert manager._is_killed is False

    def test_set_starting_balance(self, manager):
        """시작 잔고 설정 테스트"""
        manager.set_starting_balance(50_000.0)

        assert manager._starting_balance == 50_000.0
        assert manager._current_balance == 50_000.0


# ═══════════════════════════════════════════════════════════════════════════
# 포지션 사이징 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestPositionSizing:
    """포지션 사이징 테스트"""

    @pytest.fixture
    def manager(self):
        """Manager without connector"""
        config = RiskConfig(max_position_pct=10.0)
        manager = RiskManager(None, config)
        manager.set_starting_balance(100_000.0)
        return manager

    def test_fixed_position_size(self, manager):
        """고정비율 포지션 사이즈 테스트"""
        # $100,000 × 10% = $10,000 / $100 = 100주
        qty = manager.calculate_position_size("AAPL", entry_price=100.0)

        assert qty == 100

    def test_position_size_with_low_balance(self, manager):
        """잔고 대비 가격이 높을 때"""
        # $100,000 × 10% = $10,000 / $500 = 20주
        qty = manager.calculate_position_size("TSLA", entry_price=500.0)

        assert qty == 20

    def test_position_size_zero_price(self, manager):
        """가격이 0일 때"""
        qty = manager.calculate_position_size("AAPL", entry_price=0.0)

        assert qty == 0

    def test_position_size_zero_balance(self, manager):
        """잔고가 0일 때"""
        manager.set_starting_balance(0.0)
        qty = manager.calculate_position_size("AAPL", entry_price=100.0)

        assert qty == 0


# ═══════════════════════════════════════════════════════════════════════════
# 손실 한도 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestLossLimits:
    """손실 한도 테스트"""

    @pytest.fixture
    def manager(self):
        """Manager with default config"""
        config = RiskConfig(daily_loss_limit_pct=-3.0)
        manager = RiskManager(None, config)
        manager.set_starting_balance(100_000.0)
        return manager

    def test_daily_pnl_calculation(self, manager):
        """일일 손익률 계산"""
        manager.update_balance(97_000.0)  # -3%

        pnl_pct = manager.get_daily_pnl_pct()

        assert pnl_pct == -3.0

    def test_daily_limit_not_reached(self, manager):
        """일일 한도 미도달"""
        manager.update_balance(98_000.0)  # -2%

        limit_reached = manager.check_daily_limit()

        assert limit_reached is False

    def test_daily_limit_reached(self, manager):
        """일일 한도 도달"""
        manager.config.auto_kill_on_daily_limit = False  # Kill 방지
        manager.update_balance(96_000.0)  # -4%

        limit_reached = manager.check_daily_limit()

        assert limit_reached is True


# ═══════════════════════════════════════════════════════════════════════════
# 거래 가능 여부 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestTradingAllowed:
    """거래 가능 여부 테스트"""

    @pytest.fixture
    def manager(self):
        """Manager"""
        config = RiskConfig(daily_loss_limit_pct=-3.0, max_daily_trades=10)
        manager = RiskManager(None, config)
        manager.set_starting_balance(100_000.0)
        return manager

    def test_trading_allowed_normal(self, manager):
        """정상 상태에서 거래 가능"""
        assert manager.is_trading_allowed() is True

    def test_trading_not_allowed_after_kill(self, manager):
        """Kill Switch 후 거래 불가"""
        manager.kill_switch("Test")

        assert manager.is_trading_allowed() is False

    def test_trading_allowed_after_reset(self, manager):
        """Kill Switch 리셋 후 거래 가능"""
        manager.kill_switch("Test")
        manager.reset_kill_switch()

        assert manager.is_trading_allowed() is True

    def test_trading_disabled_manually(self, manager):
        """수동 비활성화"""
        manager.disable_trading()

        assert manager.is_trading_allowed() is False

        manager.enable_trading()

        assert manager.is_trading_allowed() is True


# ═══════════════════════════════════════════════════════════════════════════
# Kill Switch 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestKillSwitch:
    """Kill Switch 테스트"""

    @pytest.fixture
    def mock_connector(self):
        """Mock connector with positions"""
        connector = MagicMock()
        connector.cancel_all_orders.return_value = 3
        connector.get_positions.return_value = [
            {"symbol": "AAPL", "qty": 100},
            {"symbol": "TSLA", "qty": 50},
        ]
        connector.place_market_order.return_value = 999
        return connector

    def test_kill_switch_execution(self, mock_connector):
        """Kill Switch 실행 테스트"""
        manager = RiskManager(mock_connector)

        result = manager.kill_switch("Test Kill")

        assert result["success"] is True
        assert result["reason"] == "Test Kill"
        assert result["cancelled_orders"] == 3
        assert len(result["liquidated_positions"]) == 2
        assert manager._is_killed is True

    def test_kill_switch_without_connector(self):
        """Connector 없이 Kill Switch"""
        manager = RiskManager(None)

        result = manager.kill_switch("Test")

        assert result["success"] is True
        assert manager._is_killed is True

    def test_kill_switch_status(self, mock_connector):
        """Kill Switch 상태 확인"""
        manager = RiskManager(mock_connector)
        manager.kill_switch("Daily Limit")

        status = manager.get_status()

        assert status["is_killed"] is True
        assert status["kill_reason"] == "Daily Limit"
        assert status["trading_enabled"] is False


# ═══════════════════════════════════════════════════════════════════════════
# 거래 기록 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestTradeRecording:
    """거래 기록 테스트"""

    def test_record_trade(self):
        """거래 기록 추가"""
        manager = RiskManager(None)
        manager.set_starting_balance(100_000.0)

        manager.record_trade("AAPL", pnl=500.0, pnl_pct=5.0)
        manager.record_trade("TSLA", pnl=-200.0, pnl_pct=-2.0)

        today = date.today().strftime("%Y-%m-%d")

        assert today in manager._daily_pnl
        assert manager._daily_pnl[today].trade_count == 2
        assert manager._daily_pnl[today].realized_pnl == 300.0


# ═══════════════════════════════════════════════════════════════════════════
# Kelly Criterion 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestKellyCriterion:
    """Kelly Criterion 테스트"""

    def test_kelly_with_insufficient_trades(self):
        """거래 수 부족시 기본 비율"""
        config = RiskConfig(use_kelly=True, kelly_min_trades=20)
        manager = RiskManager(None, config)
        manager.set_starting_balance(100_000.0)

        # 거래 이력 10개만 추가 (20개 미만)
        for i in range(10):
            manager._trade_history.append({"pnl_pct": 5.0})

        qty = manager.calculate_position_size("AAPL", 100.0)

        # 기본 10% 비율 사용
        assert qty == 100  # 10% of 100K / $100

    def test_kelly_calculation(self):
        """Kelly 계산 테스트"""
        config = RiskConfig(use_kelly=True, kelly_min_trades=5, kelly_fraction=1.0)
        manager = RiskManager(None, config)
        manager.set_starting_balance(100_000.0)

        # 60% 승률, 평균 수익 10%, 평균 손실 5%
        # 승: 10건 × 10%, 패: 5건 × -5% (10개)
        for _ in range(6):
            manager._trade_history.append({"pnl_pct": 10.0})
        for _ in range(4):
            manager._trade_history.append({"pnl_pct": -5.0})

        kelly = manager._calculate_kelly_fraction()

        # Kelly should be positive for this profitable strategy
        assert kelly > 0


# ═══════════════════════════════════════════════════════════════════════════
# 실행
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
