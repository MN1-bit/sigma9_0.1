# ============================================================================
# Subscription Manager - Watchlist ↔ Massive WebSocket Subscription Sync
# ============================================================================
# 📌 이 파일의 역할:
#   - Watchlist 종목 목록과 Massive WebSocket 구독 목록 동기화
#   - 새로 추가된 종목 구독 / 제거된 종목 구독 해제
#   - Tier 2 Hot Zone 종목 우선 구독
#
# 📖 사용 예시:
#   >>> manager = SubscriptionManager(massive_ws)
#   >>> await manager.sync_watchlist(["AAPL", "NVDA", "TSLA"])
#   >>> # → AAPL, NVDA, TSLA AM 채널 구독 시작
# ============================================================================

"""
Subscription Manager

Watchlist와 Massive WebSocket 구독 목록을 동기화합니다.
Tier 2 종목은 우선 구독되며, 전체 구독 수 제한을 관리합니다.

Example:
    >>> manager = SubscriptionManager(massive_ws)
    >>> manager.set_tier2_tickers(["AAPL", "NVDA"])  # 우선 구독
    >>> await manager.sync_watchlist(watchlist_tickers)
"""

from typing import Set, List, Optional, TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from backend.data.massive_ws_client import MassiveWebSocketClient, Channel


class SubscriptionManager:
    """
    Watchlist ↔ Massive 구독 동기화 관리자
    
    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    이 클래스는 "구독 관리 비서"와 같습니다.
    
    - Watchlist에 종목이 추가되면 → Massive에 AM 채널 구독
    - Watchlist에서 종목이 빠지면 → Massive에서 구독 해제
    - Tier 2 (Hot Zone) 종목은 항상 최우선으로 구독
    """
    
    # 동시 구독 제한 (Massive 기본 1 연결당)
    MAX_SUBSCRIPTIONS = 100
    
    def __init__(self, massive_ws: Optional["MassiveWebSocketClient"] = None):
        """
        SubscriptionManager 초기화
        
        Args:
            massive_ws: MassiveWebSocketClient 인스턴스 (나중에 설정 가능)
        """
        self.massive_ws = massive_ws
        
        # 현재 구독 중인 종목
        self._subscribed: Set[str] = set()
        
        # Tier 2 (Hot Zone) 종목 - 우선 구독
        self._tier2_tickers: Set[str] = set()
        
        # 현재 차트에 표시 중인 종목 (항상 우선 구독)
        self._chart_ticker: Optional[str] = None
        
        logger.info("📋 SubscriptionManager initialized (Massive)")
    
    def set_massive_ws(self, massive_ws: "MassiveWebSocketClient"):
        """
        MassiveWebSocketClient 설정 (지연 초기화용)
        
        Args:
            massive_ws: MassiveWebSocketClient 인스턴스
        """
        self.massive_ws = massive_ws
        logger.debug("📋 SubscriptionManager Massive WS client set")
    
    def set_tier2_tickers(self, tickers: List[str]):
        """
        Tier 2 (Hot Zone) 종목 설정
        
        Tier 2 종목은 항상 최우선으로 구독됩니다.
        
        Args:
            tickers: Tier 2 종목 목록
        """
        self._tier2_tickers = set(tickers)
        logger.info(f"📋 Tier 2 tickers set: {len(tickers)}")
    
    def set_chart_ticker(self, ticker: Optional[str]):
        """
        현재 차트 종목 설정 (항상 우선 구독)
        
        Args:
            ticker: 차트에 표시 중인 종목 (None이면 해제)
        """
        self._chart_ticker = ticker
        if ticker:
            logger.info(f"📋 Chart ticker set: {ticker}")
    
    async def sync_watchlist(self, watchlist: List[str]):
        """
        Watchlist와 구독 목록 동기화
        
        Args:
            watchlist: 현재 Watchlist 종목 목록
        """
        if not self.massive_ws or not self.massive_ws.is_connected:
            logger.warning("📋 Cannot sync: Massive WS not connected")
            return
        
        from backend.data.massive_ws_client import Channel
        
        watchlist_set = set(watchlist)
        
        # ─────────────────────────────────────────────────────────────────
        # 1. 우선 구독 대상 (항상 유지)
        # ─────────────────────────────────────────────────────────────────
        priority_tickers = self._tier2_tickers.copy()
        if self._chart_ticker:
            priority_tickers.add(self._chart_ticker)
        
        # ─────────────────────────────────────────────────────────────────
        # 2. 전체 구독 대상 계산
        # ─────────────────────────────────────────────────────────────────
        desired_subscriptions = priority_tickers | watchlist_set
        
        # 구독 수 제한 적용
        if len(desired_subscriptions) > self.MAX_SUBSCRIPTIONS:
            limited = list(priority_tickers)[:self.MAX_SUBSCRIPTIONS]
            remaining_slots = self.MAX_SUBSCRIPTIONS - len(limited)
            
            if remaining_slots > 0:
                other_tickers = list(watchlist_set - priority_tickers)
                limited.extend(other_tickers[:remaining_slots])
            
            desired_subscriptions = set(limited)
            logger.warning(
                f"📋 Subscription limit reached. "
                f"Subscribed {len(desired_subscriptions)}/{len(watchlist) + len(priority_tickers)}"
            )
        
        # ─────────────────────────────────────────────────────────────────
        # 3. 차이 계산 및 적용
        # ─────────────────────────────────────────────────────────────────
        to_subscribe = desired_subscriptions - self._subscribed
        to_unsubscribe = self._subscribed - desired_subscriptions
        
        # 구독 해제
        if to_unsubscribe:
            await self.massive_ws.unsubscribe(list(to_unsubscribe), Channel.AM)
            self._subscribed -= to_unsubscribe
        
        # 새 구독
        if to_subscribe:
            await self.massive_ws.subscribe(list(to_subscribe), Channel.AM)
            self._subscribed |= to_subscribe
        
        logger.info(
            f"📋 Watchlist sync: +{len(to_subscribe)} -{len(to_unsubscribe)} "
            f"(total: {len(self._subscribed)})"
        )
    
    async def unsubscribe_all(self):
        """모든 구독 해제"""
        if self.massive_ws and self._subscribed:
            from backend.data.massive_ws_client import Channel
            await self.massive_ws.unsubscribe(list(self._subscribed), Channel.AM)
        
        self._subscribed.clear()
        logger.info("📋 All subscriptions cancelled")
    
    @property
    def subscribed_tickers(self) -> List[str]:
        """현재 구독 중인 종목 목록 (AM 채널)"""
        return list(self._subscribed)
    
    # ═══════════════════════════════════════════════════════════════════════
    # T 채널 (틱) 구독 관리 - Step 4.A.0.b.6
    # ═══════════════════════════════════════════════════════════════════════
    
    async def subscribe_tick(self, tickers: List[str]):
        """
        T 채널 (틱) 구독 추가
        
        활성 주문이나 Tier 2 종목에 사용됩니다.
        
        Args:
            tickers: 구독할 종목 목록
        """
        if not self.massive_ws or not self.massive_ws.is_connected:
            return
        
        from backend.data.massive_ws_client import Channel
        
        if not hasattr(self, '_tick_subscribed'):
            self._tick_subscribed: Set[str] = set()
        
        new_tickers = [t for t in tickers if t not in self._tick_subscribed]
        if new_tickers:
            await self.massive_ws.subscribe(new_tickers, Channel.T)
            self._tick_subscribed.update(new_tickers)
            logger.info(f"📋 Tick subscribed: {new_tickers}")
    
    async def unsubscribe_tick(self, tickers: List[str]):
        """
        T 채널 (틱) 구독 해제
        
        Args:
            tickers: 구독 해제할 종목 목록
        """
        if not self.massive_ws or not self.massive_ws.is_connected:
            return
        
        from backend.data.massive_ws_client import Channel
        
        if not hasattr(self, '_tick_subscribed'):
            return
        
        to_remove = [t for t in tickers if t in self._tick_subscribed]
        if to_remove:
            await self.massive_ws.unsubscribe(to_remove, Channel.T)
            self._tick_subscribed -= set(to_remove)
            logger.info(f"📋 Tick unsubscribed: {to_remove}")
    
    async def sync_tick_subscriptions(self):
        """
        T 채널 구독 동기화
        
        Tier 2, 차트 종목, 활성 주문 종목에 대해 T 채널 구독
        """
        if not self.massive_ws or not self.massive_ws.is_connected:
            return
        
        if not hasattr(self, '_tick_subscribed'):
            self._tick_subscribed: Set[str] = set()
        
        # 우선 구독 대상
        priority_tickers = self._tier2_tickers.copy()
        if self._chart_ticker:
            priority_tickers.add(self._chart_ticker)
        
        # 차이 계산
        to_subscribe = priority_tickers - self._tick_subscribed
        to_unsubscribe = self._tick_subscribed - priority_tickers
        
        if to_unsubscribe:
            await self.unsubscribe_tick(list(to_unsubscribe))
        
        if to_subscribe:
            await self.subscribe_tick(list(to_subscribe))
    
    @property
    def tick_subscribed_tickers(self) -> List[str]:
        """현재 T 채널 구독 중인 종목 목록"""
        if not hasattr(self, '_tick_subscribed'):
            return []
        return list(self._tick_subscribed)
    
    @property
    def stats(self) -> dict:
        """구독 통계"""
        return {
            "total_subscribed_am": len(self._subscribed),
            "total_subscribed_tick": len(getattr(self, '_tick_subscribed', set())),
            "tier2_count": len(self._tier2_tickers),
            "chart_ticker": self._chart_ticker,
            "max_subscriptions": self.MAX_SUBSCRIPTIONS,
            "subscribed_am": list(self._subscribed),
            "subscribed_tick": list(getattr(self, '_tick_subscribed', set()))
        }
