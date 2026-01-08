# ============================================================================
# Scoring Strategy Interface - 점수 계산 전략 인터페이스
# ============================================================================
# 📌 목적:
#   - realtime_scanner ↔ seismograph 순환 의존성 해소 (DIP 적용)
#   - 구현체(SeismographStrategy)는 이 인터페이스를 상속
#   - RealtimeScanner는 구현체 대신 인터페이스에만 의존
#
# 📖 사용 예시:
#   >>> class MyStrategy(ScoringStrategy):
#   ...     def calculate_watchlist_score_detailed(self, ticker, ohlcv_data):
#   ...         return {"score": 50, "score_v3": 75.0, ...}
# ============================================================================

"""
Scoring Strategy Interface

순환 의존성 해소를 위한 추상 인터페이스입니다.
RealtimeScanner는 구체적인 SeismographStrategy 대신 이 인터페이스에 의존합니다.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ScoringStrategy(ABC):
    """
    Score 계산 전략 인터페이스
    
    모든 스코어링 전략(SeismographStrategy 등)은 이 인터페이스를 구현해야 합니다.
    이를 통해 RealtimeScanner가 구현체에 직접 의존하지 않고,
    런타임에 구현체를 주입받을 수 있습니다.
    """
    
    @abstractmethod
    def calculate_watchlist_score_detailed(
        self, 
        ticker: str, 
        ohlcv_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Watchlist 점수 상세 계산
        
        Args:
            ticker: 종목 심볼 (예: "AAPL")
            ohlcv_data: OHLCV 데이터 리스트
                [{"open": float, "high": float, "low": float, 
                  "close": float, "volume": int}, ...]
        
        Returns:
            Dict containing:
                - score: float (Score V2)
                - score_v3: float (Score V3)
                - stage: str (현재 단계)
                - stage_number: int (단계 번호)
                - signals: Dict[str, bool] (신호 상태)
                - can_trade: bool (거래 가능 여부)
                - intensities_v3: Dict[str, float] (신호 강도)
        """
        pass
