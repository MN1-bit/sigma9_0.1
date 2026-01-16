# ============================================================================
# Tick Broadcaster - Massive WebSocket → GUI WebSocket Bridge
# ============================================================================
# 📌 이 파일의 역할:
#   - Massive WebSocket 데이터를 GUI 클라이언트에 브로드캐스트
#   - AM (1분봉) 데이터를 BAR 메시지로 변환하여 전송
#   - T (틱) 데이터를 TICK 메시지로 변환하여 전송
#
# 📖 Data Flow:
#   MassiveWebSocketClient
#       ↓ on_bar / on_tick callbacks
#   TickBroadcaster
#       ↓ asyncio broadcast
#   ConnectionManager.broadcast_bar()
#       ↓ WebSocket
#   GUI Clients
# ============================================================================

"""
Tick Broadcaster

Massive WebSocket에서 수신한 실시간 데이터를
GUI WebSocket으로 브로드캐스트합니다.

Example:
    >>> broadcaster = TickBroadcaster(massive_ws, ws_manager, loop)
    >>> # Massive에서 데이터가 오면 자동으로 WebSocket으로 전파됨
"""

import asyncio
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from backend.data.massive_ws_client import MassiveWebSocketClient
    from backend.api.websocket import ConnectionManager
    from backend.core.tick_dispatcher import TickDispatcher


class TickBroadcaster:
    """
    Massive → GUI WebSocket 브로드캐스터

    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    이 클래스는 "라디오 중계소"와 같습니다.

    Massive에서 실시간 주가 데이터가 오면 (원재료)
    → 이 클래스가 받아서 (중계소)
    → 모든 GUI에 동시에 뿌려줍니다 (청취자들)
    """

    def __init__(
        self,
        massive_ws: "MassiveWebSocketClient",
        ws_manager: "ConnectionManager",
        loop: Optional[asyncio.AbstractEventLoop] = None,
        tick_dispatcher: Optional["TickDispatcher"] = None,
    ):
        """
        TickBroadcaster 초기화

        Args:
            massive_ws: MassiveWebSocketClient 인스턴스
            ws_manager: GUI WebSocket ConnectionManager 인스턴스
            loop: asyncio 이벤트 루프 (None이면 자동 감지)
            tick_dispatcher: TickDispatcher 인스턴스 (틱 배포용)
        """
        self.massive_ws = massive_ws
        self.ws_manager = ws_manager
        self.loop = loop
        self.tick_dispatcher = tick_dispatcher

        # 통계
        self._bar_count = 0
        self._tick_count = 0
        self._last_update_time: Optional[datetime] = None

        # 콜백 연결
        self.massive_ws.on_bar = self._on_bar
        self.massive_ws.on_tick = self._on_tick

        logger.info("📡 TickBroadcaster initialized (Massive → GUI + Dispatcher)")

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """
        이벤트 루프 설정 (서버 시작 후 설정)

        Args:
            loop: asyncio 이벤트 루프
        """
        self.loop = loop
        logger.debug("📡 TickBroadcaster event loop set")

    def _on_bar(self, bar: dict):
        """
        Massive AM (1분봉) 수신 콜백

        Args:
            bar: {
                "type": "bar",
                "ticker": str,
                "timeframe": "1m",
                "time": float (Unix timestamp),
                "open": float,
                "high": float,
                "low": float,
                "close": float,
                "volume": int,
                "vwap": float
            }
        """
        if not self.loop:
            return

        try:
            self._bar_count += 1
            self._last_update_time = datetime.now()

            ticker = bar.get("ticker", "")

            if not ticker:
                return

            # GUI에 BAR 메시지 브로드캐스트
            asyncio.run_coroutine_threadsafe(
                self.ws_manager.broadcast_bar(
                    ticker=ticker,
                    timeframe=bar.get("timeframe", "1m"),
                    bar={
                        "time": bar.get("time"),
                        "open": bar.get("open"),
                        "high": bar.get("high"),
                        "low": bar.get("low"),
                        "close": bar.get("close"),
                        "volume": bar.get("volume"),
                        "vwap": bar.get("vwap"),
                    },
                ),
                self.loop,
            )

        except Exception as e:
            logger.error(f"❌ TickBroadcaster bar error: {e}")

    def _on_tick(self, tick: dict):
        """
        Massive T (틱) 수신 콜백

        Args:
            tick: {
                "type": "tick",
                "ticker": str,
                "price": float,
                "size": int,
                "time": float
            }
        """
        if not self.loop:
            return

        try:
            self._tick_count += 1
            self._last_update_time = datetime.now()

            ticker = tick.get("ticker", "")
            price = tick.get("price", 0)

            if not ticker or price <= 0:
                return

            # [Step 4.A.0.b] TickDispatcher로 배포 (전략, 엔진, Trailing Stop 등)
            if self.tick_dispatcher:
                self.tick_dispatcher.dispatch(tick)

            # GUI에 TICK 메시지 브로드캐스트
            asyncio.run_coroutine_threadsafe(
                self.ws_manager.broadcast_tick(
                    ticker=ticker,
                    price=price,
                    volume=tick.get("size", 0),
                    timestamp=datetime.fromtimestamp(tick.get("time", 0)).isoformat(),
                ),
                self.loop,
            )

        except Exception as e:
            logger.error(f"❌ TickBroadcaster tick error: {e}")

    @property
    def stats(self) -> dict:
        """브로드캐스터 통계 반환"""
        return {
            "bar_count": self._bar_count,
            "tick_count": self._tick_count,
            "last_update": self._last_update_time.isoformat()
            if self._last_update_time
            else None,
            "connected_clients": self.ws_manager.connection_count
            if self.ws_manager
            else 0,
        }
