# ============================================================================
# Ignition Monitor - 실시간 Ignition Score 모니터링 서비스
# ============================================================================
# 📌 이 파일의 역할:
#   - Watchlist 종목들의 실시간 가격 폴링 (1초 간격)
#   - SeismographStrategy.calculate_trigger_score() 호출
#   - Score 변화 시 WebSocket으로 브로드캐스트
#
# 📌 아키텍처 (v2 - Timer Polling):
#   - 틱 기반 → 타이머 폴링으로 전환
#   - 1초마다 REST API로 현재가 조회
#   - 프리마켓/애프터마켓 지원
#
# 📖 사용 예시:
#   >>> from backend.core.ignition_monitor import IgnitionMonitor
#   >>> monitor = IgnitionMonitor(strategy, ws_manager)
#   >>> await monitor.start(watchlist)
#   >>> # ... 1초마다 자동으로 Ignition Score 업데이트
#   >>> await monitor.stop()
# ============================================================================

"""
Ignition Monitor Module (v2 - Timer Polling)

Watchlist 종목들의 실시간 Ignition Score를 모니터링하고
Score 변화 시 WebSocket으로 GUI에 푸시합니다.

Phase 2 (Trigger) 로직을 GUI에서 실시간으로 확인할 수 있게 합니다.
"""

import asyncio
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger


class IgnitionMonitor:
    """
    실시간 Ignition Score 모니터링 서비스 (v2 - Timer Polling)

    1초마다 REST API로 현재가를 조회하여 Ignition Score를 계산하고
    변화가 있을 때마다 WebSocket으로 GUI에 푸시합니다.

    Attributes:
        strategy: SeismographStrategy 인스턴스
        ws_manager: WebSocket ConnectionManager 인스턴스
        watchlist_tickers: 모니터링 대상 종목 리스트
        scores: 종목별 현재 Ignition Score 캐시
        running: 모니터링 실행 상태
        poll_interval: 폴링 간격 (초)
    """

    def __init__(self, strategy: Any, ws_manager: Any, poll_interval: float = 1.0):
        """
        IgnitionMonitor 초기화

        Args:
            strategy: SeismographStrategy 인스턴스
            ws_manager: WebSocket ConnectionManager 인스턴스
            poll_interval: 폴링 간격 (초, 기본값: 1.0)
        """
        self.strategy = strategy
        self.ws_manager = ws_manager
        self.poll_interval = poll_interval

        self.watchlist_tickers: List[str] = []
        self.watchlist_data: Dict[str, Dict[str, Any]] = {}  # ticker -> watchlist item
        self.scores: Dict[str, float] = {}  # ticker -> score 캐시
        self.last_prices: Dict[str, float] = {}  # ticker -> last price
        self.running: bool = False
        self._poll_task: Optional[asyncio.Task] = None

        # Polygon API 설정
        self._api_key = os.getenv("MASSIVE_API_KEY", "")

        logger.debug(f"⚡ IgnitionMonitor 초기화 완료 (poll_interval={poll_interval}s)")

    # ═══════════════════════════════════════════════════════════════════════
    # 시작/중지
    # ═══════════════════════════════════════════════════════════════════════

    async def start(self, watchlist: List[Dict[str, Any]]) -> bool:
        """
        모니터링 시작

        Watchlist 종목들의 Context를 로드하고 타이머 폴링을 시작합니다.

        Args:
            watchlist: Watchlist 데이터 (Scanner 결과)

        Returns:
            bool: 시작 성공 여부
        """
        if self.running:
            logger.warning("⚡ IgnitionMonitor: 이미 실행 중")
            return False

        # Watchlist ticker 추출
        self.watchlist_tickers = [
            item.get("ticker", "") for item in watchlist if item.get("ticker")
        ]
        self.watchlist_data = {
            item.get("ticker"): item for item in watchlist if item.get("ticker")
        }

        if not self.watchlist_tickers:
            logger.warning("⚡ IgnitionMonitor: 모니터링할 종목 없음")
            return False

        # [13-002 FIX] load_watchlist_context 삭제 - watchlist_data에서 직접 처리
        # (Dead Code 분석 결과: _watchlist_context를 읽는 코드가 없음)

        # Score 캐시 초기화
        self.scores = {ticker: 0.0 for ticker in self.watchlist_tickers}
        self.last_prices = {}

        self.running = True

        # 폴링 태스크 시작
        self._poll_task = asyncio.create_task(self._polling_loop())

        logger.info(
            f"⚡ IgnitionMonitor 시작: {len(self.watchlist_tickers)}개 종목 모니터링 ({self.poll_interval}s 간격)"
        )

        return True

    async def stop(self):
        """모니터링 중지"""
        if not self.running:
            return

        self.running = False

        # 폴링 태스크 취소
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None

        self.watchlist_tickers = []
        self.watchlist_data = {}
        self.scores = {}
        self.last_prices = {}

        logger.info("⚡ IgnitionMonitor 중지")

    # ═══════════════════════════════════════════════════════════════════════
    # 타이머 폴링 (v2)
    # ═══════════════════════════════════════════════════════════════════════

    async def _polling_loop(self):
        """
        메인 폴링 루프

        1초마다 모든 Watchlist 종목의 현재가를 조회하고
        Ignition Score를 계산합니다.
        """
        import httpx

        logger.info("⚡ IgnitionMonitor: 폴링 루프 시작")

        async with httpx.AsyncClient(timeout=10.0) as client:
            while self.running:
                try:
                    # 현재가 조회 및 Score 계산
                    await self._update_all_scores(client)

                    # 다음 폴링까지 대기
                    await asyncio.sleep(self.poll_interval)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"⚡ IgnitionMonitor 폴링 에러: {e}")
                    await asyncio.sleep(self.poll_interval)

        logger.info("⚡ IgnitionMonitor: 폴링 루프 종료")

    async def _update_all_scores(self, client):
        """
        모든 종목의 현재가 조회 및 Score 업데이트

        Polygon Snapshot API를 사용하여 현재가를 조회합니다.
        """
        if not self.watchlist_tickers:
            return

        # 배치로 현재가 조회 (API 효율성)
        quotes = await self._fetch_quotes(client, self.watchlist_tickers)

        for ticker in self.watchlist_tickers:
            try:
                quote = quotes.get(ticker, {})
                price = quote.get("price", 0.0)

                if price <= 0:
                    continue

                # 가격 변화 체크
                last_price = self.last_prices.get(ticker, 0.0)
                if last_price > 0 and abs(price - last_price) < 0.001:
                    continue  # 가격 변화 없으면 스킵

                self.last_prices[ticker] = price

                # ═══════════════════════════════════════════════════════════════
                # Ignition Score 계산 (v3 - 개선된 공식)
                # ═══════════════════════════════════════════════════════════════
                #
                # 문제: 기존 공식은 +7% 상승이 필요해서 거의 달성 불가
                # 해결: 더 낮은 임계값 + Stage 보너스 + 거래량 보너스
                #
                # 공식: base_score + stage_bonus + volume_bonus
                # - base_score: 변동률 × 14 (→ +5% = 70점)
                # - stage_bonus: Stage 4 = +20, Stage 3 = +10
                # - volume_bonus: 거래량 2배 이상 = +10
                #
                watchlist_item = self.watchlist_data.get(ticker, {})
                last_close = watchlist_item.get("last_close", 0)
                stage_number = watchlist_item.get("stage_number", 0)
                avg_volume = watchlist_item.get("avg_volume", 1)

                if last_close > 0:
                    # 1. Base Score: 변동률 기반
                    # +3% = 42, +4% = 56, +5% = 70, +7% = 98
                    change_pct = ((price - last_close) / last_close) * 100
                    base_score = max(0, change_pct * 14)  # 변동률 × 14

                    # 2. Stage Bonus: Watchlist Stage에 따른 추가 점수
                    # Stage 4 (폭발 임박): +20점
                    # Stage 3 (관심 대상): +10점
                    # Stage 1-2: 0점
                    stage_bonus = 0
                    if stage_number >= 4:
                        stage_bonus = 20
                    elif stage_number >= 3:
                        stage_bonus = 10

                    # 3. Volume Bonus: 거래량 폭발 시 추가 점수
                    volume = quote.get("volume", 0)
                    volume_bonus = 0
                    if avg_volume > 0:
                        volume_ratio = volume / avg_volume
                        if volume_ratio >= 3.0:
                            volume_bonus = 15  # 3배 이상
                        elif volume_ratio >= 2.0:
                            volume_bonus = 10  # 2배 이상
                        elif volume_ratio >= 1.5:
                            volume_bonus = 5  # 1.5배 이상

                    new_score = min(100, base_score + stage_bonus + volume_bonus)

                    # 디버그 로그 (점수가 50 이상일 때만)
                    if new_score >= 50:
                        logger.debug(
                            f"⚡ {ticker}: chg={change_pct:.1f}% base={base_score:.0f} "
                            f"stage_bonus={stage_bonus} vol_bonus={volume_bonus} → {new_score:.0f}"
                        )
                else:
                    new_score = 0.0

                # 이전 점수와 비교
                old_score = self.scores.get(ticker, 0.0)
                score_delta = abs(new_score - old_score)

                # 변화가 크거나 50점 이상이면 브로드캐스트 (70→50 완화)
                if score_delta >= 5.0 or new_score >= 50.0:
                    self.scores[ticker] = new_score

                    # Anti-Trap 필터 체크 (70점 이상일 때만)
                    passed_filter = True
                    reason = ""
                    if new_score >= 70.0 and hasattr(
                        self.strategy, "check_anti_trap_filter"
                    ):
                        filter_result = self.strategy.check_anti_trap_filter(
                            ticker=ticker,
                            price=price,
                            bid=quote.get("bid", 0),
                            ask=quote.get("ask", 0),
                            timestamp=datetime.now(),
                        )
                        passed_filter, reason = filter_result

                    # WebSocket 브로드캐스트
                    if hasattr(self.ws_manager, "broadcast_ignition"):
                        await self.ws_manager.broadcast_ignition(
                            ticker=ticker,
                            score=new_score,
                            passed_filter=passed_filter,
                            reason=reason,
                        )

                    # 70점 이상이면 로그
                    if new_score >= 70.0:
                        logger.info(
                            f"⚡ IGNITION ALERT: {ticker} Score={new_score:.0f} "
                            f"({'✅ CLEAR' if passed_filter else f'❌ {reason}'}) "
                            f"[chg={change_pct:.1f}%]"
                        )

                # 점수 캐시 항상 업데이트
                self.scores[ticker] = new_score

            except Exception as e:
                logger.debug(f"⚡ {ticker} Score 계산 실패: {e}")

    async def _fetch_quotes(
        self, client, tickers: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Polygon Snapshot API로 현재가 조회

        Args:
            client: httpx.AsyncClient
            tickers: 종목 리스트

        Returns:
            Dict[str, Dict]: ticker -> {price, volume, bid, ask}
        """
        quotes = {}

        if not self._api_key:
            logger.warning("⚡ MASSIVE_API_KEY not set")
            return quotes

        # Polygon Snapshot API (배치 조회)
        # https://polygon.io/docs/stocks/get_v2_snapshot_locale_us_markets_stocks_tickers
        try:
            # 전체 스냅샷 조회
            url = "https://api.massive.com/v2/snapshot/locale/us/markets/stocks/tickers"
            params = {
                "tickers": ",".join(tickers[:50]),  # 최대 50개
                "apiKey": self._api_key,
            }

            response = await client.get(url, params=params)

            if response.status_code == 200:
                data = response.json()
                for item in data.get("tickers", []):
                    ticker = item.get("ticker", "")
                    day = item.get("day", {})
                    prev_day = item.get("prevDay", {})
                    last_quote = item.get("lastQuote", {})
                    last_trade = item.get("lastTrade", {})

                    quotes[ticker] = {
                        "price": last_trade.get("p", 0)
                        or day.get("c", 0)
                        or prev_day.get("c", 0),
                        "volume": day.get("v", 0),
                        "bid": last_quote.get("p", 0),
                        "ask": last_quote.get("P", 0),
                    }
            else:
                logger.warning(f"⚡ Snapshot API 실패: {response.status_code}")

        except Exception as e:
            logger.error(f"⚡ Quote 조회 실패: {e}")

        return quotes

    # ═══════════════════════════════════════════════════════════════════════
    # Legacy: 틱 처리 (하위 호환성)
    # ═══════════════════════════════════════════════════════════════════════

    async def on_tick(
        self,
        ticker: str,
        price: float,
        volume: int,
        timestamp: datetime,
        side: str = "B",
        bid: float = 0.0,
        ask: float = 0.0,
    ):
        """
        틱 데이터 수신 시 호출 (하위 호환성용)

        Timer Polling 방식에서는 이 메서드가 호출되지 않지만,
        WebSocket 틱도 함께 사용하는 경우를 위해 유지합니다.
        """
        if not self.running:
            return

        if ticker not in self.watchlist_tickers:
            return

        # 가격 업데이트
        self.last_prices[ticker] = price

        # 전략의 on_tick 호출
        self.strategy.on_tick(
            ticker=ticker,
            price=price,
            volume=volume,
            timestamp=timestamp,
            side=side,
            bid=bid,
            ask=ask,
        )

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
