# ============================================================================
# Watchlist Model - Watchlist 항목 구조체
# ============================================================================
# 📌 이 파일의 역할:
#   - WatchlistItem 데이터 구조체 정의
#   - 개별 신호 메타데이터 포함
#
# 📖 사용 예시:
#   >>> from backend.models import WatchlistItem
#   >>> item = WatchlistItem(
#   ...     ticker="AAPL", score=80.0, stage="Stage 4 (Tight Range)",
#   ...     stage_number=4, signals={"tight_range": True}, can_trade=True
#   ... )
#
# 📖 리팩터링 [07-001]:
#   - seismograph/models.py → backend/models/watchlist.py 이동
# ============================================================================

"""
Watchlist Model

Watchlist 항목 구조체입니다.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class WatchlistItem:
    """
    Watchlist 항목 구조체 - 개별 신호 메타데이터 포함

    ═══════════════════════════════════════════════════════════════════════
    Step 2.2.5: Trading Restrictions 지원
    ═══════════════════════════════════════════════════════════════════════

    Stage 1-2 종목은 can_trade=False (Monitoring Only)
    Stage 3-4 종목만 can_trade=True (트레이딩 허용)

    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    "주목할 종목" 리스트의 각 항목입니다.
    종목의 점수, 단계, 매수 가능 여부 등을 담고 있습니다.

    Attributes:
        ticker: 종목 코드 (예: "AAPL")
        score: Accumulation Score (0~100)
        stage: Stage 문자열 (예: "Stage 4 (Tight Range)")
        stage_number: Stage 번호 (1~4) - Trading Restrictions용
        signals: 개별 신호 탐지 결과 dict
        can_trade: 트레이딩 가능 여부 (Stage 3-4만 True)
        last_close: 최근 종가
        avg_volume: 평균 거래량
        scan_timestamp: 스캔 시각

    Example:
        >>> item = WatchlistItem(
        ...     ticker="AAPL",
        ...     score=80.0,
        ...     stage="Stage 4 (Tight Range)",
        ...     stage_number=4,
        ...     signals={"tight_range": True, "obv_divergence": False},
        ...     can_trade=True,
        ...     last_close=5.50,
        ...     avg_volume=150000,
        ... )
    """

    ticker: str
    score: float
    stage: str
    stage_number: int  # 1~4 (Trading Restrictions용)
    signals: Dict[str, bool]  # 개별 신호 탐지 결과
    can_trade: bool  # Stage 3-4만 True
    last_close: float = 0.0
    avg_volume: float = 0.0
    scan_timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        dict로 변환 (JSON 직렬화용)

        Returns:
            dict: JSON 직렬화 가능한 딕셔너리
        """
        return {
            "ticker": self.ticker,
            "score": self.score,
            "stage": self.stage,
            "stage_number": self.stage_number,
            "signals": self.signals,
            "can_trade": self.can_trade,
            "last_close": self.last_close,
            "avg_volume": self.avg_volume,
            "scan_timestamp": self.scan_timestamp.isoformat()
            if self.scan_timestamp
            else None,
        }


__all__ = ["WatchlistItem"]
