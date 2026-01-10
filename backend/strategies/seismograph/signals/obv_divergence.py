# ============================================================================
# OBV Divergence / Absorption Signal - 가격-거래량 괴리 감지
# ============================================================================
"""
OBV Divergence (V2) / Absorption (V3) 시그널 감지 모듈

V2: 가격 하락 + OBV 상승 시 매집 신호
V3: Signed Volume과 Price Reaction 비교로 흡수 감지

[03-001] seismograph.py에서 분리
"""

from typing import Any
import numpy as np
from .base import get_column, calculate_obv


def calc_obv_divergence_intensity(data: Any, obv_lookback: int = 20) -> float:
    """
    V2 OBV Divergence 강도 계산 (0.0 ~ 1.0)

    가격 기울기 vs OBV 기울기 차이로 강도 계산
    - 가격 하락폭 클수록 + OBV 상승폭 클수록 = 높은 강도

    Args:
        data: OHLCV 데이터
        obv_lookback: 관찰 기간 (일)

    Returns:
        float: 0.0 ~ 1.0
    """
    try:
        closes = get_column(data, "close", obv_lookback)
        volumes = get_column(data, "volume", obv_lookback)

        if len(closes) < 5 or len(volumes) < 5:
            return 0.0

        obv = calculate_obv(closes, volumes)

        if len(closes) < 2 or closes[0] == 0:
            return 0.0

        # 가격 변화율 (%)
        price_change_pct = (closes[-1] - closes[0]) / closes[0]

        # OBV 변화율 (정규화: 총 거래량 대비)
        total_volume = sum(volumes) if sum(volumes) > 0 else 1
        obv_change_ratio = (obv[-1] - obv[0]) / total_volume

        # Divergence: 가격 하락 + OBV 상승
        if price_change_pct > 0.02:  # 2% 이상 상승 시 divergence 아님
            return 0.0

        if obv_change_ratio <= 0:  # OBV 하락 시 divergence 아님
            return 0.0

        # 강도: 가격 하락폭과 OBV 상승폭 조합
        divergence_strength = min(
            1.0, abs(price_change_pct) * 10 + obv_change_ratio * 5
        )
        return round(divergence_strength, 2)

    except Exception:
        return 0.0


def calc_absorption_intensity_v3(data: Any) -> float:
    """
    V3.2 Absorption 강도 계산 (OBV Divergence 대체)

    핵심 개념: 거래량 많은데 가격 반응 작으면 → 흡수 발생

    수식:
    - sv = Σ(sign(returns) × volume)  : Signed Volume
    - pr = Σ(|returns|)               : Price Reaction
    - absorption = sigmoid(z(sv_norm) - z(pr_norm))

    Args:
        data: OHLCV 데이터

    Returns:
        float: 0.0 ~ 1.0
    """
    try:
        closes = get_column(data, "close", 20)
        volumes = get_column(data, "volume", 20)

        if len(closes) < 10 or len(volumes) < 10:
            return 0.0

        # === 1. 최근 10일 Signed Volume 계산 ===
        signed_volume = 0.0
        price_reaction = 0.0

        for i in range(-10, 0):
            if closes[i - 1] > 0:
                ret = (closes[i] - closes[i - 1]) / closes[i - 1]
                sign = 1 if ret > 0 else (-1 if ret < 0 else 0)
                signed_volume += sign * volumes[i]
                price_reaction += abs(ret)

        # === 2. 정규화 (Median 기반) ===
        median_volume = sorted(volumes)[len(volumes) // 2]
        if median_volume <= 0:
            return 0.0

        sv_norm = signed_volume / median_volume
        avg_pr = price_reaction / 10 if price_reaction > 0 else 0.01

        # === 3. Absorption 계산 ===
        # 5% 초과 상승 시 약한 페널티
        if len(closes) >= 6:
            price_change = (
                (closes[-1] - closes[-5]) / closes[-5] if closes[-5] > 0 else 0
            )
            if price_change > 0.05:
                return 0.3  # 상승 중이면 흡수 약함

        # V3.2: 부드러운 페널티
        if sv_norm <= 0:
            # 매도 우세: 0.0 ~ 0.5 범위
            intensity = 0.5 / (1 + np.exp(-sv_norm * 2))
        else:
            # 매수 우세: 0.5 ~ 1.0 범위
            absorption_score = sv_norm / (avg_pr / 0.02 + 0.1)
            intensity = 0.5 + 0.5 / (1 + np.exp(-absorption_score + 3.0))

        return round(float(intensity), 2)

    except Exception:
        return 0.5  # 예외 시 중립 반환
