"""
Sigma9 Startup Module
======================
서버 시작/종료 로직을 담당하는 모듈.

📌 구조:
    - config.py: Config + Logging 초기화
    - database.py: DB 초기화
    - realtime.py: Massive WS, Scanner, IgnitionMonitor 초기화
    - shutdown.py: 종료 로직

📌 사용:
    from backend.startup import (
        initialize_config,
        initialize_database,
        initialize_realtime,
        shutdown_all,
    )
"""

from backend.startup.config import initialize_config, setup_logging
from backend.startup.database import initialize_database
from backend.startup.realtime import initialize_realtime_services
from backend.startup.shutdown import shutdown_all

__all__ = [
    "initialize_config",
    "setup_logging",
    "initialize_database",
    "initialize_realtime_services",
    "shutdown_all",
]
