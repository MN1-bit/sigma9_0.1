"""
Sigma9 Trading Engine Server
=============================
FastAPI 기반 백엔드 서버.

📌 실행 방법:
    python -m backend
    
📌 API 문서:
    http://localhost:8000/docs (Swagger UI)
    http://localhost:8000/redoc (ReDoc)
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv  # 환경변수 로드

# .env 파일 로드 (최상위 레벨에서 실행)
load_dotenv()

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from loguru import logger

# ═══════════════════════════════════════════════════════════════════════════
# Logging Setup (로깅 설정)
# ═══════════════════════════════════════════════════════════════════════════

def setup_logging(config):
    """
    Loguru 로깅 설정
    
    📌 설정 기반으로 콘솔/파일 로깅 구성
    """
    logger.remove()  # 기본 핸들러 제거
    
    # 콘솔 로깅
    if config.logging.console.enabled:
        logger.add(
            sys.stderr,
            level=config.logging.level,
            colorize=config.logging.console.colorize,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
        )
    
    # 파일 로깅
    if config.logging.file.enabled:
        # logs 디렉토리 생성
        log_path = Path(config.logging.file.path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            config.logging.file.path,
            level=config.logging.level,
            rotation=config.logging.file.rotation,
            retention=config.logging.file.retention,
            compression=config.logging.file.compression,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# Application State (애플리케이션 상태)
# ═══════════════════════════════════════════════════════════════════════════

class AppState:
    """
    FastAPI app.state 대신 사용하는 명시적 상태 컨테이너
    
    📌 타입 힌팅과 IDE 지원을 위해 별도 클래스로 관리
    """
    def __init__(self):
        self.config = None           # ServerConfig
        self.ibkr = None             # IBKRConnector (Optional)
        self.engine = None           # TradingEngine (Optional)
        self.scheduler = None        # APScheduler (Optional)
        self.db = None               # Database connection
        self.strategy_loader = None  # StrategyLoader
        
        # Phase 4.A.0: Real-time Data Pipeline
        self.massive_ws = None       # MassiveWebSocketClient
        self.tick_broadcaster = None # TickBroadcaster
        self.tick_dispatcher = None  # TickDispatcher (Step 4.A.0.b)
        self.sub_manager = None      # SubscriptionManager
        self.trailing_stop = None    # TrailingStopManager (Step 4.A.0.b)
        
# 전역 상태 (의존성 주입용)
app_state = AppState()


def get_app_state() -> AppState:
    """FastAPI 의존성 주입용"""
    return app_state


# ═══════════════════════════════════════════════════════════════════════════
# Lifespan (서버 라이프사이클)
# ═══════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    서버 시작/종료 시 리소스 관리
    
    📌 Startup:
        1. Config 로드
        2. Database 초기화
        3. IBKR 연결 (Optional)
        4. Scheduler 시작 (Optional)
    
    📌 Shutdown:
        1. Scheduler 종료
        2. IBKR 연결 해제
        3. Database 연결 종료
    """
    global app_state
    
    # ─────────────────────────────────────────────────────────────
    # STARTUP
    # ─────────────────────────────────────────────────────────────
    logger.info("🚀 Sigma9 Trading Engine Server Starting...")
    
    # 1. Config 로드
    from backend.core.config_loader import load_server_config
    app_state.config = load_server_config()
    setup_logging(app_state.config)
    logger.info(f"✅ Config loaded (debug={app_state.config.server.debug})")
    
    # 2. Database 초기화 (경량 - 에러 무시)
    try:
        from backend.data.database import MarketDB
        app_state.db = MarketDB(app_state.config.market_data.db_path)
        logger.info(f"✅ Database connected: {app_state.config.market_data.db_path}")
    except Exception as e:
        logger.warning(f"⚠️ Database init skipped: {e}")
    
    # 3. Strategy Loader 초기화
    try:
        from backend.core.strategy_loader import StrategyLoader
        app_state.strategy_loader = StrategyLoader()
        strategies = app_state.strategy_loader.discover_strategies()
        logger.info(f"✅ Strategy Loader initialized. Found {len(strategies)} strategies")
    except Exception as e:
        logger.warning(f"⚠️ Strategy Loader init skipped: {e}")
    
    # 4. IBKR 연결 (auto_connect가 true일 때만)
    if app_state.config.ibkr.auto_connect:
        try:
            # IBKR 연결은 비동기로 시작만 하고 넘어감
            # 실제 연결은 백그라운드에서 시도
            logger.info("📡 IBKR connection will be attempted in background...")
            # from backend.broker.ibkr_connector import IBKRConnector
            # app_state.ibkr = IBKRConnector()
            # NOTE: IBKR 연결은 Step 4.1.3에서 API로 제어
        except Exception as e:
            logger.warning(f"⚠️ IBKR init skipped: {e}")
    
    # 5. Scheduler 초기화 (enabled일 때만)
    if app_state.config.scheduler.enabled:
        try:
            from backend.core.scheduler import TradingScheduler
            app_state.scheduler = TradingScheduler(app_state.config.scheduler, app_state.db)
            app_state.scheduler.start()
            logger.info("✅ Scheduler started")
        except ImportError:
            logger.info("ℹ️ Scheduler module not found - will be created in Step 4.1.4")
        except Exception as e:
            logger.warning(f"⚠️ Scheduler init skipped: {e}")
    
    # 6. Massive WebSocket 초기화 (Phase 4.A.0)
    import os
    if os.getenv("MASSIVE_WS_ENABLED", "false").lower() == "true":
        try:
            from backend.data.massive_ws_client import MassiveWebSocketClient
            from backend.core.tick_broadcaster import TickBroadcaster
            from backend.core.tick_dispatcher import TickDispatcher
            from backend.core.subscription_manager import SubscriptionManager
            from backend.api.websocket import manager as ws_manager
            
            # TickDispatcher 생성 (중앙 틱 배포자)
            app_state.tick_dispatcher = TickDispatcher()
            
            # 활성 전략이 있으면 TickDispatcher에 등록
            if app_state.strategy_loader:
                active_strategy = app_state.strategy_loader.get_active_strategy()
                if active_strategy and hasattr(active_strategy, 'on_tick'):
                    def strategy_tick_handler(tick: dict):
                        active_strategy.on_tick(
                            ticker=tick.get("ticker", ""),
                            price=tick.get("price", 0),
                            volume=tick.get("size", 0),
                            timestamp=tick.get("time", 0)
                        )
                    app_state.tick_dispatcher.register("strategy", strategy_tick_handler)
                    logger.info("✅ Strategy connected to TickDispatcher")
            
            # [Step 4.A.0.b.4] TrailingStopManager 연결
            try:
                from backend.core.trailing_stop import TrailingStopManager
                app_state.trailing_stop = TrailingStopManager(connector=app_state.ibkr)
                
                def trailing_tick_handler(tick: dict):
                    result = app_state.trailing_stop.on_price_update(
                        symbol=tick.get("ticker", ""),
                        current_price=tick.get("price", 0)
                    )
                    if result == "TRIGGERED":
                        logger.info(f"🛑 Trailing Stop TRIGGERED: {tick.get('ticker')}")
                
                app_state.tick_dispatcher.register("trailing_stop", trailing_tick_handler)
                logger.info("✅ TrailingStop connected to TickDispatcher")
            except Exception as e:
                logger.warning(f"⚠️ TrailingStop init skipped: {e}")
            
            app_state.massive_ws = MassiveWebSocketClient()
            app_state.tick_broadcaster = TickBroadcaster(
                app_state.massive_ws, 
                ws_manager,
                asyncio.get_event_loop(),
                tick_dispatcher=app_state.tick_dispatcher
            )
            app_state.sub_manager = SubscriptionManager(app_state.massive_ws)
            
            # 백그라운드에서 Massive 연결 시작
            async def start_massive_streaming():
                if await app_state.massive_ws.connect():
                    logger.info("✅ Massive WebSocket connected")
                    
                    # [Step 4.A.0.c P1] 초기 구독 트리거
                    # Watchlist 티커 로드 후 AM/T 채널 자동 구독
                    try:
                        if app_state.db:
                            # DB에서 현재 Watchlist 로드
                            from backend.data.database import MarketDB
                            watchlist = app_state.db.get_watchlist_tickers() if hasattr(app_state.db, 'get_watchlist_tickers') else []
                            if watchlist and app_state.sub_manager:
                                app_state.sub_manager.sync_watchlist(watchlist)
                                logger.info(f"✅ Auto-subscribed to {len(watchlist)} tickers")
                    except Exception as e:
                        logger.warning(f"⚠️ Auto-subscribe skipped: {e}")
                    
                    # [Step 4.A.0.c P0] listen() 루프 시작 (콜백이 데이터 처리)
                    async for _ in app_state.massive_ws.listen():
                        pass
                else:
                    logger.warning("⚠️ Massive WebSocket connection failed")
            
            asyncio.create_task(start_massive_streaming())
            logger.info("📡 Massive WebSocket initializing...")
            
        except Exception as e:
            logger.warning(f"⚠️ Massive WebSocket init skipped: {e}")
    
    logger.info("=" * 50)
    logger.info(f"🎯 Server running at http://{app_state.config.server.host}:{app_state.config.server.port}")
    logger.info("=" * 50)
    
    yield  # 서버 실행 중
    
    # ─────────────────────────────────────────────────────────────
    # SHUTDOWN
    # ─────────────────────────────────────────────────────────────
    logger.info("🛑 Server Shutting Down...")
    
    # Scheduler 종료
    if app_state.scheduler:
        try:
            app_state.scheduler.shutdown()
            logger.info("✅ Scheduler stopped")
        except Exception as e:
            logger.error(f"❌ Scheduler shutdown error: {e}")
    
    # IBKR 연결 해제
    if app_state.ibkr:
        try:
            app_state.ibkr.disconnect()
            logger.info("✅ IBKR disconnected")
        except Exception as e:
            logger.error(f"❌ IBKR disconnect error: {e}")
    
    logger.info("👋 Goodbye!")


# ═══════════════════════════════════════════════════════════════════════════
# FastAPI Application (애플리케이션 인스턴스)
# ═══════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="Sigma9 Trading Engine",
    version="2.0.0",
    description="Backend Server for Sigma9 Algorithmic Trading System",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware (개발용 - 프로덕션에서는 origin 제한 필요)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션: 특정 origin만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════════════
# Routers (라우터 등록)
# ═══════════════════════════════════════════════════════════════════════════

from backend.api.routes import router as api_router
from backend.api.websocket import manager as ws_manager

app.include_router(api_router, prefix="/api", tags=["API"])


# ═══════════════════════════════════════════════════════════════════════════
# WebSocket Endpoint
# ═══════════════════════════════════════════════════════════════════════════

@app.websocket("/ws/feed")
async def websocket_endpoint(websocket: WebSocket):
    """
    실시간 데이터 피드 WebSocket
    
    📌 메시지 타입:
        - LOG:xxx - 서버 로그
        - TICK:xxx - 틱 데이터
        - TRADE:xxx - 거래 이벤트
        - STATUS:xxx - 상태 변경
    """
    await ws_manager.connect(websocket)
    try:
        while True:
            # 클라이언트 메시지 수신 (하트비트 등)
            data = await websocket.receive_text()
            
            # PING/PONG 처리
            if data == "PING":
                await websocket.send_text("PONG")
            else:
                # 다른 메시지는 현재 무시
                pass
                
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket)


# ═══════════════════════════════════════════════════════════════════════════
# Health Check Endpoint
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/health", tags=["Health"])
async def health_check():
    """서버 헬스체크"""
    return {"status": "healthy", "version": "2.0.0"}


# ═══════════════════════════════════════════════════════════════════════════
# Entry Point (직접 실행 시)
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 직접 실행 시 기본 설정으로 시작
    uvicorn.run(
        "backend.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
