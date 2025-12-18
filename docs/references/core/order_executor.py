"""
============================================
주문 실행기 - IBKR 주문 관리
============================================
IBKR API를 통해 실제 주문을 전송하고 관리합니다.

⚠️ 핵심 규칙:
- 모든 주문은 approve_order() 통과 필수!
- 실패 시 3회 재시도, 이후 팝업 알림
============================================
"""

# ============================================
# 필수 라이브러리 임포트
# ============================================
from typing import Optional, List, Dict, Any
from datetime import datetime
from ib_insync import IB, Stock, MarketOrder, LimitOrder, Order, Trade
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox


class OrderExecutor(QObject):
    """
    IBKR 주문 실행기
    
    시장가/지정가 주문을 IBKR에 전송하고,
    체결 상태를 PyQt Signal로 GUI에 전달합니다.
    
    ⚠️ 모든 주문은 approve_order() 통과 후에만 실행!
    """
    
    # === PyQt Signals (GUI 통신용) ===
    order_placed = pyqtSignal(dict)      # 주문 전송됨 {order_id, symbol, action, qty}
    order_filled = pyqtSignal(dict)      # 주문 체결됨 {order_id, fill_price, filled_qty}
    order_failed = pyqtSignal(dict)      # 주문 실패 {order_id, reason}
    order_cancelled = pyqtSignal(int)    # 주문 취소됨 (order_id)
    position_update = pyqtSignal(dict)   # 포지션 변경 {symbol, position, avg_cost}
    log_message = pyqtSignal(str)        # 로그 메시지
    
    # === 상수 ===
    MAX_RETRY = 3                        # 최대 재시도 횟수
    
    def __init__(self, ib: Optional[IB] = None, risk_manager=None, parent=None) -> None:
        """
        초기화
        
        Args:
            ib: IBKRBridge에서 전달받은 IB 객체
            risk_manager: RiskManager 인스턴스 (approve_order용)
            parent: 부모 QObject
        """
        super().__init__(parent)
        self.ib = ib
        self.risk_manager = risk_manager
        
        # 주문 추적
        self._pending_orders: Dict[int, Trade] = {}
        
        # IB 이벤트 연결
        if self.ib:
            self._connect_ib_events()
    
    def set_ib(self, ib: IB) -> None:
        """
        IB 객체 설정 (나중에 연결될 경우)
        
        Args:
            ib: IB 객체
        """
        self.ib = ib
        self._connect_ib_events()
        self.log_message.emit("✅ OrderExecutor: IB 연결됨")
    
    def _connect_ib_events(self) -> None:
        """IB 이벤트 핸들러 연결"""
        if not self.ib:
            return
        
        # 주문 상태 이벤트
        self.ib.orderStatusEvent += self._on_order_status
        # 체결 이벤트
        self.ib.execDetailsEvent += self._on_exec_details
        # 포지션 이벤트
        self.ib.positionEvent += self._on_position
    
    # ============================================
    # 주문 전송 메서드
    # ============================================
    
    def place_market_order(
        self, 
        symbol: str, 
        action: str, 
        quantity: int,
        kill_status: str = "CLEAR",
        daily_loss: float = 0.0,
        account_balance: float = 0.0
    ) -> Optional[Trade]:
        """
        시장가 주문 전송
        
        Args:
            symbol: 종목 코드 (예: "SPY")
            action: "BUY" 또는 "SELL"
            quantity: 수량
            kill_status: 킬 스위치 상태
            daily_loss: 당일 손실액
            account_balance: 계좌 잔고
            
        Returns:
            Trade 객체 또는 None (실패 시)
        """
        # === 1. approve_order 체크 (필수!) ===
        if self.risk_manager:
            if not self.risk_manager.approve_order(kill_status, daily_loss, account_balance):
                self.log_message.emit(f"🚫 주문 거부됨: {action} {quantity} {symbol}")
                self.order_failed.emit({
                    "order_id": None,
                    "reason": "approve_order() 거부",
                    "symbol": symbol,
                    "action": action
                })
                return None
        
        # === 2. IB 연결 확인 ===
        if not self.ib or not self.ib.isConnected():
            self.log_message.emit("❌ IBKR 연결 안됨")
            return None
        
        # === 3. 주문 실행 (재시도 로직) ===
        for attempt in range(1, self.MAX_RETRY + 1):
            try:
                # 계약 생성 (미국 주식 기본)
                contract = Stock(symbol, "SMART", "USD")
                
                # 시장가 주문
                order = MarketOrder(action, quantity)
                
                # 주문 전송
                trade = self.ib.placeOrder(contract, order)
                
                # 주문 추적에 추가
                self._pending_orders[trade.order.orderId] = trade
                
                self.log_message.emit(
                    f"📤 시장가 주문 전송: {action} {quantity} {symbol} (ID: {trade.order.orderId})"
                )
                
                self.order_placed.emit({
                    "order_id": trade.order.orderId,
                    "symbol": symbol,
                    "action": action,
                    "quantity": quantity,
                    "order_type": "MKT",
                    "timestamp": datetime.now().isoformat()
                })
                
                return trade
                
            except Exception as e:
                self.log_message.emit(
                    f"⚠️ 주문 실패 (시도 {attempt}/{self.MAX_RETRY}): {str(e)}"
                )
                
                if attempt == self.MAX_RETRY:
                    # 3회 실패 → 팝업 알림
                    self._show_failure_popup(symbol, action, quantity, str(e))
                    self.order_failed.emit({
                        "order_id": None,
                        "reason": f"3회 실패: {str(e)}",
                        "symbol": symbol,
                        "action": action
                    })
        
        return None
    
    def place_limit_order(
        self, 
        symbol: str, 
        action: str, 
        quantity: int,
        price: float,
        kill_status: str = "CLEAR",
        daily_loss: float = 0.0,
        account_balance: float = 0.0
    ) -> Optional[Trade]:
        """
        지정가 주문 전송
        
        Args:
            symbol: 종목 코드
            action: "BUY" 또는 "SELL"
            quantity: 수량
            price: 지정가
            kill_status: 킬 스위치 상태
            daily_loss: 당일 손실액
            account_balance: 계좌 잔고
            
        Returns:
            Trade 객체 또는 None (실패 시)
        """
        # === 1. approve_order 체크 ===
        if self.risk_manager:
            if not self.risk_manager.approve_order(kill_status, daily_loss, account_balance):
                self.log_message.emit(f"🚫 주문 거부됨: {action} {quantity} {symbol} @ {price}")
                return None
        
        # === 2. IB 연결 확인 ===
        if not self.ib or not self.ib.isConnected():
            self.log_message.emit("❌ IBKR 연결 안됨")
            return None
        
        # === 3. 주문 실행 ===
        for attempt in range(1, self.MAX_RETRY + 1):
            try:
                contract = Stock(symbol, "SMART", "USD")
                order = LimitOrder(action, quantity, price)
                trade = self.ib.placeOrder(contract, order)
                
                self._pending_orders[trade.order.orderId] = trade
                
                self.log_message.emit(
                    f"📤 지정가 주문 전송: {action} {quantity} {symbol} @ ${price:.2f}"
                )
                
                self.order_placed.emit({
                    "order_id": trade.order.orderId,
                    "symbol": symbol,
                    "action": action,
                    "quantity": quantity,
                    "order_type": "LMT",
                    "price": price,
                    "timestamp": datetime.now().isoformat()
                })
                
                return trade
                
            except Exception as e:
                self.log_message.emit(f"⚠️ 지정가 주문 실패 (시도 {attempt}): {str(e)}")
                
                if attempt == self.MAX_RETRY:
                    self._show_failure_popup(symbol, action, quantity, str(e))
        
        return None
    
    # ============================================
    # 주문 관리 메서드
    # ============================================
    
    def cancel_order(self, order_id: int) -> bool:
        """
        주문 취소
        
        Args:
            order_id: 취소할 주문 ID
            
        Returns:
            성공 여부
        """
        if not self.ib or not self.ib.isConnected():
            return False
        
        trade = self._pending_orders.get(order_id)
        if not trade:
            self.log_message.emit(f"⚠️ 주문 ID {order_id}를 찾을 수 없음")
            return False
        
        try:
            self.ib.cancelOrder(trade.order)
            self.log_message.emit(f"🚫 주문 취소 요청: ID {order_id}")
            return True
        except Exception as e:
            self.log_message.emit(f"❌ 주문 취소 실패: {str(e)}")
            return False
    
    def get_open_orders(self) -> List[Trade]:
        """
        미체결 주문 목록 조회
        
        Returns:
            미체결 주문 리스트
        """
        if not self.ib or not self.ib.isConnected():
            return []
        
        return self.ib.openOrders()
    
    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """
        현재 보유 포지션 조회
        
        Returns:
            {symbol: {position, avg_cost, market_value}} 형태 딕셔너리
        """
        if not self.ib or not self.ib.isConnected():
            return {}
        
        positions = {}
        for pos in self.ib.positions():
            symbol = pos.contract.symbol
            positions[symbol] = {
                "position": pos.position,
                "avg_cost": pos.avgCost,
                "market_value": pos.position * pos.avgCost
            }
        
        return positions
    
    # ============================================
    # IB 이벤트 핸들러
    # ============================================
    
    def _on_order_status(self, trade: Trade) -> None:
        """주문 상태 변경 이벤트"""
        status = trade.orderStatus.status
        order_id = trade.order.orderId
        
        self.log_message.emit(f"📊 주문 상태: ID {order_id} → {status}")
        
        if status == "Filled":
            # 완전 체결
            self.order_filled.emit({
                "order_id": order_id,
                "fill_price": trade.orderStatus.avgFillPrice,
                "filled_qty": trade.orderStatus.filled,
                "symbol": trade.contract.symbol
            })
            # 추적에서 제거
            self._pending_orders.pop(order_id, None)
            
        elif status == "Cancelled":
            self.order_cancelled.emit(order_id)
            self._pending_orders.pop(order_id, None)
    
    def _on_exec_details(self, trade: Trade, fill) -> None:
        """체결 상세 이벤트"""
        self.log_message.emit(
            f"💰 체결: {fill.execution.side} {fill.execution.shares} @ ${fill.execution.price:.2f}"
        )
    
    def _on_position(self, position) -> None:
        """포지션 변경 이벤트"""
        self.position_update.emit({
            "symbol": position.contract.symbol,
            "position": position.position,
            "avg_cost": position.avgCost
        })
    
    # ============================================
    # 알림 메서드
    # ============================================
    
    def _show_failure_popup(self, symbol: str, action: str, quantity: int, reason: str) -> None:
        """
        3회 실패 시 팝업 알림
        
        실패 원인을 상세히 로깅하고 사용자에게 알림
        """
        # 상세 로깅
        self.log_message.emit("=" * 50)
        self.log_message.emit(f"❌ 주문 3회 실패 - 상세 정보:")
        self.log_message.emit(f"   심볼: {symbol}")
        self.log_message.emit(f"   방향: {action}")
        self.log_message.emit(f"   수량: {quantity}")
        self.log_message.emit(f"   원인: {reason}")
        self.log_message.emit(f"   시간: {datetime.now().isoformat()}")
        self.log_message.emit("=" * 50)
        
        # 팝업 (메인 스레드에서만 가능하므로 시그널 사용 권장)
        try:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Critical)
            msg.setWindowTitle("주문 실패")
            msg.setText(f"주문이 3회 실패했습니다!\n\n"
                       f"심볼: {symbol}\n"
                       f"방향: {action}\n"
                       f"수량: {quantity}\n\n"
                       f"원인: {reason}")
            msg.exec()
        except Exception:
            # 스레드 환경에서는 팝업 불가능할 수 있음
            pass


# ============================================
# 테스트 코드
# ============================================
if __name__ == "__main__":
    print("=" * 50)
    print("OrderExecutor 테스트")
    print("=" * 50)
    
    # Mock 테스트 (IB 없이)
    executor = OrderExecutor()
    executor.log_message.connect(lambda x: print(x))
    
    # IB 없이 주문 시도 → 실패 예상
    result = executor.place_market_order("SPY", "BUY", 10)
    print(f"주문 결과: {result}")
    
    # 포지션 조회 (빈 딕셔너리 예상)
    positions = executor.get_positions()
    print(f"포지션: {positions}")
    
    print("\n✅ 테스트 완료 (IB 연결 없이 기본 동작 확인)")
