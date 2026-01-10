"""
Realtime Services Initialization
=================================
실시간 데이터 파이프라인 초기화를 담당.

📌 역할:
    1. IgnitionMonitor 초기화 및 자동 시작
    2. Massive WebSocket 연결
    3. RealtimeScanner 시작
    4. IBKR 연결 (Optional)
    5. Scheduler 초기화
"""

import asyncio
import os
from typing import TYPE_CHECKING, Optional, Any

from loguru import logger

if TYPE_CHECKING:
    from backend.core.config_loader import ServerConfig
    from backend.data.database import MarketDB
    from backend.core.strategy_loader import StrategyLoader


class RealtimeServicesResult:
    """
    실시간 서비스 초기화 결과를 담는 컨테이너

    📌 서버 lifespan에서 app_state에 할당할 객체들을 담음
    """

    def __init__(self):
        self.ignition_monitor = None
        self.massive_ws = None
        self.tick_broadcaster = None
        self.tick_dispatcher = None
        self.sub_manager = None
        self.trailing_stop = None
        self.realtime_scanner = None
        self.scheduler = None
        self.ibkr = None


async def initialize_ignition_monitor(
    db: Optional["MarketDB"],
) -> Optional[Any]:
    """
    IgnitionMonitor 초기화 [Step 4.A.4]

    📌 [02-003] 직접 클래스 생성 방식으로 변경
    📌 기존 ignition_monitor.py의 initialize_ignition_monitor() 함수 삭제 예정

    Args:
        db: MarketDB 인스턴스

    Returns:
        IgnitionMonitor 인스턴스 또는 None
    """
    try:
        # [02-003] 직접 IgnitionMonitor 클래스 import (싱글톤 함수 삭제 예정)
        from backend.core.ignition_monitor import IgnitionMonitor
        from backend.api.websocket import manager as ws_manager
        from backend.strategies.seismograph import SeismographStrategy

        strategy = SeismographStrategy()
        # [02-003] 직접 IgnitionMonitor 인스턴스 생성
        monitor = IgnitionMonitor(strategy, ws_manager, poll_interval=1.0)
        logger.info("✅ IgnitionMonitor initialized")
        return monitor
    except Exception as e:
        logger.warning(f"⚠️ IgnitionMonitor init skipped: {e}")
        return None


async def start_ignition_monitor(
    ignition_monitor: Optional[Any],
    db: Optional["MarketDB"],
) -> None:
    """
    IgnitionMonitor 자동 시작 [Bugfix: Ignition Score 자동 계산]

    📌 Watchlist가 없으면 Scanner를 자동 실행하여 종목 수집

    Args:
        ignition_monitor: IgnitionMonitor 인스턴스
        db: MarketDB 인스턴스
    """
    if not ignition_monitor:
        return

    try:
        from backend.data.watchlist_store import load_watchlist, merge_watchlist

        watchlist = load_watchlist()

        # Watchlist가 없으면 Scanner 자동 실행
        if not watchlist:
            logger.info("📡 No watchlist found, running auto-scanner...")
            try:
                from backend.core.scanner import Scanner
                from backend.strategies.seismograph import SeismographStrategy

                scanner = Scanner(db)
                strategy = SeismographStrategy()

                # 간단한 스캔 실행 (Day Gainers 기반)
                results = await scanner.scan_with_strategy(strategy, limit=30)

                if results:
                    # [Issue 6.2 Fix] 덮어쓰기 대신 병합
                    watchlist = merge_watchlist(results, update_existing=True)
                    logger.info(
                        f"✅ Auto-scanner completed: {len(results)} stocks found"
                    )
                else:
                    logger.warning("⚠️ Auto-scanner returned no results")
            except Exception as scan_error:
                logger.warning(f"⚠️ Auto-scanner failed: {scan_error}")

        if watchlist:
            await ignition_monitor.start(watchlist)
            logger.info(f"✅ IgnitionMonitor started with {len(watchlist)} tickers")
        else:
            logger.info("ℹ️ IgnitionMonitor: No watchlist, will start when scanner runs")
    except Exception as e:
        logger.warning(f"⚠️ IgnitionMonitor auto-start skipped: {e}")


async def initialize_massive_websocket(
    strategy_loader: Optional["StrategyLoader"],
    ibkr: Optional[Any],
    db: Optional["MarketDB"],
) -> RealtimeServicesResult:
    """
    Massive WebSocket 및 관련 서비스 초기화 (Phase 4.A.0)

    Args:
        strategy_loader: StrategyLoader 인스턴스
        ibkr: IBKR 커넥터 인스턴스
        db: MarketDB 인스턴스

    Returns:
        RealtimeServicesResult: 초기화된 서비스들
    """
    result = RealtimeServicesResult()

    if os.getenv("MASSIVE_WS_ENABLED", "false").lower() != "true":
        return result

    try:
        from backend.data.massive_ws_client import MassiveWebSocketClient
        from backend.core.tick_broadcaster import TickBroadcaster
        from backend.core.tick_dispatcher import TickDispatcher
        from backend.core.subscription_manager import SubscriptionManager
        from backend.api.websocket import manager as ws_manager

        # TickDispatcher 생성 (중앙 틱 배포자)
        result.tick_dispatcher = TickDispatcher()

        # 활성 전략이 있으면 TickDispatcher에 등록
        # [FIX 13-001] get_active_strategy() → get_strategy() 또는 load_strategy() 사용
        if strategy_loader:
            active_strategy = strategy_loader.get_strategy(
                "seismograph"
            ) or strategy_loader.load_strategy("seismograph")
            if active_strategy and hasattr(active_strategy, "on_tick"):

                def strategy_tick_handler(tick: dict):
                    active_strategy.on_tick(
                        ticker=tick.get("ticker", ""),
                        price=tick.get("price", 0),
                        volume=tick.get("size", 0),
                        timestamp=tick.get("time", 0),
                    )

                result.tick_dispatcher.register("strategy", strategy_tick_handler)
                logger.info("✅ Strategy connected to TickDispatcher")

        # [Step 4.A.0.b.4] TrailingStopManager 초기화
        # 📌 [10-001] IBKR 네이티브 Trailing Stop 사용
        # 서버 사이드 고점 추적이므로 틱 핸들러 등록 불필요
        try:
            from backend.core.trailing_stop import TrailingStopManager

            result.trailing_stop = TrailingStopManager(connector=ibkr)
            # NOTE: 틱 핸들러 등록 제거 (10-001 리팩터링)
            # IBKR 네이티브 Trailing Stop은 서버에서 자동으로 고점 추적
            # result.tick_dispatcher.register("trailing_stop", ...) 삭제
            logger.info("✅ TrailingStop initialized (IBKR Native)")
        except Exception as e:
            logger.warning(f"⚠️ TrailingStop init skipped: {e}")

        result.massive_ws = MassiveWebSocketClient()
        result.tick_broadcaster = TickBroadcaster(
            result.massive_ws,
            ws_manager,
            asyncio.get_event_loop(),
            tick_dispatcher=result.tick_dispatcher,
        )
        result.sub_manager = SubscriptionManager(result.massive_ws)

        # 백그라운드에서 Massive 연결 시작
        async def start_massive_streaming():
            if await result.massive_ws.connect():
                logger.info("✅ Massive WebSocket connected")

                # [Step 4.A.0.c P1] 초기 구독 트리거
                try:
                    if db:
                        watchlist = (
                            db.get_watchlist_tickers()
                            if hasattr(db, "get_watchlist_tickers")
                            else []
                        )
                        if watchlist and result.sub_manager:
                            result.sub_manager.sync_watchlist(watchlist)
                            logger.info(
                                f"✅ Auto-subscribed to {len(watchlist)} tickers"
                            )
                except Exception as e:
                    logger.warning(f"⚠️ Auto-subscribe skipped: {e}")

                # [Step 4.A.0.c P0] listen() 루프 시작
                async for _ in result.massive_ws.listen():
                    pass
            else:
                logger.warning("⚠️ Massive WebSocket connection failed")

        asyncio.create_task(start_massive_streaming())
        logger.info("📡 Massive WebSocket initializing...")

    except Exception as e:
        logger.warning(f"⚠️ Massive WebSocket init skipped: {e}")

    return result


async def initialize_realtime_scanner(
    db: Optional["MarketDB"],
    ignition_monitor: Optional[Any],
) -> Optional[Any]:
    """
    RealtimeScanner 초기화 [Step 4.A.5]

    📌 [02-002] Container 또는 직접 클래스 생성 방식으로 변경
    📌 기존 realtime_scanner.py의 initialize_realtime_scanner() 함수 삭제됨

    Args:
        db: MarketDB 인스턴스
        ignition_monitor: IgnitionMonitor 인스턴스

    Returns:
        RealtimeScanner 인스턴스 또는 None
    """
    if os.getenv("REALTIME_SCANNER_ENABLED", "true").lower() != "true":
        return None

    try:
        # [02-002] 직접 RealtimeScanner 클래스 import (싱글톤 함수 삭제됨)
        from backend.core.realtime_scanner import RealtimeScanner
        from backend.data.massive_client import MassiveClient
        from backend.data.watchlist_store import load_watchlist
        from backend.api.websocket import manager as ws_manager

        # MassiveClient 인스턴스 생성 (API Key 필요)
        api_key = os.getenv("MASSIVE_API_KEY", "")
        if not api_key:
            logger.warning("⚠️ RealtimeScanner skipped: MASSIVE_API_KEY not set")
            return None

        massive_client = MassiveClient(api_key)
        await massive_client.__aenter__()  # HTTP Client 초기화

        # [01-001] ScoringStrategy DI 주입 (순환 의존성 해소)
        from backend.strategies.seismograph import SeismographStrategy

        scoring_strategy = SeismographStrategy() if db else None

        # [13-002 FIX] DataRepository 인스턴스 생성
        # RealtimeScanner는 db 대신 data_repository를 사용
        from backend.data.data_repository import DataRepository
        from backend.data.parquet_manager import ParquetManager

        parquet_manager = ParquetManager()
        repo = DataRepository(parquet_manager, massive_client)

        # [02-002] 직접 RealtimeScanner 인스턴스 생성
        scanner = RealtimeScanner(
            massive_client=massive_client,
            ws_manager=ws_manager,
            data_repository=repo,  # [13-002 FIX] db → data_repository
            ignition_monitor=ignition_monitor,
            poll_interval=1.0,  # 1초 폴링
            scoring_strategy=scoring_strategy,  # [01-001] DI 주입
        )

        # 기존 Watchlist 로드 후 시작
        existing_watchlist = load_watchlist()
        await scanner.start(initial_watchlist=existing_watchlist)
        logger.info("🔥 RealtimeScanner started (1s polling for gainers)")

        return scanner
    except Exception as e:
        logger.warning(f"⚠️ RealtimeScanner init skipped: {e}")
        return None


def initialize_scheduler(
    config: "ServerConfig", db: Optional["MarketDB"]
) -> Optional[Any]:
    """
    Trading Scheduler 초기화

    Args:
        config: ServerConfig 인스턴스
        db: MarketDB 인스턴스

    Returns:
        TradingScheduler 인스턴스 또는 None
    """
    if not config.scheduler.enabled:
        return None

    try:
        from backend.core.scheduler import TradingScheduler

        scheduler = TradingScheduler(config.scheduler, db)
        scheduler.start()
        logger.info("✅ Scheduler started")
        return scheduler
    except ImportError:
        logger.info("ℹ️ Scheduler module not found - will be created in Step 4.1.4")
        return None
    except Exception as e:
        logger.warning(f"⚠️ Scheduler init skipped: {e}")
        return None


async def initialize_realtime_services(
    config: "ServerConfig",
    db: Optional["MarketDB"],
    strategy_loader: Optional["StrategyLoader"],
) -> RealtimeServicesResult:
    """
    모든 실시간 서비스 초기화 통합 함수

    📌 수행 작업:
        1. IgnitionMonitor 초기화
        2. Daily Data Sync
        3. IBKR 연결 (auto_connect시)
        4. Scheduler 초기화
        5. Massive WebSocket 초기화
        6. IgnitionMonitor 자동 시작
        7. RealtimeScanner 초기화

    Args:
        config: ServerConfig 인스턴스
        db: MarketDB 인스턴스
        strategy_loader: StrategyLoader 인스턴스

    Returns:
        RealtimeServicesResult: 초기화된 모든 서비스
    """
    result = RealtimeServicesResult()

    # 1. IgnitionMonitor 초기화
    result.ignition_monitor = await initialize_ignition_monitor(db)

    # 2. Daily Data Sync
    from backend.startup.database import sync_daily_data

    await sync_daily_data(config, db)

    # 3. IBKR 연결 (auto_connect가 true일 때만)
    if config.ibkr.auto_connect:
        logger.info("📡 IBKR connection will be attempted in background...")
        # NOTE: IBKR 연결은 Step 4.1.3에서 API로 제어

    # 4. Scheduler 초기화
    result.scheduler = initialize_scheduler(config, db)

    # 5. Massive WebSocket 초기화
    ws_result = await initialize_massive_websocket(strategy_loader, result.ibkr, db)
    result.massive_ws = ws_result.massive_ws
    result.tick_broadcaster = ws_result.tick_broadcaster
    result.tick_dispatcher = ws_result.tick_dispatcher
    result.sub_manager = ws_result.sub_manager
    result.trailing_stop = ws_result.trailing_stop

    # 서버 시작 완료 메시지
    logger.info("=" * 50)
    logger.info(
        f"🎯 Server running at http://{config.server.host}:{config.server.port}"
    )
    logger.info("=" * 50)

    # 6. IgnitionMonitor 자동 시작
    await start_ignition_monitor(result.ignition_monitor, db)

    # 7. RealtimeScanner 초기화
    result.realtime_scanner = await initialize_realtime_scanner(
        db, result.ignition_monitor
    )

    return result
