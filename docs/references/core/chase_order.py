"""
============================================
VWAP Chase Order Manager
============================================
Green Mode를 위한 동적 Limit Order 관리 시스템

기능:
- Lower Band에 미리 Limit Order 대기
- 밴드 변경 시 Cancel/Replace
- 체결 시 VWAP에 청산 주문 배치

작성일: 2024-12-16
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Callable
from PyQt6.QtCore import QObject, pyqtSignal

from ib_insync import IB, Trade, LimitOrder, Stock

# ============================================
# ChaseOrderManager 클래스
# ============================================

class ChaseOrderManager(QObject):
    """
    VWAP Chase 전략을 위한 동적 Limit Order 관리
    
    VWAP 밴드 업데이트 시마다:
    1. Lower Band에 Limit Buy Order 유지
    2. 밴드 변경 시 Cancel → Replace
    3. 체결 시 VWAP에 청산 Limit Order 배치
    """
    
    # ============================================
    # Signals
    # ============================================
    order_placed = pyqtSignal(object)   # 주문 배치됨
    order_updated = pyqtSignal(object)  # 주문 업데이트됨
    order_filled = pyqtSignal(object)   # 주문 체결됨
    order_cancelled = pyqtSignal()      # 주문 취소됨
    log_message = pyqtSignal(str)       # 로그 메시지
    
    # ============================================
    # 설정
    # ============================================
    PRICE_THRESHOLD = 0.05   # $0.05 이상 변동 시에만 재주문
    TIMEOUT_MINUTES = 30     # 30분 미체결 시 취소
    
    def __init__(self, ib: Optional[IB] = None, symbol: str = "SOXL", 
                 parent: Optional[QObject] = None):
        """
        초기화
        
        Args:
            ib: IB 연결 객체
            symbol: 매매 대상 심볼
            parent: 부모 QObject
        """
        super().__init__(parent)
        
        self.ib = ib
        self.symbol = symbol
        
        # 상태
        self._active_entry_order: Optional[Trade] = None   # 진입 주문
        self._active_exit_order: Optional[Trade] = None    # 청산 주문
        self._has_position: bool = False
        self._entry_price: float = 0.0
        self._position_quantity: int = 0
        self._order_placed_time: Optional[datetime] = None
        
        # 현재 밴드 가격
        self._current_lower_band: float = 0.0
        self._current_vwap: float = 0.0
        
        # Risk Manager (나중에 주입)
        self._risk_manager = None
        
        # IB 이벤트 연결
        if self.ib:
            self._connect_ib_events()
    
    def set_ib(self, ib: IB) -> None:
        """IB 객체 설정"""
        self.ib = ib
        self._connect_ib_events()
    
    def set_risk_manager(self, risk_manager) -> None:
        """리스크 매니저 설정"""
        self._risk_manager = risk_manager
    
    def set_account_info(self, account_balance: float, yang_zhang_vol: float = 0.02) -> None:
        """
        계좌 정보 설정 (포지션 사이징용)
        
        Args:
            account_balance: 계좌 잔고 (USD)
            yang_zhang_vol: Yang-Zhang 변동성 (기본 2%)
        """
        self._account_balance = account_balance
        self._yang_zhang_vol = yang_zhang_vol
    
    def calculate_position_size(self, price: float) -> int:
        """
        포지션 사이즈 계산 (Volatility Targeting)
        
        docs/ref 기반 로직:
        1. 목표 연환산 변동성 = 20%
        2. 현재 변동성 = Yang-Zhang Volatility
        3. 비중 = Target_Vol / Current_Vol
        4. 변동성 높으면 비중 축소, 낮으면 확대
        
        예시:
        - 목표 20%, 현재 40% → 비중 50%
        - 목표 20%, 현재 10% → 비중 200% (최대 100%로 제한)
        
        Args:
            price: 현재 가격
            
        Returns:
            주문 수량
        """
        TARGET_VOLATILITY = 0.20   # 목표 연환산 변동성 20%
        MAX_WEIGHT = 1.0           # 최대 비중 100%
        MAX_SINGLE_POSITION = 0.25 # 단일 종목 25% 한도
        
        account = getattr(self, '_account_balance', 10000)
        yang_zhang = getattr(self, '_yang_zhang_vol', 0.02)
        
        if yang_zhang <= 0 or price <= 0:
            return 1
        
        # === Volatility Targeting ===
        # 비중 = 목표 변동성 / 현재 변동성
        vol_weight = TARGET_VOLATILITY / yang_zhang
        
        # 비중 제한 (최대 100%)
        vol_weight = min(vol_weight, MAX_WEIGHT)
        
        # 계좌 대비 투자 금액
        position_value = account * vol_weight
        
        # 주식 수량 계산
        raw_shares = position_value / price
        
        # 단일 종목 25% 한도 적용
        max_shares = int((account * MAX_SINGLE_POSITION) / price)
        final_shares = min(int(raw_shares), max_shares)
        
        # 최소 1주
        final_shares = max(1, final_shares)
        
        self.log_message.emit(
            f"📊 Vol Targeting: 20% / {yang_zhang:.1%} = {vol_weight:.1%} 비중 "
            f"→ ${position_value:,.0f} / ${price:.2f} = {int(raw_shares)}주 "
            f"(최대 {max_shares}주) → {final_shares}주"
        )
        
        return final_shares
    
    def _connect_ib_events(self) -> None:
        """IB 이벤트 연결"""
        if not self.ib:
            return
        self.ib.orderStatusEvent += self._on_order_status
    
    # ============================================
    # 핵심 메서드
    # ============================================
    
    def on_vwap_update(self, lower_band: float, vwap: float, 
                       quantity: int = 1, kill_status: str = "CLEAR",
                       symbol: str = None) -> None:
        """
        VWAP 밴드 업데이트 시 호출
        
        Args:
            lower_band: Lower Band 가격 (-2σ)
            vwap: VWAP 중심선 가격
            quantity: 주문 수량 (기본 1)
            kill_status: Kill Switch 상태
            symbol: 현재 타겟 심볼 (심볼 변경 시 주문 취소)
        """
        # 심볼 변경 감지 → 기존 주문 모두 취소
        if symbol and symbol != self.symbol:
            self.log_message.emit(f"📝 타겟 변경: {self.symbol} → {symbol}")
            self.cancel_all_orders()
            self.symbol = symbol
        
        self._current_lower_band = lower_band
        self._current_vwap = vwap
        
        # Kill Switch 체크
        if kill_status != "CLEAR":
            self.log_message.emit(f"🚫 Kill Switch 활성: {kill_status}")
            self.cancel_all_orders()
            return
        
        # 타임아웃 체크
        if self._check_timeout():
            return
        
        # IBKR에서 현재 포지션 직접 확인
        has_position = False
        position_qty = 0
        if self.ib and self.ib.isConnected():
            try:
                positions = self.ib.positions()
                for pos in positions:
                    if pos.contract.symbol == self.symbol:
                        position_qty = int(pos.position)
                        has_position = position_qty > 0
                        break
            except:
                pass
        
        if has_position:
            # 청산 주문 관리
            self._update_exit_order(vwap, position_qty)
        else:
            # 진입 주문 관리
            self._update_entry_order(lower_band, quantity)
    
    def _update_entry_order(self, lower_band: float, quantity: int) -> None:
        """
        Lower Band에 Limit Buy Order 유지
        
        Args:
            lower_band: Lower Band 가격
            quantity: 주문 수량
        """
        if lower_band <= 0:
            return
        
        # IBKR에서 현재 오픈 주문 확인 (내부 상태 대신 실제 조회)
        existing_orders = []
        if self.ib and self.ib.isConnected():
            try:
                trades = self.ib.openTrades()
                existing_orders = [t for t in trades if t.contract.symbol == self.symbol]
            except:
                pass
        
        if existing_orders:
            # 기존 주문 있음 - 가격 변동 체크
            trade = existing_orders[0]  # 첫 번째 주문 사용
            current_price = getattr(trade.order, 'lmtPrice', 0)
            price_diff = abs(lower_band - current_price)
            
            if price_diff >= self.PRICE_THRESHOLD:
                # 가격 변동 > 임계값 → 모든 주문 취소 후 재주문
                self.log_message.emit(
                    f"📝 주문 업데이트: ${current_price:.2f} → ${lower_band:.2f}"
                )
                self.cancel_all_orders()
                self._place_entry_order(lower_band, quantity)
            # else: 가격 변동 작음 - 기존 주문 유지
        else:
            # 기존 주문 없음 → 신규 주문
            self._place_entry_order(lower_band, quantity)
    
    def _update_exit_order(self, vwap: float, quantity: int) -> None:
        """
        VWAP에 Limit Sell Order 유지
        
        Args:
            vwap: VWAP 가격
            quantity: 주문 수량
        """
        if vwap <= 0 or quantity <= 0:
            return
        
        # IBKR에서 현재 SELL 오픈 주문 확인
        existing_orders = []
        if self.ib and self.ib.isConnected():
            try:
                trades = self.ib.openTrades()
                existing_orders = [t for t in trades 
                                   if t.contract.symbol == self.symbol 
                                   and t.order.action == "SELL"]
            except:
                pass
        
        if existing_orders:
            # 기존 주문 있음 - 가격 변동 체크
            trade = existing_orders[0]
            current_price = getattr(trade.order, 'lmtPrice', 0)
            price_diff = abs(vwap - current_price)
            
            if price_diff >= self.PRICE_THRESHOLD:
                # 가격 변동 > 임계값 → 모든 주문 취소 후 재주문
                self.log_message.emit(
                    f"📝 청산 주문 업데이트: ${current_price:.2f} → ${vwap:.2f}"
                )
                self.cancel_all_orders()
                self._place_exit_order(vwap, quantity)
        else:
            # 기존 주문 없음 → 신규 주문
            self._place_exit_order(vwap, quantity)
    
    # ============================================
    # 주문 배치/취소
    # ============================================
    
    def _place_entry_order(self, price: float, quantity: int) -> None:
        """진입 Limit Order 배치"""
        if not self.ib or not self.ib.isConnected():
            self.log_message.emit("⚠️ IB 연결 없음 - 주문 불가")
            return
        
        # 리스크 체크
        if self._risk_manager:
            if not self._risk_manager.approve_order("CLEAR", 0, 10000):
                self.log_message.emit("🚫 리스크 매니저: 주문 거부")
                return
        
        try:
            contract = Stock(self.symbol, "SMART", "USD")
            order = LimitOrder("BUY", quantity, round(price, 2))
            order.tif = "DAY"  # 당일 유효
            
            trade = self.ib.placeOrder(contract, order)
            self._active_entry_order = trade
            self._order_placed_time = datetime.now()
            
            self.log_message.emit(
                f"🟢 VWAP Chase: {self.symbol} BUY {quantity}주 @ ${price:.2f} 대기"
            )
            self.order_placed.emit(trade)
            
        except Exception as e:
            self.log_message.emit(f"⚠️ 진입 주문 실패: {e}")
    
    def _place_exit_order(self, price: float, quantity: int) -> None:
        """청산 Limit Order 배치"""
        if not self.ib or not self.ib.isConnected():
            return
        
        try:
            contract = Stock(self.symbol, "SMART", "USD")
            order = LimitOrder("SELL", quantity, round(price, 2))
            order.tif = "DAY"
            
            trade = self.ib.placeOrder(contract, order)
            self._active_exit_order = trade
            
            self.log_message.emit(
                f"🔴 VWAP 청산: {self.symbol} SELL {quantity}주 @ ${price:.2f} 대기"
            )
            self.order_placed.emit(trade)
            
        except Exception as e:
            self.log_message.emit(f"⚠️ 청산 주문 실패: {e}")
    
    def _cancel_and_replace_entry(self, new_price: float, quantity: int) -> None:
        """진입 주문 Cancel/Replace"""
        if self._active_entry_order:
            try:
                old_price = getattr(self._active_entry_order.order, 'lmtPrice', 0)
                self.log_message.emit(
                    f"🔄 Cancel/Replace: ${old_price:.2f} → ${new_price:.2f}"
                )
                self.ib.cancelOrder(self._active_entry_order.order)
                self._active_entry_order = None
                # 새 주문 배치
                self._place_entry_order(new_price, quantity)
            except Exception as e:
                self.log_message.emit(f"⚠️ Cancel/Replace 실패: {e}")
    
    def _cancel_and_replace_exit(self, new_price: float, quantity: int) -> None:
        """청산 주문 Cancel/Replace"""
        if self._active_exit_order:
            try:
                self.ib.cancelOrder(self._active_exit_order.order)
                self._active_exit_order = None
                self._place_exit_order(new_price, quantity)
            except Exception as e:
                self.log_message.emit(f"⚠️ Cancel/Replace 실패: {e}")
    
    def cancel_all_orders(self) -> None:
        """모든 대기 주문 취소 (IBKR에서 직접 조회)"""
        if not self.ib or not self.ib.isConnected():
            return
        
        try:
            # IBKR에서 모든 오픈 주문 조회
            trades = self.ib.openTrades()
            cancelled_count = 0
            
            for trade in trades:
                # 현재 심볼의 주문만 취소
                if trade.contract.symbol == self.symbol:
                    self.ib.cancelOrder(trade.order)
                    cancelled_count += 1
            
            if cancelled_count > 0:
                self.log_message.emit(f"🚫 {self.symbol} 주문 {cancelled_count}개 취소")
                
        except Exception as e:
            self.log_message.emit(f"⚠️ 주문 취소 실패: {e}")
        
        # 내부 상태 초기화
        self._active_entry_order = None
        self._active_exit_order = None
        self.order_cancelled.emit()
    
    # ============================================
    # 이벤트 핸들러
    # ============================================
    
    def _on_order_status(self, trade: Trade) -> None:
        """주문 상태 변경 콜백"""
        status = trade.orderStatus.status
        
        # 진입 주문 체결
        if trade == self._active_entry_order:
            if status == "Filled":
                self._on_entry_fill(trade)
            elif status in ["Cancelled", "Inactive"]:
                self._active_entry_order = None
        
        # 청산 주문 체결
        elif trade == self._active_exit_order:
            if status == "Filled":
                self._on_exit_fill(trade)
            elif status in ["Cancelled", "Inactive"]:
                self._active_exit_order = None
    
    def _on_entry_fill(self, trade: Trade) -> None:
        """진입 체결 처리"""
        fill_price = trade.orderStatus.avgFillPrice
        quantity = int(trade.order.totalQuantity)
        
        self._has_position = True
        self._entry_price = fill_price
        self._position_quantity = quantity
        self._active_entry_order = None
        
        self.log_message.emit(
            f"✅ 진입 체결: {self.symbol} {quantity}주 @ ${fill_price:.2f}"
        )
        self.order_filled.emit(trade)
        
        # 즉시 청산 주문 배치
        if self._current_vwap > 0:
            self._place_exit_order(self._current_vwap, quantity)
    
    def _on_exit_fill(self, trade: Trade) -> None:
        """청산 체결 처리"""
        fill_price = trade.orderStatus.avgFillPrice
        quantity = int(trade.order.totalQuantity)
        
        # PnL 계산
        pnl = (fill_price - self._entry_price) * quantity
        
        self._has_position = False
        self._entry_price = 0.0
        self._position_quantity = 0
        self._active_exit_order = None
        
        self.log_message.emit(
            f"✅ 청산 체결: {self.symbol} {quantity}주 @ ${fill_price:.2f}, "
            f"PnL: ${pnl:.2f}"
        )
        self.order_filled.emit(trade)
    
    # ============================================
    # 유틸리티
    # ============================================
    
    def _check_timeout(self) -> bool:
        """타임아웃 체크 - 30분 미체결 시 취소"""
        if self._order_placed_time and self._active_entry_order:
            elapsed = datetime.now() - self._order_placed_time
            if elapsed > timedelta(minutes=self.TIMEOUT_MINUTES):
                self.log_message.emit(
                    f"⏰ 진입 주문 타임아웃 ({self.TIMEOUT_MINUTES}분)"
                )
                self.cancel_all_orders()
                return True
        return False
    
    @property
    def has_position(self) -> bool:
        """포지션 보유 여부"""
        return self._has_position
    
    @property
    def has_active_order(self) -> bool:
        """활성 주문 존재 여부"""
        return self._active_entry_order is not None or self._active_exit_order is not None
    
    def get_status(self) -> Dict:
        """현재 상태 반환"""
        return {
            "symbol": self.symbol,
            "has_position": self._has_position,
            "entry_price": self._entry_price,
            "position_qty": self._position_quantity,
            "active_entry_order": self._active_entry_order is not None,
            "active_exit_order": self._active_exit_order is not None,
            "current_lower_band": self._current_lower_band,
            "current_vwap": self._current_vwap,
        }


# ============================================
# 테스트 코드
# ============================================
if __name__ == "__main__":
    print("ChaseOrderManager 테스트")
    
    # 더미 테스트 (IB 연결 없이)
    manager = ChaseOrderManager(ib=None, symbol="SOXL")
    manager.log_message.connect(print)
    
    # VWAP 업데이트 시뮬레이션
    print("\n--- VWAP 업데이트 1 ---")
    manager.on_vwap_update(lower_band=25.50, vwap=26.00, quantity=10)
    print(f"상태: {manager.get_status()}")
    
    print("\n--- VWAP 업데이트 2 (가격 변동 작음) ---")
    manager.on_vwap_update(lower_band=25.52, vwap=26.02, quantity=10)
    print(f"상태: {manager.get_status()}")
    
    print("\n--- VWAP 업데이트 3 (가격 변동 큼) ---")
    manager.on_vwap_update(lower_band=25.60, vwap=26.10, quantity=10)
    print(f"상태: {manager.get_status()}")
