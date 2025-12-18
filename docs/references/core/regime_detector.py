"""
============================================
레짐 판단 로직 (Regime Detector)
============================================
VIX Z-Score, KER, ADX를 사용하여 시장 레짐을 판단합니다.

레짐 종류:
- GREEN: 평균회귀 (저변동성, 횡보)
- RED: 추세 추종 (골디락스 - 적당한 변동성 + 강한 추세)
- BLACK: 위험 회피 (고변동성, 패닉)
============================================
"""

# ============================================
# 필수 라이브러리 임포트
# ============================================
from typing import Optional, List

import numpy as np
import pandas as pd
import pandas_ta as ta
from PyQt6.QtCore import QObject, pyqtSignal


class RegimeDetector(QObject):
    """
    시장 레짐 판단기
    
    VIX Z-Score, KER(효율비), ADX(추세강도)를 조합하여
    현재 시장이 어떤 레짐인지 판단합니다.
    
    Signals:
        regime_changed(str): 레짐 변경 시 (GREEN/RED/BLACK)
        log_message(str): 로그 메시지
    """
    
    # === PyQt Signals ===
    regime_changed = pyqtSignal(str)    # 레짐 변경
    log_message = pyqtSignal(str)       # 로그 메시지
    
    # === 임계값 (.env에서 로드 가능) ===
    Z_THRESHOLD_BLACK = 2.0     # BLACK 모드 임계값
    Z_THRESHOLD_RED = 1.0       # RED 모드 임계값
    KER_THRESHOLD = 0.3         # 골디락스 KER 임계값
    ADX_THRESHOLD = 25          # 골디락스 ADX 임계값
    
    def __init__(self, parent=None) -> None:
        """초기화"""
        super().__init__(parent)
        self._current_regime: str = "횡보"  # 기본값 (저변동성)
    
    # ============================================
    # KER (Kaufman's Efficiency Ratio) 계산
    # ============================================
    
    def calculate_ker(self, prices: List[float], period: int = 20) -> float:
        """
        KER (효율비) 계산
        
        KER = |총 가격 변화| / 총 변화량 합
        - 1에 가까울수록: 강한 추세 (효율적)
        - 0에 가까울수록: 횡보 (비효율적)
        
        Args:
            prices: 종가 리스트
            period: 계산 기간 (기본 20일)
            
        Returns:
            KER 값 (0~1)
        """
        if len(prices) < period:
            return 0.0
        
        # 최근 period 기간만 사용
        recent_prices = prices[-period:]
        
        # 총 가격 변화 (시작 → 끝)
        total_change = abs(recent_prices[-1] - recent_prices[0])
        
        # 총 변화량 합 (일별 변화의 절대값 합)
        daily_changes = [abs(recent_prices[i] - recent_prices[i-1]) 
                        for i in range(1, len(recent_prices))]
        total_volatility = sum(daily_changes)
        
        # KER 계산 (0으로 나누기 방지)
        if total_volatility == 0:
            return 0.0
        
        ker = total_change / total_volatility
        
        return round(ker, 4)
    
    # ============================================
    # ADX (Average Directional Index) 계산
    # ============================================
    
    def calculate_adx(self, high: List[float], low: List[float], 
                     close: List[float], period: int = 14) -> float:
        """
        ADX (평균 방향성 지수) 계산
        
        - ADX > 25: 강한 추세
        - ADX < 20: 약한 추세 (횡보)
        
        Args:
            high: 고가 리스트
            low: 저가 리스트
            close: 종가 리스트
            period: 계산 기간 (기본 14일)
            
        Returns:
            ADX 값
        """
        try:
            # pandas DataFrame으로 변환
            df = pd.DataFrame({
                "high": high,
                "low": low,
                "close": close
            })
            
            # pandas-ta로 ADX 계산
            adx_result = ta.adx(df["high"], df["low"], df["close"], length=period)
            
            if adx_result is None or adx_result.empty:
                return 0.0
            
            # ADX 값 반환 (마지막 값)
            adx_col = f"ADX_{period}"
            if adx_col in adx_result.columns:
                adx_value = adx_result[adx_col].iloc[-1]
                return round(float(adx_value), 2) if not pd.isna(adx_value) else 0.0
            
            return 0.0
            
        except Exception as e:
            self.log_message.emit(f"⚠️ ADX 계산 오류: {str(e)}")
            return 0.0
    
    # ============================================
    # 골디락스 존 판단
    # ============================================
    
    def is_goldilocks(self, ker: float, adx: float) -> bool:
        """
        골디락스 존 판단
        
        골디락스 = 효율적인 추세 + 강한 방향성
        → Red Mode(추세 추종) 적합
        
        Args:
            ker: 효율비 (0~1)
            adx: 추세 강도
            
        Returns:
            골디락스 여부
        """
        return ker > self.KER_THRESHOLD and adx > self.ADX_THRESHOLD
    
    # ============================================
    # 최종 레짐 판단
    # ============================================
    
    def get_regime(self, z_score: float, ker: float, adx: float) -> str:
        """
        시장 레짐 판단
        
        판단 우선순위:
        1. BLACK: Z-Score ≥ 2.0 (공포 상태)
        2. RED: Z-Score ≥ 1.0 AND 골디락스 (추세 추종 적합)
        3. GREEN: 그 외 (평균 회귀 적합)
        
        Args:
            z_score: VIX Z-Score
            ker: 효율비
            adx: 추세 강도
            
        Returns:
            "위기", "상승", 또는 "횡보"
        """
        # 1. 위기 모드 (공포)
        if z_score >= self.Z_THRESHOLD_BLACK:
            regime = "위기"
            self.log_message.emit(f"🔴 위기 모드: Z-Score {z_score:.2f} ≥ {self.Z_THRESHOLD_BLACK}")
        
        # 2. 상승 모드 (추세 추종)
        elif z_score >= self.Z_THRESHOLD_RED and self.is_goldilocks(ker, adx):
            regime = "상승"
            self.log_message.emit(f"🔵 상승 모드: Z-Score {z_score:.2f}, KER {ker:.2f}, ADX {adx:.2f}")
        
        # 3. 횡보 모드 (평균 회귀)
        else:
            regime = "횡보"
            self.log_message.emit(f"🟡 횡보 모드: Z-Score {z_score:.2f}")
        
        # 레짐 변경 알림
        if regime != self._current_regime:
            self._current_regime = regime
            self.regime_changed.emit(regime)
        
        return regime
    
    def get_current_regime(self) -> str:
        """현재 레짐 반환"""
        return self._current_regime


# ============================================
# 단위 테스트
# ============================================
if __name__ == "__main__":
    print("=" * 50)
    print("레짐 판단 로직 테스트")
    print("=" * 50)
    
    detector = RegimeDetector()
    detector.log_message.connect(lambda x: print(f"[LOG] {x}"))
    
    # 테스트 케이스
    test_cases = [
        # (z_score, ker, adx, expected)
        (2.5, 0.4, 30, "위기"),   # 공포 상태
        (1.5, 0.4, 30, "상승"),   # 골디락스 + 경계
        (1.5, 0.2, 30, "횡보"),   # 비효율적 (KER 낮음)
        (0.5, 0.4, 30, "횡보"),   # 평온한 시장
        (1.2, 0.35, 20, "횡보"),  # ADX 낮음 → 골디락스 아님
    ]
    
    print("\n📋 테스트 케이스 실행:")
    all_passed = True
    
    for z, ker, adx, expected in test_cases:
        result = detector.get_regime(z, ker, adx)
        passed = result == expected
        status = "✅" if passed else "❌"
        print(f"  {status} get_regime({z}, {ker}, {adx}) = {result} (예상: {expected})")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ 모든 테스트 통과!")
    else:
        print("❌ 일부 테스트 실패")
    
    # KER 테스트
    print("\n📊 KER 테스트:")
    prices_trend = [100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120]
    prices_sideways = [100, 102, 99, 101, 100, 103, 98, 102, 99, 101, 100]
    
    ker_trend = detector.calculate_ker(prices_trend, period=10)
    ker_sideways = detector.calculate_ker(prices_sideways, period=10)
    
    print(f"  추세 시장 KER: {ker_trend:.4f} (1에 가까움)")
    print(f"  횡보 시장 KER: {ker_sideways:.4f} (0에 가까움)")
