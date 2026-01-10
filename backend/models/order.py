# ============================================================================
# Order Models - 주문 관련 데이터 구조체
# ============================================================================
# 📌 이 파일의 역할:
#   - OrderStatus, OrderType 열거형 정의
#   - OrderRecord, Position 데이터클래스 정의
#
# 📖 사용 예시:
#   >>> from backend.models import OrderRecord, Position, OrderStatus
#   >>> order = OrderRecord(order_id=1, symbol="AAPL", action="BUY", ...)
#
# 📖 리팩터링 [07-001]:
#   - core/order_manager.py → backend/models/order.py 이동
# ============================================================================

"""
Order Models

주문 및 포지션 관련 데이터 구조체입니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional


class OrderStatus(Enum):
    """주문 상태"""

    PENDING = auto()
    PARTIAL_FILL = auto()
    FILLED = auto()
    CANCELLED = auto()
    REJECTED = auto()
    ERROR = auto()


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

    Attributes:
        order_id: 주문 ID
        symbol: 종목 심볼
        action: "BUY" 또는 "SELL"
        qty: 주문 수량
        order_type: 주문 유형 (MARKET, LIMIT 등)
        status: 현재 주문 상태
        limit_price: 지정가 (LMT 주문 시)
        stop_price: 스톱가격 (STP 주문 시)
        fill_price: 체결 가격
        created_at: 주문 생성 시각
        filled_at: 체결 시각
        cancelled_at: 취소 시각
        oca_group: OCA 그룹 ID
        signal_id: 시그널 ID (추적용)
        notes: 메모
    """

    order_id: int
    symbol: str
    action: str  # "BUY" or "SELL"
    qty: int
    order_type: OrderType
    status: OrderStatus
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    fill_price: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    oca_group: Optional[str] = None
    signal_id: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> dict:
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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "cancelled_at": self.cancelled_at.isoformat()
            if self.cancelled_at
            else None,
            "oca_group": self.oca_group,
            "signal_id": self.signal_id,
            "notes": self.notes,
        }


@dataclass
class Position:
    """
    포지션 정보

    Attributes:
        symbol: 종목 심볼
        qty: 보유 수량
        avg_price: 평균 매입가
        current_price: 현재가
        unrealized_pnl: 미실현 손익
        realized_pnl: 실현 손익
    """

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


__all__ = ["OrderStatus", "OrderType", "OrderRecord", "Position"]
