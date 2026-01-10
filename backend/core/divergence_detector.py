# ============================================================================
# Divergence Detector Module
# ============================================================================
# 📌 이 파일의 역할:
#   - zenV-zenP Divergence 탐지 (매집 패턴)
#   - Seismograph 전략의 Scout 단계
#
# 📊 Divergence 조건:
#   - zenV >= 2.0 (거래량이 평균 대비 2σ 이상)
#   - zenP < 0.5 (가격 변동이 평균 이하)
#   → 해석: 거래량은 폭발, 가격은 조용 = 누군가 조용히 매집 중
# ============================================================================

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from loguru import logger


@dataclass
class DivergenceSignal:
    """
    Divergence 탐지 신호

    Attributes:
        ticker: 종목 코드
        zenV: Volume Z-Score
        zenP: Price Z-Score
        score: Divergence 강도 (zenV - zenP)
        detected_at: 탐지 시각
    """

    ticker: str
    zenV: float
    zenP: float
    score: float  # zenV - zenP
    detected_at: datetime


class DivergenceDetector:
    """
    zenV-zenP Divergence 탐지기

    Scout 단계: 거래량은 폭발하는데 가격은 조용한 종목 탐지
    → Ignition 발생 전 조기 포착 가능

    Attributes:
        ZENV_THRESHOLD: zenV 최소 기준 (기본값: 2.0)
        ZENP_THRESHOLD: zenP 최대 기준 (기본값: 0.5)

    Example:
        >>> detector = DivergenceDetector()
        >>> signal = detector.check("AAPL", zenV=2.5, zenP=0.3)
        >>> if signal:
        ...     print(f"🔥 DIVERGENCE: {signal.ticker} (score={signal.score})")
    """

    # Divergence 조건 임계값
    ZENV_THRESHOLD: float = 2.0  # 거래량이 2σ 이상이어야 함
    ZENP_THRESHOLD: float = 0.5  # 가격 변동이 0.5σ 미만이어야 함

    def __init__(self, zenV_threshold: float = 2.0, zenP_threshold: float = 0.5):
        """
        DivergenceDetector 초기화

        Args:
            zenV_threshold: zenV 최소 기준
            zenP_threshold: zenP 최대 기준
        """
        self.ZENV_THRESHOLD = zenV_threshold
        self.ZENP_THRESHOLD = zenP_threshold
        self._active_signals: dict[str, DivergenceSignal] = {}
        logger.debug(
            f"🔍 DivergenceDetector 초기화: zenV>={zenV_threshold}, zenP<{zenP_threshold}"
        )

    def check(
        self, ticker: str, zenV: float, zenP: float
    ) -> Optional[DivergenceSignal]:
        """
        Divergence 조건 확인

        Args:
            ticker: 종목 코드
            zenV: Volume Z-Score
            zenP: Price Z-Score

        Returns:
            DivergenceSignal 또는 None
        """
        # Divergence 조건: 고거래량 + 저변동
        if zenV >= self.ZENV_THRESHOLD and zenP < self.ZENP_THRESHOLD:
            signal = DivergenceSignal(
                ticker=ticker,
                zenV=zenV,
                zenP=zenP,
                score=round(zenV - zenP, 2),
                detected_at=datetime.now(),
            )

            # 캐시에 저장
            self._active_signals[ticker] = signal
            logger.info(
                f"🔥 DIVERGENCE 탐지: {ticker} | zenV={zenV}, zenP={zenP}, score={signal.score}"
            )
            return signal

        # 조건 미충족 시 기존 신호 제거
        if ticker in self._active_signals:
            del self._active_signals[ticker]

        return None

    def get_active_signals(self) -> list[DivergenceSignal]:
        """현재 활성 Divergence 신호 목록"""
        return list(self._active_signals.values())

    def get_signal(self, ticker: str) -> Optional[DivergenceSignal]:
        """특정 종목의 Divergence 신호 조회"""
        return self._active_signals.get(ticker)

    def clear_signal(self, ticker: str) -> None:
        """특정 종목의 신호 제거"""
        if ticker in self._active_signals:
            del self._active_signals[ticker]
            logger.debug(f"🔍 {ticker} Divergence 신호 제거")

    def clear_all(self) -> None:
        """모든 신호 초기화"""
        self._active_signals.clear()
        logger.debug("🔍 모든 Divergence 신호 초기화")
