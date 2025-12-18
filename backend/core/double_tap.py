# ============================================================================
# Double Tap Manager - 재진입 로직
# ============================================================================
# 📌 이 파일의 역할:
#   - 1차 청산 후 재진입 조건 관리
#   - Cooldown, VWAP 필터, HOD 돌파 체크
#
# 📖 Master Plan 5.2 (Double Tap):
#   1. Cooldown: 1차 청산 후 3분 대기
#   2. Filter: 주가 > VWAP
#   3. Trigger: HOD 돌파 시 Stop-Limit @ HOD + $0.01
#   4. Size: 1차의 50%
#   5. Exit: Trailing Stop 1.0%
# ============================================================================

"""
Double Tap Manager

1차 청산 후 재진입 로직을 관리합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from enum import Enum, auto

from loguru import logger


class DoubleTapState(Enum):
    """Double Tap 상태"""
    IDLE = auto()           # 대기 (1차 청산 전)
    COOLDOWN = auto()       # Cooldown 중 (3분)
    WATCHING = auto()       # 조건 감시 중
    TRIGGERED = auto()      # HOD 돌파 → 진입 대기
    ENTERED = auto()        # 2차 진입 완료
    COMPLETED = auto()      # 완료 (2차 청산)
    CANCELLED = auto()      # 취소됨


@dataclass
class DoubleTapEntry:
    """
    Double Tap 진입 정보
    
    Attributes:
        symbol: 종목 심볼
        first_exit_price: 1차 청산 가격
        first_qty: 1차 수량
        cooldown_end: Cooldown 종료 시간
    """
    symbol: str
    first_exit_price: float
    first_qty: int
    first_exit_reason: str
    
    # 상태
    state: DoubleTapState = DoubleTapState.COOLDOWN
    
    # Cooldown (3분)
    cooldown_minutes: int = 3
    first_exit_time: datetime = field(default_factory=datetime.now)
    
    # 감시 데이터
    vwap: float = 0.0
    hod: float = 0.0  # High of Day
    
    # 2차 진입
    second_qty: int = 0      # 1차의 50%
    second_entry_price: float = 0.0
    second_order_id: Optional[int] = None
    
    # Trailing (1.0%)
    exit_trailing_pct: float = 1.0
    
    @property
    def cooldown_end(self) -> datetime:
        """Cooldown 종료 시간"""
        return self.first_exit_time + timedelta(minutes=self.cooldown_minutes)
    
    @property
    def is_cooldown_over(self) -> bool:
        """Cooldown 완료 여부"""
        return datetime.now() >= self.cooldown_end
    
    @property
    def trigger_price(self) -> float:
        """HOD 돌파 트리거 가격 (HOD + $0.01)"""
        return self.hod + 0.01


class DoubleTapManager:
    """
    Double Tap 관리자
    
    1차 청산 후 재진입 조건을 관리하고 실행합니다.
    
    Process Flow:
        1. on_first_exit() → Cooldown 시작
        2. update_market_data() → VWAP, HOD 업데이트
        3. check_reentry() → 조건 충족 시 True
        4. execute_reentry() → 2차 진입 실행
    
    Example:
        >>> manager = DoubleTapManager(connector, order_manager)
        >>> manager.on_first_exit("AAPL", exit_price=155.0, qty=100, reason="Stop Loss")
        >>> # 가격 업데이트 시
        >>> manager.update_market_data("AAPL", current_price=156.0, vwap=154.5, hod=155.5)
        >>> if manager.check_reentry("AAPL"):
        ...     manager.execute_reentry("AAPL")
    """
    
    DEFAULT_COOLDOWN_MINUTES = 3
    DEFAULT_SIZE_RATIO = 0.5  # 1차의 50%
    DEFAULT_EXIT_TRAIL_PCT = 1.0  # Trailing 1%
    
    def __init__(
        self,
        connector=None,
        order_manager=None,
        trailing_manager=None,
    ):
        """
        초기화
        
        Args:
            connector: IBKRConnector
            order_manager: OrderManager
            trailing_manager: TrailingStopManager
        """
        self.connector = connector
        self.order_manager = order_manager
        self.trailing_manager = trailing_manager
        
        # Double Tap 추적
        self._entries: Dict[str, DoubleTapEntry] = {}
        
        logger.debug("🎯 DoubleTapManager 초기화 완료")
    
    # ═══════════════════════════════════════════════════════════════════
    # 1차 청산 처리
    # ═══════════════════════════════════════════════════════════════════
    
    def on_first_exit(
        self,
        symbol: str,
        exit_price: float,
        qty: int,
        reason: str,
    ) -> DoubleTapEntry:
        """
        1차 청산 시 호출 → Cooldown 시작
        
        Args:
            symbol: 종목 심볼
            exit_price: 청산 가격
            qty: 청산 수량
            reason: 청산 사유 (Stop Loss, Time Stop 등)
            
        Returns:
            DoubleTapEntry: 생성된 엔트리
        """
        entry = DoubleTapEntry(
            symbol=symbol,
            first_exit_price=exit_price,
            first_qty=qty,
            first_exit_reason=reason,
            second_qty=int(qty * self.DEFAULT_SIZE_RATIO),  # 50%
        )
        
        self._entries[symbol] = entry
        
        cooldown_end = entry.cooldown_end.strftime("%H:%M:%S")
        logger.info(
            f"🎯 Double Tap 대기: {symbol} | "
            f"1차 {qty}주 @ ${exit_price:.2f} ({reason}) | "
            f"Cooldown till {cooldown_end}"
        )
        
        return entry
    
    # ═══════════════════════════════════════════════════════════════════
    # 시장 데이터 업데이트
    # ═══════════════════════════════════════════════════════════════════
    
    def update_market_data(
        self,
        symbol: str,
        current_price: float,
        vwap: float,
        hod: float,
    ) -> None:
        """
        시장 데이터 업데이트
        
        Args:
            symbol: 종목 심볼
            current_price: 현재 가격
            vwap: VWAP
            hod: High of Day
        """
        if symbol not in self._entries:
            return
        
        entry = self._entries[symbol]
        entry.vwap = vwap
        entry.hod = hod
        
        # Cooldown 완료 시 상태 전환
        if entry.state == DoubleTapState.COOLDOWN and entry.is_cooldown_over:
            entry.state = DoubleTapState.WATCHING
            logger.info(f"🎯 Cooldown 완료: {symbol} → 조건 감시 시작")
    
    # ═══════════════════════════════════════════════════════════════════
    # 재진입 조건 체크
    # ═══════════════════════════════════════════════════════════════════
    
    def check_reentry(
        self,
        symbol: str,
        current_price: float,
    ) -> bool:
        """
        재진입 조건 체크
        
        Conditions:
            1. Cooldown 완료 (3분)
            2. 주가 > VWAP
            3. HOD 돌파 (current_price > HOD)
        
        Args:
            symbol: 종목 심볼
            current_price: 현재 가격
            
        Returns:
            bool: 재진입 조건 충족 여부
        """
        if symbol not in self._entries:
            return False
        
        entry = self._entries[symbol]
        
        # 상태 체크
        if entry.state != DoubleTapState.WATCHING:
            return False
        
        # 1. Cooldown 체크
        if not entry.is_cooldown_over:
            return False
        
        # 2. VWAP 필터
        if current_price <= entry.vwap:
            logger.debug(f"🎯 {symbol}: 가격 ${current_price:.2f} <= VWAP ${entry.vwap:.2f}")
            return False
        
        # 3. HOD 돌파
        if current_price <= entry.hod:
            return False
        
        # 모든 조건 충족!
        entry.state = DoubleTapState.TRIGGERED
        logger.info(
            f"🎯 HOD 돌파: {symbol} @ ${current_price:.2f} (HOD: ${entry.hod:.2f})"
        )
        
        return True
    
    # ═══════════════════════════════════════════════════════════════════
    # 재진입 실행
    # ═══════════════════════════════════════════════════════════════════
    
    def execute_reentry(self, symbol: str) -> Optional[int]:
        """
        2차 진입 실행
        
        Args:
            symbol: 종목 심볼
            
        Returns:
            int or None: 주문 ID
        """
        if symbol not in self._entries:
            logger.warning(f"⚠️ {symbol}: Double Tap 엔트리 없음")
            return None
        
        entry = self._entries[symbol]
        
        if entry.state != DoubleTapState.TRIGGERED:
            logger.warning(f"⚠️ {symbol}: 트리거 상태 아님 ({entry.state.name})")
            return None
        
        # 진입 가격 (HOD + $0.01)
        entry_price = entry.trigger_price
        qty = entry.second_qty
        
        logger.info(
            f"🎯 Double Tap 진입: {symbol} | "
            f"BUY {qty}주 @ Stop-Limit ${entry_price:.2f}"
        )
        
        order_id = None
        
        if self.order_manager:
            order_id = self.order_manager.execute_entry(
                symbol=symbol,
                qty=qty,
                action="BUY",
                signal_id=f"DOUBLE_TAP_{symbol}",
            )
            
            if order_id:
                entry.second_order_id = order_id
                entry.second_entry_price = entry_price
                entry.state = DoubleTapState.ENTERED
                
                # Trailing Stop 설정 (1.0%)
                if self.trailing_manager:
                    self.trailing_manager.create_trailing(
                        symbol=symbol,
                        qty=qty,
                        entry_price=entry_price,
                        atr=entry_price * 0.01,  # 1% as ATR proxy
                        activation_pct=0.1,  # 즉시 활성화
                    )
        
        return order_id
    
    # ═══════════════════════════════════════════════════════════════════
    # 상태 조회 및 취소
    # ═══════════════════════════════════════════════════════════════════
    
    def get_entry(self, symbol: str) -> Optional[DoubleTapEntry]:
        """Double Tap 엔트리 조회"""
        return self._entries.get(symbol)
    
    def cancel_reentry(self, symbol: str) -> bool:
        """재진입 대기 취소"""
        if symbol not in self._entries:
            return False
        
        entry = self._entries[symbol]
        entry.state = DoubleTapState.CANCELLED
        
        # 주문이 있으면 취소
        if entry.second_order_id and self.connector:
            self.connector.cancel_order(entry.second_order_id)
        
        del self._entries[symbol]
        
        logger.info(f"🚫 Double Tap 취소: {symbol}")
        return True
    
    def get_all_entries(self) -> Dict[str, DoubleTapEntry]:
        """모든 Double Tap 엔트리 조회"""
        return self._entries.copy()
    
    def get_watching_symbols(self) -> list:
        """현재 감시 중인 심볼 목록"""
        return [
            symbol for symbol, entry in self._entries.items()
            if entry.state in [DoubleTapState.COOLDOWN, DoubleTapState.WATCHING]
        ]
