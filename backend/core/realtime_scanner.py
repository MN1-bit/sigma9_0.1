# ============================================================================
# Realtime Gainers Scanner - 실시간 급등 종목 스캐너
# ============================================================================
# 📌 이 파일의 역할:
#   - Polygon Gainers API를 1초 간격으로 폴링하여 급등 종목 탐지
#   - 신규 종목 발견 시 Watchlist에 자동 추가 및 WebSocket 브로드캐스트
#   - IgnitionMonitor에 자동 등록하여 실시간 모니터링 시작
#
# 📡 사용 API:
#   - Polygon Gainers: /v2/snapshot/locale/us/markets/stocks/gainers
#     → ~10KB, 21개 종목, 1초 폴링 시 600KB/분 (무시 가능)
#
# 📖 사용 예시:
#   >>> scanner = RealtimeScanner(polygon_client, ws_manager)
#   >>> await scanner.start()
#   # 1초마다 급등주 폴링 시작
#   >>> await scanner.stop()
# ============================================================================

"""
Realtime Gainers Scanner Module

Polygon Gainers API를 1초 간격으로 폴링하여 실시간 급등 종목을 탐지합니다.
이전에 알려지지 않은 신규 종목이 발견되면:
1. Watchlist에 자동 추가
2. WebSocket으로 GUI에 브로드캐스트
3. IgnitionMonitor에 등록하여 Ignition Score 모니터링 시작

masterplan.md Section 7.3 "Source B (Real-Time Gainers)" 구현입니다.
"""

import asyncio
import os
from datetime import datetime
from typing import Set, List, Dict, Any, Optional
from loguru import logger


class RealtimeScanner:
    """
    실시간 급등 종목 스캐너 (1초 폴링)
    
    ═══════════════════════════════════════════════════════════════════════
    역할:
    ═══════════════════════════════════════════════════════════════════════
    - Polygon Gainers API를 1초마다 폴링
    - 신규 급등 종목 탐지 (Set diff)
    - Watchlist 자동 병합 + WebSocket 브로드캐스트
    
    ═══════════════════════════════════════════════════════════════════════
    예상 결과:
    ═══════════════════════════════════════════════════════════════════════
    | 상황 | 수정 전 | 수정 후 |
    |------|--------|--------|
    | SMXT +40% 급등 | ❌ 탐지 안됨 | ✅ 1초 내 탐지 |
    | 신규 급등 종목 | ❌ 놓침 | ✅ 실시간 Watchlist 추가 |
    | Tier 2 승격 | ❌ 불가 | ✅ 자동 승격 |
    
    Attributes:
        polygon_client: PolygonClient 인스턴스
        ws_manager: WebSocket ConnectionManager 인스턴스
        ignition_monitor: IgnitionMonitor 인스턴스 (Optional)
        poll_interval: 폴링 간격 (초, 기본값: 1.0)
    """
    
    def __init__(
        self,
        polygon_client: Any,
        ws_manager: Any,
        ignition_monitor: Optional[Any] = None,
        poll_interval: float = 1.0
    ):
        """
        RealtimeScanner 초기화
        
        Args:
            polygon_client: PolygonClient 인스턴스
            ws_manager: WebSocket ConnectionManager 인스턴스
            ignition_monitor: IgnitionMonitor 인스턴스 (Optional)
            poll_interval: 폴링 간격 (초, 기본값: 1.0)
        """
        self.polygon_client = polygon_client
        self.ws_manager = ws_manager
        self.ignition_monitor = ignition_monitor
        self.poll_interval = poll_interval
        
        # 내부 상태
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._broadcast_task: Optional[asyncio.Task] = None  # [Issue 01-003] 주기적 브로드캐스트 태스크
        self._known_tickers: Set[str] = set()  # 이미 알고 있는 종목
        self._watchlist: List[Dict[str, Any]] = []  # 현재 Watchlist
        self._latest_prices: Dict[str, tuple] = {}  # [Issue 01-003] 실시간 가격 캐시 (ticker -> (price, volume))
        
        # 통계
        self._poll_count = 0
        self._new_ticker_count = 0
        self._last_poll_time: Optional[datetime] = None
        
        logger.info(f"📡 RealtimeScanner 초기화: poll_interval={poll_interval}s")
    
    # ═══════════════════════════════════════════════════════════════════════
    # Public Methods
    # ═══════════════════════════════════════════════════════════════════════
    
    async def start(self, initial_watchlist: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        1초 간격 폴링 루프 시작
        
        Args:
            initial_watchlist: 기존 Watchlist (이미 알려진 종목으로 등록)
        
        Returns:
            bool: 시작 성공 여부
        """
        if self._running:
            logger.warning("⚠️ RealtimeScanner: 이미 실행 중")
            return False
        
        # 기존 Watchlist 종목은 known으로 등록 (중복 탐지 방지)
        if initial_watchlist:
            for item in initial_watchlist:
                ticker = item.get("ticker") or item.get("symbol", "")
                if ticker:
                    self._known_tickers.add(ticker)
            self._watchlist = initial_watchlist.copy()
            logger.info(f"📋 기존 Watchlist {len(initial_watchlist)}개 종목 로드")
        
        self._running = True
        self._task = asyncio.create_task(self._polling_loop())
        self._broadcast_task = asyncio.create_task(self._periodic_watchlist_broadcast())  # [Issue 01-003]
        
        logger.info("🚀 RealtimeScanner 시작: 1초 폴링 + 브로드캐스트 활성화")
        return True
    
    async def stop(self) -> None:
        """스캐너 중지"""
        if not self._running:
            return
        
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        # [Issue 01-003] 브로드캐스트 태스크 중지
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass
            self._broadcast_task = None
        
        logger.info(f"🛑 RealtimeScanner 중지: {self._poll_count}회 폴링, {self._new_ticker_count}개 신규 종목 탐지")
    
    def get_stats(self) -> Dict[str, Any]:
        """스캐너 통계 반환"""
        return {
            "running": self._running,
            "poll_count": self._poll_count,
            "new_ticker_count": self._new_ticker_count,
            "known_ticker_count": len(self._known_tickers),
            "last_poll_time": self._last_poll_time.isoformat() if self._last_poll_time else None,
        }
    
    def get_known_tickers(self) -> List[str]:
        """현재까지 발견된 모든 종목 목록"""
        return list(self._known_tickers)
    
    # ═══════════════════════════════════════════════════════════════════════
    # Private Methods
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _polling_loop(self) -> None:
        """메인 폴링 루프"""
        logger.info("📡 RealtimeScanner 폴링 루프 시작...")
        
        while self._running:
            try:
                await self._poll_gainers()
                self._poll_count += 1
                self._last_poll_time = datetime.now()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"⚠️ RealtimeScanner 폴링 오류: {e}")
            
            await asyncio.sleep(self.poll_interval)
        
        logger.info("📡 RealtimeScanner 폴링 루프 종료")
    
    async def _poll_gainers(self) -> None:
        """Gainers API 조회 및 신규 종목 탐지"""
        try:
            gainers = await self.polygon_client.get_gainers()
            
            if not gainers:
                return
            
            for item in gainers:
                ticker = item.get("ticker", "")
                if not ticker:
                    continue
                
                # [Issue 01-003] 실시간 가격 캐시 업데이트
                price = item.get("price", 0)
                volume = item.get("volume", 0)
                if price > 0 and volume > 0:
                    self._latest_prices[ticker] = (price, volume)
                
                # 신규 종목만 처리
                if ticker not in self._known_tickers:
                    self._known_tickers.add(ticker)
                    await self._handle_new_gainer(item)
                    
        except Exception as e:
            logger.warning(f"⚠️ Gainers 폴링 실패: {e}")
    
    async def _handle_new_gainer(self, item: Dict[str, Any]) -> None:
        """
        신규 급등 종목 처리
        
        1. Watchlist에 추가 (병합)
        2. WebSocket 브로드캐스트
        3. IgnitionMonitor에 등록 (있으면)
        
        [Issue 6.1 Fix] dollar_volume 필드 추가
        [Issue 6.2 Fix] 기존 Watchlist와 병합 (덮어쓰기 대신)
        """
        ticker = item["ticker"]
        change_pct = item.get("change_pct", 0)
        price = item.get("price", 0)
        volume = item.get("volume", 0)
        
        # [Issue 6.1 Fix] dollar_volume 계산
        dollar_volume = price * volume
        
        self._new_ticker_count += 1
        
        logger.info(f"🔥 신규 급등 종목 탐지: {ticker} +{change_pct:.1f}% @ ${price:.2f} (DolVol: ${dollar_volume:,.0f})")
        
        # 1. Watchlist 항목 생성 (dollar_volume 포함)
        watchlist_item = {
            "ticker": ticker,
            "change_pct": change_pct,
            "price": price,
            "volume": volume,
            "dollar_volume": dollar_volume,  # [Issue 6.1 Fix]
            "source": "realtime_gainer",  # 출처 표시
            "discovered_at": datetime.now().isoformat(),
            # 기본 메타데이터 (Scanner가 채울 때까지 임시값)
            "score": 50.0,  # Day Gainer는 기본 50점 (Stage 3 수준)
            "score_v2": 50.0,  # [02-001] v2 점수도 동일 기본값
            "stage": "Gainer (실시간)",

            "stage_number": 3,
            "signals": {
                "realtime_gainer": True,
                "tight_range": False,
                "accumulation_bar": False,
                "obv_divergence": False,
                "volume_dryout": False,
            },
            "can_trade": True,  # Gainer는 즉시 트레이딩 가능
        }
        
        # [Issue 6.2 Fix] 기존 Watchlist와 병합 (덮어쓰기 대신)
        try:
            from backend.data.watchlist_store import load_watchlist, save_watchlist
            current = load_watchlist()  # 기존 Watchlist 로드
            
            # 중복 체크 후 추가
            existing_tickers = {w.get("ticker") for w in current}
            if ticker not in existing_tickers:
                current.append(watchlist_item)
                save_watchlist(current)
                self._watchlist = current  # 동기화
                logger.debug(f"✅ Watchlist 병합 완료: {len(current)}개 종목")
            else:
                # 이미 존재하면 내부 리스트만 동기화
                self._watchlist = current
                logger.debug(f"ℹ️ {ticker}은 이미 Watchlist에 존재")
        except Exception as e:
            logger.warning(f"⚠️ Watchlist 저장 실패: {e}")
            # 실패 시 기존 로직 유지 (내부 리스트에만 추가)
            self._watchlist.append(watchlist_item)
        
        # 3. WebSocket 브로드캐스트 (전체 Watchlist)
        # [Issue 01-002 Fix] self._watchlist는 이미 current로 동기화되어 있음
        if self.ws_manager:
            try:
                # self._watchlist가 전체 Watchlist (동기화됨)
                await self.ws_manager.broadcast_watchlist(self._watchlist)
                logger.info(f"📤 Watchlist 브로드캐스트: {len(self._watchlist)}개 (전체)")
            except Exception as e:
                logger.warning(f"⚠️ WebSocket 브로드캐스트 실패: {e}")
        
        # 4. IgnitionMonitor에 등록 (옵션)
        if self.ignition_monitor:
            try:
                # IgnitionMonitor에 종목 추가 (동적 등록)
                # NOTE: IgnitionMonitor 인터페이스에 따라 조정 필요
                if hasattr(self.ignition_monitor, 'add_ticker'):
                    self.ignition_monitor.add_ticker(ticker, watchlist_item)
                    logger.debug(f"🎯 IgnitionMonitor에 {ticker} 등록")
            except Exception as e:
                logger.warning(f"⚠️ IgnitionMonitor 등록 실패: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # [Issue 01-003] Periodic Watchlist Broadcast
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _periodic_watchlist_broadcast(self) -> None:
        """
        1초마다 전체 Watchlist를 GUI에 브로드캐스트
        
        [Issue 01-003] 데이터 Hydration:
        - 실시간 가격으로 dollar_volume 재계산
        - 모든 필드가 최신 상태로 유지됨
        """
        logger.info("📡 Periodic Watchlist Broadcast 시작 (1초 간격)")
        
        while self._running:
            try:
                await asyncio.sleep(1.0)
                
                if not self._running:
                    break
                
                # 최신 Watchlist 로드
                from backend.data.watchlist_store import load_watchlist
                watchlist = load_watchlist()
                
                if not watchlist:
                    continue
                
                # 실시간 가격/볼륨으로 dollar_volume 재계산 (Hydration)
                hydrated_count = 0
                for item in watchlist:
                    ticker = item.get("ticker")
                    if ticker and ticker in self._latest_prices:
                        price, volume = self._latest_prices[ticker]
                        item["price"] = price
                        item["volume"] = volume
                        item["dollar_volume"] = price * volume
                        hydrated_count += 1
                    
                    # [02-001] score_v2 hydration: 없으면 score로 채움
                    if "score_v2" not in item and "score" in item:
                        item["score_v2"] = item["score"]

                
                # 브로드캐스트
                if self.ws_manager:
                    await self.ws_manager.broadcast_watchlist(watchlist)
                    logger.debug(f"📤 Periodic Broadcast: {len(watchlist)}개 종목 ({hydrated_count}개 hydrated)")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"⚠️ Periodic Broadcast 오류: {e}")
        
        logger.info("📡 Periodic Watchlist Broadcast 종료")
    
    @property
    def is_running(self) -> bool:
        """스캐너 실행 중 여부"""
        return self._running
    
    @property
    def watchlist(self) -> List[Dict[str, Any]]:
        """현재 Watchlist 반환"""
        return self._watchlist


# ═══════════════════════════════════════════════════════════════════════════
# 싱글톤 인스턴스
# ═══════════════════════════════════════════════════════════════════════════

_scanner_instance: Optional[RealtimeScanner] = None


def get_realtime_scanner() -> Optional[RealtimeScanner]:
    """
    전역 RealtimeScanner 인스턴스 반환
    
    Returns:
        RealtimeScanner 또는 None (초기화 전)
    """
    return _scanner_instance


def initialize_realtime_scanner(
    polygon_client: Any,
    ws_manager: Any,
    ignition_monitor: Optional[Any] = None,
    poll_interval: float = 1.0
) -> RealtimeScanner:
    """
    RealtimeScanner 초기화 (서버 시작 시 호출)
    
    Args:
        polygon_client: PolygonClient 인스턴스
        ws_manager: WebSocket ConnectionManager 인스턴스
        ignition_monitor: IgnitionMonitor 인스턴스 (Optional)
        poll_interval: 폴링 간격 (초, 기본값: 1.0)
    
    Returns:
        RealtimeScanner 인스턴스
    """
    global _scanner_instance
    _scanner_instance = RealtimeScanner(
        polygon_client=polygon_client,
        ws_manager=ws_manager,
        ignition_monitor=ignition_monitor,
        poll_interval=poll_interval
    )
    return _scanner_instance
