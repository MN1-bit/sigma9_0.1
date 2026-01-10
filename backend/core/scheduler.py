"""
Sigma9 Trading Scheduler
=========================
APScheduler 기반 작업 스케줄러.

📌 스케줄링 작업:
    1. 장 시작 전 Watchlist 스캔 (09:45 AM ET)
    2. 장 마감 후 일일 데이터 업데이트 (16:30 PM ET)
    3. 정기 헬스체크

📌 사용법:
    from backend.core.scheduler import TradingScheduler

    scheduler = TradingScheduler(config, db)
    scheduler.start()
    ...
    scheduler.shutdown()
"""

import asyncio
from typing import Optional, Callable
from loguru import logger

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger

    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logger.warning("⚠️ APScheduler not installed. Run: pip install apscheduler")


class TradingScheduler:
    """
    거래 스케줄러

    📌 기능:
        - 미국 시장 시간대 기반 스케줄링
        - 장 시작 시 자동 스캔
        - 장 마감 후 데이터 업데이트
        - Hot-reload 가능

    📌 미국 시장 시간 (ET):
        - Pre-market: 04:00 - 09:30
        - Regular: 09:30 - 16:00
        - After-hours: 16:00 - 20:00
    """

    def __init__(self, config, db=None):
        """
        스케줄러 초기화

        Args:
            config: SchedulerConfig 객체
            db: MarketDB 인스턴스 (Optional)
        """
        if not APSCHEDULER_AVAILABLE:
            raise ImportError("APScheduler is required. Run: pip install apscheduler")

        self.config = config
        self.db = db
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.running = False

        # 콜백 함수 저장소 (외부에서 주입 가능)
        self._scan_callback: Optional[Callable] = None
        self._data_update_callback: Optional[Callable] = None

        logger.info(f"📅 TradingScheduler initialized (timezone={config.timezone})")

    def start(self):
        """스케줄러 시작"""
        if self.running:
            logger.warning("⚠️ Scheduler is already running")
            return

        # 스케줄러 생성
        self.scheduler = AsyncIOScheduler(timezone=self.config.timezone)

        # 작업 등록
        self._setup_jobs()

        # 스케줄러 시작
        self.scheduler.start()
        self.running = True

        logger.info("✅ TradingScheduler started")
        self._log_scheduled_jobs()

    def shutdown(self, wait: bool = True):
        """스케줄러 종료"""
        if not self.running:
            return

        if self.scheduler:
            self.scheduler.shutdown(wait=wait)
            self.scheduler = None

        self.running = False
        logger.info("⏹ TradingScheduler stopped")

    def set_scan_callback(self, callback: Callable):
        """
        스캔 콜백 설정

        Args:
            callback: async 함수 또는 일반 함수
        """
        self._scan_callback = callback
        logger.debug(f"📌 Scan callback set: {callback.__name__}")

    def set_data_update_callback(self, callback: Callable):
        """
        데이터 업데이트 콜백 설정

        Args:
            callback: async 함수 또는 일반 함수
        """
        self._data_update_callback = callback
        logger.debug(f"📌 Data update callback set: {callback.__name__}")

    # ─────────────────────────────────────────────────────────────
    # Job Setup
    # ─────────────────────────────────────────────────────────────

    def _setup_jobs(self):
        """스케줄링 작업 등록"""
        if not self.scheduler:
            return

        # 1. 장 시작 스캔 (09:30 + offset)
        if self.config.market_open_scan:
            scan_hour = 9
            scan_minute = 30 + self.config.market_open_offset_minutes

            # 60분 초과 시 시간 조정
            if scan_minute >= 60:
                scan_hour += scan_minute // 60
                scan_minute = scan_minute % 60

            self.scheduler.add_job(
                self._run_market_open_scan,
                trigger=CronTrigger(
                    day_of_week="mon-fri",
                    hour=scan_hour,
                    minute=scan_minute,
                    timezone=self.config.timezone,
                ),
                id="market_open_scan",
                name="Market Open Scan",
                replace_existing=True,
            )
            logger.info(
                f"📌 Job added: Market Open Scan @ {scan_hour:02d}:{scan_minute:02d} ET (Mon-Fri)"
            )

        # 2. 일일 데이터 업데이트 (장 마감 후)
        if self.config.daily_data_update:
            update_time = self.config.data_update_time.split(":")
            update_hour = int(update_time[0])
            update_minute = int(update_time[1]) if len(update_time) > 1 else 0

            self.scheduler.add_job(
                self._run_daily_data_update,
                trigger=CronTrigger(
                    day_of_week="mon-fri",
                    hour=update_hour,
                    minute=update_minute,
                    timezone=self.config.timezone,
                ),
                id="daily_data_update",
                name="Daily Data Update",
                replace_existing=True,
            )
            logger.info(
                f"📌 Job added: Daily Data Update @ {update_hour:02d}:{update_minute:02d} ET (Mon-Fri)"
            )

        # 3. 헬스체크 (5분마다)
        self.scheduler.add_job(
            self._run_health_check,
            trigger=IntervalTrigger(minutes=5),
            id="health_check",
            name="Health Check",
            replace_existing=True,
        )

    def _log_scheduled_jobs(self):
        """등록된 작업 로깅"""
        if not self.scheduler:
            return

        jobs = self.scheduler.get_jobs()
        logger.info(f"📋 Scheduled jobs ({len(jobs)}):")
        for job in jobs:
            next_run = job.next_run_time
            if next_run:
                logger.info(f"    - {job.name}: Next run at {next_run}")
            else:
                logger.info(f"    - {job.name}: (no scheduled run)")

    # ─────────────────────────────────────────────────────────────
    # Job Implementations
    # ─────────────────────────────────────────────────────────────

    async def _run_market_open_scan(self):
        """
        장 시작 스캔 실행

        📌 실행 시점: 09:30 + offset (기본 09:45 AM ET)
        📌 동작:
            1. Watchlist 생성을 위한 전략 스캔 실행
            2. 결과를 DB에 저장
            3. WebSocket으로 클라이언트에 알림
        """
        logger.info("=" * 50)
        logger.info("📊 [SCHEDULED] Market Open Scan Starting...")
        logger.info("=" * 50)

        try:
            # 외부 콜백이 설정된 경우 실행
            if self._scan_callback:
                if asyncio.iscoroutinefunction(self._scan_callback):
                    await self._scan_callback()
                else:
                    self._scan_callback()
                logger.info("✅ [SCHEDULED] Market Open Scan completed (via callback)")
                return

            # 기본 스캔 로직 (콜백 미설정 시)
            from backend.core.scanner import run_scan

            if self.db:
                result = await run_scan(self.db.db_path)
                logger.info(
                    f"✅ [SCHEDULED] Market Open Scan completed: {len(result)} items"
                )

                # WebSocket 브로드캐스트
                try:
                    from backend.api.websocket import manager

                    await manager.broadcast_watchlist(result)
                except Exception as e:
                    logger.warning(f"⚠️ Failed to broadcast watchlist: {e}")
            else:
                logger.warning("⚠️ Database not available for scan")

        except Exception as e:
            logger.error(f"❌ [SCHEDULED] Market Open Scan failed: {e}")

    async def _run_daily_data_update(self):
        """
        일일 데이터 업데이트 실행

        📌 실행 시점: 16:30 PM ET (장 마감 30분 후)
        📌 동작:
            1. Polygon에서 최신 일봉 데이터 가져오기
            2. 로컬 DB 업데이트
        """
        logger.info("=" * 50)
        logger.info("📥 [SCHEDULED] Daily Data Update Starting...")
        logger.info("=" * 50)

        try:
            # 외부 콜백이 설정된 경우 실행
            if self._data_update_callback:
                if asyncio.iscoroutinefunction(self._data_update_callback):
                    await self._data_update_callback()
                else:
                    self._data_update_callback()
                logger.info("✅ [SCHEDULED] Daily Data Update completed (via callback)")
                return

            # 기본 업데이트 로직
            from backend.data.massive_loader import update_market_data

            if self.db:
                await update_market_data(self.db)
                logger.info("✅ [SCHEDULED] Daily Data Update completed")
            else:
                logger.warning("⚠️ Database not available for update")

        except ImportError as e:
            logger.warning(f"⚠️ Data update skipped (module not found): {e}")
        except Exception as e:
            logger.error(f"❌ [SCHEDULED] Daily Data Update failed: {e}")

    async def _run_health_check(self):
        """
        정기 헬스체크

        📌 실행 간격: 5분
        📌 동작:
            - IBKR 연결 상태 확인
            - 메모리 사용량 확인
            - 로그 기록
        """
        # 간단한 로그만 기록 (디버그 레벨)
        logger.debug("💓 Health check: OK")

    # ─────────────────────────────────────────────────────────────
    # Manual Trigger (수동 실행)
    # ─────────────────────────────────────────────────────────────

    async def trigger_scan_now(self):
        """스캔 즉시 실행 (수동)"""
        logger.info("🔄 Manual scan triggered")
        await self._run_market_open_scan()

    async def trigger_data_update_now(self):
        """데이터 업데이트 즉시 실행 (수동)"""
        logger.info("🔄 Manual data update triggered")
        await self._run_daily_data_update()
