# ============================================================================
# Double Tap & Trailing Stop Tests
# ============================================================================
# 📌 실행 방법:
#   pytest tests/test_double_tap.py -v
# ============================================================================

"""
Double Tap & Trailing Stop Tests
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

import pytest

# backend 경로 추가
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from core.trailing_stop import (
    TrailingStopManager,
    TrailingStopOrder,
    TrailingStatus,
)
from core.double_tap import (
    DoubleTapManager,
    DoubleTapEntry,
    DoubleTapState,
)


# ═══════════════════════════════════════════════════════════════════════════
# TrailingStopOrder 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestTrailingStopOrder:
    """TrailingStopOrder 데이터클래스 테스트"""

    def test_order_creation(self):
        """주문 생성 테스트"""
        order = TrailingStopOrder(
            symbol="AAPL",
            qty=100,
            entry_price=150.0,
            activation_pct=3.0,
            trail_amount=2.5,
        )

        assert order.symbol == "AAPL"
        assert order.qty == 100
        assert order.status == TrailingStatus.INACTIVE

    def test_activation_price(self):
        """활성화 가격 계산"""
        order = TrailingStopOrder(
            symbol="AAPL",
            qty=100,
            entry_price=100.0,
            activation_pct=3.0,
        )

        # $100 × 1.03 = $103
        assert order.activation_price == 103.0


# ═══════════════════════════════════════════════════════════════════════════
# TrailingStopManager 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestTrailingStopManager:
    """TrailingStopManager 테스트"""

    @pytest.fixture
    def manager(self):
        return TrailingStopManager(connector=None, atr_multiplier=1.5)

    def test_create_trailing(self, manager):
        """Trailing Stop 생성"""
        order = manager.create_trailing(
            symbol="AAPL",
            qty=100,
            entry_price=150.0,
            atr=2.0,
            activation_pct=3.0,
        )

        assert order.symbol == "AAPL"
        assert order.trail_amount == 3.0  # 2.0 × 1.5
        assert order.status == TrailingStatus.INACTIVE

    def test_activation_on_profit(self, manager):
        """수익 도달 시 활성화"""
        manager.create_trailing(
            symbol="AAPL",
            qty=100,
            entry_price=100.0,
            atr=2.0,
            activation_pct=3.0,
        )

        # +3% 도달 ($103)
        result = manager.on_price_update("AAPL", current_price=103.0)

        assert result == "ACTIVATED"

        order = manager.get_trailing("AAPL")
        assert order.status == TrailingStatus.ACTIVE

    def test_no_activation_below_threshold(self, manager):
        """수익 미달 시 비활성"""
        manager.create_trailing(
            symbol="AAPL",
            qty=100,
            entry_price=100.0,
            atr=2.0,
            activation_pct=3.0,
        )

        # +2% ($102) - 아직 활성화 안됨
        result = manager.on_price_update("AAPL", current_price=102.0)

        assert result is None

        order = manager.get_trailing("AAPL")
        assert order.status == TrailingStatus.INACTIVE

    def test_trail_update_on_new_high(self, manager):
        """고점 갱신 시 Trail 가격 조정"""
        manager.create_trailing(
            symbol="AAPL",
            qty=100,
            entry_price=100.0,
            atr=2.0,
            activation_pct=3.0,
        )

        # 활성화
        manager.on_price_update("AAPL", 103.0)
        order = manager.get_trailing("AAPL")
        initial_trail = order.trail_price

        # 고점 갱신
        manager.on_price_update("AAPL", 105.0)

        assert order.highest_price == 105.0
        assert order.trail_price > initial_trail

    def test_trigger_on_pullback(self, manager):
        """하락 시 트리거"""
        manager.create_trailing(
            symbol="AAPL",
            qty=100,
            entry_price=100.0,
            atr=2.0,  # trail = 3.0
            activation_pct=3.0,
        )

        # 활성화 (고점 105)
        manager.on_price_update("AAPL", 105.0)

        order = manager.get_trailing("AAPL")
        # Trail @ 105 - 3 = 102

        # Trail 가격 이하로 하락
        result = manager.on_price_update("AAPL", 101.0)

        assert result == "TRIGGERED"
        assert order.status == TrailingStatus.TRIGGERED


# ═══════════════════════════════════════════════════════════════════════════
# DoubleTapEntry 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestDoubleTapEntry:
    """DoubleTapEntry 데이터클래스 테스트"""

    def test_entry_creation(self):
        """엔트리 생성"""
        entry = DoubleTapEntry(
            symbol="AAPL",
            first_exit_price=150.0,
            first_qty=100,
            first_exit_reason="Stop Loss",
        )

        assert entry.symbol == "AAPL"
        assert entry.state == DoubleTapState.COOLDOWN
        assert entry.cooldown_minutes == 3

    def test_cooldown_end(self):
        """Cooldown 종료 시간"""
        entry = DoubleTapEntry(
            symbol="AAPL",
            first_exit_price=150.0,
            first_qty=100,
            first_exit_reason="Stop Loss",
        )

        expected_end = entry.first_exit_time + timedelta(minutes=3)
        assert entry.cooldown_end == expected_end

    def test_trigger_price(self):
        """트리거 가격 (HOD + $0.01)"""
        entry = DoubleTapEntry(
            symbol="AAPL",
            first_exit_price=150.0,
            first_qty=100,
            first_exit_reason="Stop Loss",
        )
        entry.hod = 155.0

        assert entry.trigger_price == 155.01


# ═══════════════════════════════════════════════════════════════════════════
# DoubleTapManager 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestDoubleTapManager:
    """DoubleTapManager 테스트"""

    @pytest.fixture
    def manager(self):
        return DoubleTapManager(connector=None, order_manager=None)

    def test_on_first_exit(self, manager):
        """1차 청산 처리"""
        entry = manager.on_first_exit(
            symbol="AAPL",
            exit_price=150.0,
            qty=100,
            reason="Stop Loss",
        )

        assert entry.symbol == "AAPL"
        assert entry.second_qty == 50  # 50%
        assert entry.state == DoubleTapState.COOLDOWN

    def test_cooldown_check(self, manager):
        """Cooldown 체크"""
        manager.on_first_exit("AAPL", 150.0, 100, "Stop Loss")

        # Cooldown 중이면 재진입 불가
        result = manager.check_reentry("AAPL", 156.0)

        assert result is False

    def test_reentry_conditions(self, manager):
        """재진입 조건 체크"""
        entry = manager.on_first_exit("AAPL", 150.0, 100, "Stop Loss")

        # Cooldown 강제 완료
        entry.first_exit_time = datetime.now() - timedelta(minutes=5)
        entry.state = DoubleTapState.WATCHING

        # 시장 데이터 설정
        entry.vwap = 154.0
        entry.hod = 155.0

        # 조건: 가격 > VWAP and 가격 > HOD

        # VWAP 미달
        result = manager.check_reentry("AAPL", 153.0)
        assert result is False

        # HOD 미달
        result = manager.check_reentry("AAPL", 154.5)
        assert result is False

        # 모든 조건 충족
        result = manager.check_reentry("AAPL", 156.0)
        assert result is True
        assert entry.state == DoubleTapState.TRIGGERED

    def test_cancel_reentry(self, manager):
        """재진입 취소"""
        manager.on_first_exit("AAPL", 150.0, 100, "Stop Loss")

        result = manager.cancel_reentry("AAPL")

        assert result is True
        assert manager.get_entry("AAPL") is None


# ═══════════════════════════════════════════════════════════════════════════
# 통합 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestIntegration:
    """통합 테스트"""

    def test_full_flow(self):
        """전체 프로세스 테스트"""
        # 1. TrailingStopManager 생성
        trailing_manager = TrailingStopManager()

        # 2. DoubleTapManager 생성
        DoubleTapManager(trailing_manager=trailing_manager)

        # 3. Trailing 생성
        trailing_manager.create_trailing(
            symbol="AAPL",
            qty=100,
            entry_price=150.0,
            atr=2.0,
        )

        # 4. 수익 도달 → 활성화
        result = trailing_manager.on_price_update("AAPL", 155.0)  # +3.3%
        assert result == "ACTIVATED"

        # 5. 고점 갱신
        trailing_manager.on_price_update("AAPL", 158.0)

        # 6. 하락 → 청산
        result = trailing_manager.on_price_update("AAPL", 154.0)
        assert result == "TRIGGERED"


# ═══════════════════════════════════════════════════════════════════════════
# 실행
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
