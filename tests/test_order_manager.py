# ============================================================================
# Order Manager Tests - 주문 관리 테스트
# ============================================================================
# 📌 이 파일의 역할:
#   - OrderManager 클래스 테스트
#   - OrderRecord, OrderStatus 테스트
#   - IBKRConnector 주문 메서드 테스트 (Mock)
#
# 📌 실행 방법:
#   pytest tests/test_order_manager.py -v
# ============================================================================

"""
Order Manager Tests

주문 관리 기능의 단위 테스트입니다.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# backend 경로 추가
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from core.order_manager import (
    OrderManager,
    OrderRecord,
    OrderStatus,
    OrderType,
    Position,
)


# ═══════════════════════════════════════════════════════════════════════════
# OrderRecord 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestOrderRecord:
    """OrderRecord 데이터클래스 테스트"""

    def test_order_record_creation(self):
        """OrderRecord 생성 테스트"""
        record = OrderRecord(
            order_id=123,
            symbol="AAPL",
            action="BUY",
            qty=10,
            order_type=OrderType.MARKET,
            status=OrderStatus.PENDING,
        )

        assert record.order_id == 123
        assert record.symbol == "AAPL"
        assert record.action == "BUY"
        assert record.qty == 10
        assert record.status == OrderStatus.PENDING

    def test_order_record_to_dict(self):
        """to_dict() 테스트"""
        record = OrderRecord(
            order_id=456,
            symbol="TSLA",
            action="SELL",
            qty=5,
            order_type=OrderType.STOP,
            status=OrderStatus.FILLED,
            fill_price=250.0,
        )

        result = record.to_dict()

        assert isinstance(result, dict)
        assert result["order_id"] == 456
        assert result["symbol"] == "TSLA"
        assert result["fill_price"] == 250.0
        assert result["status"] == "FILLED"


# ═══════════════════════════════════════════════════════════════════════════
# OrderStatus Enum 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestOrderStatus:
    """OrderStatus Enum 테스트"""

    def test_order_statuses(self):
        """모든 상태 확인"""
        assert OrderStatus.PENDING
        assert OrderStatus.FILLED
        assert OrderStatus.CANCELLED
        assert OrderStatus.PARTIAL_FILL
        assert OrderStatus.REJECTED
        assert OrderStatus.ERROR


# ═══════════════════════════════════════════════════════════════════════════
# Position 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestPosition:
    """Position 데이터클래스 테스트"""

    def test_position_creation(self):
        """Position 생성 테스트"""
        pos = Position(
            symbol="NVDA",
            qty=100,
            avg_price=500.0,
            current_price=550.0,
        )

        assert pos.symbol == "NVDA"
        assert pos.qty == 100
        assert pos.avg_price == 500.0

    def test_market_value(self):
        """시장가치 계산 테스트"""
        pos = Position(
            symbol="AAPL",
            qty=10,
            avg_price=150.0,
            current_price=160.0,
        )

        assert pos.market_value == 1600.0  # 10 * 160

    def test_pnl_pct(self):
        """손익률 계산 테스트"""
        pos = Position(
            symbol="AAPL",
            qty=10,
            avg_price=100.0,
            current_price=110.0,
        )

        assert pos.pnl_pct == 10.0  # +10%

    def test_pnl_pct_negative(self):
        """손실률 계산 테스트"""
        pos = Position(
            symbol="AAPL",
            qty=10,
            avg_price=100.0,
            current_price=95.0,
        )

        assert pos.pnl_pct == -5.0  # -5%


# ═══════════════════════════════════════════════════════════════════════════
# OrderManager 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestOrderManager:
    """OrderManager 클래스 테스트"""

    @pytest.fixture
    def mock_connector(self):
        """Mock IBKRConnector 생성"""
        connector = MagicMock()

        # Signal mocks
        connector.order_placed = MagicMock()
        connector.order_placed.connect = MagicMock()
        connector.order_filled = MagicMock()
        connector.order_filled.connect = MagicMock()
        connector.order_cancelled = MagicMock()
        connector.order_cancelled.connect = MagicMock()
        connector.positions_update = MagicMock()
        connector.positions_update.connect = MagicMock()

        return connector

    def test_manager_initialization(self, mock_connector):
        """OrderManager 초기화 테스트"""
        manager = OrderManager(mock_connector)

        assert manager.connector == mock_connector
        assert len(manager._orders) == 0
        assert len(manager._positions) == 0

    def test_manager_without_connector(self):
        """Connector 없이 초기화 테스트"""
        manager = OrderManager(None)

        assert manager.connector is None
        assert len(manager._orders) == 0

    def test_execute_entry(self, mock_connector):
        """진입 주문 실행 테스트"""
        mock_connector.place_market_order.return_value = 12345

        manager = OrderManager(mock_connector)
        order_id = manager.execute_entry("AAPL", 10, "BUY")

        assert order_id == 12345
        mock_connector.place_market_order.assert_called_once_with("AAPL", 10, "BUY")

        # 주문 기록 확인
        assert 12345 in manager._orders
        record = manager._orders[12345]
        assert record.symbol == "AAPL"
        assert record.qty == 10
        assert record.status == OrderStatus.PENDING

    def test_execute_entry_without_connector(self):
        """Connector 없이 진입 실행 테스트"""
        manager = OrderManager(None)
        order_id = manager.execute_entry("AAPL", 10, "BUY")

        assert order_id is None

    def test_execute_oca_exit(self, mock_connector):
        """OCA 청산 그룹 배치 테스트"""
        mock_connector.place_oca_group.return_value = "OCA_AAPL_12345"

        manager = OrderManager(mock_connector)
        oca_id = manager.execute_oca_exit("AAPL", 10, 150.0)

        assert oca_id == "OCA_AAPL_12345"
        mock_connector.place_oca_group.assert_called_once()

    def test_get_order(self, mock_connector):
        """주문 조회 테스트"""
        mock_connector.place_market_order.return_value = 999

        manager = OrderManager(mock_connector)
        manager.execute_entry("TSLA", 5, "BUY")

        record = manager.get_order(999)

        assert record is not None
        assert record.symbol == "TSLA"
        assert record.qty == 5

    def test_get_pending_orders(self, mock_connector):
        """미체결 주문 목록 테스트"""
        mock_connector.place_market_order.side_effect = [100, 101, 102]

        manager = OrderManager(mock_connector)
        manager.execute_entry("AAPL", 10, "BUY")
        manager.execute_entry("TSLA", 5, "BUY")
        manager.execute_entry("NVDA", 3, "BUY")

        # 하나를 체결 상태로 변경
        manager._orders[101].status = OrderStatus.FILLED

        pending = manager.get_pending_orders()

        assert len(pending) == 2

    def test_cancel_order(self, mock_connector):
        """주문 취소 테스트"""
        mock_connector.cancel_order.return_value = True

        manager = OrderManager(mock_connector)
        result = manager.cancel_order(123)

        assert result is True
        mock_connector.cancel_order.assert_called_once_with(123)

    def test_on_order_filled_callback(self, mock_connector):
        """체결 콜백 테스트"""
        mock_connector.place_market_order.return_value = 555

        manager = OrderManager(mock_connector)
        manager.execute_entry("AAPL", 10, "BUY")

        # 체결 콜백 시뮬레이션
        manager._on_order_filled(
            {
                "order_id": 555,
                "symbol": "AAPL",
                "fill_price": 155.50,
            }
        )

        record = manager.get_order(555)
        assert record.status == OrderStatus.FILLED
        assert record.fill_price == 155.50
        assert record.filled_at is not None

        # 거래 로그 확인
        assert len(manager._trade_log) == 1
        assert manager._trade_log[0]["fill_price"] == 155.50


# ═══════════════════════════════════════════════════════════════════════════
# IBKRConnector 주문 메서드 Mock 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestIBKRConnectorOrderMethods:
    """IBKRConnector 주문 메서드 테스트 (Import 확인)"""

    def test_import_ibkr_connector(self):
        """IBKRConnector import 확인"""
        from broker.ibkr_connector import IBKRConnector

        # 주문 관련 Signal 확인
        assert hasattr(IBKRConnector, "order_placed")
        assert hasattr(IBKRConnector, "order_filled")
        assert hasattr(IBKRConnector, "order_cancelled")
        assert hasattr(IBKRConnector, "positions_update")

    def test_order_methods_exist(self):
        """주문 메서드 존재 확인"""
        from broker.ibkr_connector import IBKRConnector

        assert hasattr(IBKRConnector, "place_market_order")
        assert hasattr(IBKRConnector, "place_stop_order")
        assert hasattr(IBKRConnector, "place_oca_group")
        assert hasattr(IBKRConnector, "cancel_order")
        assert hasattr(IBKRConnector, "cancel_all_orders")
        assert hasattr(IBKRConnector, "get_positions")
        assert hasattr(IBKRConnector, "get_open_orders")


# ═══════════════════════════════════════════════════════════════════════════
# 실행
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
