# ============================================================================
# Score V3 - Pinpoint Algorithm
# ============================================================================
"""
Score V3: Pinpoint Algorithm (Z-Score + Harmony Bonus)

V2에서 발전한 알고리즘으로, 다음을 포함합니다:
- Z-Score 기반 정규화
- Harmony Bonus (시그널 조합 보너스)
- Redundancy Penalty (죽은 압축 필터링)

[03-001] seismograph.py에서 분리
"""

from typing import Any, Dict

# V3 가중치 (score_v3_config.py에서 가져올 수도 있음)
V3_WEIGHTS = {
    "tight_range": 0.35,  # 변동성 수축 (최중요)
    "obv_divergence": 0.30,  # 흡수 (Absorption)
    "accumulation_bar": 0.20,  # 매집봉
    "volume_dryout": 0.15,  # 거래량 마름
}


def calculate_score_v3(
    daily_data: Any, intensities: Dict[str, float], weights: Dict[str, float] = None
) -> float:
    """
    V3.2: Pinpoint Algorithm

    수식: Score = clip(Base + Harmony Bonus, 0, 100) × Redundancy Penalty

    Args:
        daily_data: 일봉 데이터 (유효성 검사용)
        intensities: 각 시그널의 V3 강도 dict
        weights: 가중치 dict (None이면 기본값 사용)

    Returns:
        float: 0.0 ~ 100.0 점수
    """
    try:
        if daily_data is None or len(daily_data) < 5:
            return 0.0

        if weights is None:
            weights = V3_WEIGHTS

        # Base Score 계산
        base_score = (
            sum(
                intensities.get(signal, 0.0) * weight
                for signal, weight in weights.items()
            )
            * 100
        )

        # Harmony Bonus
        harmony_bonus = _calculate_harmony_bonus(intensities)

        # Redundancy Penalty
        redundancy_penalty = _calculate_redundancy_penalty(intensities)

        # 최종 점수 (0~100 클리핑)
        raw_score = (base_score + harmony_bonus) * redundancy_penalty
        final_score = min(100.0, max(0.0, raw_score))

        return round(final_score, 1)

    except Exception:
        return 0.0


def _calculate_harmony_bonus(intensities: Dict[str, float]) -> float:
    """
    Harmony Bonus 계산 (시그널 조합 보너스)

    여러 시그널이 동시에 높으면 추가 보너스

    Returns:
        float: 0.0 ~ 15.0
    """
    try:
        tr = intensities.get("tight_range", 0)
        obv = intensities.get("obv_divergence", 0)
        intensities.get("accumulation_bar", 0)

        bonus = 0.0

        # Tight Range + OBV 조합
        if tr > 0.6 and obv > 0.5:
            bonus += 10.0

        # 3개 이상 동시 활성화
        active_count = sum(1 for v in intensities.values() if v > 0.5)
        if active_count >= 3:
            bonus += 5.0

        return bonus

    except Exception:
        return 0.0


def _calculate_redundancy_penalty(intensities: Dict[str, float]) -> float:
    """
    Redundancy Penalty 계산 (죽은 압축 필터링)

    Tight Range만 높고 다른 시그널이 없으면 페널티

    Returns:
        float: 0.5 ~ 1.0
    """
    try:
        tr = intensities.get("tight_range", 0)
        obv = intensities.get("obv_divergence", 0)
        ab = intensities.get("accumulation_bar", 0)
        intensities.get("volume_dryout", 0)

        # Tight Range만 높고 나머지 낮으면 페널티
        if tr > 0.7 and obv < 0.3 and ab < 0.3:
            return 0.5

        return 1.0

    except Exception:
        return 1.0
