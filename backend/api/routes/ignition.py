# ═══════════════════════════════════════════════════════════════════════════
# Ignition Endpoints
# ═══════════════════════════════════════════════════════════════════════════
#
# 📌 역할:
#     Ignition Score 모니터링 시작/중지/조회 API (Phase 2 실시간)
#
# 📌 엔드포인트:
#     POST /ignition/start   - 모니터링 시작
#     POST /ignition/stop    - 모니터링 중지
#     GET  /ignition/scores  - 현재 Ignition Score 조회
#
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, HTTPException

from .common import get_timestamp


router = APIRouter()


@router.post("/ignition/start", summary="Ignition 모니터링 시작")
async def start_ignition_monitor():
    """
    Ignition Score 모니터링을 시작합니다.

    📌 동작:
        1. 현재 Watchlist 로드
        2. IgnitionMonitor 시작
        3. 실시간 틱 수신 → Ignition Score 계산 → WebSocket 브로드캐스트
    """
    # ═══════════════════════════════════════════════════════════════════════
    # [02-003] Container 방식으로 마이그레이션
    # ═══════════════════════════════════════════════════════════════════════
    from backend.container import container
    from backend.data.watchlist_store import load_watchlist

    monitor = container.ignition_monitor()

    if not monitor:
        raise HTTPException(status_code=500, detail="IgnitionMonitor not initialized")

    if monitor.is_running:
        return {
            "status": "already_running",
            "ticker_count": monitor.ticker_count,
            "timestamp": get_timestamp(),
        }

    # Watchlist 로드
    watchlist = load_watchlist()

    if not watchlist:
        raise HTTPException(
            status_code=400, detail="Watchlist is empty. Run scanner first."
        )

    # 모니터링 시작
    success = await monitor.start(watchlist)

    return {
        "status": "started" if success else "failed",
        "ticker_count": monitor.ticker_count,
        "timestamp": get_timestamp(),
    }


@router.post("/ignition/stop", summary="Ignition 모니터링 중지")
async def stop_ignition_monitor():
    """
    Ignition Score 모니터링을 중지합니다.
    """
    # [02-003] Container 방식으로 마이그레이션
    from backend.container import container

    monitor = container.ignition_monitor()

    if not monitor:
        raise HTTPException(status_code=500, detail="IgnitionMonitor not initialized")

    await monitor.stop()

    return {"status": "stopped", "timestamp": get_timestamp()}


@router.get("/ignition/scores", summary="현재 Ignition Score 조회")
async def get_ignition_scores():
    """
    모든 Watchlist 종목의 현재 Ignition Score를 조회합니다.

    📌 반환값:
        - running: 모니터링 실행 중 여부
        - ticker_count: 모니터링 종목 수
        - scores: 종목별 Ignition Score (ticker -> score)
    """
    # [02-003] Container 방식으로 마이그레이션
    from backend.container import container

    monitor = container.ignition_monitor()

    if not monitor:
        return {
            "running": False,
            "ticker_count": 0,
            "scores": {},
            "timestamp": get_timestamp(),
        }

    return {
        "running": monitor.is_running,
        "ticker_count": monitor.ticker_count,
        "scores": monitor.get_all_scores(),
        "timestamp": get_timestamp(),
    }
