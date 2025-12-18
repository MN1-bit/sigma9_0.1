# ============================================================================
# Ignition Monitor - 실시간 Ignition Score 모니터링 서비스
# ============================================================================
# 📌 이 파일의 역할:
#   - Watchlist 종목들의 실시간 틱 구독 관리
#   - SeismographStrategy.calculate_trigger_score() 호출
#   - Score 변화 시 WebSocket으로 브로드캐스트
#
# 📖 사용 예시:
#   >>> from backend.core.ignition_monitor import IgnitionMonitor
#   >>> monitor = IgnitionMonitor(strategy, ws_manager)
#   >>> await monitor.start(watchlist)
#   >>> # ... 틱 수신 중 자동으로 Ignition Score 전송
#   >>> await monitor.stop()
# ============================================================================

"""
Ignition Monitor Module

Watchlist 종목들의 실시간 Ignition Score를 모니터링하고
Score 변화 시 WebSocket으로 GUI에 푸시합니다.

Phase 2 (Trigger) 로직을 GUI에서 실시간으로 확인할 수 있게 합니다.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger


class IgnitionMonitor:
    """
    실시간 Ignition Score 모니터링 서비스
    
    Watchlist 종목들의 틱 데이터를 수신하여 Ignition Score를 계산하고
    변화가 있을 때마다 WebSocket으로 GUI에 푸시합니다.
    
    Attributes:
        strategy: SeismographStrategy 인스턴스
        ws_manager: WebSocket ConnectionManager 인스턴스
        watchlist_tickers: 모니터링 대상 종목 리스트
        scores: 종목별 현재 Ignition Score 캐시
        running: 모니터링 실행 상태
    
    Example:
        >>> from backend.strategies.seismograph import SeismographStrategy
        >>> from backend.api.websocket import manager as ws_manager
        >>> from backend.core.ignition_monitor import IgnitionMonitor
        >>>
        >>> strategy = SeismographStrategy()
        >>> monitor = IgnitionMonitor(strategy, ws_manager)
        >>> await monitor.start(watchlist)
    """
    
    def __init__(self, strategy: Any, ws_manager: Any):
        """
        IgnitionMonitor 초기화
        
        Args:
            strategy: SeismographStrategy 인스턴스
            ws_manager: WebSocket ConnectionManager 인스턴스
        """
        self.strategy = strategy
        self.ws_manager = ws_manager
        self.watchlist_tickers: List[str] = []
        self.scores: Dict[str, float] = {}  # ticker -> score 캐시
        self.running: bool = False
        
        logger.debug("⚡ IgnitionMonitor 초기화 완료")
    
    # ═══════════════════════════════════════════════════════════════════════
    # 시작/중지
    # ═══════════════════════════════════════════════════════════════════════
    
    async def start(self, watchlist: List[Dict[str, Any]]) -> bool:
        """
        모니터링 시작
        
        Watchlist 종목들의 Context를 로드하고 모니터링을 시작합니다.
        
        Args:
            watchlist: Watchlist 데이터 (Scanner 결과)
        
        Returns:
            bool: 시작 성공 여부
        """
        if self.running:
            logger.warning("⚡ IgnitionMonitor: 이미 실행 중")
            return False
        
        # Watchlist ticker 추출
        self.watchlist_tickers = [item.get("ticker", "") for item in watchlist if item.get("ticker")]
        
        if not self.watchlist_tickers:
            logger.warning("⚡ IgnitionMonitor: 모니터링할 종목 없음")
            return False
        
        # 전략에 Watchlist Context 로드
        self.strategy.load_watchlist_context(watchlist)
        
        # Score 캐시 초기화
        self.scores = {ticker: 0.0 for ticker in self.watchlist_tickers}
        
        self.running = True
        logger.info(f"⚡ IgnitionMonitor 시작: {len(self.watchlist_tickers)}개 종목 모니터링")
        
        return True
    
    async def stop(self):
        """모니터링 중지"""
        if not self.running:
            return
        
        self.running = False
        self.watchlist_tickers = []
        self.scores = {}
        
        logger.info("⚡ IgnitionMonitor 중지")
    
    # ═══════════════════════════════════════════════════════════════════════
    # 틱 처리
    # ═══════════════════════════════════════════════════════════════════════
    
    async def on_tick(
        self, 
        ticker: str, 
        price: float, 
        volume: int, 
        timestamp: datetime,
        side: str = "B",
        bid: float = 0.0,
        ask: float = 0.0
    ):
        """
        틱 데이터 수신 시 호출
        
        Ignition Score를 계산하고, 변화가 크면 WebSocket으로 브로드캐스트합니다.
        
        Args:
            ticker: 종목 코드
            price: 체결가
            volume: 체결량
            timestamp: 체결 시간
            side: 체결 방향 ("B" = 매수, "S" = 매도)
            bid: 매수 호가
            ask: 매도 호가
        """
        if not self.running:
            return
        
        if ticker not in self.watchlist_tickers:
            return
        
        # 전략의 on_tick 호출 → Signal 반환
        signal = self.strategy.on_tick(
            ticker=ticker,
            price=price,
            volume=volume,
            timestamp=timestamp,
            side=side,
            bid=bid,
            ask=ask
        )
        
        # 현재 Ignition Score 조회 (전략 내부 상태에서)
        # calculate_trigger_score를 호출하여 점수 계산
        new_score = self.strategy.calculate_trigger_score(ticker)
        
        # 이전 점수와 비교 (5점 이상 변화 시 브로드캐스트)
        old_score = self.scores.get(ticker, 0.0)
        score_delta = abs(new_score - old_score)
        
        if score_delta >= 5.0 or new_score >= 70.0:
            self.scores[ticker] = new_score
            
            # Anti-Trap 필터 체크
            passed_filter = True
            reason = ""
            if new_score >= 70.0:
                filter_result = self.strategy.check_anti_trap_filter(
                    ticker=ticker,
                    price=price,
                    bid=bid,
                    ask=ask,
                    timestamp=timestamp
                )
                passed_filter, reason = filter_result
            
            # WebSocket 브로드캐스트
            await self.ws_manager.broadcast_ignition(
                ticker=ticker,
                score=new_score,
                passed_filter=passed_filter,
                reason=reason
            )
            
            # 70점 이상이면 로그
            if new_score >= 70.0:
                logger.info(f"⚡ IGNITION ALERT: {ticker} Score={new_score:.0f} "
                           f"({'✅ CLEAR' if passed_filter else f'❌ {reason}'})")
    
    # ═══════════════════════════════════════════════════════════════════════
    # 상태 조회
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_all_scores(self) -> Dict[str, float]:
        """
        모든 종목의 현재 Ignition Score 반환
        
        Returns:
            Dict[str, float]: ticker -> score
        """
        return self.scores.copy()
    
    def get_score(self, ticker: str) -> float:
        """
        특정 종목의 Ignition Score 반환
        
        Args:
            ticker: 종목 코드
        
        Returns:
            float: Ignition Score (없으면 0.0)
        """
        return self.scores.get(ticker, 0.0)
    
    @property
    def is_running(self) -> bool:
        """모니터링 실행 중 여부"""
        return self.running
    
    @property
    def ticker_count(self) -> int:
        """모니터링 중인 종목 수"""
        return len(self.watchlist_tickers)


# ═══════════════════════════════════════════════════════════════════════════
# 싱글톤 인스턴스 (서버에서 초기화)
# ═══════════════════════════════════════════════════════════════════════════

_monitor_instance: Optional[IgnitionMonitor] = None


def get_ignition_monitor() -> Optional[IgnitionMonitor]:
    """
    전역 IgnitionMonitor 인스턴스 반환
    
    Returns:
        IgnitionMonitor 또는 None (초기화 전)
    """
    return _monitor_instance


def initialize_ignition_monitor(strategy: Any, ws_manager: Any) -> IgnitionMonitor:
    """
    IgnitionMonitor 초기화 (서버 시작 시 호출)
    
    Args:
        strategy: SeismographStrategy 인스턴스
        ws_manager: WebSocket ConnectionManager 인스턴스
    
    Returns:
        IgnitionMonitor 인스턴스
    """
    global _monitor_instance
    _monitor_instance = IgnitionMonitor(strategy, ws_manager)
    return _monitor_instance
