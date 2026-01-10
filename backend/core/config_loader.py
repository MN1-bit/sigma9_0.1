"""
Sigma9 Configuration Loader
============================
YAML 설정 파일을 Python 객체로 로드하는 유틸리티.

📌 사용법:
    # 서버 설정 로드
    from backend.core.config_loader import load_server_config
    config = load_server_config()
    print(config.server.host)  # "0.0.0.0"

    # 클라이언트 설정 로드
    from backend.core.config_loader import load_client_config
    config = load_client_config()
    print(config.server.host)  # "localhost"
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import yaml


# ═══════════════════════════════════════════════════════════════════════════
# Server Config Data Classes (서버 설정 데이터 클래스)
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class ServerNetworkConfig:
    """서버 네트워크 설정"""

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    reload: bool = True
    workers: int = 1


@dataclass
class IBKRConfig:
    """IBKR 연결 설정"""

    host: str = "127.0.0.1"
    port: int = 7497
    client_id: int = 1
    readonly: bool = False
    timeout: int = 30
    auto_connect: bool = True
    auto_reconnect: bool = True


@dataclass
class DatabaseConfig:
    """데이터베이스 설정"""

    type: str = "sqlite"
    path: str = "data/sigma9.db"
    wal_mode: bool = True


@dataclass
class MarketDataConfig:
    """시장 데이터 설정"""

    db_path: str = "data/market_data.db"
    initial_load_days: int = 30
    auto_update_on_start: bool = True


@dataclass
class MassiveConfig:
    """Massive.com API 설정"""

    enabled: bool = True
    base_url: str = "https://api.Massive.com"
    rate_limit: int = 5
    retry_count: int = 3
    retry_delay: float = 2.0


@dataclass
class StrategyConfig:
    """전략 설정"""

    default: str = "seismograph"
    auto_load: bool = True
    hot_reload: bool = True


@dataclass
class RiskConfig:
    """리스크 관리 설정"""

    max_position_pct: float = 50.0
    max_concurrent: int = 3
    max_daily_trades: int = 50
    daily_loss_limit_pct: float = 3.0
    weekly_loss_limit_pct: float = 10.0
    per_trade_stop_pct: float = 5.0
    kelly_fraction: float = 0.5


@dataclass
class SchedulerConfig:
    """스케줄러 설정"""

    enabled: bool = True
    timezone: str = "America/New_York"
    market_open_scan: bool = True
    market_open_offset_minutes: int = 15
    daily_data_update: bool = True
    data_update_time: str = "16:30"


@dataclass
class LoggingFileConfig:
    """파일 로깅 설정"""

    enabled: bool = True
    path: str = "logs/sigma9.log"
    rotation: str = "1 day"
    retention: str = "7 days"
    compression: str = "zip"


@dataclass
class LoggingConsoleConfig:
    """콘솔 로깅 설정"""

    enabled: bool = True
    colorize: bool = True


@dataclass
class LoggingConfig:
    """로깅 설정"""

    level: str = "DEBUG"
    format: str = "json"
    console: LoggingConsoleConfig = field(default_factory=LoggingConsoleConfig)
    file: LoggingFileConfig = field(default_factory=LoggingFileConfig)


@dataclass
class LLMConfig:
    """LLM Oracle 설정"""

    enabled: bool = False
    default_provider: str = "openai"
    default_model: str = "gpt-4-turbo"
    fallback_provider: str = "anthropic"
    fallback_model: str = "claude-3-5-sonnet-20241022"
    timeout: int = 60
    max_retries: int = 2


@dataclass
class ServerConfig:
    """서버 전체 설정"""

    server: ServerNetworkConfig = field(default_factory=ServerNetworkConfig)
    ibkr: IBKRConfig = field(default_factory=IBKRConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    market_data: MarketDataConfig = field(default_factory=MarketDataConfig)
    massive: MassiveConfig = field(default_factory=MassiveConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)


# ═══════════════════════════════════════════════════════════════════════════
# Client Config Data Classes (클라이언트 설정 데이터 클래스)
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class ClientServerConfig:
    """클라이언트 → 서버 연결 설정"""

    host: str = "localhost"
    port: int = 8000
    ws_path: str = "/ws/feed"
    api_path: str = "/api"
    use_ssl: bool = False


@dataclass
class ConnectionConfig:
    """연결 동작 설정"""

    auto_connect: bool = True
    reconnect_enabled: bool = True
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 10
    timeout: int = 30
    heartbeat_interval: int = 15


@dataclass
class GUIConfig:
    """GUI 설정"""

    theme: str = "dark"
    window_opacity: float = 0.95
    acrylic_alpha: int = 180
    particle_opacity: float = 0.6
    tint_color: str = "#1a1a2e"
    remember_window_position: bool = True
    confirm_kill_switch: bool = True


@dataclass
class ChartConfig:
    """차트 설정"""

    default_timeframe: str = "1D"
    show_volume: bool = True
    show_vwap: bool = True
    show_indicators: bool = True
    max_bars: int = 500


@dataclass
class ClientLoggingConfig:
    """클라이언트 로깅 설정"""

    level: str = "INFO"
    console_visible: bool = True
    max_console_lines: int = 500


@dataclass
class ClientConfig:
    """클라이언트 전체 설정"""

    server: ClientServerConfig = field(default_factory=ClientServerConfig)
    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    gui: GUIConfig = field(default_factory=GUIConfig)
    chart: ChartConfig = field(default_factory=ChartConfig)
    logging: ClientLoggingConfig = field(default_factory=ClientLoggingConfig)


# ═══════════════════════════════════════════════════════════════════════════
# Config Loader Functions (설정 로더 함수)
# ═══════════════════════════════════════════════════════════════════════════


def _get_project_root() -> Path:
    """프로젝트 루트 디렉토리 반환"""
    # 이 파일의 위치: backend/core/config_loader.py
    # 프로젝트 루트: 2단계 위
    return Path(__file__).parent.parent.parent


def _load_yaml(file_path: Path) -> Dict[str, Any]:
    """YAML 파일 로드"""
    if not file_path.exists():
        raise FileNotFoundError(f"Config file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _dict_to_dataclass(data: Dict[str, Any], cls: type) -> Any:
    """
    딕셔너리를 데이터클래스로 변환 (재귀적)

    📌 중첩된 dataclass도 자동 변환
    """
    if data is None:
        return cls()

    # 해당 dataclass의 필드 정보 가져오기
    import dataclasses

    if not dataclasses.is_dataclass(cls):
        return data

    field_types = {f.name: f.type for f in dataclasses.fields(cls)}
    kwargs = {}

    for field_name, field_type in field_types.items():
        if field_name in data:
            value = data[field_name]
            # 중첩된 dataclass 처리
            if dataclasses.is_dataclass(field_type) and isinstance(value, dict):
                kwargs[field_name] = _dict_to_dataclass(value, field_type)
            else:
                kwargs[field_name] = value

    return cls(**kwargs)


def load_server_config(config_path: Optional[str] = None) -> ServerConfig:
    """
    서버 설정 로드

    📌 환경변수 오버라이드 지원:
        - SIGMA9_SERVER_HOST
        - SIGMA9_SERVER_PORT
        - SIGMA9_IBKR_HOST
        - SIGMA9_IBKR_PORT

    Args:
        config_path: 설정 파일 경로 (기본: backend/config/server_config.yaml)

    Returns:
        ServerConfig: 서버 설정 객체
    """
    if config_path is None:
        config_path = _get_project_root() / "backend" / "config" / "server_config.yaml"
    else:
        config_path = Path(config_path)

    # YAML 로드
    data = _load_yaml(config_path)

    # 환경변수 오버라이드
    if os.getenv("SIGMA9_SERVER_HOST"):
        data.setdefault("server", {})["host"] = os.getenv("SIGMA9_SERVER_HOST")
    if os.getenv("SIGMA9_SERVER_PORT"):
        data.setdefault("server", {})["port"] = int(os.getenv("SIGMA9_SERVER_PORT"))
    if os.getenv("SIGMA9_IBKR_HOST"):
        data.setdefault("ibkr", {})["host"] = os.getenv("SIGMA9_IBKR_HOST")
    if os.getenv("SIGMA9_IBKR_PORT"):
        data.setdefault("ibkr", {})["port"] = int(os.getenv("SIGMA9_IBKR_PORT"))

    # 데이터클래스로 변환
    config = ServerConfig()

    for section_name in [
        "server",
        "ibkr",
        "database",
        "market_data",
        "massive",
        "strategy",
        "risk",
        "scheduler",
        "logging",
        "llm",
    ]:
        if section_name in data:
            section_cls = type(getattr(config, section_name))
            setattr(
                config,
                section_name,
                _dict_to_dataclass(data[section_name], section_cls),
            )

    return config


def load_client_config(config_path: Optional[str] = None) -> ClientConfig:
    """
    클라이언트 설정 로드

    Args:
        config_path: 설정 파일 경로 (기본: frontend/config/client_config.yaml)

    Returns:
        ClientConfig: 클라이언트 설정 객체
    """
    if config_path is None:
        config_path = _get_project_root() / "frontend" / "config" / "client_config.yaml"
    else:
        config_path = Path(config_path)

    # YAML 로드
    data = _load_yaml(config_path)

    # 데이터클래스로 변환
    config = ClientConfig()

    for section_name in ["server", "connection", "gui", "chart", "logging"]:
        if section_name in data:
            section_cls = type(getattr(config, section_name))
            setattr(
                config,
                section_name,
                _dict_to_dataclass(data[section_name], section_cls),
            )

    return config


# ═══════════════════════════════════════════════════════════════════════════
# Convenience Functions (편의 함수)
# ═══════════════════════════════════════════════════════════════════════════

# 싱글톤 캐시
_server_config: Optional[ServerConfig] = None
_client_config: Optional[ClientConfig] = None


def get_server_config() -> ServerConfig:
    """서버 설정 싱글톤 반환 (캐시됨)"""
    global _server_config
    if _server_config is None:
        _server_config = load_server_config()
    return _server_config


def get_client_config() -> ClientConfig:
    """클라이언트 설정 싱글톤 반환 (캐시됨)"""
    global _client_config
    if _client_config is None:
        _client_config = load_client_config()
    return _client_config


def reload_configs():
    """설정 캐시 초기화 (hot-reload용)"""
    global _server_config, _client_config
    _server_config = None
    _client_config = None
