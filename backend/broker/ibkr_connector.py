# ============================================================================
# IBKR Connector - IB Gateway/TWS 연결 관리
# ============================================================================
# 📌 이 파일의 역할:
#   Interactive Brokers Gateway에 연결하여 실시간 시장 데이터를 수신합니다.
#   GUI가 멈추지 않도록 별도 스레드(QThread)에서 실행됩니다.
#
# 📌 masterplan.md 2.1절 / development_steps.md Step 2.1 기준 구현
# 📌 참조: docs/references/core/bridge.py (핵심 패턴만 채택)
# ============================================================================

"""
IBKR Connector Module

IB Gateway/TWS와의 연결을 관리하고 실시간 시장 데이터를 수신합니다.
PyQt6 QThread 기반으로 GUI와 분리된 백그라운드에서 동작합니다.

Example:
    # 커넥터 생성 및 시그널 연결
    connector = IBKRConnector()
    connector.connected.connect(on_connection_changed)
    connector.price_update.connect(on_price_received)
    
    # 연결 시작
    connector.start()
    
    # 시세 구독
    connector.subscribe_ticker(["SPY", "QQQ"])
    
    # 종료
    connector.stop()
"""

import os
from typing import Optional, Dict, List
from dotenv import load_dotenv

# ib_insync - IBKR API 래퍼
# 참고: https://ib-insync.readthedocs.io/
from ib_insync import IB, util, Stock, Ticker, MarketOrder, StopOrder, LimitOrder, Trade
import time

# PyQt6 - GUI 스레드 분리 및 시그널
from PyQt6.QtCore import QThread, pyqtSignal

# .env 파일에서 환경 변수 로드
# 프로젝트 루트의 .env 파일을 자동으로 찾아서 로드합니다
load_dotenv()


# ═══════════════════════════════════════════════════════════════════════════
# IBKRConnector 클래스
# ═══════════════════════════════════════════════════════════════════════════

class IBKRConnector(QThread):
    """
    IBKR 연결 커넥터 (QThread 기반)
    
    백그라운드 스레드에서 IB Gateway/TWS에 연결하고,
    실시간 시장 데이터를 PyQt Signal로 GUI에 전달합니다.
    
    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5 - Explain Like I'm 5):
    ═══════════════════════════════════════════════════════════════════════
    이 클래스는 "주식 시장 라디오"와 같습니다.
    
    1. 라디오를 켠다 (connect) → IB Gateway에 연결
    2. 채널을 맞춘다 (subscribe) → SPY, QQQ 등 원하는 종목 선택
    3. 소리가 들린다 (signal) → 실시간 가격이 계속 들어옴
    4. 라디오를 끈다 (stop) → 연결 종료
    
    ═══════════════════════════════════════════════════════════════════════
    PyQt Signals:
    ═══════════════════════════════════════════════════════════════════════
    
    - connected(bool): 연결 상태가 변경될 때 발생
        - True: 연결 성공
        - False: 연결 해제 또는 실패
    
    - price_update(dict): 실시간 가격이 업데이트될 때 발생
        - {"symbol": "SPY", "last": 450.25, "bid": 450.20, "ask": 450.30, ...}
    
    - account_update(dict): 계좌 정보가 업데이트될 때 발생
        - {"account": "DU...", "balance": 100000.0, "available": 95000.0}
    
    - error(str): 에러가 발생했을 때
        - "❌ 연결 오류: ..."
    
    - log_message(str): 로그 메시지 (디버깅/상태 표시용)
        - "🔌 IBKR 연결 시도 중..."
    
    ═══════════════════════════════════════════════════════════════════════
    Configuration (.env 파일):
    ═══════════════════════════════════════════════════════════════════════
    
    IB_HOST=127.0.0.1      # IB Gateway 호스트 (기본: 로컬)
    IB_PORT=4002           # 포트 (Paper: 4002, Live: 4001)
    IB_CLIENT_ID=1         # 클라이언트 ID (고유해야 함)
    IB_ACCOUNT=            # 계좌 ID (선택, 비워두면 자동 감지)
    """
    
    # ═══════════════════════════════════════════════════════════════════
    # PyQt Signals 정의
    # ═══════════════════════════════════════════════════════════════════
    # 스레드에서 GUI로 데이터를 전달하는 "통신 채널"입니다.
    # emit()으로 신호를 보내면, connect()로 연결된 함수가 호출됩니다.
    # ═══════════════════════════════════════════════════════════════════
    
    connected = pyqtSignal(bool)        # 연결 상태 변경
    price_update = pyqtSignal(dict)     # 실시간 가격 업데이트
    account_update = pyqtSignal(dict)   # 계좌 정보 업데이트
    error = pyqtSignal(str)             # 에러 메시지
    log_message = pyqtSignal(str)       # 로그 메시지
    
    # ═══════════════════════════════════════════════════════════════════
    # 주문 관련 Signals (Step 3.1 OMS)
    # ═══════════════════════════════════════════════════════════════════
    order_placed = pyqtSignal(dict)     # 주문 접수됨 {order_id, symbol, action, qty, ...}
    order_filled = pyqtSignal(dict)     # 주문 체결됨 {order_id, symbol, fill_price, ...}
    order_cancelled = pyqtSignal(dict)  # 주문 취소됨 {order_id, symbol, ...}
    order_error = pyqtSignal(str, str)  # 주문 오류 (order_id, message)
    positions_update = pyqtSignal(list) # 포지션 목록 변경 [{symbol, qty, avg_price, ...}]
    
    def __init__(self, parent=None) -> None:
        """
        커넥터 초기화
        
        .env 파일에서 연결 설정을 로드하고, 내부 상태를 초기화합니다.
        이 시점에서는 아직 연결하지 않습니다 (start() 호출 시 연결).
        
        Args:
            parent: 부모 QObject (선택)
        """
        super().__init__(parent)
        
        # --- IB 객체 (연결 후 생성됨) ---
        # ib_insync.IB 클래스의 인스턴스
        # 실제 IBKR API와 통신하는 핵심 객체
        self.ib: Optional[IB] = None
        
        # --- 연결 설정 (.env에서 로드) ---
        # os.getenv(키, 기본값): 환경 변수를 읽고, 없으면 기본값 사용
        self.host: str = os.getenv("IB_HOST", "127.0.0.1")
        self.port: int = int(os.getenv("IB_PORT", "4002"))
        self.client_id: int = int(os.getenv("IB_CLIENT_ID", "1"))
        self.account: str = os.getenv("IB_ACCOUNT", "")
        
        # --- 상태 플래그 ---
        # _is_running: 스레드 루프가 돌아야 하는지 (stop() 호출 시 False)
        # _is_connected: 현재 IB Gateway에 연결되어 있는지
        self._is_running: bool = False
        self._is_connected: bool = False
        
        # --- 시세 구독 추적 ---
        # 구독 중인 Ticker 객체를 심볼별로 저장
        # {"SPY": Ticker(...), "QQQ": Ticker(...)}
        self._subscribed_tickers: Dict[str, Ticker] = {}
        
        # 로그: 설정 로드 완료
        # (아직 GUI 연결 전이므로 print 사용)
        print(f"[IBKRConnector] 설정 로드: {self.host}:{self.port} (Client ID: {self.client_id})")
        
        # --- 주문 추적 (Step 3.1 OMS) ---
        # 활성 주문 추적: order_id -> Trade 객체
        self._active_orders: Dict[int, Trade] = {}
        # OCA 그룹 추적: oca_group_id -> [order_ids]
        self._oca_groups: Dict[str, List[int]] = {}
    
    # ═══════════════════════════════════════════════════════════════════
    # 스레드 메인 루프
    # ═══════════════════════════════════════════════════════════════════
    
    def run(self) -> None:
        """
        스레드 메인 루프 (QThread.start() 호출 시 자동 실행)
        
        이 메서드는 다음 순서로 동작합니다:
        1. IB Gateway에 연결 시도 (최대 3회 재시도)
        2. 연결 성공 시 이벤트 루프 유지
        3. stop() 호출 또는 연결 끊김 시 종료
        
        ═══════════════════════════════════════════════════════════════
        왜 별도 스레드가 필요한가?
        ═══════════════════════════════════════════════════════════════
        - 메인 스레드에서 연결을 기다리면 GUI가 멈춰버림 (프리징)
        - 별도 스레드에서 연결하면 GUI는 계속 반응할 수 있음
        - ib_insync의 이벤트 루프도 별도 스레드에서 돌려야 함
        """
        self._is_running = True
        self.log_message.emit("🔌 IBKR 연결 시도 중...")
        
        try:
            # --- ib_insync용 이벤트 루프 시작 (필수!) ---
            # ib_insync는 내부적으로 asyncio 이벤트 루프가 필요함
            # util.startLoop()는 현재 스레드에 이벤트 루프를 생성
            util.startLoop()
            
            # --- IB 객체 생성 ---
            self.ib = IB()
            
            # --- 연결 시도 (Exponential Backoff 재시도) ---
            # 네트워크 문제로 1회 실패할 수 있으므로 최대 3회 시도
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    self.log_message.emit(f"📡 연결 시도 {attempt}/{max_retries}...")
                    
                    # IB Gateway에 연결 (타임아웃 10초)
                    # host: IB Gateway 주소 (보통 127.0.0.1)
                    # port: Paper 4002, Live 4001
                    # clientId: 고유해야 함 (같은 ID로 중복 연결 불가)
                    self.ib.connect(
                        host=self.host,
                        port=self.port,
                        clientId=self.client_id,
                        timeout=10
                    )
                    
                    # 연결 성공!
                    self._is_connected = True
                    self.connected.emit(True)
                    self.log_message.emit(f"✅ IBKR 연결 성공! (포트: {self.port})")
                    
                    # 초기 계좌 정보 조회
                    self._fetch_account_info()
                    
                    # 재시도 루프 탈출
                    break
                    
                except Exception as e:
                    self.log_message.emit(f"⚠️ 연결 실패: {str(e)}")
                    
                    if attempt < max_retries:
                        # Exponential Backoff: 1초, 2초, 4초...
                        # 네트워크 문제는 잠시 후 해결될 수 있으므로
                        # 점점 길게 기다리면서 재시도
                        wait_time = 2 ** (attempt - 1)
                        self.log_message.emit(f"⏳ {wait_time}초 후 재시도...")
                        QThread.msleep(wait_time * 1000)  # 밀리초 단위
                    else:
                        # 마지막 시도도 실패
                        raise
            
            # --- 이벤트 루프 유지 ---
            # 연결이 유지되는 동안 IB 이벤트를 처리
            # ib.sleep(0.1): 100ms마다 이벤트 체크 (CPU 부하 최소화)
            while self._is_running and self.ib.isConnected():
                self.ib.sleep(0.1)
                
        except Exception as e:
            # 연결 실패 또는 런타임 에러
            self.error.emit(f"❌ 연결 오류: {str(e)}")
            self._is_connected = False
            self.connected.emit(False)
        
        finally:
            # --- 정리 (항상 실행) ---
            self._disconnect()
    
    def _fetch_account_info(self) -> None:
        """
        계좌 정보 조회 및 GUI에 전달
        
        NetLiquidation (순자산), AvailableFunds (가용 자금) 등을 조회합니다.
        """
        if not self.ib or not self.ib.isConnected():
            return
        
        try:
            # 계좌 요약 정보 요청
            account_values = self.ib.accountSummary()
            
            # 필요한 정보 추출
            info: Dict[str, any] = {
                # 계좌 ID (비어있으면 첫 번째 계좌 사용)
                "account": self.account or (
                    self.ib.managedAccounts()[0] 
                    if self.ib.managedAccounts() 
                    else "N/A"
                ),
                "balance": 0.0,      # 순자산
                "available": 0.0,    # 가용 자금
            }
            
            # 계좌 값 파싱
            for av in account_values:
                if av.tag == "NetLiquidation":
                    info["balance"] = float(av.value)
                elif av.tag == "AvailableFunds":
                    info["available"] = float(av.value)
            
            # GUI에 전달
            self.account_update.emit(info)
            self.log_message.emit(f"💰 계좌 정보: ${info['balance']:,.2f}")
            
        except Exception as e:
            self.log_message.emit(f"⚠️ 계좌 정보 조회 실패: {str(e)}")
    
    def _disconnect(self) -> None:
        """
        연결 해제 (내부용)
        
        IB Gateway와의 연결을 안전하게 종료합니다.
        """
        if self.ib and self.ib.isConnected():
            self.ib.disconnect()
            self.log_message.emit("🔌 IBKR 연결 해제됨")
        
        self._is_connected = False
        self.connected.emit(False)
    
    # ═══════════════════════════════════════════════════════════════════
    # 공개 메서드 (외부에서 호출)
    # ═══════════════════════════════════════════════════════════════════
    
    def stop(self) -> None:
        """
        연결 중지 및 스레드 종료
        
        이 메서드를 호출하면:
        1. 이벤트 루프가 중단됨
        2. 모든 시세 구독이 해제됨
        3. IB Gateway 연결이 해제됨
        4. 스레드가 종료됨
        """
        self._is_running = False
        self.log_message.emit("⏹ 연결 중지 요청됨...")
        
        # 스레드 종료 대기 (최대 5초)
        self.wait(5000)
    
    def is_connected(self) -> bool:
        """
        현재 연결 상태 반환
        
        Returns:
            bool: True면 연결됨, False면 연결 안 됨
        """
        return self._is_connected
    
    def get_ib(self) -> Optional[IB]:
        """
        IB 객체 반환 (다른 모듈에서 고급 기능 사용 시)
        
        Returns:
            IB: ib_insync IB 객체 (연결 안 됐으면 None)
        
        Warning:
            이 객체를 직접 사용할 때는 스레드 안전성에 주의하세요.
        """
        return self.ib if self._is_connected else None
    
    # ═══════════════════════════════════════════════════════════════════
    # 실시간 시세 구독
    # ═══════════════════════════════════════════════════════════════════
    
    def subscribe_ticker(self, symbols: List[str]) -> None:
        """
        실시간 시세 구독 시작
        
        지정한 심볼들의 실시간 가격을 구독합니다.
        가격이 변경될 때마다 price_update 시그널이 발생합니다.
        
        Args:
            symbols: 구독할 심볼 리스트 (예: ["SPY", "QQQ", "AAPL"])
        
        Example:
            >>> connector.subscribe_ticker(["SPY"])
            >>> # 이후 price_update 시그널로 가격 수신
        """
        if not self.ib or not self.ib.isConnected():
            self.log_message.emit("❌ 시세 구독 실패: IBKR 연결 안됨")
            return
        
        for symbol in symbols:
            # 이미 구독 중이면 건너뜀
            if symbol in self._subscribed_tickers:
                continue
            
            try:
                # Stock 계약 생성
                # SMART: IB의 스마트 라우팅 (최적 거래소 자동 선택)
                contract = Stock(symbol, "SMART", "USD")
                
                # 시세 구독 요청
                # reqMktData 파라미터:
                #   contract: 구독할 계약
                #   "": genericTickList (기본 틱만)
                #   False: snapshot 아님 (스트리밍)
                #   False: regulatorySnapshot 아님
                #   []: 추가 옵션 없음
                ticker = self.ib.reqMktData(
                    contract,
                    "",
                    False,
                    False,
                    []
                )
                
                # 가격 업데이트 콜백 등록
                ticker.updateEvent += self._on_price_update
                
                # 구독 목록에 추가
                self._subscribed_tickers[symbol] = ticker
                
                self.log_message.emit(f"📡 시세 구독 시작: {symbol}")
                
            except Exception as e:
                self.log_message.emit(f"⚠️ {symbol} 구독 실패: {str(e)}")
    
    def unsubscribe_ticker(self, symbol: str) -> None:
        """
        시세 구독 해제
        
        Args:
            symbol: 구독 해제할 심볼
        """
        if symbol not in self._subscribed_tickers:
            return
        
        try:
            ticker = self._subscribed_tickers.pop(symbol)
            if self.ib and self.ib.isConnected():
                self.ib.cancelMktData(ticker.contract)
            self.log_message.emit(f"📴 시세 구독 해제: {symbol}")
        except Exception as e:
            self.log_message.emit(f"⚠️ {symbol} 구독 해제 실패: {str(e)}")
    
    def unsubscribe_all(self) -> None:
        """모든 시세 구독 해제"""
        symbols = list(self._subscribed_tickers.keys())
        for symbol in symbols:
            self.unsubscribe_ticker(symbol)
    
    def _on_price_update(self, ticker: Ticker) -> None:
        """
        시세 업데이트 콜백 (내부용)
        
        ib_insync에서 가격이 변경될 때마다 이 메서드가 호출됩니다.
        받은 데이터를 딕셔너리로 변환하여 price_update 시그널로 전달합니다.
        
        Args:
            ticker: ib_insync Ticker 객체
        """
        try:
            symbol = ticker.contract.symbol
            
            # 시세 데이터 딕셔너리 생성
            data = {
                "symbol": symbol,
                "last": ticker.last if ticker.last else 0.0,    # 최근 체결가
                "bid": ticker.bid if ticker.bid else 0.0,       # 매수 호가
                "ask": ticker.ask if ticker.ask else 0.0,       # 매도 호가
                "volume": ticker.volume if ticker.volume else 0, # 거래량
                "high": ticker.high if ticker.high else 0.0,    # 고가
                "low": ticker.low if ticker.low else 0.0,       # 저가
                "close": ticker.close if ticker.close else 0.0, # 전일 종가
            }
            
            # GUI에 전달
            self.price_update.emit(data)
            
        except Exception:
            # 시세 업데이트가 매우 빈번하므로 에러 로깅 생략
            pass
    
    # ═══════════════════════════════════════════════════════════════════
    # 주문 관리 (Step 3.1 OMS)
    # ═══════════════════════════════════════════════════════════════════
    
    def place_market_order(
        self, 
        symbol: str, 
        qty: int, 
        action: str = "BUY"
    ) -> Optional[int]:
        """
        시장가 주문 배치
        
        Args:
            symbol: 종목 심볼 (예: "AAPL")
            qty: 수량
            action: "BUY" 또는 "SELL"
            
        Returns:
            int: 주문 ID (실패 시 None)
            
        Example:
            >>> order_id = connector.place_market_order("AAPL", 10, "BUY")
        """
        if not self.ib or not self.ib.isConnected():
            self.log_message.emit("❌ 주문 실패: IBKR 연결 안됨")
            return None
        
        try:
            # Stock 계약 생성
            contract = Stock(symbol, "SMART", "USD")
            
            # 시장가 주문 생성
            order = MarketOrder(action, qty)
            
            # 주문 배치
            trade = self.ib.placeOrder(contract, order)
            order_id = trade.order.orderId
            
            # 주문 추적에 추가
            self._active_orders[order_id] = trade
            
            # 체결 콜백 등록
            trade.filledEvent += lambda t: self._on_order_filled(t)
            trade.cancelledEvent += lambda t: self._on_order_cancelled(t)
            
            # Signal 발생
            self.order_placed.emit({
                "order_id": order_id,
                "symbol": symbol,
                "action": action,
                "qty": qty,
                "order_type": "MKT",
                "status": "Submitted",
            })
            
            self.log_message.emit(f"📤 주문 접수: {action} {qty} {symbol} @ MKT (ID: {order_id})")
            return order_id
            
        except Exception as e:
            self.log_message.emit(f"❌ 주문 실패: {str(e)}")
            self.order_error.emit("", str(e))
            return None
    
    def place_stop_order(
        self, 
        symbol: str, 
        qty: int, 
        stop_price: float,
        action: str = "SELL",
        oca_group: Optional[str] = None
    ) -> Optional[int]:
        """
        Stop Loss 주문 배치
        
        Args:
            symbol: 종목 심볼
            qty: 수량
            stop_price: Stop 가격
            action: "BUY" 또는 "SELL" (기본: SELL)
            oca_group: OCA 그룹 ID (선택)
            
        Returns:
            int: 주문 ID (실패 시 None)
        """
        if not self.ib or not self.ib.isConnected():
            self.log_message.emit("❌ Stop 주문 실패: IBKR 연결 안됨")
            return None
        
        try:
            contract = Stock(symbol, "SMART", "USD")
            
            # Stop 주문 생성
            order = StopOrder(action, qty, stop_price)
            
            # OCA 그룹 설정 (있으면)
            if oca_group:
                order.ocaGroup = oca_group
                order.ocaType = 1  # Cancel on Fill
            
            trade = self.ib.placeOrder(contract, order)
            order_id = trade.order.orderId
            
            self._active_orders[order_id] = trade
            
            # 콜백 등록
            trade.filledEvent += lambda t: self._on_order_filled(t)
            trade.cancelledEvent += lambda t: self._on_order_cancelled(t)
            
            # OCA 그룹 추적
            if oca_group:
                if oca_group not in self._oca_groups:
                    self._oca_groups[oca_group] = []
                self._oca_groups[oca_group].append(order_id)
            
            self.order_placed.emit({
                "order_id": order_id,
                "symbol": symbol,
                "action": action,
                "qty": qty,
                "order_type": "STP",
                "stop_price": stop_price,
                "oca_group": oca_group,
                "status": "Submitted",
            })
            
            self.log_message.emit(f"📤 Stop 주문: {action} {qty} {symbol} @ ${stop_price:.2f} (ID: {order_id})")
            return order_id
            
        except Exception as e:
            self.log_message.emit(f"❌ Stop 주문 실패: {str(e)}")
            return None
    
    def place_oca_group(
        self, 
        symbol: str, 
        qty: int, 
        entry_price: float,
        stop_loss_pct: float = -2.0,
        profit_target_pct: float = 8.0,
    ) -> Optional[str]:
        """
        OCA (One-Cancels-All) 그룹 주문 배치
        
        진입 즉시 3개 주문을 OCA로 묶어 전송합니다.
        하나가 체결되면 나머지는 자동 취소됩니다.
        
        Args:
            symbol: 종목 심볼
            qty: 수량
            entry_price: 진입 가격 (Stop/Limit 계산 기준)
            stop_loss_pct: Stop Loss 비율 (기본: -2.0%)
            profit_target_pct: Profit Target 비율 (기본: 8.0%)
            
        Returns:
            str: OCA 그룹 ID (실패 시 None)
            
        Note:
            masterplan 5.1절 기준:
            - Safety Stop: -2.0%
            - Profit Target: +8.0%
        """
        if not self.ib or not self.ib.isConnected():
            self.log_message.emit("❌ OCA 그룹 실패: IBKR 연결 안됨")
            return None
        
        try:
            # OCA 그룹 ID 생성
            oca_group = f"OCA_{symbol}_{int(time.time())}"
            
            contract = Stock(symbol, "SMART", "USD")
            
            # --- 1. Stop Loss 주문 ---
            stop_price = entry_price * (1 + stop_loss_pct / 100)
            stop_order = StopOrder("SELL", qty, round(stop_price, 2))
            stop_order.ocaGroup = oca_group
            stop_order.ocaType = 1  # Cancel on Fill
            
            stop_trade = self.ib.placeOrder(contract, stop_order)
            self._active_orders[stop_trade.order.orderId] = stop_trade
            
            # --- 2. Profit Target (Limit) 주문 ---
            limit_price = entry_price * (1 + profit_target_pct / 100)
            limit_order = LimitOrder("SELL", qty, round(limit_price, 2))
            limit_order.ocaGroup = oca_group
            limit_order.ocaType = 1
            
            limit_trade = self.ib.placeOrder(contract, limit_order)
            self._active_orders[limit_trade.order.orderId] = limit_trade
            
            # OCA 그룹 추적
            self._oca_groups[oca_group] = [
                stop_trade.order.orderId,
                limit_trade.order.orderId,
            ]
            
            # 콜백 등록
            for trade in [stop_trade, limit_trade]:
                trade.filledEvent += lambda t: self._on_order_filled(t)
                trade.cancelledEvent += lambda t: self._on_order_cancelled(t)
            
            self.log_message.emit(
                f"📦 OCA 그룹 배치: {symbol} | "
                f"Stop ${stop_price:.2f} / Target ${limit_price:.2f}"
            )
            
            return oca_group
            
        except Exception as e:
            self.log_message.emit(f"❌ OCA 그룹 실패: {str(e)}")
            return None
    
    def cancel_order(self, order_id: int) -> bool:
        """
        주문 취소
        
        Args:
            order_id: 취소할 주문 ID
            
        Returns:
            bool: 성공 여부
        """
        if order_id not in self._active_orders:
            self.log_message.emit(f"⚠️ 주문 ID {order_id}를 찾을 수 없음")
            return False
        
        try:
            trade = self._active_orders[order_id]
            self.ib.cancelOrder(trade.order)
            self.log_message.emit(f"🚫 주문 취소 요청: ID {order_id}")
            return True
        except Exception as e:
            self.log_message.emit(f"❌ 주문 취소 실패: {str(e)}")
            return False
    
    def cancel_all_orders(self) -> int:
        """
        모든 미체결 주문 취소
        
        Returns:
            int: 취소 요청한 주문 수
        """
        if not self.ib or not self.ib.isConnected():
            return 0
        
        try:
            self.ib.reqGlobalCancel()
            count = len(self._active_orders)
            self.log_message.emit(f"🚫 전체 주문 취소 요청: {count}개")
            return count
        except Exception as e:
            self.log_message.emit(f"❌ 전체 취소 실패: {str(e)}")
            return 0
    
    def get_positions(self) -> List[dict]:
        """
        현재 포지션 조회
        
        Returns:
            list: 포지션 목록 [{symbol, qty, avg_price, market_value, pnl}]
        """
        if not self.ib or not self.ib.isConnected():
            return []
        
        try:
            positions = self.ib.positions()
            result = []
            
            for pos in positions:
                result.append({
                    "symbol": pos.contract.symbol,
                    "qty": pos.position,
                    "avg_price": pos.avgCost,
                    "contract": pos.contract,
                })
            
            # Signal 발생
            self.positions_update.emit(result)
            return result
            
        except Exception as e:
            self.log_message.emit(f"⚠️ 포지션 조회 실패: {str(e)}")
            return []
    
    def get_open_orders(self) -> List[dict]:
        """
        미체결 주문 조회
        
        Returns:
            list: 미체결 주문 목록
        """
        if not self.ib or not self.ib.isConnected():
            return []
        
        try:
            open_trades = self.ib.openTrades()
            result = []
            
            for trade in open_trades:
                result.append({
                    "order_id": trade.order.orderId,
                    "symbol": trade.contract.symbol,
                    "action": trade.order.action,
                    "qty": trade.order.totalQuantity,
                    "order_type": trade.order.orderType,
                    "status": trade.orderStatus.status,
                })
            
            return result
            
        except Exception as e:
            self.log_message.emit(f"⚠️ 미체결 조회 실패: {str(e)}")
            return []
    
    # ═══════════════════════════════════════════════════════════════════
    # 주문 콜백 (내부용)
    # ═══════════════════════════════════════════════════════════════════
    
    def _on_order_filled(self, trade: Trade) -> None:
        """주문 체결 콜백"""
        try:
            order_id = trade.order.orderId
            symbol = trade.contract.symbol
            
            # 활성 주문에서 제거
            if order_id in self._active_orders:
                del self._active_orders[order_id]
            
            # 체결 정보
            fill_price = trade.orderStatus.avgFillPrice
            
            self.order_filled.emit({
                "order_id": order_id,
                "symbol": symbol,
                "action": trade.order.action,
                "qty": trade.order.totalQuantity,
                "fill_price": fill_price,
                "status": "Filled",
            })
            
            self.log_message.emit(f"✅ 체결: {symbol} @ ${fill_price:.2f} (ID: {order_id})")
            
            # 포지션 업데이트
            self.get_positions()
            
        except Exception as e:
            self.log_message.emit(f"⚠️ 체결 콜백 오류: {str(e)}")
    
    def _on_order_cancelled(self, trade: Trade) -> None:
        """주문 취소 콜백"""
        try:
            order_id = trade.order.orderId
            symbol = trade.contract.symbol
            
            # 활성 주문에서 제거
            if order_id in self._active_orders:
                del self._active_orders[order_id]
            
            self.order_cancelled.emit({
                "order_id": order_id,
                "symbol": symbol,
                "status": "Cancelled",
            })
            
            self.log_message.emit(f"🚫 취소됨: {symbol} (ID: {order_id})")
            
        except Exception as e:
            self.log_message.emit(f"⚠️ 취소 콜백 오류: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════
# 단위 테스트 / 연결 테스트
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    이 스크립트를 직접 실행하면 IB Gateway 연결 테스트를 수행합니다.
    
    사전 조건:
        1. IB Gateway가 실행 중이어야 함 (Paper Trading, 포트 4002)
        2. .env 파일이 프로젝트 루트에 있어야 함
    
    실행:
        python backend/broker/ibkr_connector.py
    """
    import sys
    from PyQt6.QtCore import QCoreApplication, QTimer
    
    # Qt 애플리케이션 생성 (GUI 없이 이벤트 루프만)
    app = QCoreApplication(sys.argv)
    
    # 커넥터 생성
    connector = IBKRConnector()
    
    # 시그널 연결 (콘솔 출력)
    connector.connected.connect(lambda x: print(f"[연결 상태] {'🟢 연결됨' if x else '🔴 연결 안됨'}"))
    connector.account_update.connect(lambda x: print(f"[계좌 정보] {x}"))
    connector.price_update.connect(lambda x: print(f"[시세] {x['symbol']}: ${x['last']:.2f}"))
    connector.error.connect(lambda x: print(f"[에러] {x}"))
    connector.log_message.connect(lambda x: print(f"[로그] {x}"))
    
    # 연결 성공 시 SPY 구독
    def on_connected(is_connected: bool):
        if is_connected:
            connector.subscribe_ticker(["SPY"])
    
    connector.connected.connect(on_connected)
    
    # 연결 시작
    connector.start()
    
    # 15초 후 종료
    def shutdown():
        print("\n--- 테스트 종료 ---")
        connector.stop()
        app.quit()
    
    QTimer.singleShot(15000, shutdown)
    
    print("=== IBKR Connector 테스트 시작 ===")
    print("IB Gateway가 실행 중이어야 합니다. (Paper Trading, 포트 4002)")
    print("15초 후 자동 종료됩니다.\n")
    
    sys.exit(app.exec())
