# ============================================================================
# Order Manager - 주문 상태 관리 및 추적
# ============================================================================
# 📌 이 파일의 역할:
#   - 주문 상태 추적 (Pending, Filled, Cancelled)
#   - Signal 기반 진입 주문 실행
#   - OCA 그룹 관리
#   - 거래 로그 기록
#
# 📖 사용 예시:
#   >>> from backend.core.order_manager import OrderManager
#   >>> manager = OrderManager(connector)
#   >>> order_id = manager.execute_entry(signal)
#   >>> oca_id = manager.execute_oca_exit(order_id, entry_price)
# ============================================================================

"""
Order Manager Module

주문 상태 관리 및 Signal 기반 주문 실행을 담당합니다.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, List, Any

from loguru import logger


# ═══════════════════════════════════════════════════════════════════════════
# Enum 및 데이터클래스
# ═══════════════════════════════════════════════════════════════════════════


class OrderStatus(Enum):
    """주문 상태"""

    PENDING = auto()  # 미체결 대기
    PARTIAL_FILL = auto()  # 부분 체결
    FILLED = auto()  # 전량 체결
    CANCELLED = auto()  # 취소됨
    REJECTED = auto()  # 거부됨
    ERROR = auto()  # 오류


class OrderType(Enum):
    """주문 유형"""

    MARKET = "MKT"
    LIMIT = "LMT"
    STOP = "STP"
    STOP_LIMIT = "STP LMT"
    TRAILING_STOP = "TRAIL"


@dataclass
class OrderRecord:
    """
    주문 기록

    주문의 전체 라이프사이클을 추적합니다.
    """

    order_id: int
    symbol: str
    action: str  # "BUY" or "SELL"
    qty: int
    order_type: OrderType
    status: OrderStatus

    # 가격 정보
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    fill_price: Optional[float] = None

    # 시간 정보
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None

    # OCA 그룹
    oca_group: Optional[str] = None

    # 메타데이터
    signal_id: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "action": self.action,
            "qty": self.qty,
            "order_type": self.order_type.value,
            "status": self.status.name,
            "limit_price": self.limit_price,
            "stop_price": self.stop_price,
            "fill_price": self.fill_price,
            "created_at": self.created_at.isoformat(),
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "oca_group": self.oca_group,
        }


@dataclass
class Position:
    """포지션 정보"""

    symbol: str
    qty: int
    avg_price: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

    @property
    def market_value(self) -> float:
        """시장가치"""
        return self.qty * self.current_price

    @property
    def pnl_pct(self) -> float:
        """손익률"""
        if self.avg_price == 0:
            return 0.0
        return ((self.current_price - self.avg_price) / self.avg_price) * 100


# ═══════════════════════════════════════════════════════════════════════════
# OrderManager 클래스
# ═══════════════════════════════════════════════════════════════════════════


class OrderManager:
    """
    주문 관리자

    IBKRConnector와 연동하여 주문을 관리합니다.

    Responsibilities:
        - Signal 기반 진입 주문 실행
        - OCA 그룹 (Exit Orders) 배치
        - 주문 상태 추적
        - 포지션 관리

    Example:
        >>> from backend.broker.ibkr_connector import IBKRConnector
        >>> connector = IBKRConnector()
        >>> manager = OrderManager(connector)
        >>>
        >>> # Signal 기반 진입
        >>> order_id = manager.execute_entry(signal)
        >>>
        >>> # OCA 그룹 배치
        >>> oca_id = manager.execute_oca_exit(order_id, entry_price)
    """

    def __init__(self, connector=None):
        """
        OrderManager 초기화

        Args:
            connector: IBKRConnector 인스턴스 (None이면 Mock 모드)
        """
        self.connector = connector

        # 주문 추적
        self._orders: Dict[int, OrderRecord] = {}

        # 포지션 추적
        self._positions: Dict[str, Position] = {}

        # OCA 그룹 추적
        self._oca_groups: Dict[str, List[int]] = {}

        # 거래 로그
        self._trade_log: List[Dict[str, Any]] = []

        # 콜백 연결
        if connector:
            self._connect_signals()

        logger.debug("📋 OrderManager 초기화 완료")

    def _connect_signals(self) -> None:
        """IBKRConnector Signal 연결"""
        if not self.connector:
            return

        self.connector.order_placed.connect(self._on_order_placed)
        self.connector.order_filled.connect(self._on_order_filled)
        self.connector.order_cancelled.connect(self._on_order_cancelled)
        self.connector.positions_update.connect(self._on_positions_update)

    # ═══════════════════════════════════════════════════════════════════
    # 진입 주문
    # ═══════════════════════════════════════════════════════════════════

    def execute_entry(
        self,
        symbol: str,
        qty: int,
        action: str = "BUY",
        signal_id: Optional[str] = None,
    ) -> Optional[int]:
        """
        진입 주문 실행

        Args:
            symbol: 종목 심볼
            qty: 수량
            action: "BUY" 또는 "SELL"
            signal_id: 시그널 ID (추적용)

        Returns:
            int: 주문 ID (실패 시 None)
        """
        if not self.connector:
            logger.warning("⚠️ Connector 없음 - Mock 모드")
            return None

        # 시장가 주문 실행
        order_id = self.connector.place_market_order(symbol, qty, action)

        if order_id:
            # 주문 기록 생성
            record = OrderRecord(
                order_id=order_id,
                symbol=symbol,
                action=action,
                qty=qty,
                order_type=OrderType.MARKET,
                status=OrderStatus.PENDING,
                signal_id=signal_id,
            )
            self._orders[order_id] = record

            logger.info(f"📤 진입 주문 실행: {action} {qty} {symbol} (ID: {order_id})")

        return order_id

    def execute_oca_exit(
        self,
        symbol: str,
        qty: int,
        entry_price: float,
        stop_loss_pct: float = -2.0,
        profit_target_pct: float = 8.0,
    ) -> Optional[str]:
        """
        OCA 청산 그룹 배치

        진입 후 즉시 호출하여 Stop Loss와 Profit Target을 동시에 배치합니다.

        Args:
            symbol: 종목 심볼
            qty: 수량
            entry_price: 진입 가격
            stop_loss_pct: Stop Loss 비율 (기본: -2.0%)
            profit_target_pct: Profit Target 비율 (기본: 8.0%)

        Returns:
            str: OCA 그룹 ID (실패 시 None)
        """
        if not self.connector:
            logger.warning("⚠️ Connector 없음 - Mock 모드")
            return None

        oca_id = self.connector.place_oca_group(
            symbol=symbol,
            qty=qty,
            entry_price=entry_price,
            stop_loss_pct=stop_loss_pct,
            profit_target_pct=profit_target_pct,
        )

        if oca_id:
            self._oca_groups[oca_id] = []
            logger.info(f"📦 OCA 그룹 배치: {symbol} (ID: {oca_id})")

        return oca_id

    # ═══════════════════════════════════════════════════════════════════
    # 상태 조회
    # ═══════════════════════════════════════════════════════════════════

    def get_order(self, order_id: int) -> Optional[OrderRecord]:
        """주문 조회"""
        return self._orders.get(order_id)

    def get_pending_orders(self) -> List[OrderRecord]:
        """미체결 주문 목록"""
        return [o for o in self._orders.values() if o.status == OrderStatus.PENDING]

    def get_position(self, symbol: str) -> Optional[Position]:
        """포지션 조회"""
        return self._positions.get(symbol)

    def get_all_positions(self) -> List[Position]:
        """모든 포지션 목록"""
        return list(self._positions.values())

    def get_trade_log(self) -> List[Dict[str, Any]]:
        """거래 로그 조회"""
        return self._trade_log

    # ═══════════════════════════════════════════════════════════════════
    # 취소
    # ═══════════════════════════════════════════════════════════════════

    def cancel_order(self, order_id: int) -> bool:
        """주문 취소"""
        if not self.connector:
            return False

        return self.connector.cancel_order(order_id)

    def cancel_all(self) -> int:
        """모든 주문 취소"""
        if not self.connector:
            return 0

        return self.connector.cancel_all_orders()

    # ═══════════════════════════════════════════════════════════════════
    # 콜백 핸들러
    # ═══════════════════════════════════════════════════════════════════

    def _on_order_placed(self, data: dict) -> None:
        """주문 접수 콜백"""
        order_id = data.get("order_id")
        if order_id and order_id not in self._orders:
            record = OrderRecord(
                order_id=order_id,
                symbol=data.get("symbol", ""),
                action=data.get("action", ""),
                qty=data.get("qty", 0),
                order_type=OrderType.MARKET,
                status=OrderStatus.PENDING,
            )
            self._orders[order_id] = record

    def _on_order_filled(self, data: dict) -> None:
        """주문 체결 콜백"""
        order_id = data.get("order_id")
        if order_id in self._orders:
            record = self._orders[order_id]
            record.status = OrderStatus.FILLED
            record.fill_price = data.get("fill_price", 0)
            record.filled_at = datetime.now()

            # 거래 로그 추가
            self._trade_log.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "order_id": order_id,
                    "symbol": record.symbol,
                    "action": record.action,
                    "qty": record.qty,
                    "fill_price": record.fill_price,
                    "type": "FILL",
                }
            )

            logger.info(f"✅ 체결 기록: {record.symbol} @ ${record.fill_price:.2f}")

    def _on_order_cancelled(self, data: dict) -> None:
        """주문 취소 콜백"""
        order_id = data.get("order_id")
        if order_id in self._orders:
            record = self._orders[order_id]
            record.status = OrderStatus.CANCELLED
            record.cancelled_at = datetime.now()

            logger.info(f"🚫 취소 기록: {record.symbol}")

    def _on_positions_update(self, positions: list) -> None:
        """포지션 업데이트 콜백"""
        for pos in positions:
            symbol = pos.get("symbol")
            if symbol:
                self._positions[symbol] = Position(
                    symbol=symbol,
                    qty=pos.get("qty", 0),
                    avg_price=pos.get("avg_price", 0),
                )
