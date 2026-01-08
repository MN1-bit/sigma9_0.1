# ═══════════════════════════════════════════════════════════════════════════
# Strategy Endpoints
# ═══════════════════════════════════════════════════════════════════════════
#
# 📌 역할:
#     전략 목록 조회, 로드, 리로드 API
#
# 📌 엔드포인트:
#     GET  /strategies              - 전략 목록 조회
#     POST /strategies/{name}/load   - 전략 로드
#     POST /strategies/{name}/reload - 전략 리로드
#
# ═══════════════════════════════════════════════════════════════════════════

from typing import List

from fastapi import APIRouter, HTTPException
from loguru import logger

from .models import StrategyInfo
from .common import get_timestamp


router = APIRouter()


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
        app_state.strategy_loader.load_strategy(name)
        logger.info(f"✅ Strategy loaded: {name}")
        return {"status": "loaded", "name": name, "timestamp": get_timestamp()}
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
        app_state.strategy_loader.reload_strategy(name)
        logger.info(f"🔄 Strategy reloaded: {name}")
        return {"status": "reloaded", "name": name, "timestamp": get_timestamp()}
    except Exception as e:
        logger.error(f"Failed to reload strategy {name}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
