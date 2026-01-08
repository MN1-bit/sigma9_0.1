# ═══════════════════════════════════════════════════════════════════════════
# Watchlist Endpoints
# ═══════════════════════════════════════════════════════════════════════════
#
# 📌 역할:
#     Watchlist 조회 및 재계산 API
#
# 📌 엔드포인트:
#     GET  /watchlist              - 현재 Watchlist 조회
#     POST /watchlist/recalculate  - Score V3 재계산
#
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, HTTPException
from loguru import logger



router = APIRouter()


@router.get("/watchlist", summary="Watchlist 조회")
async def get_watchlist():
    """
    현재 Watchlist를 조회합니다.
    
    📌 반환값:
        - ticker: 종목 코드
        - score: 매집 점수 (0~100)
        - stage: 매집 단계 (Stage 1~4)
        - last_close: 최근 종가
        - change_pct: 변동률 (%)
        - intensities: 신호 강도 dict
    """
    from backend.data.watchlist_store import load_watchlist
    
    # [02-001c FIX] 원시 dict를 그대로 반환 (Pydantic 변환 시 필드 손실 방지)
    raw_watchlist = load_watchlist()
    
    if raw_watchlist:
        logger.info(f"📋 Watchlist 반환: {len(raw_watchlist)}개 항목")
        return raw_watchlist
    
    # 데이터가 없으면 빈 리스트 반환
    logger.warning("⚠️ Watchlist 비어 있음")
    return []


@router.post("/watchlist/recalculate", summary="Score V2 재계산")
async def recalculate_watchlist_scores():
    """
    [Phase 9] 전체 Watchlist의 score_v3를 재계산합니다.
    
    📌 동작:
        1. 순차 재계산 (종목당 100ms 딜레이)
        2. DB에서 일봉 조회 → score_v3 계산
        3. Watchlist 저장 및 브로드캐스트
    
    Returns:
        success: 성공 종목 수
        failed: 실패 종목 수
        skipped: 스킵 종목 수 (데이터 부족)
        timestamp: 완료 시각
    """
    from backend.core.realtime_scanner import get_scanner_instance
    
    scanner = get_scanner_instance()
    
    if not scanner:
        raise HTTPException(status_code=500, detail="RealtimeScanner not initialized")
    
    try:
        result = await scanner.recalculate_all_scores()
        return {
            "status": "success",
            **result
        }
    except Exception as e:
        logger.error(f"Score V3 재계산 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
