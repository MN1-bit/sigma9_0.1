# ============================================================================
# Z-Score Calculator Module
# ============================================================================
# 📌 이 파일의 역할:
#   - zenV (Volume Z-Score) 및 zenP (Price Z-Score) 계산
#   - Tier 2 Hot Zone 매집 패턴 탐지용
#
# 📊 Z-Score 공식:
#   Z = (X - μ) / σ
#   - X: 현재 값
#   - μ: 평균 (20일 기준)
#   - σ: 표준편차 (20일 기준)
#
# 📖 사용 예시:
#   >>> calc = ZScoreCalculator()
#   >>> result = calc.calculate("AAPL", daily_bars)
#   >>> print(f"zenV={result.zenV}, zenP={result.zenP}")
# ============================================================================

from dataclasses import dataclass
from typing import Optional

import numpy as np
from loguru import logger


# ═══════════════════════════════════════════════════════════════════════════
# 데이터클래스
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ZScoreResult:
    """
    Z-Score 계산 결과
    
    Attributes:
        zenV: Volume Z-Score (당일 거래량이 평균 대비 몇 표준편차인지)
        zenP: Price Z-Score (당일 가격 변동이 평균 대비 몇 표준편차인지)
    
    해석:
        - > 2.0: 비정상적으로 높음 🔥
        - > 1.0: 평균 이상
        - < -1.0: 평균 이하
        
        매집 신호: zenV > 2.0 AND zenP < 1.0 (높은 거래량, 낮은 가격 변동)
    """
    zenV: float  # Volume Z-Score
    zenP: float  # Price Z-Score


@dataclass
class DailyStats:
    """
    장중 Time-Projection 계산용 일별 통계 캐시
    
    Attributes:
        avg_volume: 과거 N일 평균 거래량
        std_volume: 과거 N일 거래량 표준편차
        avg_change: 과거 N일 평균 가격 변동률
        std_change: 과거 N일 가격 변동률 표준편차
    """
    avg_volume: float
    std_volume: float
    avg_change: float
    std_change: float


# ═══════════════════════════════════════════════════════════════════════════
# ZScoreCalculator 클래스
# ═══════════════════════════════════════════════════════════════════════════

class ZScoreCalculator:
    """
    Z-Score 계산기
    
    20일 일봉 데이터를 기반으로 Volume과 Price Change의 Z-Score를 계산합니다.
    
    Attributes:
        lookback: Z-Score 계산에 사용할 기간 (기본값: 20일)
    
    Example:
        >>> calculator = ZScoreCalculator(lookback=20)
        >>> daily_bars = [
        ...     {"date": "2025-12-01", "open": 100, "high": 102, "low": 99, "close": 101, "volume": 1000000},
        ...     # ... 20일치 데이터
        ... ]
        >>> result = calculator.calculate("AAPL", daily_bars)
        >>> print(f"zenV={result.zenV:.2f}, zenP={result.zenP:.2f}")
    """
    
    def __init__(self, lookback: int = 20):
        """
        ZScoreCalculator 초기화
        
        Args:
            lookback: Z-Score 계산에 사용할 기간 (기본값: 20일)
        """
        self.lookback = lookback
        self._cache: dict[str, DailyStats] = {}  # ticker -> DailyStats 캐시
        logger.debug(f"📊 ZScoreCalculator 초기화: lookback={lookback}")
    
    def calculate(self, ticker: str, daily_bars: list[dict]) -> ZScoreResult:
        """
        20일 일봉 데이터로 Z-Score 계산
        
        Args:
            ticker: 종목 코드 (로깅용)
            daily_bars: 일봉 데이터 리스트 (오래된 순 -> 최신순)
                각 딕셔너리는 다음 키를 가집니다:
                - date: 날짜
                - open, high, low, close: 가격
                - volume: 거래량
        
        Returns:
            ZScoreResult: zenV와 zenP를 담은 결과 객체
            
        Note:
            - 데이터가 lookback 기간보다 짧으면 zenV=0, zenP=0 반환
            - 표준편차가 0이면 해당 Z-Score는 0 반환
        """
        # ─────────────────────────────────────────────────────────────────
        # 데이터 검증
        # ─────────────────────────────────────────────────────────────────
        if not daily_bars or len(daily_bars) < self.lookback:
            logger.warning(f"⚠️ {ticker}: 데이터 부족 ({len(daily_bars) if daily_bars else 0}일 < {self.lookback}일)")
            return ZScoreResult(zenV=0.0, zenP=0.0)
        
        # lookback 기간의 데이터만 사용
        recent = daily_bars[-self.lookback:]
        
        # ─────────────────────────────────────────────────────────────────
        # zenV (Volume Z-Score) 계산
        # - 오늘 거래량이 어제까지의 평균 대비 몇 표준편차인지
        # ─────────────────────────────────────────────────────────────────
        try:
            volumes = [bar.get("volume", 0) for bar in recent]
            # 어제까지의 평균과 표준편차 (오늘 제외)
            historical_volumes = volumes[:-1]
            avg_vol = float(np.mean(historical_volumes))
            std_vol = float(np.std(historical_volumes, ddof=0))  # population std
            
            today_vol = volumes[-1]
            
            if std_vol > 0:
                zenV = (today_vol - avg_vol) / std_vol
            else:
                zenV = 0.0
                
        except (ValueError, TypeError) as e:
            logger.warning(f"⚠️ {ticker}: zenV 계산 실패 - {e}")
            zenV = 0.0
        
        # ─────────────────────────────────────────────────────────────────
        # zenP (Price Z-Score) 계산
        # - 오늘 가격 변동(abs % change)이 어제까지 평균 대비 몇 표준편차인지
        # ─────────────────────────────────────────────────────────────────
        try:
            # 일간 변동률 계산 (절대값)
            changes = []
            for i in range(1, len(recent)):
                prev_close = recent[i - 1].get("close", 0)
                curr_close = recent[i].get("close", 0)
                
                if prev_close > 0:
                    pct_change = abs((curr_close - prev_close) / prev_close * 100)
                    changes.append(pct_change)
            
            if len(changes) < 2:
                zenP = 0.0
            else:
                # 어제까지의 변동률 평균과 표준편차 (오늘 제외)
                historical_changes = changes[:-1]
                avg_chg = float(np.mean(historical_changes))
                std_chg = float(np.std(historical_changes, ddof=0))  # population std
                
                today_chg = changes[-1] if changes else 0.0
                
                if std_chg > 0:
                    zenP = (today_chg - avg_chg) / std_chg
                else:
                    zenP = 0.0
                    
        except (ValueError, TypeError) as e:
            logger.warning(f"⚠️ {ticker}: zenP 계산 실패 - {e}")
            zenP = 0.0
        
        # ─────────────────────────────────────────────────────────────────
        # 결과 반환 (소수점 2자리까지)
        # ─────────────────────────────────────────────────────────────────
        result = ZScoreResult(
            zenV=round(zenV, 2),
            zenP=round(zenP, 2)
        )
        
        logger.debug(f"📊 {ticker} Z-Score: zenV={result.zenV}, zenP={result.zenP}")
        return result
    
    def calculate_batch(self, tickers_data: dict[str, list[dict]]) -> dict[str, ZScoreResult]:
        """
        여러 종목의 Z-Score 일괄 계산
        
        Args:
            tickers_data: {ticker: daily_bars} 형식의 딕셔너리
        
        Returns:
            dict[str, ZScoreResult]: {ticker: ZScoreResult} 형식의 결과
        """
        results = {}
        for ticker, bars in tickers_data.items():
            results[ticker] = self.calculate(ticker, bars)
        
        logger.info(f"📊 Z-Score 일괄 계산 완료: {len(results)}개 종목")
        return results
    
    # ─────────────────────────────────────────────────────────────────────────
    # 장중 실시간 Time-Projected Z-Score
    # ─────────────────────────────────────────────────────────────────────────
    
    def build_cache(self, ticker: str, daily_bars: list[dict]) -> Optional[DailyStats]:
        """
        장 시작 전 일별 통계 캐시 빌드
        
        Args:
            ticker: 종목 코드
            daily_bars: 최근 N일 일봉 데이터 (오래된 순)
        
        Returns:
            DailyStats 또는 None (데이터 부족시)
        """
        if not daily_bars or len(daily_bars) < self.lookback:
            logger.warning(f"⚠️ {ticker}: 캐시 빌드 실패 (데이터 부족)")
            return None
        
        recent = daily_bars[-self.lookback:]
        
        # Volume 통계
        volumes = [bar.get("volume", 0) for bar in recent]
        avg_volume = float(np.mean(volumes))
        std_volume = float(np.std(volumes, ddof=0))
        
        # Price Change 통계
        changes = []
        for i in range(1, len(recent)):
            prev_close = recent[i - 1].get("close", 0)
            curr_close = recent[i].get("close", 0)
            if prev_close > 0:
                pct_change = abs((curr_close - prev_close) / prev_close * 100)
                changes.append(pct_change)
        
        avg_change = float(np.mean(changes)) if changes else 0.0
        std_change = float(np.std(changes, ddof=0)) if changes else 0.0
        
        stats = DailyStats(
            avg_volume=avg_volume,
            std_volume=std_volume,
            avg_change=avg_change,
            std_change=std_change
        )
        
        self._cache[ticker] = stats
        logger.debug(f"📊 {ticker} 캐시 빌드: avg_vol={avg_volume:,.0f}, std_vol={std_volume:,.0f}")
        return stats
    
    def calculate_projected_zenV(
        self, 
        ticker: str, 
        current_volume: int, 
        elapsed_ratio: float
    ) -> float:
        """
        장중 시간 보정 zenV 계산 (Time-Projected)
        
        Args:
            ticker: 종목 코드
            current_volume: 오늘 현재까지 누적 거래량
            elapsed_ratio: 장 경과 비율 (0.0 = 장시작, 1.0 = 장마감)
        
        Returns:
            Time-Projected zenV
        
        Example:
            오전 10시 (경과 8%), 거래량 200만주, 평균 일거래량 1000만주
            → expected = 1000만 × 0.08 = 80만주
            → zenV = (200만 - 80만) / adjusted_std
            → 결과: 강한 양의 신호 (평소 속도의 2.5배)
        """
        stats = self._cache.get(ticker)
        if not stats or elapsed_ratio <= 0:
            return 0.0
        
        # 시간 보정 기대값 (선형 projection)
        expected = stats.avg_volume * elapsed_ratio
        
        # 표준편차도 시간에 따라 조정 (sqrt rule)
        import math
        adjusted_std = stats.std_volume * math.sqrt(elapsed_ratio)
        
        if adjusted_std <= 0:
            return 0.0
        
        return round((current_volume - expected) / adjusted_std, 2)
    
    def calculate_projected_zenP(
        self, 
        ticker: str, 
        current_change_pct: float
    ) -> float:
        """
        장중 zenP 계산 (당일 가격 변동률)
        
        Args:
            ticker: 종목 코드
            current_change_pct: 오늘 가격 변동률 (%)
        
        Returns:
            zenP (가격 변동 Z-Score)
        """
        stats = self._cache.get(ticker)
        if not stats or stats.std_change <= 0:
            return 0.0
        
        return round((abs(current_change_pct) - stats.avg_change) / stats.std_change, 2)
    
    def get_cached_stats(self, ticker: str) -> Optional[DailyStats]:
        """캐시된 통계 조회"""
        return self._cache.get(ticker)
