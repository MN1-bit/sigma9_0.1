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
from typing import Optional, Dict, List, Tuple
from dotenv import load_dotenv

# ib_insync - IBKR API 래퍼
# 참고: https://ib-insync.readthedocs.io/
from ib_insync import IB, util, Stock, MarketOrder, StopOrder, LimitOrder, Trade, Order
import time
import threading
from typing import Callable

# ═══════════════════════════════════════════════════════════════════════════
# [02-003] PyQt6 의존성 제거
# ═══════════════════════════════════════════════════════════════════════════
#
# 📌 리팩터링 배경:
#   - Backend Layer가 GUI 프레임워크에 의존 → Layer 경계 위반
#   - 테스트 시 PyQt6 환경 필수 → 테스트 복잡도 증가
#
# 📌 변경 사항:
#   - QThread → threading.Thread
#   - pyqtSignal → Callback 패턴
#   - Frontend에서 IBKREventAdapter가 callback을 Signal로 변환
#
# ═══════════════════════════════════════════════════════════════════════════

# .env 파일에서 환경 변수 로드
# 프로젝트 루트의 .env 파일을 자동으로 찾아서 로드합니다
load_dotenv()


# ═══════════════════════════════════════════════════════════════════════════
# Callback Type Aliases (가독성용)
# ═══════════════════════════════════════════════════════════════════════════
OnConnectedCallback = Callable[[bool], None]
OnAccountUpdateCallback = Callable[[dict], None]
OnErrorCallback = Callable[[str], None]
OnLogMessageCallback = Callable[[str], None]
OnOrderPlacedCallback = Callable[[dict], None]
OnOrderFilledCallback = Callable[[dict], None]
OnOrderCancelledCallback = Callable[[dict], None]
OnOrderErrorCallback = Callable[[str, str], None]
OnPositionsUpdateCallback = Callable[[list], None]


# ═══════════════════════════════════════════════════════════════════════════
# IBKRConnector 클래스
# ═══════════════════════════════════════════════════════════════════════════


class IBKRConnector:
    """
    IBKR 연결 커넥터 (순수 Python)

    백그라운드 스레드에서 IB Gateway/TWS에 연결하고,
    Callback 패턴으로 이벤트를 외부에 전달합니다.

    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5 - Explain Like I'm 5):
    ═══════════════════════════════════════════════════════════════════════
    이 클래스는 "주식 시장 라디오"와 같습니다.

    1. 라디오를 켠다 (connect) → IB Gateway에 연결
    2. 채널을 맞춘다 (subscribe) → SPY, QQQ 등 원하는 종목 선택
    3. 소리가 들린다 (callback) → 실시간 가격이 계속 들어옴
    4. 라디오를 끈다 (stop) → 연결 종료

    ═══════════════════════════════════════════════════════════════════════
    Callbacks (이벤트 핸들러):
    ═══════════════════════════════════════════════════════════════════════

    - on_connected(bool): 연결 상태가 변경될 때 호출
        - True: 연결 성공
        - False: 연결 해제 또는 실패

    - on_account_update(dict): 계좌 정보가 업데이트될 때 호출
        - {"account": "DU...", "balance": 100000.0, "available": 95000.0}

    - on_error(str): 에러가 발생했을 때 호출
        - "❌ 연결 오류: ..."

    - on_log_message(str): 로그 메시지 (디버깅/상태 표시용)
        - "🔌 IBKR 연결 시도 중..."

    ═══════════════════════════════════════════════════════════════════════
    Configuration (.env 파일):
    ═══════════════════════════════════════════════════════════════════════

    IB_HOST=127.0.0.1      # IB Gateway 호스트 (기본: 로컬)
    IB_PORT=4002           # 포트 (Paper: 4002, Live: 4001)
    IB_CLIENT_ID=1         # 클라이언트 ID (고유해야 함)
    IB_ACCOUNT=            # 계좌 ID (선택, 비워두면 자동 감지)

    ═══════════════════════════════════════════════════════════════════════
    사용 예시 (Frontend Adapter와 함께):
    ═══════════════════════════════════════════════════════════════════════

    # Backend에서 커넥터 생성
    connector = IBKRConnector()

    # Frontend Adapter에서 callback 등록
    connector.set_on_connected(adapter._on_connected)
    connector.set_on_account_update(adapter._on_account_update)

    # 연결 시작
    connector.start()
    """

    def __init__(self) -> None:
        """
        커넥터 초기화

        .env 파일에서 연결 설정을 로드하고, 내부 상태를 초기화합니다.
        이 시점에서는 아직 연결하지 않습니다 (start() 호출 시 연결).
        """
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

        # --- 스레드 관리 [02-003] ---
        # threading.Thread로 백그라운드 실행
        self._thread: Optional[threading.Thread] = None

        # --- 주문 추적 (Step 3.1 OMS) ---
        # 활성 주문 추적: order_id -> Trade 객체
        self._active_orders: Dict[int, Trade] = {}
        # OCA 그룹 추적: oca_group_id -> [order_ids]
        self._oca_groups: Dict[str, List[int]] = {}

        # ═══════════════════════════════════════════════════════════════
        # [02-003] Callback 속성 초기화
        # ═══════════════════════════════════════════════════════════════
        # Frontend의 IBKREventAdapter가 이 callback을 등록하여
        # pyqtSignal로 변환합니다.
        # ═══════════════════════════════════════════════════════════════
        self._on_connected: Optional[OnConnectedCallback] = None
        self._on_account_update: Optional[OnAccountUpdateCallback] = None
        self._on_error: Optional[OnErrorCallback] = None
        self._on_log_message: Optional[OnLogMessageCallback] = None
        self._on_order_placed: Optional[OnOrderPlacedCallback] = None
        self._on_order_filled: Optional[OnOrderFilledCallback] = None
        self._on_order_cancelled: Optional[OnOrderCancelledCallback] = None
        self._on_order_error: Optional[OnOrderErrorCallback] = None
        self._on_positions_update: Optional[OnPositionsUpdateCallback] = None

    # ═══════════════════════════════════════════════════════════════════
    # [02-003] Callback Setter Methods
    # ═══════════════════════════════════════════════════════════════════
    # Frontend의 IBKREventAdapter가 callback을 등록합니다.
    # ═══════════════════════════════════════════════════════════════════

    def set_on_connected(self, callback: OnConnectedCallback) -> None:
        """연결 상태 변경 callback 설정"""
        self._on_connected = callback

    def set_on_account_update(self, callback: OnAccountUpdateCallback) -> None:
        """계좌 업데이트 callback 설정"""
        self._on_account_update = callback

    def set_on_error(self, callback: OnErrorCallback) -> None:
        """에러 callback 설정"""
        self._on_error = callback

    def set_on_log_message(self, callback: OnLogMessageCallback) -> None:
        """로그 메시지 callback 설정"""
        self._on_log_message = callback

    def set_on_order_placed(self, callback: OnOrderPlacedCallback) -> None:
        """주문 접수 callback 설정"""
        self._on_order_placed = callback

    def set_on_order_filled(self, callback: OnOrderFilledCallback) -> None:
        """주문 체결 callback 설정"""
        self._on_order_filled = callback

    def set_on_order_cancelled(self, callback: OnOrderCancelledCallback) -> None:
        """주문 취소 callback 설정"""
        self._on_order_cancelled = callback

    def set_on_order_error(self, callback: OnOrderErrorCallback) -> None:
        """주문 에러 callback 설정"""
        self._on_order_error = callback

    def set_on_positions_update(self, callback: OnPositionsUpdateCallback) -> None:
        """포지션 업데이트 callback 설정"""
        self._on_positions_update = callback

    # ═══════════════════════════════════════════════════════════════════
    # [02-003] Callback 호출 헬퍼 (emit 대체)
    # ═══════════════════════════════════════════════════════════════════

    def _emit_connected(self, is_connected: bool) -> None:
        """연결 상태 변경 알림 (callback 호출)"""
        if self._on_connected:
            self._on_connected(is_connected)

    def _emit_account_update(self, info: dict) -> None:
        """계좌 업데이트 알림"""
        if self._on_account_update:
            self._on_account_update(info)

    def _emit_error(self, message: str) -> None:
        """에러 알림"""
        if self._on_error:
            self._on_error(message)

    def _emit_log_message(self, message: str) -> None:
        """로그 메시지 알림"""
        if self._on_log_message:
            self._on_log_message(message)

    def _emit_order_placed(self, order_info: dict) -> None:
        """주문 접수 알림"""
        if self._on_order_placed:
            self._on_order_placed(order_info)

    def _emit_order_filled(self, fill_info: dict) -> None:
        """주문 체결 알림"""
        if self._on_order_filled:
            self._on_order_filled(fill_info)

    def _emit_order_cancelled(self, cancel_info: dict) -> None:
        """주문 취소 알림"""
        if self._on_order_cancelled:
            self._on_order_cancelled(cancel_info)

    def _emit_order_error(self, order_id: str, message: str) -> None:
        """주문 에러 알림"""
        if self._on_order_error:
            self._on_order_error(order_id, message)

    def _emit_positions_update(self, positions: list) -> None:
        """포지션 업데이트 알림"""
        if self._on_positions_update:
            self._on_positions_update(positions)

    # ═══════════════════════════════════════════════════════════════════
    # 스레드 메인 루프
    # ═══════════════════════════════════════════════════════════════════

    def _run(self) -> None:
        """
        스레드 메인 루프 (start() 호출 시 백그라운드에서 실행)

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
        self._emit_log_message("🔌 IBKR 연결 시도 중...")

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
                    self._emit_log_message(f"📡 연결 시도 {attempt}/{max_retries}...")

                    # IB Gateway에 연결 (타임아웃 10초)
                    # host: IB Gateway 주소 (보통 127.0.0.1)
                    # port: Paper 4002, Live 4001
                    # clientId: 고유해야 함 (같은 ID로 중복 연결 불가)
                    self.ib.connect(
                        host=self.host,
                        port=self.port,
                        clientId=self.client_id,
                        timeout=10,
                    )

                    # 연결 성공!
                    self._is_connected = True
                    self._emit_connected(True)
                    self._emit_log_message(f"✅ IBKR 연결 성공! (포트: {self.port})")

                    # 초기 계좌 정보 조회
                    self._fetch_account_info()

                    # 재시도 루프 탈출
                    break

                except Exception as e:
                    self._emit_log_message(f"⚠️ 연결 실패: {str(e)}")

                    if attempt < max_retries:
                        # Exponential Backoff: 1초, 2초, 4초...
                        # 네트워크 문제는 잠시 후 해결될 수 있으므로
                        # 점점 길게 기다리면서 재시도
                        wait_time = 2 ** (attempt - 1)
                        self._emit_log_message(f"⏳ {wait_time}초 후 재시도...")
                        time.sleep(wait_time)  # 초 단위
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
            self._emit_error(f"❌ 연결 오류: {str(e)}")
            self._is_connected = False
            self._emit_connected(False)

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
                "account": self.account
                or (
                    self.ib.managedAccounts()[0] if self.ib.managedAccounts() else "N/A"
                ),
                "balance": 0.0,  # 순자산
                "available": 0.0,  # 가용 자금
            }

            # 계좌 값 파싱
            for av in account_values:
                if av.tag == "NetLiquidation":
                    info["balance"] = float(av.value)
                elif av.tag == "AvailableFunds":
                    info["available"] = float(av.value)

            # GUI에 전달
            self._emit_account_update(info)
            self._emit_log_message(f"💰 계좌 정보: ${info['balance']:,.2f}")

        except Exception as e:
            self._emit_log_message(f"⚠️ 계좌 정보 조회 실패: {str(e)}")

    def _disconnect(self) -> None:
        """
        연결 해제 (내부용)

        IB Gateway와의 연결을 안전하게 종료합니다.
        """
        if self.ib and self.ib.isConnected():
            self.ib.disconnect()
            self._emit_log_message("🔌 IBKR 연결 해제됨")

        self._is_connected = False
        self._emit_connected(False)

    # ═══════════════════════════════════════════════════════════════════
    # 공개 메서드 (외부에서 호출)
    # ═══════════════════════════════════════════════════════════════════

    def start(self) -> None:
        """
        연결 시작 (백그라운드 스레드에서 실행)

        이 메서드를 호출하면 별도 스레드에서 run()이 실행됩니다.
        GUI 메인 스레드가 멈추지 않도록 분리하여 실행합니다.

        Example:
            >>> connector = IBKRConnector()
            >>> connector.set_on_connected(on_connected_callback)
            >>> connector.start()
        """
        if self._thread and self._thread.is_alive():
            self._emit_log_message("⚠️ 이미 실행 중입니다")
            return

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

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
        self._emit_log_message("⏹ 연결 중지 요청됨...")

        # 스레드 종료 대기 (최대 5초)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

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
    # [DEPRECATED] 실시간 시세 구독 - Massive WebSocket으로 대체 (Phase 4.A.0)
    #
    # 기존 메서드들 제거됨:
    #   - subscribe_ticker()
    #   - unsubscribe_ticker()
    #   - unsubscribe_all()
    #   - _on_price_update()
    #
    # 실시간 시세는 이제 backend/data/massive_ws_client.py 사용
    # ═══════════════════════════════════════════════════════════════════

    # ═══════════════════════════════════════════════════════════════════
    # 주문 관리 (Step 3.1 OMS)
    # ═══════════════════════════════════════════════════════════════════

    def place_market_order(
        self, symbol: str, qty: int, action: str = "BUY"
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
            self._emit_log_message("❌ 주문 실패: IBKR 연결 안됨")
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
            self._emit_order_placed(
                {
                    "order_id": order_id,
                    "symbol": symbol,
                    "action": action,
                    "qty": qty,
                    "order_type": "MKT",
                    "status": "Submitted",
                }
            )

            self._emit_log_message(
                f"📤 주문 접수: {action} {qty} {symbol} @ MKT (ID: {order_id})"
            )
            return order_id

        except Exception as e:
            self._emit_log_message(f"❌ 주문 실패: {str(e)}")
            self._emit_order_error("", str(e))
            return None

    def place_stop_order(
        self,
        symbol: str,
        qty: int,
        stop_price: float,
        action: str = "SELL",
        oca_group: Optional[str] = None,
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
            self._emit_log_message("❌ Stop 주문 실패: IBKR 연결 안됨")
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

            self._emit_order_placed(
                {
                    "order_id": order_id,
                    "symbol": symbol,
                    "action": action,
                    "qty": qty,
                    "order_type": "STP",
                    "stop_price": stop_price,
                    "oca_group": oca_group,
                    "status": "Submitted",
                }
            )

            self._emit_log_message(
                f"📤 Stop 주문: {action} {qty} {symbol} @ ${stop_price:.2f} (ID: {order_id})"
            )
            return order_id

        except Exception as e:
            self._emit_log_message(f"❌ Stop 주문 실패: {str(e)}")
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
            self._emit_log_message("❌ OCA 그룹 실패: IBKR 연결 안됨")
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

            self._emit_log_message(
                f"📦 OCA 그룹 배치: {symbol} | "
                f"Stop ${stop_price:.2f} / Target ${limit_price:.2f}"
            )

            return oca_group

        except Exception as e:
            self._emit_log_message(f"❌ OCA 그룹 실패: {str(e)}")
            return None

    # ═══════════════════════════════════════════════════════════════════
    # 신규 주문 타입 (10-001 리팩터링)
    # ═══════════════════════════════════════════════════════════════════

    def place_limit_order(
        self,
        symbol: str,
        qty: int,
        limit_price: float,
        action: str = "BUY",
        tif: str = "DAY",
        oca_group: Optional[str] = None,
    ) -> Optional[int]:
        """
        지정가 주문 배치

        Args:
            symbol: 종목 심볼 (예: "AAPL")
            qty: 수량
            limit_price: 지정가
            action: "BUY" 또는 "SELL"
            tif: 유효 기간 - DAY, GTC, IOC, FOK
            oca_group: OCA 그룹 ID (선택)

        Returns:
            int: 주문 ID (실패 시 None)

        Example:
            >>> order_id = connector.place_limit_order("AAPL", 10, 150.0)
        """
        if not self.ib or not self.ib.isConnected():
            self._emit_log_message("❌ Limit 주문 실패: IBKR 연결 안됨")
            return None

        try:
            contract = Stock(symbol, "SMART", "USD")
            order = LimitOrder(action, qty, limit_price)
            order.tif = tif

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

            self._emit_order_placed(
                {
                    "order_id": order_id,
                    "symbol": symbol,
                    "action": action,
                    "qty": qty,
                    "order_type": "LMT",
                    "limit_price": limit_price,
                    "tif": tif,
                    "oca_group": oca_group,
                    "status": "Submitted",
                }
            )

            self._emit_log_message(
                f"📤 Limit 주문: {action} {qty} {symbol} @ ${limit_price:.2f} "
                f"(TIF: {tif}, ID: {order_id})"
            )
            return order_id

        except Exception as e:
            self._emit_log_message(f"❌ Limit 주문 실패: {str(e)}")
            return None

    def place_stop_limit_order(
        self,
        symbol: str,
        qty: int,
        stop_price: float,
        limit_price: float,
        action: str = "SELL",
        oca_group: Optional[str] = None,
    ) -> Optional[int]:
        """
        Stop Limit 주문 배치

        Stop 가격 도달 시 Limit 주문으로 전환됨.
        슬리피지 방지에 유용 (급락 시 지정가 미만으로 체결되지 않음).

        Args:
            symbol: 종목 심볼
            qty: 수량
            stop_price: Stop 트리거 가격
            limit_price: 트리거 후 적용할 Limit 가격
            action: "BUY" 또는 "SELL" (기본: SELL)
            oca_group: OCA 그룹 ID (선택)

        Returns:
            int: 주문 ID (실패 시 None)

        Example:
            # Stop $95 도달 시 $94 이상에서만 매도
            >>> order_id = connector.place_stop_limit_order("AAPL", 10, 95.0, 94.0)
        """
        if not self.ib or not self.ib.isConnected():
            self._emit_log_message("❌ Stop Limit 주문 실패: IBKR 연결 안됨")
            return None

        try:
            contract = Stock(symbol, "SMART", "USD")

            # Stop Limit 주문 수동 생성
            order = Order()
            order.action = action
            order.totalQuantity = qty
            order.orderType = "STP LMT"
            order.auxPrice = stop_price  # Stop 가격
            order.lmtPrice = limit_price  # Limit 가격

            if oca_group:
                order.ocaGroup = oca_group
                order.ocaType = 1

            trade = self.ib.placeOrder(contract, order)
            order_id = trade.order.orderId

            self._active_orders[order_id] = trade

            trade.filledEvent += lambda t: self._on_order_filled(t)
            trade.cancelledEvent += lambda t: self._on_order_cancelled(t)

            if oca_group:
                if oca_group not in self._oca_groups:
                    self._oca_groups[oca_group] = []
                self._oca_groups[oca_group].append(order_id)

            self._emit_order_placed(
                {
                    "order_id": order_id,
                    "symbol": symbol,
                    "action": action,
                    "qty": qty,
                    "order_type": "STP LMT",
                    "stop_price": stop_price,
                    "limit_price": limit_price,
                    "oca_group": oca_group,
                    "status": "Submitted",
                }
            )

            self._emit_log_message(
                f"📤 Stop Limit: {action} {qty} {symbol} @ "
                f"Stop ${stop_price:.2f} → Limit ${limit_price:.2f} (ID: {order_id})"
            )
            return order_id

        except Exception as e:
            self._emit_log_message(f"❌ Stop Limit 실패: {str(e)}")
            return None

    def place_trailing_stop_order(
        self,
        symbol: str,
        qty: int,
        trail_amount: float,
        action: str = "SELL",
        oca_group: Optional[str] = None,
    ) -> Optional[int]:
        """
        IBKR 네이티브 Trailing Stop 주문 배치

        서버 사이드에서 자동으로 고점을 추적합니다.
        클라이언트에서 틱마다 폴링할 필요가 없어 100ms 배칭에 영향 없음.

        Args:
            symbol: 종목 심볼
            qty: 수량
            trail_amount: 트레일 금액 (달러 단위, 예: ATR × 1.5)
            action: "BUY" 또는 "SELL" (기본: SELL)
            oca_group: OCA 그룹 ID (선택)

        Returns:
            int: 주문 ID (실패 시 None)

        Example:
            # ATR이 $1.5일 때 $2.25 트레일
            >>> order_id = connector.place_trailing_stop_order("AAPL", 10, 2.25)
        """
        if not self.ib or not self.ib.isConnected():
            self._emit_log_message("❌ Trailing Stop 주문 실패: IBKR 연결 안됨")
            return None

        try:
            contract = Stock(symbol, "SMART", "USD")

            # TRAIL 주문 생성
            order = Order()
            order.action = action
            order.totalQuantity = qty
            order.orderType = "TRAIL"
            order.auxPrice = trail_amount  # Trail amount (달러)

            if oca_group:
                order.ocaGroup = oca_group
                order.ocaType = 1

            trade = self.ib.placeOrder(contract, order)
            order_id = trade.order.orderId

            self._active_orders[order_id] = trade

            trade.filledEvent += lambda t: self._on_order_filled(t)
            trade.cancelledEvent += lambda t: self._on_order_cancelled(t)

            if oca_group:
                if oca_group not in self._oca_groups:
                    self._oca_groups[oca_group] = []
                self._oca_groups[oca_group].append(order_id)

            self._emit_order_placed(
                {
                    "order_id": order_id,
                    "symbol": symbol,
                    "action": action,
                    "qty": qty,
                    "order_type": "TRAIL",
                    "trail_amount": trail_amount,
                    "oca_group": oca_group,
                    "status": "Submitted",
                }
            )

            self._emit_log_message(
                f"📤 Trailing Stop: {action} {qty} {symbol} | "
                f"Trail ${trail_amount:.2f} (ID: {order_id})"
            )
            return order_id

        except Exception as e:
            self._emit_log_message(f"❌ Trailing Stop 실패: {str(e)}")
            return None

    def place_trailing_stop_limit_order(
        self,
        symbol: str,
        qty: int,
        trail_amount: float,
        limit_offset: float,
        action: str = "SELL",
    ) -> Optional[int]:
        """
        Trailing Stop Limit 주문 배치

        Trailing Stop이 트리거되면 Limit 주문으로 전환.
        급락 시 슬리피지를 방지하면서 수익을 보호.

        Args:
            symbol: 종목 심볼
            qty: 수량
            trail_amount: 트레일 금액 (달러 단위)
            limit_offset: Stop 트리거 후 Limit 오프셋 (달러 단위)
            action: "BUY" 또는 "SELL" (기본: SELL)

        Returns:
            int: 주문 ID (실패 시 None)

        Example:
            # $2 트레일, 트리거 시 Stop 가격에서 $0.50 아래까지 매도 허용
            >>> order_id = connector.place_trailing_stop_limit_order(
            ...     "AAPL", 10, 2.0, 0.50
            ... )
        """
        if not self.ib or not self.ib.isConnected():
            self._emit_log_message("❌ Trailing Stop Limit 실패: IBKR 연결 안됨")
            return None

        try:
            contract = Stock(symbol, "SMART", "USD")

            order = Order()
            order.action = action
            order.totalQuantity = qty
            order.orderType = "TRAIL LIMIT"
            order.auxPrice = trail_amount  # Trail amount
            order.trailStopPrice = trail_amount  # 초기 trail stop price
            order.lmtPriceOffset = limit_offset  # Limit offset

            trade = self.ib.placeOrder(contract, order)
            order_id = trade.order.orderId

            self._active_orders[order_id] = trade

            trade.filledEvent += lambda t: self._on_order_filled(t)
            trade.cancelledEvent += lambda t: self._on_order_cancelled(t)

            self._emit_order_placed(
                {
                    "order_id": order_id,
                    "symbol": symbol,
                    "action": action,
                    "qty": qty,
                    "order_type": "TRAIL LIMIT",
                    "trail_amount": trail_amount,
                    "limit_offset": limit_offset,
                    "status": "Submitted",
                }
            )

            self._emit_log_message(
                f"📤 Trailing Stop Limit: {action} {qty} {symbol} | "
                f"Trail ${trail_amount:.2f}, Offset ${limit_offset:.2f} (ID: {order_id})"
            )
            return order_id

        except Exception as e:
            self._emit_log_message(f"❌ Trailing Stop Limit 실패: {str(e)}")
            return None

    def place_moc_order(
        self,
        symbol: str,
        qty: int,
        action: str = "SELL",
    ) -> Optional[int]:
        """
        Market-on-Close 주문 배치

        장 마감 시 시장가로 체결.
        EOD (End of Day) 청산에 유용.

        Args:
            symbol: 종목 심볼
            qty: 수량
            action: "BUY" 또는 "SELL" (기본: SELL)

        Returns:
            int: 주문 ID (실패 시 None)

        Note:
            MOC 주문은 보통 장 마감 15분 전까지만 제출 가능
        """
        if not self.ib or not self.ib.isConnected():
            self._emit_log_message("❌ MOC 주문 실패: IBKR 연결 안됨")
            return None

        try:
            contract = Stock(symbol, "SMART", "USD")

            order = Order()
            order.action = action
            order.totalQuantity = qty
            order.orderType = "MOC"

            trade = self.ib.placeOrder(contract, order)
            order_id = trade.order.orderId

            self._active_orders[order_id] = trade

            trade.filledEvent += lambda t: self._on_order_filled(t)
            trade.cancelledEvent += lambda t: self._on_order_cancelled(t)

            self._emit_order_placed(
                {
                    "order_id": order_id,
                    "symbol": symbol,
                    "action": action,
                    "qty": qty,
                    "order_type": "MOC",
                    "status": "Submitted",
                }
            )

            self._emit_log_message(
                f"📤 MOC 주문: {action} {qty} {symbol} @ 장 마감 (ID: {order_id})"
            )
            return order_id

        except Exception as e:
            self._emit_log_message(f"❌ MOC 주문 실패: {str(e)}")
            return None

    def place_loc_order(
        self,
        symbol: str,
        qty: int,
        limit_price: float,
        action: str = "SELL",
    ) -> Optional[int]:
        """
        Limit-on-Close 주문 배치

        장 마감 시 지정가 이상/이하로만 체결.
        종가 체결을 원하지만 불리한 가격을 피하고 싶을 때 유용.

        Args:
            symbol: 종목 심볼
            qty: 수량
            limit_price: 최소/최대 체결 가격
            action: "BUY" 또는 "SELL" (기본: SELL)

        Returns:
            int: 주문 ID (실패 시 None)
        """
        if not self.ib or not self.ib.isConnected():
            self._emit_log_message("❌ LOC 주문 실패: IBKR 연결 안됨")
            return None

        try:
            contract = Stock(symbol, "SMART", "USD")

            order = Order()
            order.action = action
            order.totalQuantity = qty
            order.orderType = "LOC"
            order.lmtPrice = limit_price

            trade = self.ib.placeOrder(contract, order)
            order_id = trade.order.orderId

            self._active_orders[order_id] = trade

            trade.filledEvent += lambda t: self._on_order_filled(t)
            trade.cancelledEvent += lambda t: self._on_order_cancelled(t)

            self._emit_order_placed(
                {
                    "order_id": order_id,
                    "symbol": symbol,
                    "action": action,
                    "qty": qty,
                    "order_type": "LOC",
                    "limit_price": limit_price,
                    "status": "Submitted",
                }
            )

            self._emit_log_message(
                f"📤 LOC 주문: {action} {qty} {symbol} @ ${limit_price:.2f} "
                f"장 마감 (ID: {order_id})"
            )
            return order_id

        except Exception as e:
            self._emit_log_message(f"❌ LOC 주문 실패: {str(e)}")
            return None

    def place_bracket_order(
        self,
        symbol: str,
        qty: int,
        entry_price: float,
        take_profit_price: float,
        stop_loss_price: float,
        action: str = "BUY",
    ) -> Optional[Tuple[int, int, int]]:
        """
        ib_insync 네이티브 Bracket 주문 배치

        3개 주문이 연결됨: Parent (진입) + Take Profit + Stop Loss
        Parent 체결 시 자식 주문 활성화.
        하나의 자식이 체결되면 다른 자식은 자동 취소 (OCA).

        Args:
            symbol: 종목 심볼
            qty: 수량
            entry_price: 진입 지정가
            take_profit_price: Take Profit 지정가
            stop_loss_price: Stop Loss 가격
            action: "BUY" 또는 "SELL" (기본: BUY)

        Returns:
            Tuple[int, int, int]: (parent_id, tp_id, sl_id) 또는 None

        Example:
            # $100에 매수, $110 익절, $95 손절
            >>> ids = connector.place_bracket_order(
            ...     "AAPL", 10, 100.0, 110.0, 95.0
            ... )
            >>> parent_id, tp_id, sl_id = ids
        """
        if not self.ib or not self.ib.isConnected():
            self._emit_log_message("❌ Bracket 주문 실패: IBKR 연결 안됨")
            return None

        try:
            contract = Stock(symbol, "SMART", "USD")

            # ib_insync 네이티브 bracketOrder 사용
            # 자동으로 OCA 그룹을 구성하고 Parent-Child 관계 설정
            bracket = self.ib.bracketOrder(
                action=action,
                quantity=qty,
                limitPrice=entry_price,
                takeProfitPrice=take_profit_price,
                stopLossPrice=stop_loss_price,
            )

            order_ids = []
            for order in bracket:
                trade = self.ib.placeOrder(contract, order)
                order_id = trade.order.orderId
                order_ids.append(order_id)

                self._active_orders[order_id] = trade
                trade.filledEvent += lambda t: self._on_order_filled(t)
                trade.cancelledEvent += lambda t: self._on_order_cancelled(t)

            parent_id, tp_id, sl_id = order_ids

            self._emit_order_placed(
                {
                    "order_id": parent_id,
                    "symbol": symbol,
                    "action": action,
                    "qty": qty,
                    "order_type": "BRACKET",
                    "entry_price": entry_price,
                    "take_profit_price": take_profit_price,
                    "stop_loss_price": stop_loss_price,
                    "child_orders": [tp_id, sl_id],
                    "status": "Submitted",
                }
            )

            self._emit_log_message(
                f"📦 Bracket 주문: {action} {qty} {symbol} @ ${entry_price:.2f} | "
                f"TP ${take_profit_price:.2f} / SL ${stop_loss_price:.2f} "
                f"(Parent: {parent_id})"
            )
            return (parent_id, tp_id, sl_id)

        except Exception as e:
            self._emit_log_message(f"❌ Bracket 주문 실패: {str(e)}")
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
            self._emit_log_message(f"⚠️ 주문 ID {order_id}를 찾을 수 없음")
            return False

        try:
            trade = self._active_orders[order_id]
            self.ib.cancelOrder(trade.order)
            self._emit_log_message(f"🚫 주문 취소 요청: ID {order_id}")
            return True
        except Exception as e:
            self._emit_log_message(f"❌ 주문 취소 실패: {str(e)}")
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
            self._emit_log_message(f"🚫 전체 주문 취소 요청: {count}개")
            return count
        except Exception as e:
            self._emit_log_message(f"❌ 전체 취소 실패: {str(e)}")
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
                result.append(
                    {
                        "symbol": pos.contract.symbol,
                        "qty": pos.position,
                        "avg_price": pos.avgCost,
                        "contract": pos.contract,
                    }
                )

            # Signal 발생
            self._emit_positions_update(result)
            return result

        except Exception as e:
            self._emit_log_message(f"⚠️ 포지션 조회 실패: {str(e)}")
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
                result.append(
                    {
                        "order_id": trade.order.orderId,
                        "symbol": trade.contract.symbol,
                        "action": trade.order.action,
                        "qty": trade.order.totalQuantity,
                        "order_type": trade.order.orderType,
                        "status": trade.orderStatus.status,
                    }
                )

            return result

        except Exception as e:
            self._emit_log_message(f"⚠️ 미체결 조회 실패: {str(e)}")
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

            self._emit_order_filled(
                {
                    "order_id": order_id,
                    "symbol": symbol,
                    "action": trade.order.action,
                    "qty": trade.order.totalQuantity,
                    "fill_price": fill_price,
                    "status": "Filled",
                }
            )

            self._emit_log_message(
                f"✅ 체결: {symbol} @ ${fill_price:.2f} (ID: {order_id})"
            )

            # 포지션 업데이트
            self.get_positions()

        except Exception as e:
            self._emit_log_message(f"⚠️ 체결 콜백 오류: {str(e)}")

    def _on_order_cancelled(self, trade: Trade) -> None:
        """주문 취소 콜백"""
        try:
            order_id = trade.order.orderId
            symbol = trade.contract.symbol

            # 활성 주문에서 제거
            if order_id in self._active_orders:
                del self._active_orders[order_id]

            self._emit_order_cancelled(
                {
                    "order_id": order_id,
                    "symbol": symbol,
                    "status": "Cancelled",
                }
            )

            self._emit_log_message(f"🚫 취소됨: {symbol} (ID: {order_id})")

        except Exception as e:
            self._emit_log_message(f"⚠️ 취소 콜백 오류: {str(e)}")


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
    import time

    # 테스트용 callback 함수들
    def on_connected(is_connected: bool) -> None:
        status = "🟢 연결됨" if is_connected else "🔴 연결 안됨"
        print(f"[연결 상태] {status}")

    def on_account_update(info: dict) -> None:
        print(f"[계좌 정보] {info}")

    def on_error(message: str) -> None:
        print(f"[에러] {message}")

    def on_log_message(message: str) -> None:
        print(f"[로그] {message}")

    # 커넥터 생성
    connector = IBKRConnector()

    # Callback 등록
    connector.set_on_connected(on_connected)
    connector.set_on_account_update(on_account_update)
    connector.set_on_error(on_error)
    connector.set_on_log_message(on_log_message)

    print("=== IBKR Connector 테스트 시작 ===")
    print("IB Gateway가 실행 중이어야 합니다. (Paper Trading, 포트 4002)")
    print("15초 후 자동 종료됩니다.\n")

    # 연결 시작
    connector.start()

    # 15초 대기 후 종료
    try:
        time.sleep(15)
    except KeyboardInterrupt:
        print("\n[Ctrl+C 감지]")
    finally:
        print("\n--- 테스트 종료 ---")
        connector.stop()
