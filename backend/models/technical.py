# ============================================================================
# Technical Models - 기술적 분석 관련 데이터 구조체
# ============================================================================
# 📌 이 파일의 역할:
#   - IndicatorResult, StopLossLevels, ZScoreResult and DailyStats 정의
#   - 지표 계산 결과 및 통계 데이터 구조체
#
# 📖 사용 예시:
#   >>> from backend.models import ZScoreResult, IndicatorResult
#   >>> result = ZScoreResult(zenV=1.5, zenP=2.0)
#
# 📖 리팩터링 [07-001]:
#   - 분산된 technical 모델들을 중앙화
# ============================================================================

"""
Technical Analysis Models

기술적 분석 관련 데이터 구조체입니다.
"""

from dataclasses import dataclass


@dataclass
class IndicatorResult:
    """
    지표 계산 결과 구조체

    Attributes:
        value: 지표 값
        is_valid: 유효성 여부
        message: 부가 메시지 (에러 등)
    """

    value: float
    is_valid: bool = True
    message: str = ""


@dataclass
class StopLossLevels:
    """
    Stop-Loss / Take-Profit 레벨 구조체

    Attributes:
        entry_price: 진입 가격
        stop_loss: 스탑로스 가격
        take_profit_1: 1차 목표가
        take_profit_2: 2차 목표가
        take_profit_3: 3차 목표가
        risk_amount: 리스크 금액
    """

    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    risk_amount: float


@dataclass
class ZScoreResult:
    """
    Z-Score 계산 결과

    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    Z-Score는 "평균에서 얼마나 떨어져 있나"를 표준편차 단위로 측정합니다.
    zenV = 거래량 Z-Score, zenP = 가격변동 Z-Score

    Attributes:
        zenV: 거래량 Z-Score
        zenP: 가격변동 Z-Score
    """

    zenV: float
    zenP: float


@dataclass
class DailyStats:
    """
    장중 Time-Projection 계산용 일별 통계 캐시

    Attributes:
        avg_volume: 평균 거래량
        std_volume: 거래량 표준편차
        avg_change: 평균 변동률
        std_change: 변동률 표준편차
    """

    avg_volume: float
    std_volume: float
    avg_change: float
    std_change: float


__all__ = ["IndicatorResult", "StopLossLevels", "ZScoreResult", "DailyStats"]
