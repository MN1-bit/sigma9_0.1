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
from ib_insync import IB, util, Stock, Ticker

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
