# ============================================================================
# Signals Base - 시그널 공통 유틸리티
# ============================================================================
"""
Signals 공통 유틸리티 모듈

모든 시그널 함수에서 사용하는 공통 함수들을 정의합니다.
"""

from typing import Any, List
import numpy as np


def get_column(data: Any, col_name: str, lookback: int = 20) -> List[float]:
    """
    데이터에서 특정 컬럼 추출 (DataFrame/dict 호환)
    
    Args:
        data: OHLCV 데이터 (DataFrame 또는 list of dict)
        col_name: 컬럼명 ('open', 'high', 'low', 'close', 'volume')
        lookback: 가져올 데이터 수
        
    Returns:
        list: 숫자 리스트
    """
    if hasattr(data, 'iloc'):
        # DataFrame
        col = data[col_name].tail(lookback).tolist() if col_name in data.columns else \
              data[col_name.capitalize()].tail(lookback).tolist()
    else:
        # list of dict
        col = [
            float(d.get(col_name, d.get(col_name.capitalize(), 0)))
            for d in data[-lookback:]
        ]
    return col


def calculate_atr(highs: List[float], lows: List[float], closes: List[float]) -> List[float]:
    """
    True Range 리스트 계산
    
    Args:
        highs: 고가 리스트
        lows: 저가 리스트
        closes: 종가 리스트
        
    Returns:
        list: True Range 값들
    """
    tr_list = []
    for i in range(1, len(highs)):
        h_l = highs[i] - lows[i]
        h_pc = abs(highs[i] - closes[i - 1])
        l_pc = abs(lows[i] - closes[i - 1])
        tr_list.append(max(h_l, h_pc, l_pc))
    return tr_list


def calculate_obv(closes: List[float], volumes: List[float]) -> List[float]:
    """
    On-Balance Volume 계산
    
    Args:
        closes: 종가 리스트
        volumes: 거래량 리스트
        
    Returns:
        list: OBV 값들
    """
    obv = [0.0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv.append(obv[-1] + volumes[i])
        elif closes[i] < closes[i - 1]:
            obv.append(obv[-1] - volumes[i])
        else:
            obv.append(obv[-1])
    return obv
