# ============================================================================
# Score V1 - Stage-Based Priority System
# ============================================================================
"""
Score V1: Stage 기반 우선순위 점수 시스템

매집 단계(Stage)에 따라 우선순위를 부여합니다.
Boolean 결과를 기반으로 고정 점수를 반환합니다.

[03-001] seismograph.py에서 분리
"""

from typing import Any, Dict, Callable


def calculate_score_v1(
    daily_data: Any,
    signal_funcs: Dict[str, Callable[[Any], float]]
) -> float:
    """
    V1: Stage-Based Priority 점수 계산
    
    | 우선순위 | 점수 | 조건 | 의미 |
    |---------|------|------|------|
    | 1순위 | 100점 | Tight Range + OBV | 🔥 폭발 임박 |
    | 2순위 |  80점 | Tight Range only | 높은 관심 |
    | 3순위 |  70점 | Accumulation Bar + OBV | 관심 대상 |
    | 4순위 |  50점 | Accumulation Bar only | 추적 중 |
    | 5순위 |  30점 | OBV Divergence only | 모니터링 |
    | 6순위 |  10점 | Volume Dry-out only | 관찰 대상 |
    
    Args:
        daily_data: 일봉 데이터
        signal_funcs: 시그널 계산 함수들 dict
            예: {"tight_range": calc_tight_range_intensity, ...}
        
    Returns:
        float: 0 ~ 100 점수
    """
    try:
        if daily_data is None or len(daily_data) < 5:
            return 0.0
        
        # 시그널 감지 (0.5 초과면 True)
        has_tight_range = signal_funcs.get("tight_range", lambda x: 0)(daily_data) > 0.5
        has_accumulation_bar = signal_funcs.get("accumulation_bar", lambda x: 0)(daily_data) > 0.5
        has_obv_divergence = signal_funcs.get("obv_divergence", lambda x: 0)(daily_data) > 0.5
        has_volume_dryout = signal_funcs.get("volume_dryout", lambda x: 0)(daily_data) > 0.5
        
        # Stage-Based Priority 점수 할당
        if has_tight_range and has_obv_divergence:
            return 100.0  # 🔥 폭발 임박
        
        if has_tight_range:
            return 80.0  # 높은 관심
        
        if has_accumulation_bar and has_obv_divergence:
            return 70.0  # 관심 대상
        
        if has_accumulation_bar:
            return 50.0  # 추적 중
        
        if has_obv_divergence:
            return 30.0  # 모니터링
        
        if has_volume_dryout:
            return 10.0  # 관찰 대상
        
        return 0.0
        
    except Exception:
        return 0.0
