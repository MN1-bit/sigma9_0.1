# ═══════════════════════════════════════════════════════════════════════════
# Position Endpoints
# ═══════════════════════════════════════════════════════════════════════════
#
# 📌 역할:
#     현재 보유 포지션 조회 API
#
# 📌 엔드포인트:
#     GET /positions - 포지션 조회
#
# ═══════════════════════════════════════════════════════════════════════════

from typing import List

from fastapi import APIRouter

from .models import PositionItem


router = APIRouter()


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
