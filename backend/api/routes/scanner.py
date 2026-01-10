# ═══════════════════════════════════════════════════════════════════════════
# Scanner Endpoints
# ═══════════════════════════════════════════════════════════════════════════
#
# 📌 역할:
#     Scanner 실행 및 Day Gainers 조회/추가 API
#
# 📌 엔드포인트:
#     POST /scanner/run              - Scanner 실행
#     GET  /gainers                  - 당일 급등주 조회
#     POST /gainers/add-to-watchlist - 급등주를 Watchlist에 추가
#
# ═══════════════════════════════════════════════════════════════════════════

import os

from fastapi import APIRouter, HTTPException
from loguru import logger

from .common import get_timestamp


router = APIRouter()


@router.post("/scanner/run", summary="Scanner 실행")
async def run_scanner(strategy_name: str = "seismograph"):
    """
    Scanner를 실행하여 Watchlist를 생성합니다.

    📌 [11-002] 동작 (DataRepository 마이그레이션):
        1. DataRepository에서 Parquet 데이터 조회
        2. 전략의 스캔 로직 실행 (Seismograph)
        3. Watchlist 저장 및 반환
    """
    from backend.container import container
    from backend.core.scanner import Scanner

    logger.info(f"🔍 Scanner 실행 요청: {strategy_name}")

    try:
        # [11-002] Container에서 DataRepository 주입
        repo = container.data_repository()

        # Scanner 생성 및 실행
        scanner = Scanner(repo, watchlist_size=50)
        watchlist = await scanner.run_daily_scan(
            min_price=2.0, max_price=20.0, min_volume=100_000, lookback_days=20
        )

        # Watchlist 저장 (병합)
        if watchlist:
            # [Issue 01-002 Fix] 기존 Day Gainer 유지를 위해 병합 저장
            from backend.data.watchlist_store import merge_watchlist

            merged = merge_watchlist(watchlist, update_existing=True)
            logger.info(
                f"✅ Scanner 완료: {len(watchlist)}개 스캔, {len(merged)}개 총 Watchlist"
            )
        else:
            logger.warning("⚠️ Scanner: 조건에 맞는 종목 없음")

        return {
            "status": "success",
            "strategy": strategy_name,
            "item_count": len(watchlist) if watchlist else 0,
            "timestamp": get_timestamp(),
        }

    except Exception as e:
        logger.error(f"Scanner 실행 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gainers", summary="당일 급등주 조회")
async def get_day_gainers():
    """
    Massive.com API를 통해 당일 급등주 상위 20개를 조회합니다.

    📌 데이터:
        - 실시간 (장중)
        - 전일 종가 대비 상승률 기준
        - 거래량 10,000 이상만 포함

    Returns:
        list: 급등주 리스트 [{ticker, change_pct, last_price, volume}, ...]
    """
    from backend.data.massive_client import MassiveClient

    api_key = os.getenv("MASSIVE_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="MASSIVE_API_KEY not configured")

    try:
        async with MassiveClient(api_key) as client:
            gainers = await client.fetch_day_gainers()

        return {
            "status": "success",
            "count": len(gainers),
            "gainers": gainers,
            "timestamp": get_timestamp(),
        }
    except Exception as e:
        logger.error(f"Day Gainers 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gainers/add-to-watchlist", summary="급등주를 Watchlist에 추가")
async def add_gainers_to_watchlist():
    """
    당일 급등주를 현재 Watchlist에 병합합니다.

    📌 동작:
        1. Massive Gainers API로 급등주 조회
        2. 현재 Watchlist와 병합 (중복 제거)
        3. score=0 (급등주)으로 표시
    """
    from backend.data.massive_client import MassiveClient

    # [02-004] Container 방식으로 마이그레이션
    from backend.container import container

    api_key = os.getenv("MASSIVE_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="MASSIVE_API_KEY not configured")

    try:
        # 급등주 조회
        async with MassiveClient(api_key) as client:
            gainers = await client.fetch_day_gainers()

        if not gainers:
            return {"status": "no_gainers", "added": 0}

        # [02-004] Container에서 WatchlistStore 주입받음
        store = container.watchlist_store()
        watchlist = store.load()
        existing_tickers = {item.get("ticker") for item in watchlist}

        # 급등주 중 Watchlist에 없는 것만 추가
        added_count = 0
        for g in gainers:
            ticker = g.get("ticker", "")
            if ticker and ticker not in existing_tickers:
                watchlist.append(
                    {
                        "ticker": ticker,
                        "score": 0,  # 급등주 표시 (점수 없음)
                        "stage": "🚀 Day Gainer",
                        "stage_number": 0,
                        "signals": {},
                        "can_trade": False,  # 분석 전이므로 거래 불가
                        "last_close": g.get("last_price", 0),
                        "change_pct": g.get("change_pct", 0),
                        "avg_volume": g.get("volume", 0),
                    }
                )
                added_count += 1
                existing_tickers.add(ticker)

        # 저장
        store.save(watchlist)

        logger.info(f"✅ 급등주 {added_count}개 Watchlist에 추가")

        return {
            "status": "success",
            "added": added_count,
            "total": len(watchlist),
            "timestamp": get_timestamp(),
        }
    except Exception as e:
        logger.error(f"급등주 추가 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))
