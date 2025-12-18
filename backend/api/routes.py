"""
Sigma9 REST API Routes
=======================
백엔드 제어 및 조회 API 엔드포인트.

📌 엔드포인트 목록:
    GET  /api/status          - 서버/엔진 상태 조회
    POST /api/control         - 엔진 제어 (start/stop/kill)
    GET  /api/watchlist       - Watchlist 조회
    GET  /api/positions       - 포지션 조회
    POST /api/kill-switch     - 긴급 정지
    GET  /api/strategies      - 전략 목록
    POST /api/strategies/{name}/reload - 전략 리로드
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from loguru import logger


# ═══════════════════════════════════════════════════════════════════════════
# Request/Response Models (요청/응답 모델)
# ═══════════════════════════════════════════════════════════════════════════

class EngineCommand(str, Enum):
    """엔진 제어 명령"""
    START = "start"
    STOP = "stop"
    KILL = "kill"


class ControlRequest(BaseModel):
    """엔진 제어 요청"""
    command: EngineCommand = Field(..., description="제어 명령 (start/stop/kill)")


class ControlResponse(BaseModel):
    """엔진 제어 응답"""
    status: str = Field(..., description="요청 처리 상태 (accepted/rejected)")
    command: str = Field(..., description="실행된 명령")
    message: str = Field(..., description="결과 메시지")
    timestamp: str = Field(..., description="처리 시각 (ISO8601)")


class ServerStatus(BaseModel):
    """서버 상태"""
    server: str = Field(default="running", description="서버 상태")
    engine: str = Field(default="stopped", description="엔진 상태 (stopped/running)")
    ibkr: str = Field(default="disconnected", description="IBKR 연결 상태")
    scheduler: str = Field(default="inactive", description="스케줄러 상태")
    uptime_seconds: float = Field(default=0, description="서버 가동 시간 (초)")
    active_positions: int = Field(default=0, description="활성 포지션 수")
    active_orders: int = Field(default=0, description="활성 주문 수")
    timestamp: str = Field(..., description="조회 시각 (ISO8601)")


class WatchlistItem(BaseModel):
    """Watchlist 항목"""
    ticker: str
    score: float
    stage: str
    last_close: float
    change_pct: float


class PositionItem(BaseModel):
    """포지션 항목"""
    ticker: str
    quantity: int
    avg_cost: float
    current_price: float
    unrealized_pnl: float
    pnl_pct: float


class StrategyInfo(BaseModel):
    """전략 정보"""
    name: str
    version: str
    description: str
    is_loaded: bool


class AnalysisRequest(BaseModel):
    """LLM 분석 요청"""
    ticker: str
    question: Optional[str] = None
    provider: Optional[str] = "openai"
    model: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════
# Router Instance
# ═══════════════════════════════════════════════════════════════════════════

router = APIRouter()

# 서버 시작 시각 (uptime 계산용)
_server_start_time: datetime = datetime.now(timezone.utc)

# 엔진 상태 (임시 - 실제로는 Engine 클래스에서 관리)
_engine_running: bool = False


def _get_timestamp() -> str:
    """현재 시각을 ISO8601 형식으로 반환"""
    return datetime.now(timezone.utc).isoformat()


def _get_uptime_seconds() -> float:
    """서버 가동 시간 (초) 반환"""
    return (datetime.now(timezone.utc) - _server_start_time).total_seconds()


# ═══════════════════════════════════════════════════════════════════════════
# Status Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/status", response_model=ServerStatus, summary="서버 상태 조회")
async def get_status():
    """
    서버, 엔진, IBKR, 스케줄러 상태를 조회합니다.
    
    📌 상태값:
        - server: running/stopped
        - engine: running/stopped
        - ibkr: connected/disconnected
        - scheduler: active/inactive
    """
    from backend.server import app_state
    
    # IBKR 상태 확인
    ibkr_status = "disconnected"
    if app_state.ibkr:
        try:
            ibkr_status = "connected" if app_state.ibkr.is_connected() else "disconnected"
        except:
            ibkr_status = "error"
    
    # 스케줄러 상태 확인
    scheduler_status = "inactive"
    if app_state.scheduler:
        try:
            scheduler_status = "active" if app_state.scheduler.running else "inactive"
        except:
            scheduler_status = "error"
    
    # 엔진 상태 확인
    engine_status = "stopped"
    active_positions = 0
    active_orders = 0
    if app_state.engine:
        try:
            engine_status = "running" if app_state.engine.is_running else "stopped"
            active_positions = app_state.engine.position_count
            active_orders = app_state.engine.order_count
        except:
            pass
    elif _engine_running:
        engine_status = "running"
    
    return ServerStatus(
        server="running",
        engine=engine_status,
        ibkr=ibkr_status,
        scheduler=scheduler_status,
        uptime_seconds=_get_uptime_seconds(),
        active_positions=active_positions,
        active_orders=active_orders,
        timestamp=_get_timestamp()
    )


# ═══════════════════════════════════════════════════════════════════════════
# Control Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/control", response_model=ControlResponse, summary="엔진 제어")
async def control_engine(request: ControlRequest):
    """
    트레이딩 엔진을 제어합니다.
    
    📌 명령:
        - start: 엔진 시작 (IBKR 연결, 전략 로드, 모니터링 시작)
        - stop: 엔진 정지 (신규 거래 차단, 기존 포지션 유지)
        - kill: 긴급 정지 (모든 주문 취소, 모든 포지션 청산)
    """
    global _engine_running
    from backend.server import app_state
    
    logger.info(f"🎮 Control command received: {request.command}")
    
    if request.command == EngineCommand.START:
        if _engine_running:
            return ControlResponse(
                status="rejected",
                command=request.command,
                message="Engine is already running",
                timestamp=_get_timestamp()
            )
        
        # TODO: 실제 엔진 시작 로직
        # app_state.engine.start()
        _engine_running = True
        logger.info("🚀 Trading Engine Started")
        
        return ControlResponse(
            status="accepted",
            command=request.command,
            message="Engine started successfully",
            timestamp=_get_timestamp()
        )
    
    elif request.command == EngineCommand.STOP:
        if not _engine_running:
            return ControlResponse(
                status="rejected",
                command=request.command,
                message="Engine is not running",
                timestamp=_get_timestamp()
            )
        
        # TODO: 실제 엔진 정지 로직
        # app_state.engine.stop()
        _engine_running = False
        logger.info("⏹ Trading Engine Stopped")
        
        return ControlResponse(
            status="accepted",
            command=request.command,
            message="Engine stopped successfully",
            timestamp=_get_timestamp()
        )
    
    elif request.command == EngineCommand.KILL:
        # Kill Switch는 항상 실행
        logger.warning("⚡ KILL SWITCH ACTIVATED!")
        
        # TODO: 실제 Kill Switch 로직
        # 1. 모든 미체결 주문 취소
        # 2. 모든 포지션 시장가 청산
        # 3. 엔진 정지
        _engine_running = False
        
        return ControlResponse(
            status="accepted",
            command=request.command,
            message="Kill switch executed - All orders cancelled, all positions closed",
            timestamp=_get_timestamp()
        )


@router.post("/kill-switch", response_model=ControlResponse, summary="긴급 정지")
async def kill_switch():
    """
    🔴 긴급 정지 버튼
    
    모든 미체결 주문을 취소하고 모든 포지션을 시장가로 청산합니다.
    확인 없이 즉시 실행됩니다.
    """
    return await control_engine(ControlRequest(command=EngineCommand.KILL))


# ═══════════════════════════════════════════════════════════════════════════
# Engine Control Endpoints (Alternative)
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/engine/start", response_model=ControlResponse, summary="엔진 시작")
async def start_engine():
    """트레이딩 엔진을 시작합니다."""
    return await control_engine(ControlRequest(command=EngineCommand.START))


@router.post("/engine/stop", response_model=ControlResponse, summary="엔진 정지")
async def stop_engine():
    """트레이딩 엔진을 정지합니다."""
    return await control_engine(ControlRequest(command=EngineCommand.STOP))


@router.get("/engine/status", summary="엔진 상태 조회")
async def get_engine_status():
    """엔진 상세 상태를 조회합니다."""
    return {
        "running": _engine_running,
        "strategy": "seismograph" if _engine_running else None,
        "watchlist_count": 0,  # TODO: 실제 값
        "timestamp": _get_timestamp()
    }


# ═══════════════════════════════════════════════════════════════════════════
# Watchlist Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/watchlist", response_model=List[WatchlistItem], summary="Watchlist 조회")
async def get_watchlist():
    """
    현재 Watchlist를 조회합니다.
    
    📌 반환값:
        - ticker: 종목 코드
        - score: 매집 점수 (0~100)
        - stage: 매집 단계 (Stage 1~4)
        - last_close: 최근 종가
        - change_pct: 변동률 (%)
    """
    # TODO: 실제 Watchlist 조회 로직
    # from backend.server import app_state
    # if app_state.engine:
    #     return app_state.engine.get_watchlist()
    
    # 임시 Mock 데이터
    return [
        WatchlistItem(ticker="AAPL", score=85.0, stage="Stage 4", last_close=175.50, change_pct=1.2),
        WatchlistItem(ticker="MSFT", score=72.0, stage="Stage 3", last_close=378.20, change_pct=-0.5),
        WatchlistItem(ticker="NVDA", score=68.0, stage="Stage 2", last_close=495.00, change_pct=2.1),
    ]


# ═══════════════════════════════════════════════════════════════════════════
# Position Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/positions", response_model=List[PositionItem], summary="포지션 조회")
async def get_positions():
    """
    현재 보유 포지션을 조회합니다.
    """
    # TODO: 실제 포지션 조회 로직
    # from backend.server import app_state
    # if app_state.ibkr:
    #     return app_state.ibkr.get_positions()
    
    # 임시 빈 리스트 반환
    return []


# ═══════════════════════════════════════════════════════════════════════════
# Strategy Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/strategies", response_model=List[StrategyInfo], summary="전략 목록 조회")
async def get_strategies():
    """
    사용 가능한 전략 목록을 조회합니다.
    """
    from backend.server import app_state
    
    if not app_state.strategy_loader:
        return []
    
    try:
        # 발견된 전략 목록
        discovered = app_state.strategy_loader.discover_strategies()
        loaded = app_state.strategy_loader.list_loaded()
        loaded_names = {s.get("name") for s in loaded}
        
        strategies = []
        for name in discovered:
            is_loaded = name in loaded_names
            
            # 로드된 전략이면 메타정보 가져오기
            if is_loaded:
                meta = next((s for s in loaded if s.get("name") == name), {})
                strategies.append(StrategyInfo(
                    name=name,
                    version=meta.get("version", "1.0.0"),
                    description=meta.get("description", ""),
                    is_loaded=True
                ))
            else:
                strategies.append(StrategyInfo(
                    name=name,
                    version="?",
                    description="Not loaded",
                    is_loaded=False
                ))
        
        return strategies
    
    except Exception as e:
        logger.error(f"Failed to get strategies: {e}")
        return []


@router.post("/strategies/{name}/load", summary="전략 로드")
async def load_strategy(name: str):
    """
    지정된 전략을 로드합니다.
    """
    from backend.server import app_state
    
    if not app_state.strategy_loader:
        raise HTTPException(status_code=500, detail="Strategy loader not initialized")
    
    try:
        strategy = app_state.strategy_loader.load_strategy(name)
        logger.info(f"✅ Strategy loaded: {name}")
        return {"status": "loaded", "name": name, "timestamp": _get_timestamp()}
    except Exception as e:
        logger.error(f"Failed to load strategy {name}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/strategies/{name}/reload", summary="전략 리로드")
async def reload_strategy(name: str):
    """
    지정된 전략을 핫 리로드합니다.
    """
    from backend.server import app_state
    
    if not app_state.strategy_loader:
        raise HTTPException(status_code=500, detail="Strategy loader not initialized")
    
    try:
        strategy = app_state.strategy_loader.reload_strategy(name)
        logger.info(f"🔄 Strategy reloaded: {name}")
        return {"status": "reloaded", "name": name, "timestamp": _get_timestamp()}
    except Exception as e:
        logger.error(f"Failed to reload strategy {name}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# Oracle (LLM) Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/oracle/models", summary="LLM 모델 목록")
async def get_oracle_models():
    """
    사용 가능한 LLM 모델 목록을 조회합니다.
    """
    try:
        from backend.llm.oracle import oracle_service
        return await oracle_service.get_available_models()
    except Exception as e:
        logger.error(f"Failed to get oracle models: {e}")
        return {"providers": [], "error": str(e)}


@router.post("/oracle/analyze", summary="종목 분석 요청")
async def analyze_ticker(request: AnalysisRequest):
    """
    종목에 대한 LLM 분석을 요청합니다.
    """
    try:
        from backend.llm.oracle import oracle_service
        
        prompt = f"Analyze ticker {request.ticker}."
        if request.question:
            prompt += f" Question: {request.question}"
        
        result = await oracle_service.analyze(prompt, request.provider, request.model)
        return {
            "ticker": request.ticker,
            "analysis": result,
            "timestamp": _get_timestamp()
        }
    except Exception as e:
        logger.error(f"Oracle analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
