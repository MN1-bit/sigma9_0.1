# ═══════════════════════════════════════════════════════════════════════════
# Z-Score Endpoints (Step 4.A.3)
# ═══════════════════════════════════════════════════════════════════════════
#
# 📌 역할:
#     종목 Z-Score (zenV, zenP) 계산 API
#
# 📌 엔드포인트:
#     GET /zscore/{ticker} - 종목 Z-Score 조회
#
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, HTTPException
from loguru import logger

from .common import get_timestamp


router = APIRouter()


@router.get("/zscore/{ticker}", summary="종목 Z-Score 조회")
async def get_zscore(ticker: str):
    """
    특정 종목의 Z-Score (zenV, zenP)를 계산합니다.
    
    📌 Z-Score:
        - zenV: Volume Z-Score (거래량이 평균 대비 몇 표준편차인지)
        - zenP: Price Z-Score (가격 변동이 평균 대비 몇 표준편차인지)
    
    📌 매집 신호:
        - zenV > 2.0 AND zenP < 1.0: 높은 거래량, 낮은 가격 변동 = 매집 가능성 🔥
    
    Args:
        ticker: 종목 심볼 (예: "AAPL")
    
    Returns:
        dict: {ticker, zenV, zenP, timestamp}
    
    Example:
        GET /api/zscore/AAPL
        → {"ticker": "AAPL", "zenV": 2.35, "zenP": 0.45, "timestamp": "..."}
    """
    from backend.data.database import MarketDB
    from backend.core.zscore_calculator import ZScoreCalculator
    
    logger.info(f"📊 Z-Score 조회 요청: {ticker}")
    
    try:
        # MarketDB에서 20일 일봉 데이터 조회
        db = MarketDB("data/market_data.db")
        await db.initialize()
        
        # get_daily_bars returns most recent first (DESC), we need oldest first
        daily_bars = await db.get_daily_bars(ticker.upper(), days=25)  # 여유분 포함
        
        if not daily_bars:
            logger.warning(f"⚠️ {ticker}: 일봉 데이터 없음")
            return {
                "ticker": ticker.upper(),
                "zenV": 0.0,
                "zenP": 0.0,
                "data_available": False,
                "message": "No daily bar data available",
                "timestamp": get_timestamp()
            }
        
        # DailyBar 객체를 딕셔너리로 변환하고 시간순 정렬 (오래된 → 최신)
        bars_dict = [bar.to_dict() for bar in reversed(daily_bars)]
        
        # Z-Score 계산
        calculator = ZScoreCalculator(lookback=20)
        result = calculator.calculate(ticker.upper(), bars_dict)
        
        return {
            "ticker": ticker.upper(),
            "zenV": result.zenV,
            "zenP": result.zenP,
            "data_available": True,
            "bars_used": len(bars_dict),
            "timestamp": get_timestamp()
        }
        
    except Exception as e:
        logger.error(f"Z-Score 계산 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
