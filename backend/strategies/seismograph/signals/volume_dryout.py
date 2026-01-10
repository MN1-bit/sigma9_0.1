# ============================================================================
# Volume Dryout Signal - 거래량 마름 감지
# ============================================================================
"""
Volume Dryout 시그널 감지 모듈

거래량 급감(마름)을 감지합니다.
"폭풍 전 고요"를 의미하며, 폭발 준비 신호입니다.

[03-001] seismograph.py에서 분리
"""

from typing import Any
import numpy as np
from .base import get_column


def calc_volume_dryout_intensity(data: Any, dryout_threshold: float = 0.4) -> float:
    """
    V2 Volume Dry-out 강도 계산 (0.0 ~ 1.0)

    최근 3일 vs 20일 평균 비율로 강도 계산
    - 40% → 0.0 (threshold)
    - 20% → 0.5
    - 0%  → 1.0

    Args:
        data: OHLCV 데이터
        dryout_threshold: 기준 임계값 (기본 0.4)

    Returns:
        float: 0.0 ~ 1.0
    """
    try:
        volumes = get_column(data, "volume", 20)

        if len(volumes) < 5:
            return 0.0

        avg_20d = np.mean(volumes)
        avg_3d = np.mean(volumes[-3:])

        if avg_20d <= 0:
            return 0.0

        ratio = avg_3d / avg_20d

        # threshold 이상 → 0, 0 → 1.0
        if ratio >= dryout_threshold:
            return 0.0

        intensity = 1.0 - (ratio / dryout_threshold)
        return round(intensity, 2)

    except Exception:
        return 0.0


def calc_volume_dryout_intensity_v3(
    data: Any,
    dryout_threshold: float = 0.4,
    support_factor_func: Any = None,
    min_price_location: float = 0.4,
    penalty_steepness: float = 3.0,
) -> float:
    """
    V3.2 Volume Dryout 강도 계산 - Sigmoid 연속 페널티

    거래량 감소 + 가격 지지 동시 확인
    - Volume Dryout: 최근 3일 vs 20일 비율
    - V3.2: Support 이탈 → Sigmoid 연속 페널티

    수식: support_penalty = 1 / (1 + exp(-k * support_dist))

    Args:
        data: OHLCV 데이터
        dryout_threshold: 거래량 마름 임계값
        support_factor_func: Support Factor 계산 함수 (외부 주입)
        min_price_location: 최소 가격 위치 임계값
        penalty_steepness: Sigmoid 기울기

    Returns:
        float: 0.0 ~ 1.0
    """
    try:
        volumes = get_column(data, "volume", 20)

        if len(volumes) < 5:
            return 0.0

        avg_20d = np.mean(volumes)
        avg_3d = np.mean(volumes[-3:])

        if avg_20d <= 0:
            return 0.0

        ratio = avg_3d / avg_20d

        # Volume Dryout 기본 강도
        if ratio >= dryout_threshold:
            volume_intensity = 0.0
        else:
            volume_intensity = 1.0 - (ratio / dryout_threshold)

        # Support Factor 계산 (외부 함수 또는 기본값)
        if support_factor_func is not None:
            support_factor = support_factor_func(data)
        else:
            support_factor = _calc_support_factor_default(data)

        # support_dist 정규화
        support_dist = (support_factor - min_price_location) / (
            1.0 - min_price_location
        )

        # Sigmoid 변환
        support_penalty = 1.0 / (1.0 + np.exp(-penalty_steepness * support_dist))

        # 최종 강도 = Volume Dryout × Support Penalty
        intensity = volume_intensity * support_penalty

        return round(intensity, 2)

    except Exception:
        return 0.0


def _calc_support_factor_default(data: Any) -> float:
    """
    기본 Support Factor 계산

    최근 종가가 20일 범위 내에서 어디에 위치하는지 계산

    Returns:
        float: 0.0 ~ 1.0 (1.0 = 상단, 0.0 = 하단)
    """
    try:
        closes = get_column(data, "close", 20)
        highs = get_column(data, "high", 20)
        lows = get_column(data, "low", 20)

        if len(closes) < 5:
            return 0.5

        current_close = closes[-1]
        period_high = max(highs)
        period_low = min(lows)

        if period_high == period_low:
            return 0.5

        location = (current_close - period_low) / (period_high - period_low)
        return round(location, 2)

    except Exception:
        return 0.5
