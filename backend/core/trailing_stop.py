# ============================================================================
# Trailing Stop Manager - Harvest 로직
# ============================================================================
# 📌 이 파일의 역할:
#   - Trailing Stop 주문 관리
#   - +3% 도달 시 ATR 기반 Trailing 활성화
#
# 📖 Master Plan 5.1:
#   - Profit Harvester: TRAIL (ATR×1.5), +3% 도달 시 활성화
# ============================================================================

"""
Trailing Stop Manager

수익 보호를 위한 Trailing Stop 관리를 담당합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum, auto

from loguru import logger


class TrailingStatus(Enum):
    """Trailing Stop 상태"""
    INACTIVE = auto()   # 비활성 (수익 미도달)
    PENDING = auto()    # 활성화 대기 중
    ACTIVE = auto()     # 활성화됨 (Trailing 중)
    TRIGGERED = auto()  # 트리거됨 (청산)


@dataclass
class TrailingStopOrder:
    """
    Trailing Stop 주문 정보
    
    Attributes:
        symbol: 종목 심볼
        qty: 수량
        entry_price: 진입 가격
        activation_pct: 활성화 조건 (% 수익)
        trail_amount: Trailing 금액 (달러)
        status: 현재 상태
    """
    symbol: str
    qty: int
    entry_price: float
    activation_pct: float = 3.0  # +3% 도달 시 활성화
    trail_amount: float = 0.0    # ATR × 1.5
    
    # 상태
    status: TrailingStatus = TrailingStatus.INACTIVE
    
    # 추적 가격
    highest_price: float = 0.0   # 고점
    trail_price: float = 0.0     # 현재 Trail 가격
    
    # 시간
    created_at: datetime = field(default_factory=datetime.now)
    activated_at: Optional[datetime] = None
    triggered_at: Optional[datetime] = None
    
    # 주문 정보
    order_id: Optional[int] = None
    
    @property
    def activation_price(self) -> float:
        """활성화 가격 (+3%)"""
        return self.entry_price * (1 + self.activation_pct / 100)
    
    @property
    def current_pnl_pct(self) -> float:
        """현재 P&L %"""
        if self.entry_price <= 0:
            return 0.0
        return ((self.highest_price - self.entry_price) / self.entry_price) * 100


class TrailingStopManager:
    """
    Trailing Stop 관리자
    
    수익 보호를 위한 Trailing Stop을 관리합니다.
    
    Features:
        - +X% 도달 시 자동 활성화
        - ATR 기반 Trail Amount
        - 고점 갱신 시 자동 Trail 가격 조정
    
    Example:
        >>> manager = TrailingStopManager(connector)
        >>> manager.create_trailing(
        ...     symbol="AAPL",
        ...     qty=100,
        ...     entry_price=150.0,
        ...     atr=2.5
        ... )
        >>> # 가격 업데이트 시
        >>> manager.on_price_update("AAPL", current_price=155.0)
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
        
        logger.debug("📈 TrailingStopManager 초기화 완료")
    
    # ═══════════════════════════════════════════════════════════════════
    # Trailing Stop 생성
    # ═══════════════════════════════════════════════════════════════════
    
    def create_trailing(
        self,
        symbol: str,
        qty: int,
        entry_price: float,
        atr: float,
        activation_pct: float = 3.0,
    ) -> TrailingStopOrder:
        """
        Trailing Stop 생성
        
        Args:
            symbol: 종목 심볼
            qty: 수량
            entry_price: 진입 가격
            atr: ATR (Average True Range)
            activation_pct: 활성화 조건 (기본: +3%)
            
        Returns:
            TrailingStopOrder: 생성된 주문 객체
        """
        trail_amount = atr * self.atr_multiplier
        
        order = TrailingStopOrder(
            symbol=symbol,
            qty=qty,
            entry_price=entry_price,
            activation_pct=activation_pct,
            trail_amount=trail_amount,
            highest_price=entry_price,
        )
        
        self._trailing_orders[symbol] = order
        
        logger.info(
            f"📈 Trailing 생성: {symbol} | "
            f"활성화 @ ${order.activation_price:.2f} (+{activation_pct}%) | "
            f"Trail ${trail_amount:.2f}"
        )
        
        return order
    
    # ═══════════════════════════════════════════════════════════════════
    # 가격 업데이트
    # ═══════════════════════════════════════════════════════════════════
    
    def on_price_update(self, symbol: str, current_price: float) -> Optional[str]:
        """
        가격 업데이트 처리
        
        Args:
            symbol: 종목 심볼
            current_price: 현재 가격
            
        Returns:
            str or None: "ACTIVATED" (활성화됨), "TRIGGERED" (청산), None (변화 없음)
        """
        if symbol not in self._trailing_orders:
            return None
        
        order = self._trailing_orders[symbol]
        
        # ─────────────────────────────────────────────────────────────────
        # 1. 비활성 상태 → 활성화 조건 체크
        # ─────────────────────────────────────────────────────────────────
        if order.status == TrailingStatus.INACTIVE:
            if current_price >= order.activation_price:
                order.status = TrailingStatus.ACTIVE
                order.activated_at = datetime.now()
                order.highest_price = current_price
                order.trail_price = current_price - order.trail_amount
                
                logger.info(
                    f"🟢 Trailing 활성화: {symbol} @ ${current_price:.2f} | "
                    f"Trail @ ${order.trail_price:.2f}"
                )
                
                # IBKR에 Trailing Stop 주문 전송
                self._place_trailing_order(order)
                
                return "ACTIVATED"
        
        # ─────────────────────────────────────────────────────────────────
        # 2. 활성 상태 → 고점 갱신 또는 트리거
        # ─────────────────────────────────────────────────────────────────
        elif order.status == TrailingStatus.ACTIVE:
            # 고점 갱신
            if current_price > order.highest_price:
                order.highest_price = current_price
                order.trail_price = current_price - order.trail_amount
                
                logger.debug(f"📈 Trail 갱신: {symbol} | Trail @ ${order.trail_price:.2f}")
            
            # Trail 가격 도달 → 트리거
            if current_price <= order.trail_price:
                order.status = TrailingStatus.TRIGGERED
                order.triggered_at = datetime.now()
                
                logger.warning(
                    f"🔔 Trailing 트리거: {symbol} @ ${current_price:.2f} | "
                    f"P&L: {order.current_pnl_pct:+.1f}%"
                )
                
                return "TRIGGERED"
        
        return None
    
    def _place_trailing_order(self, order: TrailingStopOrder) -> None:
        """IBKR에 Trailing Stop 주문 전송"""
        if not self.connector:
            logger.debug("⚠️ Connector 없음 - Trailing 주문 스킵")
            return
        
        # Note: IBKR의 Trailing Stop은 Trail Amount로 설정
        # 여기서는 단순화하여 Stop Order로 대체
        order_id = self.connector.place_stop_order(
            symbol=order.symbol,
            qty=order.qty,
            stop_price=order.trail_price,
            action="SELL",
        )
        
        if order_id:
            order.order_id = order_id
    
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
