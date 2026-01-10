# ═══════════════════════════════════════════════════════════════════════════
# Data Sync Endpoints (Issue 1: 일봉 데이터 동기화)
# ═══════════════════════════════════════════════════════════════════════════
#
# 📌 역할:
#     일봉 데이터 동기화 및 상태 조회 API
#
# 📌 엔드포인트:
#     POST /sync/daily  - 일봉 데이터 동기화
#     GET  /sync/status - 동기화 상태 조회
#
# ═══════════════════════════════════════════════════════════════════════════

import os

from fastapi import APIRouter, HTTPException
from loguru import logger

from .common import get_timestamp


router = APIRouter()


@router.post("/sync/daily", summary="일봉 데이터 동기화")
async def sync_daily_data():
    """
    누락된 일봉 데이터를 Massive.com에서 가져와 DB에 저장합니다.

    📌 동작:
        1. DB의 가장 최근 일봉 날짜 확인
        2. 최근 날짜 ~ 오늘 사이의 누락된 거래일 계산
        3. 누락된 날짜만 Massive API로 가져와 저장

    📌 사용 시점:
        - 서버 시작 시 자동 호출
        - 수동으로 동기화 필요 시

    Returns:
        dict: {status, records_added, db_latest_date, market_latest_date}

    Example:
        POST /api/sync/daily
        → {"status": "success", "records_added": 50, ...}
    """
    from backend.data.database import MarketDB
    from backend.data.massive_client import MassiveClient
    from backend.data.massive_loader import MassiveLoader

    api_key = os.getenv("MASSIVE_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=500, detail="MASSIVE_API_KEY not configured")

    logger.info("🔄 일봉 데이터 동기화 시작...")

    try:
        # DB 초기화
        db = MarketDB("data/market_data.db")
        await db.initialize()

        # MassiveLoader로 증분 업데이트
        async with MassiveClient(api_key) as client:
            loader = MassiveLoader(db, client)

            # 동기화 상태 확인
            sync_status = await loader.get_sync_status()

            if sync_status.get("is_up_to_date"):
                logger.info("✅ 일봉 데이터 이미 최신 상태")
                return {
                    "status": "up_to_date",
                    "records_added": 0,
                    "db_latest_date": sync_status.get("db_latest_date"),
                    "market_latest_date": sync_status.get("market_latest_date"),
                    "timestamp": get_timestamp(),
                }

            # 증분 업데이트 실행
            records_added = await loader.update_market_data()

            # 업데이트 후 상태 다시 확인
            updated_status = await loader.get_sync_status()

            logger.info(f"✅ 일봉 데이터 동기화 완료: {records_added}개 레코드 추가")

            return {
                "status": "success",
                "records_added": records_added,
                "db_latest_date": updated_status.get("db_latest_date"),
                "market_latest_date": updated_status.get("market_latest_date"),
                "timestamp": get_timestamp(),
            }

    except Exception as e:
        logger.error(f"일봉 데이터 동기화 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/status", summary="데이터 동기화 상태 조회")
async def get_sync_status():
    """
    현재 데이터 동기화 상태를 조회합니다.

    Returns:
        dict: {db_latest_date, market_latest_date, missing_days, is_up_to_date}
    """
    from backend.data.database import MarketDB
    from backend.data.massive_client import MassiveClient
    from backend.data.massive_loader import MassiveLoader

    api_key = os.getenv("MASSIVE_API_KEY", "")
    if not api_key:
        return {
            "status": "error",
            "message": "MASSIVE_API_KEY not configured",
            "timestamp": get_timestamp(),
        }

    try:
        db = MarketDB("data/market_data.db")
        await db.initialize()

        async with MassiveClient(api_key) as client:
            loader = MassiveLoader(db, client)
            sync_status = await loader.get_sync_status()

        return {**sync_status, "timestamp": get_timestamp()}

    except Exception as e:
        logger.error(f"동기화 상태 조회 실패: {e}")
        return {"status": "error", "message": str(e), "timestamp": get_timestamp()}
