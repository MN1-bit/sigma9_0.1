# ═══════════════════════════════════════════════════════════════════════════
# Status Endpoints
# ═══════════════════════════════════════════════════════════════════════════
#
# 📌 역할:
#     서버, 엔진, IBKR, 스케줄러 상태 조회 API
#
# 📌 엔드포인트:
#     GET  /status           - 서버 전체 상태 조회
#     GET  /engine/status    - 엔진 상세 상태 조회
#
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter

from .models import ServerStatus
from .common import get_timestamp, get_uptime_seconds, is_engine_running


router = APIRouter()


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
        except Exception:
            ibkr_status = "error"
    
    # 스케줄러 상태 확인
    scheduler_status = "inactive"
    if app_state.scheduler:
        try:
            scheduler_status = "active" if app_state.scheduler.running else "inactive"
        except Exception:
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
        except Exception:
            pass
    elif is_engine_running():
        engine_status = "running"
    
    return ServerStatus(
        server="running",
        engine=engine_status,
        ibkr=ibkr_status,
        scheduler=scheduler_status,
        uptime_seconds=get_uptime_seconds(),
        active_positions=active_positions,
        active_orders=active_orders,
        timestamp=get_timestamp()
    )


@router.get("/engine/status", summary="엔진 상태 조회")
async def get_engine_status():
    """엔진 상세 상태를 조회합니다."""
    return {
        "running": is_engine_running(),
        "strategy": "seismograph" if is_engine_running() else None,
        "watchlist_count": 0,  # TODO: 실제 값
        "timestamp": get_timestamp()
    }
