# backend/core/trading_context.py
"""
TradingContext: Backend Source of Truth for Active Ticker

📌 [09-009] 모든 Backend 서비스가 참조하는 "현재 활성 티커"
📌 Frontend에서 WebSocket으로 변경 요청 수신
📌 변경 시 구독자들에게 알림
"""

from typing import Callable

from loguru import logger


class TradingContext:
    """
    트레이딩 세션의 공유 콘텍스트 (Source of Truth)

    📌 [09-009] 모든 Backend 서비스가 참조하는 "현재 활성 티커"
    📌 Frontend에서 WebSocket으로 변경 요청 수신
    📌 변경 시 구독자들에게 알림

    Example:
        >>> context = TradingContext()
        >>> context.set_active_ticker("AAPL", source="watchlist")
        True
        >>> context.active_ticker
        'AAPL'
    """

    def __init__(self) -> None:
        self._active_ticker: str | None = None
        self._previous_ticker: str | None = None
        # Subscriber callback signature: (ticker: str, source: str) -> None
        self._subscribers: list[Callable[[str, str], None]] = []
        logger.debug("[TradingContext] Initialized")

    @property
    def active_ticker(self) -> str | None:
        """현재 활성 티커 (읽기 전용)"""
        return self._active_ticker

    @property
    def previous_ticker(self) -> str | None:
        """이전 활성 티커"""
        return self._previous_ticker

    def set_active_ticker(self, ticker: str, source: str = "unknown") -> bool:
        """
        활성 티커 변경 (유일한 진입점)

        Args:
            ticker: 새 티커 심볼
            source: 변경 출처 (watchlist, search, tier2, ...)

        Returns:
            bool: 변경되었으면 True, 동일 티커면 False
        """
        if self._active_ticker == ticker:
            logger.debug(f"[TradingContext] Same ticker, skip: {ticker}")
            return False

        self._previous_ticker = self._active_ticker
        self._active_ticker = ticker

        logger.info(
            f"[TradingContext] Active ticker changed: "
            f"{self._previous_ticker} → {ticker} (source: {source})"
        )

        # 구독자들에게 알림 (ELI5: 누군가 티커가 바뀌면 알려달라고 했으면, 여기서 알려줌)
        for callback in self._subscribers:
            try:
                callback(ticker, source)
            except Exception as e:
                logger.error(f"[TradingContext] Subscriber error: {e}")

        return True

    def subscribe(self, callback: Callable[[str, str], None]) -> None:
        """
        티커 변경 구독

        Args:
            callback: (ticker, source) -> None 형태의 콜백 함수
        """
        if callback not in self._subscribers:
            self._subscribers.append(callback)
            callback_name = getattr(callback, "__name__", repr(callback))
            logger.debug(f"[TradingContext] Subscriber added: {callback_name}")

    def unsubscribe(self, callback: Callable[[str, str], None]) -> None:
        """구독 해제"""
        if callback in self._subscribers:
            self._subscribers.remove(callback)
            callback_name = getattr(callback, "__name__", repr(callback))
            logger.debug(f"[TradingContext] Subscriber removed: {callback_name}")
