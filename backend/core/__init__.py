# ============================================================================
# Backend Core Package
# ============================================================================
# 이 패키지는 Sigma9 트레이딩 시스템의 핵심 로직을 담당합니다.
#
# 📦 포함 모듈:
#   - strategy_base.py: 전략 추상 인터페이스 (ABC) + Signal 데이터 클래스
#   - mock_data.py: 테스트용 가상 시장 데이터 생성기
#   - strategy_loader.py: 전략 플러그인 동적 로더 (Step 2.x에서 구현)
#   - engine.py: 트레이딩 엔진 (전략 실행) (Step 2.x에서 구현)
#   - risk_manager.py: 리스크 관리 (손절, 포지션 크기) (Step 3.x에서 구현)
#   - double_tap.py: 재진입 로직 (Step 3.x에서 구현)
# ============================================================================

"""
Sigma9 Core Package

트레이딩 시스템의 핵심 비즈니스 로직을 담당하는 패키지입니다.

Example:
    from backend.core import StrategyBase, Signal, MockPriceFeed
    
    # 전략 정의
    class MyStrategy(StrategyBase):
        ...
    
    # Mock 데이터 생성
    feed = MockPriceFeed(mode="random_walk")
"""

from .strategy_base import StrategyBase, Signal
from .mock_data import MockPriceFeed

__all__ = [
    # 전략 인터페이스
    "StrategyBase",
    "Signal",
    # Mock 데이터
    "MockPriceFeed",
]

