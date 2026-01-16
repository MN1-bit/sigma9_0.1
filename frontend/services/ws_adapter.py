"""
Sigma9 WebSocket Adapter
=========================
WebSocket 기반 실시간 스트리밍 클라이언트.

📌 사용법:
    from frontend.services.ws_adapter import WsAdapter

    adapter = WsAdapter("ws://localhost:8000/ws/feed")
    adapter.log_received.connect(on_log)
    adapter.watchlist_updated.connect(on_watchlist)
    await adapter.connect()

📌 메시지 타입:
    - LOG:xxx       - 서버 로그
    - TICK:xxx      - 틱 데이터 (JSON)
    - TRADE:xxx     - 거래 이벤트 (JSON)
    - WATCHLIST:xxx - Watchlist 업데이트 (JSON)
    - STATUS:xxx    - 상태 변경 (JSON)
    - IGNITION:xxx  - Ignition Score 업데이트 (JSON)
"""

import asyncio
import json
import threading
from typing import Optional
from enum import Enum
from loguru import logger

try:
    from PyQt6.QtCore import (
        QObject,
        pyqtSignal,
        QTimer,
        Qt,
        pyqtSlot,
        QMetaObject,
        Q_ARG,
    )

    PYQT_AVAILABLE = True
except ImportError:
    try:
        from PySide6.QtCore import (
            QObject,
            Signal as pyqtSignal,
            QTimer,
            Qt,
            Slot as pyqtSlot,
            QMetaObject,
        )

        PYQT_AVAILABLE = True
    except ImportError:
        PYQT_AVAILABLE = False
        logger.warning("⚠️ PyQt6/PySide6 not available")

try:
    import websockets

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logger.warning("⚠️ websockets not installed. Run: pip install websockets")


class MessageType(str, Enum):
    """WebSocket 메시지 타입"""

    LOG = "LOG"
    TICK = "TICK"
    BAR = "BAR"  # Phase 4.A.0: 실시간 OHLCV 바 업데이트
    TRADE = "TRADE"
    WATCHLIST = "WATCHLIST"
    STATUS = "STATUS"
    IGNITION = "IGNITION"  # Phase 2: 실시간 Ignition Score
    ERROR = "ERROR"
    PONG = "PONG"


class WsAdapter(QObject):
    """
    WebSocket 클라이언트 Adapter

    📌 기능:
        - 서버 WebSocket 연결 관리
        - 자동 재연결
        - 메시지 파싱 및 Signal 발생
        - 하트비트 (PING/PONG)

    📌 Signals:
        - connected: 연결 성공
        - disconnected: 연결 해제
        - log_received(str): 로그 메시지 수신
        - tick_received(dict): 틱 데이터 수신
        - trade_received(dict): 거래 이벤트 수신
        - watchlist_updated(list): Watchlist 업데이트
        - status_changed(dict): 상태 변경
        - error_occurred(str): 에러 발생
    """

    # Signals
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    log_received = pyqtSignal(str)
    tick_received = pyqtSignal(dict)
    bar_received = pyqtSignal(
        dict
    )  # Phase 4.A.0: {"ticker": str, "timeframe": str, "bar": dict}
    trade_received = pyqtSignal(dict)
    watchlist_updated = pyqtSignal(list)
    status_changed = pyqtSignal(dict)
    ignition_updated = pyqtSignal(dict)  # {"ticker": str, "score": float, ...}
    heartbeat_received = pyqtSignal(
        dict
    )  # [08-001] {"server_time_utc": str, "sent_at": int}
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        ws_url: str,
        reconnect_interval: int = 5,
        heartbeat_interval: int = 15,
        parent=None,
    ):
        """
        WebSocket Adapter 초기화

        Args:
            ws_url: WebSocket URL (e.g., "ws://localhost:8000/ws/feed")
            reconnect_interval: 재연결 시도 간격 (초)
            heartbeat_interval: 하트비트 간격 (초)
            parent: Qt 부모 객체
        """
        super().__init__(parent)

        if not WEBSOCKETS_AVAILABLE:
            raise ImportError("websockets is required. Run: pip install websockets")

        self.ws_url = ws_url
        self.reconnect_interval = reconnect_interval
        self.heartbeat_interval = heartbeat_interval

        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._is_connected = False
        self._should_reconnect = True
        self._receive_task: Optional[asyncio.Task] = None
        self._heartbeat_timer: Optional[QTimer] = None
        # [14-003 FIX] asyncio 이벤트 루프 참조 저장 (cross-thread PING용)
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None

        # [14-003 FIX] QueuedConnection으로 메인 스레드에서 실행 보장
        # connect()가 백그라운드 스레드에서 emit해도 _start_heartbeat은 메인 스레드에서 실행됨
        self.connected.connect(
            self._start_heartbeat, Qt.ConnectionType.QueuedConnection
        )

        logger.debug(f"WsAdapter initialized: {self.ws_url}")

    @property
    def is_connected(self) -> bool:
        """연결 상태 반환"""
        return self._is_connected and self._ws is not None

    # ─────────────────────────────────────────────────────────────
    # Connection Management
    # ─────────────────────────────────────────────────────────────

    async def connect(self) -> bool:
        """
        WebSocket 연결

        Returns:
            bool: 연결 성공 여부
        """
        if self._is_connected:
            logger.debug("Already connected")
            return True

        try:
            logger.info(f"📡 Connecting to {self.ws_url}...")
            self._ws = await websockets.connect(
                self.ws_url,
                ping_interval=None,  # 수동 PING 관리
                close_timeout=5,
            )

            self._is_connected = True
            self._should_reconnect = True
            # [14-003 FIX] 이벤트 루프 참조 저장 (cross-thread PING용)
            self._event_loop = asyncio.get_running_loop()

            # 수신 태스크 시작
            self._receive_task = asyncio.create_task(self._receive_loop())

            # [14-003 FIX] 이벤트 루프 저장 후, signal emit으로 메인 스레드에서 heartbeat 시작
            # ELI5: connected.emit() → Line 139의 QueuedConnection → 메인 스레드에서 _start_heartbeat 실행
            # (QTimer.singleShot는 백그라운드 스레드에서 호출되면 작동하지 않으므로 제거)

            logger.info("✅ WebSocket connected")
            self.connected.emit()
            return True

        except Exception as e:
            logger.error(f"❌ WebSocket connection failed: {e}")
            self.error_occurred.emit(str(e))
            return False

    async def disconnect(self):
        """WebSocket 연결 해제"""
        self._should_reconnect = False
        self._stop_heartbeat()

        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

        if self._is_connected:
            self._is_connected = False
            logger.info("📡 WebSocket disconnected")
            self.disconnected.emit()

    async def _receive_loop(self):
        """메시지 수신 루프"""
        try:
            async for message in self._ws:
                # [DEBUG] 모든 수신 메시지 출력
                print(f"[DEBUG] ws_adapter RECEIVED: {message[:100]}")
                self._handle_message(message)

        except websockets.ConnectionClosed as e:
            logger.warning(f"WebSocket connection closed: {e}")
            self._is_connected = False
            self.disconnected.emit()

            # 자동 재연결
            if self._should_reconnect:
                await self._reconnect()

        except Exception as e:
            logger.error(f"WebSocket receive error: {e}")
            self.error_occurred.emit(str(e))

    async def _reconnect(self):
        """자동 재연결"""
        while self._should_reconnect:
            logger.info(f"🔄 Reconnecting in {self.reconnect_interval}s...")
            await asyncio.sleep(self.reconnect_interval)

            if await self.connect():
                break

    # ─────────────────────────────────────────────────────────────
    # Message Handling
    # ─────────────────────────────────────────────────────────────

    def _handle_message(self, message: str):
        """
        메시지 파싱 및 Signal 발생

        메시지 형식: TYPE:DATA
        예: LOG:Hello World
            TICK:{"ticker":"AAPL","price":150.25}
        """
        try:
            # 타입과 데이터 분리
            if ":" not in message:
                logger.debug(f"Unknown message format: {message[:50]}")
                return

            msg_type, data = message.split(":", 1)

            # 타입별 처리
            if msg_type == MessageType.LOG:
                self.log_received.emit(data)

            elif msg_type == MessageType.TICK:
                try:
                    tick_data = json.loads(data)
                    self.tick_received.emit(tick_data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid TICK JSON: {data[:50]}")

            elif msg_type == MessageType.BAR:
                # Phase 4.A.0: 실시간 바 업데이트
                try:
                    bar_data = json.loads(data)
                    self.bar_received.emit(bar_data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid BAR JSON: {data[:50]}")

            elif msg_type == MessageType.TRADE:
                try:
                    trade_data = json.loads(data)
                    self.trade_received.emit(trade_data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid TRADE JSON: {data[:50]}")

            elif msg_type == MessageType.WATCHLIST:
                try:
                    wl_data = json.loads(data)
                    items = wl_data.get("items", [])
                    self.watchlist_updated.emit(items)

                    # [08-001] 모든 메시지에서 시간 정보 추출 → TimeDisplayWidget 업데이트
                    if "_server_time_utc" in wl_data and "_sent_at" in wl_data:
                        heartbeat_data = {
                            "server_time_utc": wl_data["_server_time_utc"],
                            "sent_at": wl_data["_sent_at"],
                        }
                        # [08-001] 직접 계산된 E 레이턴시가 있으면 사용 (가장 정확)
                        if "_event_latency_ms" in wl_data:
                            heartbeat_data["event_latency_ms"] = wl_data[
                                "_event_latency_ms"
                            ]
                        # 이벤트 타임 (fallback)
                        elif "_event_time" in wl_data:
                            heartbeat_data["event_time"] = wl_data["_event_time"]
                        print(
                            f"[DEBUG] WATCHLIST→heartbeat_received.emit: {heartbeat_data}"
                        )
                        self.heartbeat_received.emit(heartbeat_data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid WATCHLIST JSON: {data[:50]}")

            elif msg_type == MessageType.STATUS:
                try:
                    status_data = json.loads(data)
                    self.status_changed.emit(status_data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid STATUS JSON: {data[:50]}")

            elif msg_type == MessageType.PONG:
                # [08-001] 하트비트 응답에서 시간 정보 추출
                print(f"[DEBUG] ws_adapter PONG received: {data[:100]}")
                try:
                    heartbeat_data = json.loads(data) if data else {}
                    print(f"[DEBUG] Emitting heartbeat_received: {heartbeat_data}")
                    self.heartbeat_received.emit(heartbeat_data)
                except json.JSONDecodeError:
                    # 이전 형식 (데이터 없음) 호환
                    pass

            elif msg_type == MessageType.IGNITION:
                try:
                    ignition_data = json.loads(data)
                    self.ignition_updated.emit(ignition_data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid IGNITION JSON: {data[:50]}")

            elif msg_type == MessageType.ERROR:
                self.error_occurred.emit(data)

            else:
                logger.debug(f"Unknown message type: {msg_type}")

        except Exception as e:
            logger.error(f"Message handling error: {e}")

    # ─────────────────────────────────────────────────────────────
    # Heartbeat
    # ─────────────────────────────────────────────────────────────

    @pyqtSlot()
    def _start_heartbeat(self):
        """하트비트 타이머 시작

        [14-003 FIX] @pyqtSlot 데코레이터로 QMetaObject.invokeMethod에서 호출 가능
        """
        print(
            f"[DEBUG] _start_heartbeat called in thread: {threading.current_thread().name}"
        )
        if self._heartbeat_timer:
            self._heartbeat_timer.stop()

        self._heartbeat_timer = QTimer(self)
        self._heartbeat_timer.timeout.connect(self._send_ping)
        self._heartbeat_timer.start(self.heartbeat_interval * 1000)
        print(f"[DEBUG] Heartbeat timer started: interval={self.heartbeat_interval}s")

    def _stop_heartbeat(self):
        """하트비트 타이머 중지"""
        if self._heartbeat_timer:
            self._heartbeat_timer.stop()
            self._heartbeat_timer = None

    def _send_ping(self):
        """
        PING 메시지 전송

        [14-003 FIX] PyQt 메인 스레드에서 QTimer로 호출되므로
        asyncio.run_coroutine_threadsafe() 사용하여 별도 이벤트 루프에서 실행
        """
        print(f"[DEBUG] _send_ping called, connected={self._is_connected}")
        if self._ws and self._is_connected and self._event_loop:
            # [14-003 FIX] PyQt 스레드 → asyncio 스레드로 안전하게 코루틴 전달
            asyncio.run_coroutine_threadsafe(self._async_send_ping(), self._event_loop)

    async def _async_send_ping(self):
        """비동기 PING 전송"""
        try:
            print("[DEBUG] Sending PING to server...")
            await self._ws.send("PING")
            print("[DEBUG] PING sent successfully")
        except Exception as e:
            logger.debug(f"PING failed: {e}")

    # ─────────────────────────────────────────────────────────────
    # Send Message
    # ─────────────────────────────────────────────────────────────

    async def send(self, message: str) -> bool:
        """
        메시지 전송

        Args:
            message: 전송할 메시지

        Returns:
            bool: 전송 성공 여부
        """
        if not self._ws or not self._is_connected:
            logger.warning("Cannot send: not connected")
            return False

        try:
            await self._ws.send(message)
            return True
        except Exception as e:
            logger.error(f"Send failed: {e}")
            return False
