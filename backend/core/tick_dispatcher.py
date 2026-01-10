# ============================================================================
# Tick Dispatcher - 틱 데이터 중앙 배포자
# ============================================================================
# 📌 이 파일의 역할:
#   - Massive WebSocket에서 수신한 틱 데이터를 여러 구독자에게 배포
#   - 전략 모듈, Trading Engine, Trailing Stop, GUI 등에 동시 전달
#
# 📖 Data Flow:
#   MassiveWebSocketClient.on_tick
#       ↓
#   TickDispatcher.dispatch()
#       ↓
#   ├─→ Seismograph.on_tick() (Ignition 계산)
#   ├─→ TradingEngine.on_tick() (진입/청산)
#   ├─→ TrailingStopManager.on_price_update() (손절/익절)
#   └─→ ConnectionManager.broadcast_tick() (GUI)
# ============================================================================

"""
Tick Dispatcher

틱 데이터를 시스템 전반의 구독자에게 배포합니다.

Example:
    >>> dispatcher = TickDispatcher()
    >>> dispatcher.register("strategy", strategy.on_tick)
    >>> dispatcher.register("trailing", trailing_stop.on_price_update)
    >>>
    >>> # 틱 수신 시
    >>> dispatcher.dispatch({"ticker": "AAPL", "price": 178.50, "volume": 100})
"""

from typing import Dict, Callable, Optional, List
from datetime import datetime

from loguru import logger


class TickDispatcher:
    """
    틱 데이터 중앙 배포자

    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    이 클래스는 "우체부"와 같습니다.

    Massive에서 틱 데이터가 도착하면:
    1. 전략 모듈에게 배달 → Ignition Score 계산
    2. Trading Engine에게 배달 → 진입/청산 판단
    3. Trailing Stop에게 배달 → 손절/익절 체크
    4. GUI에게 배달 → 화면에 표시

    모든 배달은 동시에 일어납니다 (비동기 아님, 순차 호출).
    """

    def __init__(self):
        """TickDispatcher 초기화"""
        # 구독자 목록: {name: callback}
        self._subscribers: Dict[str, Callable[[dict], None]] = {}

        # 틱 필터 (특정 종목만 특정 구독자에게)
        self._ticker_filters: Dict[str, List[str]] = {}  # {subscriber_name: [tickers]}

        # 통계
        self._dispatch_count = 0
        self._last_dispatch_time: Optional[datetime] = None

        logger.info("📮 TickDispatcher initialized")

    def register(
        self,
        name: str,
        callback: Callable[[dict], None],
        tickers: Optional[List[str]] = None,
    ):
        """
        구독자 등록

        Args:
            name: 구독자 이름 (예: "strategy", "trailing_stop")
            callback: 틱 수신 시 호출할 함수 (tick: dict) -> None
            tickers: 필터할 종목 목록 (None이면 모든 종목 수신)
        """
        self._subscribers[name] = callback

        if tickers:
            self._ticker_filters[name] = tickers
        elif name in self._ticker_filters:
            del self._ticker_filters[name]

        logger.info(f"📮 Subscriber registered: {name} (tickers: {tickers or 'all'})")

    def unregister(self, name: str):
        """
        구독 해제

        Args:
            name: 해제할 구독자 이름
        """
        if name in self._subscribers:
            del self._subscribers[name]
            self._ticker_filters.pop(name, None)
            logger.info(f"📮 Subscriber unregistered: {name}")

    def update_filter(self, name: str, tickers: List[str]):
        """
        특정 구독자의 종목 필터 업데이트

        Args:
            name: 구독자 이름
            tickers: 새로운 필터 종목 목록
        """
        if name in self._subscribers:
            if tickers:
                self._ticker_filters[name] = tickers
            elif name in self._ticker_filters:
                del self._ticker_filters[name]
            logger.debug(f"📮 Filter updated for {name}: {tickers}")

    def dispatch(self, tick: dict):
        """
        틱 데이터 배포

        모든 구독자에게 틱 데이터를 전달합니다.
        필터가 설정된 구독자는 해당 종목만 수신합니다.

        Args:
            tick: {
                "ticker": str,
                "price": float,
                "size": int,
                "time": float (Unix timestamp)
            }
        """
        ticker = tick.get("ticker", "")

        if not ticker:
            return

        self._dispatch_count += 1
        self._last_dispatch_time = datetime.now()

        # 각 구독자에게 배포
        for name, callback in self._subscribers.items():
            try:
                # 필터 체크
                if name in self._ticker_filters:
                    if ticker not in self._ticker_filters[name]:
                        continue

                # 콜백 호출
                callback(tick)

            except Exception as e:
                logger.warning(f"📮 Dispatch error to {name}: {e}")

    def dispatch_bar(self, bar: dict):
        """
        바 데이터 배포 (1분봉 등)

        틱과 동일한 구조로 배포되지만, type 필드로 구분 가능.

        Args:
            bar: {"type": "bar", "ticker": str, ...}
        """
        bar["type"] = "bar"
        self.dispatch(bar)

    @property
    def subscriber_count(self) -> int:
        """현재 구독자 수"""
        return len(self._subscribers)

    @property
    def subscribers(self) -> List[str]:
        """구독자 이름 목록"""
        return list(self._subscribers.keys())

    @property
    def stats(self) -> dict:
        """배포 통계"""
        return {
            "subscriber_count": len(self._subscribers),
            "subscribers": list(self._subscribers.keys()),
            "dispatch_count": self._dispatch_count,
            "last_dispatch": self._last_dispatch_time.isoformat()
            if self._last_dispatch_time
            else None,
        }
