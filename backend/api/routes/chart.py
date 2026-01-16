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
        raise HTTPException(
            status_code=400, detail="Invalid timeframe. Use 1, 5, 15, or 60"
        )
    if days < 1 or days > 10:
        raise HTTPException(status_code=400, detail="Days must be between 1 and 10")

    # 날짜 범위 계산
    to_date = datetime.now().strftime("%Y-%m-%d")
    from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    logger.info(
        f"📊 Intraday 차트 조회: {ticker} {timeframe}m ({from_date} ~ {to_date})"
    )

    try:
        async with MassiveClient(api_key) as client:
            bars = await client.fetch_intraday_bars(
                ticker=ticker.upper(),
                multiplier=timeframe,
                from_date=from_date,
                to_date=to_date,
                limit=5000,
            )

        if not bars:
            return {
                "status": "no_data",
                "ticker": ticker.upper(),
                "timeframe": timeframe,
                "count": 0,
                "candles": [],
                "timestamp": get_timestamp(),
            }

        # 차트 위젯 포맷으로 변환 (timestamp -> time)
        candles = []
        for bar in bars:
            candles.append(
                {
                    "time": bar["timestamp"]
                    // 1000,  # ms -> seconds (TradingView 포맷)
                    "open": bar["open"],
                    "high": bar["high"],
                    "low": bar["low"],
                    "close": bar["close"],
                    "volume": bar["volume"],
                }
            )

        return {
            "status": "success",
            "ticker": ticker.upper(),
            "timeframe": timeframe,
            "count": len(candles),
            "candles": candles,
            "timestamp": get_timestamp(),
        }

    except Exception as e:
        logger.error(f"Intraday 차트 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# GET /chart/bars - 히스토리컬 바 조회 (L2 → L3 캐시)
# ═══════════════════════════════════════════════════════════════════════════
#
# 📌 역할:
#     차트 Pan/Zoom 시 추가 히스토리 데이터를 가져옵니다.
#     L2 (SQLite) 먼저 조회, Miss 시 L3 (Massive API) 호출 후 캐싱.
#
# 📌 이동 배경:
#     원래 frontend/gui/dashboard.py의 _fetch_historical_bars()에 있던 로직.
#     Frontend가 DB/API 직접 접근하는 것은 아키텍처 위반이므로 Backend로 이동.
#
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/chart/bars", summary="히스토리컬 바 조회 (Parquet 캐시)")
async def get_historical_bars(
    ticker: str,
    timeframe: str = "5m",  # 1m, 5m, 15m, 1h
    limit: int = 100,  # 가져올 바 개수
    before: int = None,  # 이 타임스탬프(ms) 이전 데이터 조회
):
    """
    히스토리컬 바 데이터 조회 (Parquet → API 캐시)

    📌 사용 시나리오:
        차트를 왼쪽(과거)으로 스크롤할 때 추가 데이터 로드

    📌 [11-002] 캐시 전략 (Parquet 전환):
        1. DataRepository에서 Parquet 조회 (auto_fill=True)
        2. 누락 시 → Massive API 자동 호출 → Parquet 저장

    Example:
        GET /api/chart/bars?ticker=AAPL&timeframe=5m&limit=100&before=1704067200000
    """
    from backend.container import container

    # =========================================================================
    # 파라미터 파싱
    # =========================================================================
    ticker = ticker.upper()

    # 타임프레임 → ParquetManager 형식 변환
    tf_map = {"1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h"}
    parquet_tf = tf_map.get(timeframe.lower(), "5m")

    # 기준 시간 (before가 없으면 현재 시간)
    if before:
        ref_time = datetime.fromtimestamp(before / 1000)
    else:
        ref_time = datetime.now()

    # 날짜 범위 계산 (하루 바 개수 추정으로 필요 일수 산출)
    tf_to_min = {"1m": 1, "5m": 5, "15m": 15, "1h": 60}
    multiplier = tf_to_min.get(parquet_tf, 5)
    bars_per_day = {1: 390, 5: 78, 15: 26, 60: 7}.get(multiplier, 78)
    days_back = max(5, limit // bars_per_day + 2)

    from_date = (ref_time - timedelta(days=days_back)).strftime("%Y-%m-%d")
    to_date = (ref_time - timedelta(days=1)).strftime("%Y-%m-%d")

    logger.info(f"📊 Historical bars: {ticker} {timeframe} ({from_date} ~ {to_date})")

    try:
        # =====================================================================
        # [11-002] DataRepository를 통한 Parquet 조회
        # ELI5: DataRepository가 알아서 Parquet에서 읽고, 없으면 API 호출해서 저장
        # =====================================================================
        repo = container.data_repository()

        # DataRepository의 get_intraday_bars 사용 (auto_fill=True 기본값)
        df = await repo.get_intraday_bars(
            ticker=ticker,
            timeframe=parquet_tf,
            days=days_back,
        )

        if df.empty:
            return {
                "status": "no_data",
                "ticker": ticker,
                "timeframe": timeframe,
                "count": 0,
                "candles": [],
                "timestamp": get_timestamp(),
            }

        # DataFrame → candles 리스트 변환
        candles = []
        for _, row in df.iterrows():
            ts = row.get("timestamp", 0)
            if ts > 1e12:  # ms → seconds
                ts = ts // 1000

            candles.append(
                {
                    "time": ts,
                    "open": row["open"],
                    "high": row["high"],
                    "low": row["low"],
                    "close": row["close"],
                    "volume": row.get("volume", 0),
                }
            )

        # limit 개수로 제한
        if len(candles) > limit:
            candles = candles[-limit:]

        logger.info(f"📥 DataRepository: {len(candles)} bars from Parquet")

        return {
            "status": "success",
            "source": "parquet_cache",
            "ticker": ticker,
            "timeframe": timeframe,
            "count": len(candles),
            "candles": candles,
            "timestamp": get_timestamp(),
        }

    except Exception as e:
        logger.error(f"Historical bars 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _format_candles(bars: list) -> list:
    """
    바 데이터를 차트 위젯 포맷으로 변환

    📌 변환:
        - timestamp (ms) → time (seconds) for TradingView 포맷
    """
    candles = []
    for bar in bars:
        ts = bar.get("timestamp", bar.get("time", 0))
        if ts > 1e12:  # ms → seconds
            ts = ts // 1000

        candles.append(
            {
                "time": ts,
                "open": bar["open"],
                "high": bar["high"],
                "low": bar["low"],
                "close": bar["close"],
                "volume": bar.get("volume", 0),
            }
        )
    return candles
