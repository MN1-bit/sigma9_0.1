"""
Shutdown Logic
===============
서버 종료 시 리소스 정리를 담당.

📌 역할:
    1. RealtimeScanner 종료
    2. IgnitionMonitor 종료
    3. Scheduler 종료
    4. IBKR 연결 해제
"""

from typing import TYPE_CHECKING, Optional, Any

from loguru import logger

if TYPE_CHECKING:
    from backend.startup.realtime import RealtimeServicesResult


async def shutdown_all(
    realtime_scanner: Optional[Any] = None,
    ignition_monitor: Optional[Any] = None,
    scheduler: Optional[Any] = None,
    ibkr: Optional[Any] = None,
) -> None:
    """
    모든 서비스 종료

    📌 Graceful shutdown 순서:
        1. RealtimeScanner
        2. IgnitionMonitor
        3. Scheduler
        4. IBKR

    Args:
        realtime_scanner: RealtimeScanner 인스턴스
        ignition_monitor: IgnitionMonitor 인스턴스
        scheduler: TradingScheduler 인스턴스
        ibkr: IBKR 커넥터 인스턴스
    """
    logger.info("🛑 Server Shutting Down...")

    # 1. RealtimeScanner 종료 [Step 4.A.5]
    if realtime_scanner:
        try:
            await realtime_scanner.stop()
            logger.info("✅ RealtimeScanner stopped")
        except Exception as e:
            logger.error(f"❌ RealtimeScanner shutdown error: {e}")

    # 2. IgnitionMonitor 종료 [Bugfix: Ignition Score 자동 종료]
    if ignition_monitor:
        try:
            await ignition_monitor.stop()
            logger.info("✅ IgnitionMonitor stopped")
        except Exception as e:
            logger.error(f"❌ IgnitionMonitor shutdown error: {e}")

    # 3. Scheduler 종료
    if scheduler:
        try:
            scheduler.shutdown()
            logger.info("✅ Scheduler stopped")
        except Exception as e:
            logger.error(f"❌ Scheduler shutdown error: {e}")

    # 4. IBKR 연결 해제
    if ibkr:
        try:
            ibkr.disconnect()
            logger.info("✅ IBKR disconnected")
        except Exception as e:
            logger.error(f"❌ IBKR disconnect error: {e}")

    logger.info("👋 Goodbye!")


async def shutdown_from_result(result: "RealtimeServicesResult") -> None:
    """
    RealtimeServicesResult 객체를 받아 모든 서비스 종료

    Args:
        result: RealtimeServicesResult 인스턴스
    """
    await shutdown_all(
        realtime_scanner=result.realtime_scanner,
        ignition_monitor=result.ignition_monitor,
        scheduler=result.scheduler,
        ibkr=result.ibkr,
    )
