# ============================================================================
# Score V2 - Weighted Intensity System
# ============================================================================
"""
Score V2: 가중합 기반 연속 점수 시스템

각 시그널의 강도(0~1)에 가중치를 곱해 연속적인 점수를 반환합니다.
V1의 Step 함수 대신 연속 함수를 사용합니다.

[03-001] seismograph.py에서 분리
"""

from typing import Any, Dict

# 신호별 가중치 (Masterplan 기준)
SCORE_WEIGHTS = {
    "tight_range": 0.30,       # VCP 패턴 (30%)
    "obv_divergence": 0.35,    # 스마트 머니 (35%)
    "accumulation_bar": 0.25,  # 매집 완료 (25%)
    "volume_dryout": 0.10,     # 준비 단계 (10%)
}


def calculate_score_v2(
    daily_data: Any,
    intensities: Dict[str, float],
    weights: Dict[str, float] = None
) -> float:
    """
    V2: 가중합 기반 연속 점수 계산
    
    수식: Score = 100 × Σ(w_i × I_i)
    
    where:
        w_i = 신호 가중치
        I_i = 신호 강도 (0.0 ~ 1.0)
    
    Args:
        daily_data: 일봉 데이터 (유효성 검사용)
        intensities: 각 시그널의 강도 dict
            예: {"tight_range": 0.8, "obv_divergence": 0.5, ...}
        weights: 가중치 dict (None이면 기본값 사용)
        
    Returns:
        float: 0.0 ~ 100.0 연속 점수
    """
    try:
        if daily_data is None or len(daily_data) < 5:
            return 0.0
        
        if weights is None:
            weights = SCORE_WEIGHTS
        
        # 가중합 계산
        raw_score = sum(
            intensities.get(signal, 0.0) * weight
            for signal, weight in weights.items()
        )
        
        return round(raw_score * 100, 1)
        
    except Exception:
        return 0.0
