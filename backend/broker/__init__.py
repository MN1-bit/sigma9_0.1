# ============================================================================
# Backend Broker Package
# ============================================================================
# 이 패키지는 브로커(IBKR) 연동을 담당합니다.
#
# 📦 포함 모듈:
#   - ibkr_connector.py: Interactive Brokers 연동 (ib_insync)
#
# 📌 주요 기능:
#   - TWS/IB Gateway 연결
#   - 실시간 시세 수신
#   - 주문 실행 (OCA 그룹 포함)
#   - 포지션/잔고 조회
# ============================================================================

"""
Sigma9 Broker Package

브로커 연동 모듈을 포함하는 패키지입니다.
현재는 Interactive Brokers (IBKR)만 지원합니다.
"""

from .ibkr_connector import IBKRConnector

__all__ = [
    "IBKRConnector",
]
