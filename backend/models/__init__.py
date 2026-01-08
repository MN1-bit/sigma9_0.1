# ============================================================================
# Backend Models - 중앙 모델 저장소
# ============================================================================
# 📌 이 파일의 역할:
#   - 모든 공용 데이터 모델을 단일 진입점에서 export
#   - 순환 의존성 방지 및 임포트 경로 단순화
#
# 📖 사용 예시:
#   >>> from backend.models import TickData, WatchlistItem, RiskConfig
#
# 📖 리팩터링 [07-001]:
#   - 14개 이상 파일에 분산된 모델을 중앙화
# ============================================================================

"""
Backend Models

모든 공용 데이터 모델을 단일 진입점에서 제공합니다.
"""

# Tick & Watchlist
from .tick import TickData
from .watchlist import WatchlistItem

# Order & Position
from .order import OrderStatus, OrderType, OrderRecord, Position

# Risk
from .risk import RiskConfig

# Backtest
from .backtest import BacktestConfig, Trade, BacktestReport

# Technical
from .technical import IndicatorResult, StopLossLevels, ZScoreResult, DailyStats


__all__ = [
    # Tick & Watchlist
    "TickData",
    "WatchlistItem",
    # Order & Position
    "OrderStatus",
    "OrderType",
    "OrderRecord",
    "Position",
    # Risk
    "RiskConfig",
    # Backtest
    "BacktestConfig",
    "Trade",
    "BacktestReport",
    # Technical
    "IndicatorResult",
    "StopLossLevels",
    "ZScoreResult",
    "DailyStats",
]
