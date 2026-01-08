# ═══════════════════════════════════════════════════════════════════════════
# Control Endpoints
# ═══════════════════════════════════════════════════════════════════════════
#
# 📌 역할:
#     트레이딩 엔진 제어 API (시작, 정지, 긴급 정지)
#
# 📌 엔드포인트:
#     POST /control         - 엔진 제어 (start/stop/kill)
#     POST /kill-switch     - 긴급 정지
#     POST /engine/start    - 엔진 시작
#     POST /engine/stop     - 엔진 정지
#
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter
from loguru import logger

from .models import EngineCommand, ControlRequest, ControlResponse
from .common import get_timestamp, is_engine_running, set_engine_running


router = APIRouter()


@router.post("/control", response_model=ControlResponse, summary="엔진 제어")
async def control_engine(request: ControlRequest):
    """
    트레이딩 엔진을 제어합니다.
    
    📌 명령:
        - start: 엔진 시작 (IBKR 연결, 전략 로드, 모니터링 시작)
        - stop: 엔진 정지 (신규 거래 차단, 기존 포지션 유지)
        - kill: 긴급 정지 (모든 주문 취소, 모든 포지션 청산)
    """
    
    logger.info(f"🎮 Control command received: {request.command}")
    
    if request.command == EngineCommand.START:
        if is_engine_running():
            return ControlResponse(
                status="rejected",
                command=request.command,
                message="Engine is already running",
                timestamp=get_timestamp()
            )
        
        # TODO: 실제 엔진 시작 로직
        # app_state.engine.start()
        set_engine_running(True)
        logger.info("🚀 Trading Engine Started")
        
        return ControlResponse(
            status="accepted",
            command=request.command,
            message="Engine started successfully",
            timestamp=get_timestamp()
        )
    
    elif request.command == EngineCommand.STOP:
        if not is_engine_running():
            return ControlResponse(
                status="rejected",
                command=request.command,
                message="Engine is not running",
                timestamp=get_timestamp()
            )
        
        # TODO: 실제 엔진 정지 로직
        # app_state.engine.stop()
        set_engine_running(False)
        logger.info("⏹ Trading Engine Stopped")
        
        return ControlResponse(
            status="accepted",
            command=request.command,
            message="Engine stopped successfully",
            timestamp=get_timestamp()
        )
    
    elif request.command == EngineCommand.KILL:
        # Kill Switch는 항상 실행
        logger.warning("⚡ KILL SWITCH ACTIVATED!")
        
        # TODO: 실제 Kill Switch 로직
        # 1. 모든 미체결 주문 취소
        # 2. 모든 포지션 시장가 청산
        # 3. 엔진 정지
        set_engine_running(False)
        
        return ControlResponse(
            status="accepted",
            command=request.command,
            message="Kill switch executed - All orders cancelled, all positions closed",
            timestamp=get_timestamp()
        )


@router.post("/kill-switch", response_model=ControlResponse, summary="긴급 정지")
async def kill_switch():
    """
    🔴 긴급 정지 버튼
    
    모든 미체결 주문을 취소하고 모든 포지션을 시장가로 청산합니다.
    확인 없이 즉시 실행됩니다.
    """
    return await control_engine(ControlRequest(command=EngineCommand.KILL))


@router.post("/engine/start", response_model=ControlResponse, summary="엔진 시작")
async def start_engine():
    """트레이딩 엔진을 시작합니다."""
    return await control_engine(ControlRequest(command=EngineCommand.START))


@router.post("/engine/stop", response_model=ControlResponse, summary="엔진 정지")
async def stop_engine():
    """트레이딩 엔진을 정지합니다."""
    return await control_engine(ControlRequest(command=EngineCommand.STOP))
