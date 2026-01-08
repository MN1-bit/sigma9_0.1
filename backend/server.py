"""
Sigma9 Trading Engine Server
=============================
FastAPI 기반 백엔드 서버.

📌 실행 방법:
    python -m backend

📌 API 문서:
    http://localhost:8000/docs (Swagger UI)
    http://localhost:8000/redoc (ReDoc)

📌 [04-001] Refactored:
    lifespan 로직을 backend/startup/ 모듈로 분리.
    - config.py: Config + Logging 초기화
    - database.py: DB + StrategyLoader 초기화
    - realtime.py: Massive WS, Scanner, IgnitionMonitor
    - shutdown.py: 종료 로직
"""

from dotenv import load_dotenv

# .env 파일 로드 (최상위 레벨에서 실행)
load_dotenv()

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json  # [08-001] heartbeat JSON serialization
from loguru import logger

# [02-001] DI Container import
from backend.container import container, Container

# [04-001] Startup module imports
from backend.startup.config import initialize_config
from backend.startup.database import initialize_database, sync_daily_data
from backend.startup.realtime import initialize_realtime_services
from backend.startup.shutdown import shutdown_all


# ═══════════════════════════════════════════════════════════════════════════
# Application State (애플리케이션 상태)
# ═══════════════════════════════════════════════════════════════════════════


class AppState:
    """
    FastAPI app.state 대신 사용하는 명시적 상태 컨테이너

    📌 타입 힌팅과 IDE 지원을 위해 별도 클래스로 관리
    """

    def __init__(self):
        self.config = None  # ServerConfig
        self.ibkr = None  # IBKRConnector (Optional)
        self.engine = None  # TradingEngine (Optional)
        self.scheduler = None  # APScheduler (Optional)
        self.db = None  # Database connection
        self.strategy_loader = None  # StrategyLoader

        # Phase 4.A.0: Real-time Data Pipeline
        self.massive_ws = None  # MassiveWebSocketClient
        self.tick_broadcaster = None  # TickBroadcaster
        self.tick_dispatcher = None  # TickDispatcher (Step 4.A.0.b)
        self.sub_manager = None  # SubscriptionManager
        self.trailing_stop = None  # TrailingStopManager (Step 4.A.0.b)
        self.ignition_monitor = None  # IgnitionMonitor [Step 4.A.4]
        self.realtime_scanner = None  # RealtimeScanner [Step 4.A.5]


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

    📌 [04-001] Refactored from ~320 lines to ~50 lines
        로직을 backend/startup/ 모듈로 분리

    📌 Startup:
        1. Config 로드 (startup.config)
        2. Database 초기화 (startup.database)
        3. 실시간 서비스 초기화 (startup.realtime)

    📌 Shutdown:
        1. 모든 서비스 종료 (startup.shutdown)
    """
    global app_state

    # ─────────────────────────────────────────────────────────────
    # STARTUP
    # ─────────────────────────────────────────────────────────────
    logger.info("🚀 Sigma9 Trading Engine Server Starting...")

    # 1. Config 로드 + DI Container wiring
    app_state.config = initialize_config()

    # 2. Database + StrategyLoader 초기화
    app_state.db, app_state.strategy_loader = initialize_database(app_state.config)

    # 3. Daily Data Sync
    await sync_daily_data(app_state.config, app_state.db)

    # 4. 실시간 서비스 초기화 (IgnitionMonitor, Massive WS, Scanner, Scheduler)
    realtime_result = await initialize_realtime_services(
        config=app_state.config,
        db=app_state.db,
        strategy_loader=app_state.strategy_loader,
    )

    # 결과를 app_state에 할당
    app_state.ignition_monitor = realtime_result.ignition_monitor
    app_state.massive_ws = realtime_result.massive_ws
    app_state.tick_broadcaster = realtime_result.tick_broadcaster
    app_state.tick_dispatcher = realtime_result.tick_dispatcher
    app_state.sub_manager = realtime_result.sub_manager
    app_state.trailing_stop = realtime_result.trailing_stop
    app_state.realtime_scanner = realtime_result.realtime_scanner
    app_state.scheduler = realtime_result.scheduler
    app_state.ibkr = realtime_result.ibkr

    yield  # 서버 실행 중

    # ─────────────────────────────────────────────────────────────
    # SHUTDOWN
    # ─────────────────────────────────────────────────────────────
    await shutdown_all(
        realtime_scanner=app_state.realtime_scanner,
        ignition_monitor=app_state.ignition_monitor,
        scheduler=app_state.scheduler,
        ibkr=app_state.ibkr,
    )


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

            # PING/PONG 처리 [08-001: heartbeat에 시간 정보 추가]
            if data == "PING":
                import time
                from datetime import datetime, timezone

                heartbeat = {
                    "server_time_utc": datetime.now(timezone.utc).isoformat(),
                    "sent_at": int(time.time() * 1000),  # Unix ms
                }
                await websocket.send_text(f"PONG:{json.dumps(heartbeat)}")
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
    uvicorn.run("backend.server:app", host="0.0.0.0", port=8000, reload=True)
