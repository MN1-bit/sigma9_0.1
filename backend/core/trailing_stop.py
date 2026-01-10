# ============================================================================
# Trailing Stop Manager - IBKR 네이티브 Trailing Stop 사용
# ============================================================================
# 📌 이 파일의 역할:
#   - IBKR 네이티브 Trailing Stop 주문 관리
#   - 서버 사이드에서 고점 추적 (클라이언트 틱 폴링 불필요)
#
# 📖 Master Plan 5.1:
#   - Profit Harvester: TRAIL (ATR×1.5)
#
# 📌 10-001 리팩터링:
#   - 클라이언트 사이드 → IBKR 네이티브 마이그레이션
#   - on_price_update() 제거 (서버 사이드에서 자동 추적)
# ============================================================================

"""
Trailing Stop Manager (IBKR Native)

IBKR 서버 사이드 Trailing Stop 주문을 관리합니다.
고점 추적은 IBKR 서버에서 자동으로 수행됩니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict
from enum import Enum, auto

from loguru import logger


class TrailingStatus(Enum):
    """Trailing Stop 상태"""

    PENDING = auto()  # 주문 대기 중
    SUBMITTED = auto()  # IBKR에 전송됨
    FILLED = auto()  # 체결됨 (청산)
    CANCELLED = auto()  # 취소됨


@dataclass
class TrailingStopOrder:
    """
    Trailing Stop 주문 정보

    Attributes:
        symbol: 종목 심볼
        qty: 수량
        entry_price: 진입 가격
        trail_amount: Trailing 금액 (달러)
        status: 현재 상태
        order_id: IBKR 주문 ID
    """

    symbol: str
    qty: int
    entry_price: float
    trail_amount: float  # ATR × 1.5

    # 상태
    status: TrailingStatus = TrailingStatus.PENDING

    # 주문 정보
    order_id: Optional[int] = None

    # 시간
    created_at: datetime = field(default_factory=datetime.now)
    submitted_at: Optional[datetime] = None


class TrailingStopManager:
    """
    Trailing Stop 관리자 (IBKR 네이티브)

    IBKR 서버 사이드 Trailing Stop을 관리합니다.
    클라이언트에서 틱 폴링이 필요 없어 100ms 배칭에 영향 없음.

    Example:
        >>> manager = TrailingStopManager(connector)
        >>> order_id = manager.create_trailing(
        ...     symbol="AAPL",
        ...     qty=100,
        ...     atr=2.5
        ... )
        >>> # IBKR 서버가 자동으로 고점 추적
    """

    def __init__(self, connector=None, atr_multiplier: float = 1.5):
        """
        초기화

        Args:
            connector: IBKRConnector 인스턴스
            atr_multiplier: ATR 배수 (기본: 1.5)
        """
        self.connector = connector
        self.atr_multiplier = atr_multiplier

        # 활성 Trailing Stop 추적
        self._trailing_orders: Dict[str, TrailingStopOrder] = {}

        logger.debug("📈 TrailingStopManager 초기화 (IBKR Native)")

    # ═══════════════════════════════════════════════════════════════════
    # Trailing Stop 생성 (IBKR 네이티브)
    # ═══════════════════════════════════════════════════════════════════

    def create_trailing(
        self,
        symbol: str,
        qty: int,
        atr: float,
        entry_price: Optional[float] = None,
    ) -> Optional[int]:
        """
        IBKR 네이티브 Trailing Stop 주문 전송

        서버 사이드에서 자동으로 고점을 추적합니다.
        클라이언트에서 on_price_update()를 호출할 필요가 없습니다.

        Args:
            symbol: 종목 심볼
            qty: 수량
            atr: ATR (Average True Range)
            entry_price: 진입 가격 (로깅용, 선택)

        Returns:
            int: IBKR 주문 ID (실패 시 None)
        """
        trail_amount = atr * self.atr_multiplier

        order = TrailingStopOrder(
            symbol=symbol,
            qty=qty,
            entry_price=entry_price or 0.0,
            trail_amount=trail_amount,
        )

        # IBKR에 네이티브 Trailing Stop 주문 전송
        order_id = self._place_trailing_order(order)

        if order_id:
            order.order_id = order_id
            order.status = TrailingStatus.SUBMITTED
            order.submitted_at = datetime.now()
            self._trailing_orders[symbol] = order

            logger.info(
                f"📈 Trailing 주문 전송: {symbol} | "
                f"Trail ${trail_amount:.2f} (ATR×{self.atr_multiplier}) | "
                f"Order ID: {order_id}"
            )
            return order_id
        else:
            logger.warning(f"⚠️ Trailing 주문 실패: {symbol}")
            return None

    def _place_trailing_order(self, order: TrailingStopOrder) -> Optional[int]:
        """IBKR에 네이티브 Trailing Stop 주문 전송"""
        if not self.connector:
            logger.debug("⚠️ Connector 없음 - Trailing 주문 스킵")
            return None

        # IBKR 네이티브 Trailing Stop 사용 (서버 사이드 고점 추적)
        return self.connector.place_trailing_stop_order(
            symbol=order.symbol,
            qty=order.qty,
            trail_amount=order.trail_amount,
            action="SELL",
        )

    # ═══════════════════════════════════════════════════════════════════
    # 조회 및 취소
    # ═══════════════════════════════════════════════════════════════════

    def get_trailing(self, symbol: str) -> Optional[TrailingStopOrder]:
        """Trailing Stop 조회"""
        return self._trailing_orders.get(symbol)

    def cancel_trailing(self, symbol: str) -> bool:
        """Trailing Stop 취소"""
        if symbol not in self._trailing_orders:
            return False

        order = self._trailing_orders.pop(symbol)

        if order.order_id and self.connector:
            self.connector.cancel_order(order.order_id)

        logger.info(f"🚫 Trailing 취소: {symbol}")
        return True

    def get_all_trailing(self) -> Dict[str, TrailingStopOrder]:
        """모든 Trailing Stop 조회"""
        return self._trailing_orders.copy()

    def on_order_filled(self, order_id: int) -> None:
        """
        주문 체결 콜백

        IBKR 콜백에서 호출됨.

        Args:
            order_id: 체결된 주문 ID
        """
        for symbol, order in list(self._trailing_orders.items()):
            if order.order_id == order_id:
                order.status = TrailingStatus.FILLED
                logger.info(f"✅ Trailing 체결: {symbol} (Order ID: {order_id})")
                break

    def on_order_cancelled(self, order_id: int) -> None:
        """
        주문 취소 콜백

        IBKR 콜백에서 호출됨.

        Args:
            order_id: 취소된 주문 ID
        """
        for symbol, order in list(self._trailing_orders.items()):
            if order.order_id == order_id:
                order.status = TrailingStatus.CANCELLED
                self._trailing_orders.pop(symbol, None)
                logger.info(f"🚫 Trailing 취소됨: {symbol} (Order ID: {order_id})")
                break
