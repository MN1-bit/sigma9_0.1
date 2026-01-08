# ═══════════════════════════════════════════════════════════════════════════
# Tier 2 (Hot Zone) Endpoints - Step 4.A.0.d
# ═══════════════════════════════════════════════════════════════════════════
#
# 📌 역할:
#     Tier 2 (Hot Zone) 종목 승격/해제/상태 조회 API
#
# 📌 엔드포인트:
#     POST /tier2/promote - Tier 2 승격
#     POST /tier2/demote  - Tier 2 해제
#     GET  /tier2/status  - Tier 2 상태 조회
#
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, HTTPException
from loguru import logger

from .models import Tier2PromoteRequest
from .common import get_timestamp


router = APIRouter()


@router.post("/tier2/promote", summary="Tier 2 (Hot Zone) 승격")
async def promote_to_tier2(request: Tier2PromoteRequest):
    """
    종목을 Tier 2 (Hot Zone)로 승격합니다.
    
    📌 동작:
        1. SubscriptionManager에 Tier 2 종목 설정
        2. T채널 (틱) 자동 구독
        3. TickDispatcher 필터 업데이트 (전략에 Tier 2만 전달)
    
    Args:
        tickers: Tier 2로 승격할 종목 목록
    
    Returns:
        dict: {status, promoted_count, tick_subscribed}
    """
    from backend.server import app_state
    
    tickers = request.tickers
    
    if not tickers:
        return {
            "status": "no_tickers",
            "promoted_count": 0,
            "timestamp": get_timestamp()
        }
    
    logger.info(f"🔥 Tier 2 승격 요청: {tickers}")
    
    promoted_count = 0
    tick_subscribed = []
    
    try:
        # 1. SubscriptionManager 업데이트
        if app_state.sub_manager:
            app_state.sub_manager.set_tier2_tickers(tickers)
            
            # 2. T채널 구독 동기화
            await app_state.sub_manager.sync_tick_subscriptions()
            tick_subscribed = app_state.sub_manager.tick_subscribed_tickers
            promoted_count = len(tickers)
            
            logger.info(f"✅ Tier 2 설정 완료: {len(tickers)}개, T채널: {len(tick_subscribed)}개")
        
        # 3. TickDispatcher 필터 업데이트 (전략에 Tier 2만 전달)
        if app_state.tick_dispatcher:
            app_state.tick_dispatcher.update_filter("strategy", tickers)
            logger.info(f"✅ TickDispatcher 필터 업데이트: {tickers}")
        
        return {
            "status": "success",
            "promoted_count": promoted_count,
            "tick_subscribed": tick_subscribed,
            "timestamp": get_timestamp()
        }
        
    except Exception as e:
        logger.error(f"Tier 2 승격 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tier2/demote", summary="Tier 2 해제")
async def demote_from_tier2(request: Tier2PromoteRequest):
    """
    종목을 Tier 2에서 해제합니다.
    
    📌 동작:
        1. SubscriptionManager에서 Tier 2 제거
        2. T채널 구독 해제
        3. TickDispatcher 필터 업데이트
    """
    from backend.server import app_state
    
    tickers = request.tickers
    
    if not tickers:
        return {"status": "no_tickers", "timestamp": get_timestamp()}
    
    logger.info(f"⬇️ Tier 2 해제 요청: {tickers}")
    
    try:
        if app_state.sub_manager:
            # 현재 Tier 2에서 제거
            current_tier2 = set(app_state.sub_manager._tier2_tickers)
            new_tier2 = current_tier2 - set(tickers)
            app_state.sub_manager.set_tier2_tickers(list(new_tier2))
            
            # T채널 동기화
            await app_state.sub_manager.sync_tick_subscriptions()
        
        # TickDispatcher 필터 업데이트
        if app_state.tick_dispatcher and app_state.sub_manager:
            app_state.tick_dispatcher.update_filter(
                "strategy", 
                list(app_state.sub_manager._tier2_tickers)
            )
        
        return {
            "status": "success",
            "remaining_tier2": list(app_state.sub_manager._tier2_tickers) if app_state.sub_manager else [],
            "timestamp": get_timestamp()
        }
        
    except Exception as e:
        logger.error(f"Tier 2 해제 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tier2/status", summary="Tier 2 상태 조회")
async def get_tier2_status():
    """
    현재 Tier 2 (Hot Zone) 상태를 조회합니다.
    
    Returns:
        dict: {tier2_tickers, tick_subscribed, dispatcher_filter}
    """
    from backend.server import app_state
    
    tier2_tickers = []
    tick_subscribed = []
    dispatcher_stats = {}
    
    if app_state.sub_manager:
        tier2_tickers = list(app_state.sub_manager._tier2_tickers)
        tick_subscribed = app_state.sub_manager.tick_subscribed_tickers
    
    if app_state.tick_dispatcher:
        dispatcher_stats = app_state.tick_dispatcher.stats
    
    return {
        "tier2_tickers": tier2_tickers,
        "tick_subscribed": tick_subscribed,
        "dispatcher_stats": dispatcher_stats,
        "timestamp": get_timestamp()
    }
