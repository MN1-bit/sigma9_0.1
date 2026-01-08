# ═══════════════════════════════════════════════════════════════════════════
# Chart Data Endpoints (Multi-Timeframe Support)
# ═══════════════════════════════════════════════════════════════════════════
#
# 📌 역할:
#     Intraday 차트 데이터 조회 API
#
# 📌 엔드포인트:
#     GET /chart/intraday/{ticker} - Intraday 차트 데이터 조회
#
# ═══════════════════════════════════════════════════════════════════════════

import os
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from loguru import logger

from .common import get_timestamp


router = APIRouter()


@router.get("/chart/intraday/{ticker}", summary="Intraday 차트 데이터 조회")
async def get_intraday_chart(
    ticker: str,
    timeframe: int = 5,  # 1, 5, 15, 60 (분 단위)
    days: int = 2,  # 조회 일수 (1-10)
):
    """
    특정 종목의 Intraday 차트 데이터를 조회합니다.
    
    📌 타임프레임:
        - 1: 1분봉
        - 5: 5분봉
        - 15: 15분봉
        - 60: 1시간봉
    
    📌 반환값:
        - candles: OHLCV 데이터 리스트
        - ticker: 종목 심볼
        - timeframe: 타임프레임 (분)
        - count: 데이터 개수
    
    Example:
        GET /api/chart/intraday/AAPL?timeframe=5&days=2
    """
    from backend.data.massive_client import MassiveClient
    
    # API Key 확인
    api_key = os.getenv("MASSIVE_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="MASSIVE_API_KEY not configured")
    
    # 파라미터 검증
    if timeframe not in [1, 5, 15, 60]:
        raise HTTPException(status_code=400, detail="Invalid timeframe. Use 1, 5, 15, or 60")
    if days < 1 or days > 10:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 10")
    
    # 날짜 범위 계산
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    logger.info(f"📊 Intraday 차트 조회: {ticker} {timeframe}m ({from_date} ~ {to_date})")
    
    try:
        async with MassiveClient(api_key) as client:
            bars = await client.fetch_intraday_bars(
                ticker=ticker.upper(),
                multiplier=timeframe,
                from_date=from_date,
                to_date=to_date,
                limit=5000
            )
        
        if not bars:
            return {
                "status": "no_data",
                "ticker": ticker.upper(),
                "timeframe": timeframe,
                "count": 0,
                "candles": [],
                "timestamp": get_timestamp()
            }
        
        # 차트 위젯 포맷으로 변환 (timestamp -> time)
        candles = []
        for bar in bars:
            candles.append({
                "time": bar["timestamp"] // 1000,  # ms -> seconds (TradingView 포맷)
                "open": bar["open"],
                "high": bar["high"],
                "low": bar["low"],
                "close": bar["close"],
                "volume": bar["volume"],
            })
        
        return {
            "status": "success",
            "ticker": ticker.upper(),
            "timeframe": timeframe,
            "count": len(candles),
            "candles": candles,
            "timestamp": get_timestamp()
        }
        
    except Exception as e:
        logger.error(f"Intraday 차트 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
