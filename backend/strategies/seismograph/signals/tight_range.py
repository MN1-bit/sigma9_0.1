# ============================================================================
# Tight Range Signal - ATR 기반 변동성 수축 감지
# ============================================================================
"""
Tight Range (VCP) 시그널 감지 모듈

ATR(Average True Range) 비율을 사용하여 변동성 수축을 감지합니다.
변동성이 수축하면 폭발 임박 신호로 해석합니다.

[03-001] seismograph.py에서 분리
"""

from typing import Any
import numpy as np
from .base import get_column, calculate_atr


def calc_tight_range_intensity(data: Any) -> float:
    """
    V2 Tight Range 강도 계산 (0.0 ~ 1.0)
    
    ATR_5 / ATR_20 비율이 낮을수록 강함
    - 비율 ≤ 30%: intensity = 1.0
    - 비율 ≥ 70%: intensity = 0.0
    - 그 사이: 선형 보간
    
    Args:
        data: OHLCV 데이터
        
    Returns:
        float: 0.0 ~ 1.0
    """
    try:
        highs = get_column(data, 'high', 20)
        lows = get_column(data, 'low', 20)
        closes = get_column(data, 'close', 20)
        
        if len(highs) < 20:
            return 0.0
        
        tr_list = calculate_atr(highs, lows, closes)
        
        if len(tr_list) < 19:
            return 0.0
        
        atr_5d = np.mean(tr_list[-5:])
        atr_20d = np.mean(tr_list)
        
        if atr_20d <= 0:
            return 0.0
        
        ratio = atr_5d / atr_20d
        
        # 선형 보간: 0.3 이하 → 1.0, 0.7 이상 → 0.0
        intensity = max(0.0, min(1.0, (0.7 - ratio) / 0.4))
        return round(intensity, 2)
        
    except Exception:
        return 0.0


def calc_tight_range_intensity_v3(
    data: Any,
    lookback_days: int = 60,
    use_percentile: bool = True,
    min_samples: int = 20,
    sigmoid_k: float = 2.5,
    sigmoid_x0: float = -0.5
) -> float:
    """
    V3.2 Tight Range 강도 계산 - Percentile 기반 정규화
    
    60일 ATR 히스토리에서 현재 ATR의 상대적 위치를 percentile로 계산.
    레짐 변화에 강건 (Z-Score의 분산 의존성 제거)
    
    percentile 낮을수록(변동성 수축) → 강도 높음
    
    Args:
        data: OHLCV 데이터
        lookback_days: ATR 히스토리 기간 (기본 60일)
        use_percentile: True면 percentile 방식, False면 Z-Score Sigmoid
        min_samples: 최소 샘플 수
        sigmoid_k: Sigmoid 기울기 (Z-Score 방식)
        sigmoid_x0: Sigmoid 중심점 (Z-Score 방식)
        
    Returns:
        float: 0.0 ~ 1.0
    """
    try:
        highs = get_column(data, 'high', lookback_days)
        lows = get_column(data, 'low', lookback_days)
        closes = get_column(data, 'close', lookback_days)
        
        if len(highs) < 20:
            return 0.0
        
        atr_list = calculate_atr(highs, lows, closes)
        
        if len(atr_list) < min_samples:
            return 0.0
        
        # 현재 ATR (최근 5일 평균)
        current_atr = np.mean(atr_list[-5:])
        
        if use_percentile:
            # V3.2: Percentile 기반 정규화
            count_lower = sum(1 for x in atr_list if x < current_atr)
            percentile = count_lower / len(atr_list)
            intensity = 1.0 - percentile
        else:
            # 기존: Z-Score Sigmoid
            mean_atr = np.mean(atr_list)
            std_atr = np.std(atr_list)
            
            if std_atr <= 0:
                return 0.0
            
            z = (current_atr - mean_atr) / std_atr
            intensity = 1 / (1 + np.exp(sigmoid_k * (z - sigmoid_x0)))
        
        return round(float(intensity), 2)
        
    except Exception:
        return 0.0
