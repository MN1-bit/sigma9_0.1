"""
Database Initialization
========================
DB 연결 및 Strategy Loader 초기화를 담당.

📌 역할:
    1. MarketDB 초기화
    2. StrategyLoader 초기화
    3. Daily Data Sync 점검
"""

import os
from typing import TYPE_CHECKING, Optional, Tuple

from loguru import logger

if TYPE_CHECKING:
    from backend.core.config_loader import ServerConfig
    from backend.data.database import MarketDB
    from backend.core.strategy_loader import StrategyLoader


def initialize_database(
    config: "ServerConfig",
) -> Tuple[Optional["MarketDB"], Optional["StrategyLoader"]]:
    """
    데이터베이스 및 Strategy Loader 초기화
    
    📌 수행 작업:
        1. MarketDB 연결
        2. StrategyLoader 초기화 및 전략 탐색
    
    Args:
        config: ServerConfig 인스턴스
    
    Returns:
        Tuple[MarketDB | None, StrategyLoader | None]: 초기화된 객체들
    """
    db: Optional["MarketDB"] = None
    strategy_loader: Optional["StrategyLoader"] = None
    
    # 1. Database 초기화 (경량 - 에러 무시)
    try:
        from backend.data.database import MarketDB
        db = MarketDB(config.market_data.db_path)
        logger.info(f"✅ Database connected: {config.market_data.db_path}")
    except Exception as e:
        logger.warning(f"⚠️ Database init skipped: {e}")
    
    # 2. Strategy Loader 초기화
    try:
        from backend.core.strategy_loader import StrategyLoader
        strategy_loader = StrategyLoader()
        strategies = strategy_loader.discover_strategies()
        logger.info(f"✅ Strategy Loader initialized. Found {len(strategies)} strategies")
    except Exception as e:
        logger.warning(f"⚠️ Strategy Loader init skipped: {e}")
    
    return db, strategy_loader


async def sync_daily_data(config: "ServerConfig", db: Optional["MarketDB"]) -> None:
    """
    일봉 데이터 동기화 점검 및 실행
    
    📌 Bugfix: Issue 1 - 일봉 차트 날짜 제한 해결
    
    Args:
        config: ServerConfig 인스턴스
        db: MarketDB 인스턴스 (None이면 스킵)
    """
    api_key = os.getenv("MASSIVE_API_KEY", "")
    if not api_key or not db:
        return
    
    try:
        logger.info("🔄 Checking daily data sync status...")
        from backend.data.massive_client import MassiveClient
        from backend.data.massive_loader import MassiveLoader
        
        async with MassiveClient(api_key) as client:
            loader = MassiveLoader(db, client)
            sync_status = await loader.get_sync_status()
            
            if not sync_status.get("is_up_to_date"):
                missing_days = sync_status.get("missing_days", 0)
                logger.info(f"📊 {missing_days} days of daily data missing, starting sync...")
                records = await loader.update_market_data()
                logger.info(f"✅ Daily data synced: {records} records added")
            else:
                logger.info("✅ Daily data already up-to-date")
    except Exception as e:
        logger.warning(f"⚠️ Daily data sync skipped: {e}")
