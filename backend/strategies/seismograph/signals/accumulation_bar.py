# ============================================================================
# Accumulation Bar Signal - 매집봉 감지
# ============================================================================
"""
Accumulation Bar 시그널 감지 모듈

가격 변동 작고 거래량 높은 캔들을 감지합니다.
세력의 매집 활동을 나타내는 신호입니다.

[03-001] seismograph.py에서 분리
"""

from typing import Any
import numpy as np
from .base import get_column


def calc_accumulation_bar_intensity(data: Any) -> float:
    """
    V2 Accumulation Bar 강도 계산 (0.0 ~ 1.0)

    Volume Spike 배수로 강도 계산
    - 2x → 0.0
    - 3x → 0.33
    - 5x → 1.0

    Args:
        data: OHLCV 데이터

    Returns:
        float: 0.0 ~ 1.0
    """
    try:
        latest = data.iloc[-1] if hasattr(data, "iloc") else data[-1]

        open_price = float(latest.get("open", latest.get("Open", 0)))
        close_price = float(latest.get("close", latest.get("Close", 0)))

        if open_price == 0:
            return 0.0

        price_change = abs(close_price - open_price) / open_price

        # 가격 변동이 크면 매집봉 아님
        if price_change > 0.025:
            return 0.0

        volumes = get_column(data, "volume", 20)
        if len(volumes) < 5:
            return 0.0

        avg_volume = np.mean(volumes[:-1])
        current_volume = float(volumes[-1])

        if avg_volume <= 0:
            return 0.0

        volume_ratio = current_volume / avg_volume

        # 2x 미만 → 0, 5x 이상 → 1.0
        intensity = max(0.0, min(1.0, (volume_ratio - 2) / 3))
        return round(intensity, 2)

    except Exception:
        return 0.0


def calc_accumulation_bar_intensity_v3(
    data: Any,
    float_shares: int = 10_000_000,
    base_score: float = 0.5,
    accum_period_days: int = 10,
    bullish_threshold_high: float = 0.6,
    bullish_threshold_low: float = 0.4,
    adj_bullish: float = 0.15,
    quiet_range_pct: float = 0.02,
    quiet_threshold_high: float = 0.7,
    quiet_threshold_low: float = 0.3,
    adj_quiet: float = 0.1,
) -> float:
    """
    V3.1 Accumulation Bar 강도 계산 - 시간 분리 + 이상치 내성

    특징:
    1. Base 0.5 + 가감점 구조 (중립 기준점)
    2. 과거 10일간의 매집 기간 분석 (Dryout와 시간 분리)
    3. Median + 비율 기반 (이상치에 강건)
    4. Float 기반 동적 기간 계산

    Args:
        data: OHLCV 캔들 데이터
        float_shares: 유통 주식 수 (기본값 10M)
        base_score: 기준 점수 (0.5)
        accum_period_days: 매집 기간 분석 일수

    Returns:
        float: 0.0 ~ 1.0 (0.5 = 중립)
    """
    try:
        BASE_SCORE = base_score

        # === 1. 동적 기간 계산 ===
        dryout_days = min(10, max(3, 3 + float_shares // 3_000_000))
        accum_start = dryout_days + accum_period_days
        accum_end = dryout_days

        if len(data) < accum_start:
            return BASE_SCORE

        # 매집 기간 데이터 추출
        if hasattr(data, "iloc"):
            period = data.iloc[-accum_start:-accum_end]
            period = [row.to_dict() for _, row in period.iterrows()]
        else:
            period = data[-accum_start:-accum_end]

        n = len(period)
        if n == 0:
            return BASE_SCORE

        adjustment = 0.0

        # === 2. 양봉 비율 ===
        bullish_count = sum(
            1
            for d in period
            if float(d.get("close", d.get("Close", 0)))
            > float(d.get("open", d.get("Open", 0)))
        )
        bullish_ratio = bullish_count / n

        if bullish_ratio >= bullish_threshold_high:
            adjustment += adj_bullish
        elif bullish_ratio <= bullish_threshold_low:
            adjustment -= adj_bullish

        # === 3. 방향성 있는 조용함 (Directional Quiet Days) ===
        quiet_days_list = []
        for d in period:
            close = float(d.get("close", d.get("Close", 0)))
            high = float(d.get("high", d.get("High", 0)))
            low = float(d.get("low", d.get("Low", 0)))
            if close > 0 and (high - low) / close < quiet_range_pct:
                midpoint = (high + low) / 2
                quiet_days_list.append(close > midpoint)

        if quiet_days_list:
            upper_close_ratio = sum(quiet_days_list) / len(quiet_days_list)

            if upper_close_ratio >= quiet_threshold_high:
                adjustment += adj_quiet
            elif upper_close_ratio <= quiet_threshold_low:
                adjustment -= adj_quiet * 0.5

        # === 4. 최종 강도 ===
        intensity = BASE_SCORE + adjustment
        return round(max(0.0, min(1.0, intensity)), 2)

    except Exception:
        return base_score
