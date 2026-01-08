# ═══════════════════════════════════════════════════════════════════════════
# Routes Common Utilities
# ═══════════════════════════════════════════════════════════════════════════
#
# 📌 역할:
#     routes/ 하위 라우터들이 공유하는 공용 유틸리티 함수들.
#     - 타임스탬프 생성
#     - 서버 uptime 계산
#     - 전역 상태 관리
#
# ═══════════════════════════════════════════════════════════════════════════

from datetime import datetime, timezone


# 서버 시작 시각 (uptime 계산용)
_server_start_time: datetime = datetime.now(timezone.utc)

# 엔진 상태 (임시 - 실제로는 Engine 클래스에서 관리)
_engine_running: bool = False


def get_timestamp() -> str:
    """
    현재 시각을 ISO8601 형식으로 반환합니다.
    
    Returns:
        str: ISO8601 형식 타임스탬프 (예: "2024-01-01T12:00:00+00:00")
    """
    return datetime.now(timezone.utc).isoformat()


def get_uptime_seconds() -> float:
    """
    서버 가동 시간을 초 단위로 반환합니다.
    
    Returns:
        float: 서버 시작 이후 경과 시간 (초)
    """
    return (datetime.now(timezone.utc) - _server_start_time).total_seconds()


def is_engine_running() -> bool:
    """
    엔진 실행 상태를 반환합니다.
    
    Returns:
        bool: 엔진 실행 중이면 True
    """
    return _engine_running


def set_engine_running(running: bool) -> None:
    """
    엔진 실행 상태를 설정합니다.
    
    Args:
        running: True면 실행 중, False면 정지
    """
    global _engine_running
    _engine_running = running
