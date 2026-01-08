"""
Config & Logging Initialization
================================
서버 설정 로드 및 로깅 설정을 담당.

📌 역할:
    1. ServerConfig YAML 로드
    2. Loguru 콘솔/파일 핸들러 설정
    3. DI Container wiring
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from backend.core.config_loader import ServerConfig


def setup_logging(config: "ServerConfig") -> None:
    """
    Loguru 로깅 설정
    
    📌 설정 기반으로 콘솔/파일 로깅 구성
    
    Args:
        config: ServerConfig 인스턴스
    """
    logger.remove()  # 기본 핸들러 제거
    
    # 콘솔 로깅
    if config.logging.console.enabled:
        logger.add(
            sys.stderr,
            level=config.logging.level,
            colorize=config.logging.console.colorize,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
        )
    
    # 파일 로깅
    if config.logging.file.enabled:
        # logs 디렉토리 생성
        log_path = Path(config.logging.file.path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            config.logging.file.path,
            level=config.logging.level,
            rotation=config.logging.file.rotation,
            retention=config.logging.file.retention,
            compression=config.logging.file.compression,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        )


def initialize_config() -> "ServerConfig":
    """
    서버 설정 로드 및 DI Container 초기화
    
    📌 수행 작업:
        1. YAML 설정 파일 로드
        2. Loguru 설정
        3. DI Container wiring
    
    Returns:
        ServerConfig: 로드된 설정 객체
    """
    from backend.core.config_loader import load_server_config
    from backend.container import container
    
    # 1. Config 로드
    config = load_server_config()
    setup_logging(config)
    logger.info(f"✅ Config loaded (debug={config.server.debug})")
    
    # 2. DI Container wiring
    # 📌 Container에 Config 바인딩 및 모듈 wiring
    # 이렇게 하면 routes.py 등에서 @inject 데코레이터로 의존성 주입 사용 가능
    try:
        container.config.from_dict({
            "market_data": {"db_path": config.market_data.db_path},
            "scanner": {"poll_interval": 1.0},
            "ignition": {"poll_interval": 1.0},
        })
        container.wire(modules=[
            "backend.api.routes",
            "backend.server",
        ])
        logger.info("✅ DI Container wired")
    except Exception as e:
        logger.warning(f"⚠️ DI Container wiring skipped: {e}")
    
    return config
