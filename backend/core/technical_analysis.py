# ============================================================================
# Technical Analysis - 기술 지표 계산 모듈
# ============================================================================
# 📌 이 파일의 역할:
#   - 실시간 기술 지표 계산 (VWAP, ATR, MA)
#   - 동적 Stop-Loss / Take-Profit 레벨 계산
#   - SeismographStrategy와 연동하여 진입/청산 판단에 활용
#
# 📖 사용 예시:
#   >>> from backend.core.technical_analysis import TechnicalAnalysis, DynamicStopLoss
#   >>> vwap = TechnicalAnalysis.calculate_vwap(prices, volumes, highs, lows)
#   >>> atr = TechnicalAnalysis.calculate_atr(highs, lows, closes)
#   >>> sl, tp = DynamicStopLoss.calculate_levels(entry_price, atr)
# ============================================================================

"""
Technical Analysis Module

실시간 트레이딩에 필요한 기술 지표를 계산합니다.

주요 지표:
    - VWAP (Volume Weighted Average Price): 거래량 가중 평균 가격
    - ATR (Average True Range): 평균 진정 변동폭
    - SMA/EMA (Simple/Exponential Moving Average): 이동 평균
"""

from typing import List, Tuple, Optional, Union
from dataclasses import dataclass
import numpy as np
from loguru import logger


# ═══════════════════════════════════════════════════════════════════════════
# 데이터 타입 정의
# ═══════════════════════════════════════════════════════════════════════════

# 센트 정밀도를 위한 별칭
PriceList = Union[List[float], np.ndarray]
VolumeList = Union[List[int], List[float], np.ndarray]


@dataclass
class IndicatorResult:
    """지표 계산 결과 구조체"""
    value: float
    is_valid: bool = True
    message: str = ""


@dataclass
class StopLossLevels:
    """Stop-Loss / Take-Profit 레벨 구조체"""
    entry_price: float
    stop_loss: float
    take_profit_1: float  # 1R (1:1)
    take_profit_2: float  # 2R (2:1)
    take_profit_3: float  # 3R (3:1)
    risk_amount: float    # 진입가 - SL
    

# ═══════════════════════════════════════════════════════════════════════════
# TechnicalAnalysis 클래스
# ═══════════════════════════════════════════════════════════════════════════

class TechnicalAnalysis:
    """
    기술 지표 계산 (정적 메서드 모음)
    
    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    
    주식 가격이 그냥 숫자로 보이지만, 여러 방법으로 분석하면
    "앞으로 오를지 내릴지" 힌트를 얻을 수 있습니다.
    
    - VWAP: "평균 얼마에 거래됐나?" (큰 손이 어느 가격대에서 샀는지)
    - ATR: "하루에 얼마나 움직이나?" (변동성 측정)
    - MA: "평균적인 흐름이 상승인가 하락인가?" (추세 확인)
    """
    
    @staticmethod
    def calculate_vwap(
        prices: PriceList,
        volumes: VolumeList,
        highs: Optional[PriceList] = None,
        lows: Optional[PriceList] = None,
    ) -> float:
        """
        VWAP (Volume Weighted Average Price) 계산
        
        ═══════════════════════════════════════════════════════════════
        쉬운 설명 (ELI5):
        ═══════════════════════════════════════════════════════════════
        "평균 가격"인데, 거래량이 많은 가격에 더 가중치를 줍니다.
        
        예: 10달러에 100주, 11달러에 900주 거래됐다면
            일반 평균 = (10+11)/2 = 10.5
            VWAP = (10×100 + 11×900) / 1000 = 10.9
        
        VWAP 위에서 사면 "비싸게 산 것", 아래면 "싸게 산 것"입니다.
        
        Args:
            prices: 종가 리스트 (또는 typical price 사용 시 무시됨)
            volumes: 거래량 리스트
            highs: 고가 리스트 (있으면 Typical Price 사용)
            lows: 저가 리스트 (있으면 Typical Price 사용)
        
        Returns:
            float: VWAP 값
        
        Example:
            >>> TechnicalAnalysis.calculate_vwap([10, 11, 12], [100, 200, 150])
            11.11...
        """
        prices = np.array(prices, dtype=float)
        volumes = np.array(volumes, dtype=float)
        
        if len(prices) == 0 or len(volumes) == 0:
            return 0.0
        
        if len(prices) != len(volumes):
            return 0.0
        
        # Typical Price 사용 (고가, 저가, 종가의 평균)
        if highs is not None and lows is not None:
            highs = np.array(highs, dtype=float)
            lows = np.array(lows, dtype=float)
            typical_prices = (highs + lows + prices) / 3
        else:
            typical_prices = prices
        
        # VWAP = Σ(가격 × 거래량) / Σ(거래량)
        total_volume = np.sum(volumes)
        if total_volume == 0:
            return 0.0
        
        vwap = np.sum(typical_prices * volumes) / total_volume
        return float(vwap)
    
    @staticmethod
    def calculate_atr(
        highs: PriceList,
        lows: PriceList,
        closes: PriceList,
        period: int = 14,
    ) -> float:
        """
        ATR (Average True Range) 계산
        
        ═══════════════════════════════════════════════════════════════
        쉬운 설명 (ELI5):
        ═══════════════════════════════════════════════════════════════
        "이 주식이 하루에 얼마나 움직이는가?"를 측정합니다.
        
        ATR이 0.5달러면 "하루에 대략 50센트씩 움직인다"는 뜻입니다.
        Stop-Loss를 정할 때 이 값을 참고합니다.
        
        Args:
            highs: 고가 리스트
            lows: 저가 리스트
            closes: 종가 리스트
            period: 평균 기간 (기본 14일)
        
        Returns:
            float: ATR 값
        
        Example:
            >>> TechnicalAnalysis.calculate_atr([11,12,13], [9,10,11], [10,11,12])
            1.5
        """
        highs = np.array(highs, dtype=float)
        lows = np.array(lows, dtype=float)
        closes = np.array(closes, dtype=float)
        
        n = len(highs)
        if n < 2:
            return 0.0
        
        # True Range 계산
        # TR = max(H-L, |H-PC|, |L-PC|) where PC = Previous Close
        tr_list = []
        for i in range(1, n):
            h_l = highs[i] - lows[i]
            h_pc = abs(highs[i] - closes[i - 1])
            l_pc = abs(lows[i] - closes[i - 1])
            tr_list.append(max(h_l, h_pc, l_pc))
        
        if len(tr_list) == 0:
            return 0.0
        
        # ATR = TR의 평균 (최근 period개)
        tr_array = np.array(tr_list)
        atr = np.mean(tr_array[-period:])
        return float(atr)
    
    @staticmethod
    def calculate_sma(
        prices: PriceList,
        period: int = 20,
    ) -> float:
        """
        SMA (Simple Moving Average) 계산
        
        ═══════════════════════════════════════════════════════════════
        쉬운 설명 (ELI5):
        ═══════════════════════════════════════════════════════════════
        "최근 N일 평균 가격"입니다.
        
        현재 가격이 SMA 위면 "상승 추세", 아래면 "하락 추세" 힌트입니다.
        
        Args:
            prices: 가격 리스트
            period: 평균 기간
        
        Returns:
            float: SMA 값
        """
        prices = np.array(prices, dtype=float)
        
        if len(prices) < period:
            # 데이터가 부족하면 있는 것만으로 계산
            return float(np.mean(prices)) if len(prices) > 0 else 0.0
        
        return float(np.mean(prices[-period:]))
    
    @staticmethod
    def calculate_ema(
        prices: PriceList,
        period: int = 20,
    ) -> float:
        """
        EMA (Exponential Moving Average) 계산
        
        ═══════════════════════════════════════════════════════════════
        쉬운 설명 (ELI5):
        ═══════════════════════════════════════════════════════════════
        SMA와 비슷하지만, 최근 가격에 더 가중치를 줍니다.
        
        "최신 정보"가 더 중요하다고 할 때 사용합니다.
        
        Args:
            prices: 가격 리스트
            period: 평균 기간
        
        Returns:
            float: EMA 값
        """
        prices = np.array(prices, dtype=float)
        
        if len(prices) == 0:
            return 0.0
        
        if len(prices) < period:
            return float(np.mean(prices))
        
        # EMA 계산
        # multiplier = 2 / (period + 1)
        # EMA = (Price - EMA_prev) × multiplier + EMA_prev
        multiplier = 2 / (period + 1)
        
        # 첫 EMA는 SMA로 시작
        ema = np.mean(prices[:period])
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return float(ema)
    
    @staticmethod
    def calculate_rsi(
        prices: PriceList,
        period: int = 14,
    ) -> float:
        """
        RSI (Relative Strength Index) 계산
        
        ═══════════════════════════════════════════════════════════════
        쉬운 설명 (ELI5):
        ═══════════════════════════════════════════════════════════════
        "과열인가 과냉인가?"를 0~100으로 표시합니다.
        
        - 70 이상: 과열 (너무 많이 올랐다)
        - 30 이하: 과냉 (너무 많이 떨어졌다)
        
        Args:
            prices: 가격 리스트
            period: 기간 (기본 14)
        
        Returns:
            float: RSI 값 (0~100)
        """
        prices = np.array(prices, dtype=float)
        
        if len(prices) < period + 1:
            return 50.0  # 중립값 반환
        
        # 가격 변화 계산
        deltas = np.diff(prices)
        
        # 상승/하락 분리
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # 평균 계산
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)


# ═══════════════════════════════════════════════════════════════════════════
# DynamicStopLoss 클래스
# ═══════════════════════════════════════════════════════════════════════════

class DynamicStopLoss:
    """
    ATR 기반 동적 Stop-Loss / Take-Profit 계산
    
    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    
    "손절선"을 정할 때, 변동성이 큰 주식은 넓게, 작은 주식은 좁게 잡아야 합니다.
    
    예: ATR이 0.5달러인 주식을 5달러에 샀다면
        - Stop-Loss = 5 - (0.5 × 2) = 4달러 (2ATR 하락 시 청산)
        - Take-Profit = 5 + (0.5 × 4) = 7달러 (4ATR 상승 시 수익 실현)
    """
    
    @staticmethod
    def calculate_stop_loss(
        entry_price: float,
        atr: float,
        multiplier: float = 2.0,
    ) -> float:
        """
        Stop-Loss 가격 계산
        
        Args:
            entry_price: 진입 가격
            atr: ATR 값
            multiplier: ATR 배수 (기본 2.0 = 2 ATR)
        
        Returns:
            float: Stop-Loss 가격
        """
        if atr <= 0:
            # ATR이 없으면 기본 5% 손절
            return entry_price * 0.95
        
        return entry_price - (atr * multiplier)
    
    @staticmethod
    def calculate_take_profit(
        entry_price: float,
        atr: float,
        multiplier: float = 4.0,
    ) -> float:
        """
        Take-Profit 가격 계산
        
        Args:
            entry_price: 진입 가격
            atr: ATR 값
            multiplier: ATR 배수 (기본 4.0 = 4 ATR = 2R)
        
        Returns:
            float: Take-Profit 가격
        """
        if atr <= 0:
            return entry_price * 1.10  # 기본 10% 익절
        
        return entry_price + (atr * multiplier)
    
    @staticmethod
    def calculate_levels(
        entry_price: float,
        atr: float,
        sl_multiplier: float = 2.0,
        risk_reward_1: float = 1.0,
        risk_reward_2: float = 2.0,
        risk_reward_3: float = 3.0,
    ) -> StopLossLevels:
        """
        전체 SL/TP 레벨 계산
        
        ═══════════════════════════════════════════════════════════════
        masterplan.md 5.2절 기준
        ═══════════════════════════════════════════════════════════════
        
        Args:
            entry_price: 진입 가격
            atr: ATR 값
            sl_multiplier: SL ATR 배수 (기본 2.0)
            risk_reward_1/2/3: R:R 비율
        
        Returns:
            StopLossLevels: SL/TP 레벨 구조체
        
        Example:
            >>> levels = DynamicStopLoss.calculate_levels(10.0, 0.5, 2.0)
            >>> print(f"SL: {levels.stop_loss}, TP1: {levels.take_profit_1}")
            SL: 9.0, TP1: 11.0
        """
        if atr <= 0:
            atr = entry_price * 0.025  # 기본 2.5%
        
        risk_amount = atr * sl_multiplier
        
        return StopLossLevels(
            entry_price=entry_price,
            stop_loss=entry_price - risk_amount,
            take_profit_1=entry_price + (risk_amount * risk_reward_1),
            take_profit_2=entry_price + (risk_amount * risk_reward_2),
            take_profit_3=entry_price + (risk_amount * risk_reward_3),
            risk_amount=risk_amount,
        )


# ═══════════════════════════════════════════════════════════════════════════
# 편의 함수
# ═══════════════════════════════════════════════════════════════════════════

def calculate_all_indicators(
    highs: PriceList,
    lows: PriceList,
    closes: PriceList,
    volumes: VolumeList,
    current_price: float,
) -> dict:
    """
    모든 주요 지표를 한 번에 계산
    
    Args:
        highs, lows, closes, volumes: OHLCV 데이터
        current_price: 현재가
    
    Returns:
        dict: 모든 지표 값
    """
    vwap = TechnicalAnalysis.calculate_vwap(closes, volumes, highs, lows)
    atr = TechnicalAnalysis.calculate_atr(highs, lows, closes)
    sma_20 = TechnicalAnalysis.calculate_sma(closes, 20)
    ema_9 = TechnicalAnalysis.calculate_ema(closes, 9)
    rsi = TechnicalAnalysis.calculate_rsi(closes)
    
    levels = DynamicStopLoss.calculate_levels(current_price, atr)
    
    return {
        "vwap": vwap,
        "atr": atr,
        "sma_20": sma_20,
        "ema_9": ema_9,
        "rsi": rsi,
        "stop_loss": levels.stop_loss,
        "take_profit_1": levels.take_profit_1,
        "take_profit_2": levels.take_profit_2,
        "take_profit_3": levels.take_profit_3,
        "risk_amount": levels.risk_amount,
        "above_vwap": current_price > vwap,
        "above_sma": current_price > sma_20,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 테스트
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """독립 실행 테스트"""
    import sys
    
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")
    
    # 테스트 데이터
    prices = [10.0, 10.5, 11.0, 10.8, 11.2, 11.5, 11.3, 11.8, 12.0, 12.5]
    volumes = [1000, 1500, 2000, 1200, 1800, 2500, 1100, 2200, 1900, 2100]
    highs = [p + 0.3 for p in prices]
    lows = [p - 0.2 for p in prices]
    
    print("\n" + "=" * 60)
    print("📊 Technical Analysis Test")
    print("=" * 60)
    
    # VWAP
    vwap = TechnicalAnalysis.calculate_vwap(prices, volumes, highs, lows)
    print(f"\n✅ VWAP: ${vwap:.2f}")
    
    # ATR
    atr = TechnicalAnalysis.calculate_atr(highs, lows, prices)
    print(f"✅ ATR: ${atr:.4f}")
    
    # SMA/EMA
    sma = TechnicalAnalysis.calculate_sma(prices, 5)
    ema = TechnicalAnalysis.calculate_ema(prices, 5)
    print(f"✅ SMA(5): ${sma:.2f}")
    print(f"✅ EMA(5): ${ema:.2f}")
    
    # RSI
    rsi = TechnicalAnalysis.calculate_rsi(prices)
    print(f"✅ RSI: {rsi:.1f}")
    
    # Stop-Loss Levels
    current = 12.5
    levels = DynamicStopLoss.calculate_levels(current, atr)
    print(f"\n─────────────────────────────────")
    print(f"📍 Entry: ${levels.entry_price:.2f}")
    print(f"🛑 Stop-Loss: ${levels.stop_loss:.2f}")
    print(f"🎯 TP1 (1R): ${levels.take_profit_1:.2f}")
    print(f"🎯 TP2 (2R): ${levels.take_profit_2:.2f}")
    print(f"🎯 TP3 (3R): ${levels.take_profit_3:.2f}")
    print(f"💰 Risk: ${levels.risk_amount:.2f}")
    
    # All indicators
    print(f"\n─────────────────────────────────")
    all_ind = calculate_all_indicators(highs, lows, prices, volumes, current)
    print(f"📈 All Indicators: {all_ind}")
