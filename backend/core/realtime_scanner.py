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
        db: Optional[Any] = None,  # [02-001b] MarketDB 인스턴스
        ignition_monitor: Optional[Any] = None,
        poll_interval: float = 1.0
    ):
        """
        RealtimeScanner 초기화
        
        Args:
            polygon_client: PolygonClient 인스턴스
            ws_manager: WebSocket ConnectionManager 인스턴스
            db: MarketDB 인스턴스 (Optional, score_v2 계산용)
            ignition_monitor: IgnitionMonitor 인스턴스 (Optional)
            poll_interval: 폴링 간격 (초, 기본값: 1.0)
        """
        self.polygon_client = polygon_client
        self.ws_manager = ws_manager
        self.db = db  # [02-001b]
        self.ignition_monitor = ignition_monitor
        self.poll_interval = poll_interval
        
        # [02-001b] SeismographStrategy 초기화 (DB가 있을 때만)
        self.strategy = None
        if db:
            try:
                from backend.strategies.seismograph import SeismographStrategy
                self.strategy = SeismographStrategy()
                logger.info("📊 SeismographStrategy 초기화 완료 (score_v2 계산 활성화)")
            except Exception as e:
                logger.warning(f"⚠️ SeismographStrategy 초기화 실패: {e}")
        
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
        
        logger.info(f"📡 RealtimeScanner 초기화: poll_interval={poll_interval}s, db={'✓' if db else '✗'}")
    
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
        self._recalc_task = asyncio.create_task(self._periodic_score_recalculation())  # [Phase 9]
        
        logger.info("🚀 RealtimeScanner 시작: 1초 폴링 + 브로드캐스트 + 1시간 자동 재계산 활성화")
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
        
        # [Phase 9] 자동 재계산 태스크 중지
        if hasattr(self, '_recalc_task') and self._recalc_task:
            self._recalc_task.cancel()
            try:
                await self._recalc_task
            except asyncio.CancelledError:
                pass
            self._recalc_task = None
        
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
        
        1. DB에서 일봉 조회 → 없으면 API fetch
        2. score_v2 계산
        3. Watchlist에 추가 (병합)
        4. WebSocket 브로드캐스트
        5. IgnitionMonitor에 등록 (있으면)
        
        [02-001b] DB 기반 score_v2 계산 + Massive API fetch
        """
        ticker = item["ticker"]
        change_pct = item.get("change_pct", 0)
        price = item.get("price", 0)
        volume = item.get("volume", 0)
        
        # [Issue 6.1 Fix] dollar_volume 계산
        dollar_volume = price * volume
        
        self._new_ticker_count += 1
        
        logger.info(f"🔥 신규 급등 종목 탐지: {ticker} +{change_pct:.1f}% @ ${price:.2f} (DolVol: ${dollar_volume:,.0f})")
        
        # [02-001b] Score V2 계산 (DB + API fetch)
        score = None
        score_v2 = None
        stage = "Gainer (실시간)"
        stage_number = 3
        signals = {
            "realtime_gainer": True,
            "tight_range": False,
            "accumulation_bar": False,
            "obv_divergence": False,
            "volume_dryout": False,
        }
        can_trade = True
        
        if self.db and self.strategy:
            try:
                # 1) DB에서 일봉 조회
                bars = await self.db.get_daily_bars(ticker, days=20)
                
                # 2) DB에 일봉이 부족하면 Massive API에서 fetch
                if not bars or len(bars) < 5:
                    logger.info(f"📥 {ticker}: DB에 일봉 부족 ({len(bars) if bars else 0}개), Massive API에서 fetch...")
                    await self._fetch_and_store_daily_bars(ticker, days=30)
                    bars = await self.db.get_daily_bars(ticker, days=20)
                
                # 3) Score V2 계산
                if bars and len(bars) >= 5:
                    data = [{"open": b.open, "high": b.high, "low": b.low, "close": b.close, "volume": b.volume} 
                            for b in reversed(bars)]
                    result = self.strategy.calculate_watchlist_score_detailed(ticker, data)
                    score = result.get("score")
                    score_v2 = result.get("score_v2")
                    stage = result.get("stage", stage)
                    stage_number = result.get("stage_number", stage_number)
                    signals = result.get("signals", signals)
                    can_trade = result.get("can_trade", can_trade)
                    logger.info(f"📊 {ticker}: score_v2={score_v2:.1f} (DB 기반)")
                else:
                    logger.warning(f"⚠️ {ticker}: 일봉 데이터 부족, score_v2=None")
            except Exception as e:
                logger.warning(f"⚠️ {ticker} score 계산 실패: {e}")
        
        # 1. Watchlist 항목 생성 (score_v2 포함)
        watchlist_item = {
            "ticker": ticker,
            "change_pct": change_pct,
            "price": price,
            "volume": volume,
            "dollar_volume": dollar_volume,
            "source": "realtime_gainer",
            "discovered_at": datetime.now().isoformat(),
            # [02-001b] 계산된 score 값 사용 (없으면 None → GUI에서 ⚠️ 표시)
            "score": score,
            "score_v2": score_v2,
            "stage": stage,
            "stage_number": stage_number,
            "signals": signals,
            "can_trade": can_trade,
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
    # [02-001b] Massive API Fetch Helper
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _fetch_and_store_daily_bars(self, ticker: str, days: int = 30) -> int:
        """
        Massive API에서 특정 종목의 일봉 데이터를 가져와 DB에 삽입
        
        fetch_grouped_daily()는 전체 종목을 가져오므로,
        단일 종목만 필요할 때는 해당 종목만 필터링하여 저장
        
        Args:
            ticker: 종목 심볼
            days: 가져올 일수 (기본값: 30일)
            
        Returns:
            int: 저장된 일봉 개수
        """
        from datetime import timedelta
        
        if not self.polygon_client or not self.db:
            logger.warning(f"⚠️ {ticker}: polygon_client 또는 db가 없어서 fetch 불가")
            return 0
        
        try:
            from backend.data.polygon_loader import PolygonLoader
            
            # 최근 N 거래일 계산
            end_date = datetime.now() - timedelta(days=1)
            start_date = end_date - timedelta(days=days)
            trading_days = PolygonLoader.get_trading_days_between(start_date, end_date)
            
            if not trading_days:
                logger.warning(f"⚠️ {ticker}: 거래일 없음")
                return 0
            
            stored_count = 0
            # 최근 10거래일만 fetch (API 부하 감소)
            for date in trading_days[-10:]:
                try:
                    bars = await self.polygon_client.fetch_grouped_daily(date)
                    if not bars:
                        continue
                    
                    # 해당 종목만 필터링
                    for bar in bars:
                        bar_ticker = bar.get("T") or bar.get("ticker", "")
                        if bar_ticker == ticker:
                            # DB에 삽입
                            await self.db.insert_daily_bar(
                                ticker=ticker,
                                date=date,
                                open_price=bar.get("o", 0),
                                high=bar.get("h", 0),
                                low=bar.get("l", 0),
                                close=bar.get("c", 0),
                                volume=bar.get("v", 0),
                                vwap=bar.get("vw", 0),
                            )
                            stored_count += 1
                            break
                except Exception as e:
                    logger.debug(f"⚠️ {ticker} @ {date} fetch 실패: {e}")
                    continue
            
            if stored_count > 0:
                logger.info(f"✅ {ticker}: {stored_count}개 일봉 저장됨")
            else:
                logger.warning(f"⚠️ {ticker}: API에서 데이터를 찾을 수 없음")
            
            return stored_count
            
        except Exception as e:
            logger.warning(f"⚠️ {ticker} 일봉 fetch 실패: {e}")
            return 0
    
    # ═══════════════════════════════════════════════════════════════════════
    # [Issue 01-003] Periodic Watchlist Broadcast
    # ═══════════════════════════════════════════════════════════════════════
    
    async def _periodic_watchlist_broadcast(self) -> None:
        """
        1초마다 전체 Watchlist를 GUI에 브로드캐스트
        
        [Issue 01-003] 데이터 Hydration:
        - 실시간 가격으로 dollar_volume 재계산
        - 모든 필드가 최신 상태로 유지됨
        
        [Phase 6] score_v2 없는 항목 실시간 계산
        """
        logger.info("📡 Periodic Watchlist Broadcast 시작 (1초 간격)")
        
        # [Phase 6] score_v2 계산이 필요한 티커 캐시 (중복 계산 방지)
        _score_v2_calculated: set = set()
        
        while self._running:
            try:
                await asyncio.sleep(1.0)
                
                if not self._running:
                    break
                
                # 최신 Watchlist 로드
                from backend.data.watchlist_store import load_watchlist, save_watchlist
                watchlist = load_watchlist()
                
                if not watchlist:
                    continue
                
                # 실시간 가격/볼륨으로 dollar_volume 재계산 (Hydration)
                hydrated_count = 0
                score_v2_calculated_count = 0
                watchlist_updated = False
                
                for item in watchlist:
                    ticker = item.get("ticker")
                    if not ticker:
                        continue
                    
                    # dollar_volume hydration
                    if ticker in self._latest_prices:
                        price, volume = self._latest_prices[ticker]
                        item["price"] = price
                        item["volume"] = volume
                        item["dollar_volume"] = price * volume
                        hydrated_count += 1
                    
                    # [Phase 6] score_v2 없는 항목 실시간 계산
                    score_v2 = item.get("score_v2")
                    if (score_v2 is None or score_v2 == 0) and ticker not in _score_v2_calculated:
                        if self.db and self.strategy:
                            try:
                                bars = await self.db.get_daily_bars(ticker, days=20)
                                if bars and len(bars) >= 5:
                                    data = [{"open": b.open, "high": b.high, "low": b.low, "close": b.close, "volume": b.volume} 
                                            for b in reversed(bars)]
                                    result = self.strategy.calculate_watchlist_score_detailed(ticker, data)
                                    item["score"] = result.get("score")
                                    item["score_v2"] = result.get("score_v2")
                                    item["stage"] = result.get("stage", item.get("stage", ""))
                                    item["stage_number"] = result.get("stage_number", item.get("stage_number", 0))
                                    score_v2_calculated_count += 1
                                    watchlist_updated = True
                                    logger.info(f"📊 {ticker}: score_v2={result.get('score_v2'):.1f} (Periodic 계산)")
                                else:
                                    # [Phase 7] 일봉 5일 미만 → 신규/IPO 마커
                                    item["score_v2"] = -1
                                    item["stage"] = "신규/IPO (데이터 부족)"
                                    watchlist_updated = True
                                    logger.info(f"🆕 {ticker}: 일봉 {len(bars) if bars else 0}일 미만 → 신규/IPO 마커")
                                _score_v2_calculated.add(ticker)  # 성공/실패 상관없이 캐시에 추가
                            except Exception as e:
                                logger.debug(f"⚠️ {ticker} score_v2 계산 실패: {e}")
                                _score_v2_calculated.add(ticker)
                
                # [Phase 6] 계산된 score_v2를 저장소에 반영 (영구 저장)
                if watchlist_updated:
                    try:
                        save_watchlist(watchlist)
                    except Exception as e:
                        logger.debug(f"⚠️ Watchlist 저장 실패: {e}")
                
                # 브로드캐스트
                if self.ws_manager:
                    await self.ws_manager.broadcast_watchlist(watchlist)
                    if score_v2_calculated_count > 0:
                        logger.debug(f"📤 Periodic Broadcast: {len(watchlist)}개 종목 ({hydrated_count}개 hydrated, {score_v2_calculated_count}개 score_v2 계산)")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"⚠️ Periodic Broadcast 오류: {e}")
        
        logger.info("📡 Periodic Watchlist Broadcast 종료")
    
    # ═══════════════════════════════════════════════════════════════════════
    # [Phase 9] Score V2 재계산 시스템
    # ═══════════════════════════════════════════════════════════════════════
    
    async def recalculate_all_scores(self) -> dict:
        """
        [Phase 9] 전체 Watchlist score_v2 순차 재계산
        
        부하 분산을 위해 1종목당 100ms 딜레이
        
        Returns:
            dict: {"success": int, "failed": int, "skipped": int, "timestamp": str}
        """
        from datetime import datetime
        from backend.data.watchlist_store import load_watchlist, save_watchlist
        
        if not self.db or not self.strategy:
            logger.warning("⚠️ DB 또는 Strategy 미초기화 - 재계산 불가")
            return {"success": 0, "failed": 0, "skipped": 0, "timestamp": datetime.now().strftime("%H:%M:%S")}
        
        watchlist = load_watchlist()
        if not watchlist:
            return {"success": 0, "failed": 0, "skipped": 0, "timestamp": datetime.now().strftime("%H:%M:%S")}
        
        success, failed, skipped = 0, 0, 0
        logger.info(f"🔄 Score V2 재계산 시작: {len(watchlist)}개 종목")
        
        for item in watchlist:
            ticker = item.get("ticker")
            if not ticker:
                skipped += 1
                continue
            
            try:
                bars = await self.db.get_daily_bars(ticker, days=20)
                
                if bars and len(bars) >= 5:
                    data = [{"open": b.open, "high": b.high, "low": b.low, "close": b.close, "volume": b.volume} 
                            for b in reversed(bars)]
                    result = self.strategy.calculate_watchlist_score_detailed(ticker, data)
                    item["score"] = result.get("score")
                    item["score_v2"] = result.get("score_v2")
                    item["stage"] = result.get("stage", "")
                    item["stage_number"] = result.get("stage_number", 0)
                    success += 1
                    logger.debug(f"📊 {ticker}: score_v2={result.get('score_v2'):.1f}")
                else:
                    # 일봉 부족 → 신규/IPO 마커
                    item["score_v2"] = -1
                    item["stage"] = "신규/IPO (데이터 부족)"
                    skipped += 1
                
                await asyncio.sleep(0.1)  # 100ms 딜레이 (부하 분산)
                
            except Exception as e:
                logger.debug(f"⚠️ {ticker} 재계산 실패: {e}")
                failed += 1
        
        # 저장
        try:
            save_watchlist(watchlist)
        except Exception as e:
            logger.warning(f"⚠️ Watchlist 저장 실패: {e}")
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        logger.info(f"✅ Score V2 재계산 완료: 성공={success}, 실패={failed}, 스킵={skipped} (at {timestamp})")
        
        # 브로드캐스트
        if self.ws_manager:
            await self.ws_manager.broadcast_watchlist(watchlist)
        
        return {"success": success, "failed": failed, "skipped": skipped, "timestamp": timestamp}
    
    async def _periodic_score_recalculation(self) -> None:
        """
        [Phase 9] 1시간마다 자동으로 score_v2 재계산
        """
        logger.info("⏰ 자동 Score V2 재계산 시작 (1시간 간격)")
        
        while self._running:
            try:
                await asyncio.sleep(3600)  # 1시간 = 3600초
                
                if not self._running:
                    break
                
                logger.info("⏰ 1시간 경과 - 자동 Score V2 재계산 실행")
                await self.recalculate_all_scores()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"⚠️ 자동 재계산 오류: {e}")
        
        logger.info("⏰ 자동 Score V2 재계산 종료")
    
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
    db: Optional[Any] = None,  # [02-001b] MarketDB 인스턴스
    ignition_monitor: Optional[Any] = None,
    poll_interval: float = 1.0
) -> RealtimeScanner:
    """
    RealtimeScanner 초기화 (서버 시작 시 호출)
    
    Args:
        polygon_client: PolygonClient 인스턴스
        ws_manager: WebSocket ConnectionManager 인스턴스
        db: MarketDB 인스턴스 (Optional, score_v2 계산용)
        ignition_monitor: IgnitionMonitor 인스턴스 (Optional)
        poll_interval: 폴링 간격 (초, 기본값: 1.0)
    
    Returns:
        RealtimeScanner 인스턴스
    """
    global _scanner_instance
    _scanner_instance = RealtimeScanner(
        polygon_client=polygon_client,
        ws_manager=ws_manager,
        db=db,  # [02-001b]
        ignition_monitor=ignition_monitor,
        poll_interval=poll_interval
    )
    return _scanner_instance


def get_scanner_instance() -> Optional[RealtimeScanner]:
    """
    [Phase 9] 현재 RealtimeScanner 인스턴스 반환
    
    API 엔드포인트에서 스캐너에 접근할 때 사용
    """
    global _scanner_instance
    return _scanner_instance

