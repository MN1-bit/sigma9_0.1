# ============================================================================
# Seismograph Strategy - 매집 탐지 + 폭발 포착 전략
# ============================================================================
# 📌 이 파일의 역할:
#   Sigma9의 핵심 전략입니다. 두 단계로 작동합니다:
#   - Phase 1 (Scanning): 일봉 기반으로 "매집 중인 종목" 탐지 → Watchlist 생성
#   - Phase 2 (Trigger): 실시간 틱 기반으로 "폭발 순간" 포착 → 진입 신호
#
# 📌 masterplan.md Section 3, 4 기준 구현
# 📌 development_steps.md Step 2.2, 2.3 기준
# ============================================================================

"""
Seismograph Strategy Module

미국 마이크로캡 주식에서 세력의 매집(Accumulation)을 사전 탐지하고,
폭발 순간(Ignition)을 포착하는 2단계 전략입니다.

Phase 1 (Scanning - 이 파일):
    - 일봉 데이터 기반 매집 징후 점수화
    - Accumulation Score ≥ 60점 종목 50개 선정
    
Phase 2 (Trigger - Step 2.3에서 구현):
    - 실시간 틱 기반 폭발 감지
    - Ignition Score ≥ 70점 시 진입 신호

Example:
    >>> from backend.strategies.seismograph import SeismographStrategy
    >>> strategy = SeismographStrategy()
    >>> score = strategy.calculate_watchlist_score("AAPL", daily_data)
    >>> print(f"Accumulation Score: {score}")
"""

import sys
from pathlib import Path
from typing import Any, Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time as dt_time
from collections import deque
import numpy as np

# backend 폴더를 경로에 추가 (상대 import 호환성)
backend_path = Path(__file__).parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from core.strategy_base import StrategyBase, Signal
from core.technical_analysis import TechnicalAnalysis, DynamicStopLoss

# V3 설정 임포트
from strategies.score_v3_config import (
    V3_WEIGHTS, ZSCORE_SIGMOID, SUPPORT_CONFIG, ACCUMBAR_CONFIG, SIGNAL_MODIFIER_CONFIG,
    PERCENTILE_CONFIG, REDUNDANCY_PENALTY_CONFIG
)


# ═══════════════════════════════════════════════════════════════════════════
# 틱 데이터 구조체
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class TickData:
    """
    실시간 틱 데이터 구조체
    
    틱 버퍼에 저장되어 Ignition Score 계산에 사용됩니다.
    
    Attributes:
        price: 체결 가격
        volume: 체결 수량
        timestamp: 체결 시간
        side: 체결 방향 ("B" = 매수, "S" = 매도)
    """
    price: float
    volume: int
    timestamp: datetime
    side: str = "B"  # "B" (buy) or "S" (sell)


@dataclass
class WatchlistItem:
    """
    Watchlist 항목 구조체 - 개별 신호 메타데이터 포함
    
    ═══════════════════════════════════════════════════════════════════════
    Step 2.2.5: Trading Restrictions 지원
    ═══════════════════════════════════════════════════════════════════════
    
    Stage 1-2 종목은 can_trade=False (Monitoring Only)
    Stage 3-4 종목만 can_trade=True (트레이딩 허용)
    
    Attributes:
        ticker: 종목 코드 (예: "AAPL")
        score: Accumulation Score (0~100)
        stage: Stage 문자열 (예: "Stage 4 (Tight Range)")
        stage_number: Stage 번호 (1~4) - Trading Restrictions용
        signals: 개별 신호 탐지 결과 dict
        can_trade: 트레이딩 가능 여부 (Stage 3-4만 True)
        last_close: 최근 종가
        avg_volume: 평균 거래량
        scan_timestamp: 스캔 시각
    
    Example:
        >>> item = WatchlistItem(
        ...     ticker="AAPL",
        ...     score=80.0,
        ...     stage="Stage 4 (Tight Range)",
        ...     stage_number=4,
        ...     signals={"tight_range": True, "obv_divergence": False, ...},
        ...     can_trade=True,
        ...     last_close=5.50,
        ...     avg_volume=150000,
        ... )
    """
    ticker: str
    score: float
    stage: str
    stage_number: int  # 1~4 (Trading Restrictions용)
    signals: Dict[str, bool]  # 개별 신호 탐지 결과
    can_trade: bool  # Stage 3-4만 True
    last_close: float = 0.0
    avg_volume: float = 0.0
    scan_timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """dict로 변환 (JSON 직렬화용)"""
        return {
            "ticker": self.ticker,
            "score": self.score,
            "stage": self.stage,
            "stage_number": self.stage_number,
            "signals": self.signals,
            "can_trade": self.can_trade,
            "last_close": self.last_close,
            "avg_volume": self.avg_volume,
            "scan_timestamp": self.scan_timestamp.isoformat() if self.scan_timestamp else None,
        }

# ═══════════════════════════════════════════════════════════════════════════
# SeismographStrategy 클래스
# ═══════════════════════════════════════════════════════════════════════════

class SeismographStrategy(StrategyBase):
    """
    Seismograph (지진계) 전략
    
    세력의 매집을 탐지하는 것이 마치 지진 전 미세한 진동을 감지하는 것과 같아서
    "Seismograph"라는 이름이 붙었습니다.
    
    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    큰 지진(주가 급등) 전에는 미세한 진동(매집 신호)이 있습니다.
    이 전략은 그 진동을 감지해서 "곧 폭발할 종목"을 미리 찾아냅니다.
    
    1. Phase 1 (매일 아침):
       - 모든 종목을 스캔해서 "매집 점수" 계산
       - 점수 높은 50개를 Watchlist에 추가
    
    2. Phase 2 (장중 실시간):
       - Watchlist 종목들을 실시간 감시
       - "폭발 순간" 포착되면 매수 신호
    
    ═══════════════════════════════════════════════════════════════════════
    Accumulation Score (매집 점수) 구성:
    ═══════════════════════════════════════════════════════════════════════
    
    | 신호 | Weight | 설명 |
    |------|--------|------|
    | 매집봉 | 30% | 가격 변동 작고 거래량 큼 |
    | OBV Divergence | 40% | 주가 하락인데 OBV 상승 |
    | Volume Dry-out | 20% | 거래량 급감 (폭풍 전 고요) |
    | Tight Range | 10% | 변동폭 축소 (VCP 패턴) |
    """
    
    # ═══════════════════════════════════════════════════════════════════
    # 클래스 속성 (메타정보)
    # ═══════════════════════════════════════════════════════════════════
    
    name = "Seismograph"
    version = "1.0.0"
    description = "매집 탐지 + 폭발 포착 2단계 전략 (Sigma9 Core)"
    
    def __init__(self) -> None:
        """
        전략 초기화
        
        설정 파라미터를 초기화합니다.
        각 파라미터는 value(현재값), min(최소), max(최대), description(설명)을 가집니다.
        GUI에서 이 값들을 표시하고 사용자가 조정할 수 있습니다.
        """
        # === Scanning 파라미터 (Phase 1) ===
        self.config: Dict[str, Dict[str, Any]] = {
            # 매집 점수 기준 (이 점수 이상이면 Watchlist 후보)
            "accumulation_threshold": {
                "value": 60,
                "min": 40,
                "max": 80,
                "description": "Watchlist 진입 기준 점수 (0~100)"
            },
            # 매집봉 거래량 배수 (평균의 X배 이상)
            "spike_volume_multiplier": {
                "value": 3.0,
                "min": 2.0,
                "max": 5.0,
                "description": "매집봉 인식 거래량 배수"
            },
            # OBV 기울기 계산 기간
            "obv_lookback": {
                "value": 20,
                "min": 10,
                "max": 30,
                "description": "OBV 다이버전스 관찰 기간 (일)"
            },
            # 거래량 마름(Dry-out) 기준
            "dryout_threshold": {
                "value": 0.4,
                "min": 0.3,
                "max": 0.6,
                "description": "거래량 마름 기준 (평균 대비 비율)"
            },
            # ATR 축소 비율 (VCP)
            "atr_ratio_threshold": {
                "value": 0.5,
                "min": 0.3,
                "max": 0.7,
                "description": "Tight Range 인식 ATR 비율"
            },
        }
        
        # === Trigger 파라미터 (Phase 2) ===
        self.config.update({
            "ignition_threshold": {
                "value": 70,
                "min": 50,
                "max": 90,
                "description": "진입 신호 기준 점수 (0~100)"
            },
            "tick_velocity_multiplier": {
                "value": 8.0,
                "min": 4.0,
                "max": 15.0,
                "description": "틱 속도 인식 배수 (10초 체결 vs 1분 평균)"
            },
            "volume_burst_multiplier": {
                "value": 6.0,
                "min": 3.0,
                "max": 12.0,
                "description": "거래량 폭발 인식 배수 (1분 vs 5분 평균)"
            },
            "price_break_pct": {
                "value": 0.5,
                "min": 0.3,
                "max": 1.0,
                "description": "박스권 돌파 인식 퍼센트 (%)"
            },
            "buy_pressure_ratio": {
                "value": 1.8,
                "min": 1.5,
                "max": 2.5,
                "description": "매수 압력 비율 (매수/매도)"
            },
            # Anti-Trap 필터 파라미터
            "max_spread_pct": {
                "value": 1.0,
                "min": 0.5,
                "max": 2.0,
                "description": "최대 허용 스프레드 (%)"
            },
            "min_minutes_after_open": {
                "value": 15,
                "min": 5,
                "max": 30,
                "description": "개장 후 최소 경과 시간 (분)"
            },
        })
        
        # === 내부 상태 (Phase 1) ===
        self._watchlist: List[str] = []  # 현재 감시 중인 종목 리스트
        
        # Step 2.3.4: Watchlist Context - Stage 정보 + Trading Restrictions
        # key: ticker, value: {"stage_number": int, "can_trade": bool, "signals": dict, ...}
        self._watchlist_context: Dict[str, Dict[str, Any]] = {}
        
        # === 내부 상태 (Phase 2 - Trigger) ===
        # 종목별 틱 버퍼 (최근 60초 분량)
        self._tick_buffer: Dict[str, deque] = {}
        # 종목별 1분봉 버퍼 (최근 5분)
        self._bar_1m: Dict[str, List[Dict]] = {}
        # 종목별 당일 VWAP
        self._vwap: Dict[str, float] = {}
        # 종목별 박스권 (고점, 저점)
        self._box_range: Dict[str, Tuple[float, float]] = {}
        # 미국 동부시간 장 시작 시간 (09:30 ET)
        self._market_open_time = dt_time(9, 30)
    
    # ═══════════════════════════════════════════════════════════════════
    # Scanning Layer (Phase 1)
    # ═══════════════════════════════════════════════════════════════════
    
    def get_universe_filter(self) -> dict:
        """
        Universe 필터 조건 반환
        
        전체 종목 중에서 관심 대상을 좁히는 첫 번째 필터입니다.
        마이크로캡 종목 중 아직 급등하지 않은 종목만 선택합니다.
        
        Returns:
            dict: 필터 조건
            
        Note:
            masterplan.md 3.1절 기준
        """
        return {
            # 가격 필터: $2 ~ $10 (폭발력 최대 구간)
            "price_min": 2.00,
            "price_max": 10.00,
            
            # 시가총액: $50M ~ $300M (마이크로캡)
            "market_cap_min": 50_000_000,    # 5천만 달러
            "market_cap_max": 300_000_000,   # 3억 달러
            
            # Float (유통주식수): 1500만주 미만 (Low Float = 급등 용이)
            "float_max": 15_000_000,
            
            # 평균 거래량: 10만주 이상 (최소 유동성)
            "avg_volume_min": 100_000,
            
            # 당일 변동률: 0% ~ 5% (아직 터지지 않은 종목)
            "change_pct_min": 0.0,
            "change_pct_max": 5.0,
        }
    
    def calculate_watchlist_score(self, ticker: str, daily_data: Any) -> float:
        """
        일봉 기반 Accumulation Score (매집 점수) 계산
        
        ═══════════════════════════════════════════════════════════════
        Stage-Based Priority System (masterplan.md 3.2절)
        ═══════════════════════════════════════════════════════════════
        
        기존 Weighted Sum 대신, 매집 단계(Stage)에 따라 우선순위 부여:
        
        | 우선순위 | 점수 | 조건 | 의미 |
        |---------|------|------|------|
        | 1순위 | 100점 | Tight Range + OBV | 🔥 폭발 임박 |
        | 2순위 |  80점 | Tight Range only | 높은 관심 |
        | 3순위 |  70점 | Accumulation Bar + OBV | 관심 대상 |
        | 4순위 |  50점 | Accumulation Bar only | 추적 중 |
        | 5순위 |  30점 | OBV Divergence only | 모니터링 |
        | 6순위 |  10점 | Volume Dry-out only | 관찰 대상 |
        
        Args:
            ticker: 종목 코드 (예: "AAPL")
            daily_data: 일봉 데이터 (pandas DataFrame 또는 dict)
                필수 컬럼: open, high, low, close, volume
        
        Returns:
            float: 0 ~ 100 사이의 점수 (Stage 기반 우선순위)
        
        Note:
            v2 가중합 계산은 calculate_watchlist_score_v2() 참조
        """
        try:
            # 데이터 유효성 검사 (최소 5일 필요, 이상적으로 20일)
            if daily_data is None or len(daily_data) < 5:
                return 0.0
            
            # === 4가지 매집 신호 탐지 ===
            # Stage 4 (폭발 임박): Tight Range / VCP
            has_tight_range = self._check_tight_range(daily_data) > 0.5
            
            # Stage 3 (매집 완료): Accumulation Bar
            has_accumulation_bar = self._check_accumulation_bar(daily_data) > 0.5
            
            # Stage 2 (매집 진행): OBV Divergence
            has_obv_divergence = self._check_obv_divergence(daily_data) > 0.5
            
            # Stage 1 (매집 준비): Volume Dry-out
            has_volume_dryout = self._check_volume_dryout(daily_data) > 0.5
            
            # === Stage-Based Priority 점수 할당 ===
            
            # 1순위: Tight Range + OBV → 🔥 폭발 임박 (즉시 진입 대기)
            if has_tight_range and has_obv_divergence:
                return 100.0
            
            # 2순위: Tight Range only → 높은 관심
            if has_tight_range:
                return 80.0
            
            # 3순위: Accumulation Bar + OBV → 관심 대상
            if has_accumulation_bar and has_obv_divergence:
                return 70.0
            
            # 4순위: Accumulation Bar only → 추적 중
            if has_accumulation_bar:
                return 50.0
            
            # 5순위: OBV Divergence only → 모니터링
            if has_obv_divergence:
                return 30.0
            
            # 6순위: Volume Dry-out only → 관찰 대상
            if has_volume_dryout:
                return 10.0
            
            # 해당 없음
            return 0.0
            
        except Exception:
            # 데이터 오류 시 0점
            return 0.0
    
    # ═══════════════════════════════════════════════════════════════════
    # v2: 연속 점수 시스템 (가중합 기반)
    # ═══════════════════════════════════════════════════════════════════
    
    # 신호별 가중치 (Masterplan 기준)
    SCORE_WEIGHTS = {
        "tight_range": 0.30,      # VCP 패턴 (30%)
        "obv_divergence": 0.35,   # 스마트 머니 (35%)
        "accumulation_bar": 0.25, # 매집 완료 (25%)
        "volume_dryout": 0.10,    # 준비 단계 (10%)
    }
    
    def calculate_watchlist_score_v2(self, ticker: str, daily_data: Any) -> float:
        """
        v2: 연속 점수 시스템 (가중합 기반)
        
        ═══════════════════════════════════════════════════════════════════
        개선된 점수 계산 (02-001_score_calculation_enhancement.md)
        ═══════════════════════════════════════════════════════════════════
        
        기존 step 함수 대신 연속적인 0~100 점수를 반환합니다.
        각 신호의 "강도(intensity)"를 계산하여 가중합으로 최종 점수 산출.
        
        수식:
            Score = 100 × Σ(w_i × I_i)
            
        where:
            w_i = 신호 가중치 (tight_range=0.30, obv=0.35, ...)
            I_i = 신호 강도 (0.0 ~ 1.0)
        
        Args:
            ticker: 종목 코드 (예: "AAPL")
            daily_data: 일봉 데이터 (pandas DataFrame 또는 list of dict)
                필수 컬럼: open, high, low, close, volume
        
        Returns:
            float: 0.0 ~ 100.0 연속 점수
        """
        try:
            if daily_data is None or len(daily_data) < 5:
                return 0.0
            
            # 각 신호의 강도 계산 (0.0 ~ 1.0)
            intensities = self._calculate_signal_intensities(daily_data)
            
            # 가중합 계산
            raw_score = sum(
                intensities.get(signal, 0.0) * weight
                for signal, weight in self.SCORE_WEIGHTS.items()
            )
            
            return round(raw_score * 100, 1)  # 0~100 스케일
            
        except Exception:
            return 0.0
    
    def _calculate_signal_intensities(self, data: Any) -> Dict[str, float]:
        """
        개별 신호 강도 계산 (0.0 ~ 1.0)
        
        Boolean 신호 대신 연속적인 강도 값을 반환합니다.
        
        Args:
            data: OHLCV 데이터
            
        Returns:
            dict: 각 신호의 강도 (0.0 ~ 1.0)
        """
        return {
            "tight_range": self._calc_tight_range_intensity(data),
            "obv_divergence": self._calc_obv_divergence_intensity(data),
            "accumulation_bar": self._calc_accumulation_bar_intensity(data),
            "volume_dryout": self._calc_volume_dryout_intensity(data),
        }
    
    def _calc_tight_range_intensity(self, data: Any) -> float:
        """
        Tight Range 강도 계산 (0.0 ~ 1.0)
        
        ATR_5 / ATR_20 비율이 낮을수록 강함
        - 비율 ≤ 30%: intensity = 1.0
        - 비율 ≥ 70%: intensity = 0.0
        - 그 사이: 선형 보간
        """
        try:
            highs = self._get_column(data, 'high', 20)
            lows = self._get_column(data, 'low', 20)
            closes = self._get_column(data, 'close', 20)
            
            if len(highs) < 20:
                return 0.0
            
            # True Range 계산
            tr_list = []
            for i in range(1, len(highs)):
                h_l = highs[i] - lows[i]
                h_pc = abs(highs[i] - closes[i - 1])
                l_pc = abs(lows[i] - closes[i - 1])
                tr_list.append(max(h_l, h_pc, l_pc))
            
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
    
    def _calc_obv_divergence_intensity(self, data: Any) -> float:
        """
        OBV Divergence 강도 계산 (0.0 ~ 1.0)
        
        가격 기울기 vs OBV 기울기 차이로 강도 계산
        - 가격 하락폭 클수록 + OBV 상승폭 클수록 = 높은 강도
        """
        try:
            lookback = self.config["obv_lookback"]["value"]
            closes = self._get_column(data, 'close', lookback)
            volumes = self._get_column(data, 'volume', lookback)
            
            if len(closes) < 5 or len(volumes) < 5:
                return 0.0
            
            # OBV 계산
            obv = [0.0]
            for i in range(1, len(closes)):
                if closes[i] > closes[i - 1]:
                    obv.append(obv[-1] + volumes[i])
                elif closes[i] < closes[i - 1]:
                    obv.append(obv[-1] - volumes[i])
                else:
                    obv.append(obv[-1])
            
            # 정규화된 기울기 계산
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
            
            # 강도: 가격 하락폭(-price_change_pct)과 OBV 상승폭을 곱함
            # 최대값 클램핑
            divergence_strength = min(1.0, abs(price_change_pct) * 10 + obv_change_ratio * 5)
            return round(divergence_strength, 2)
            
        except Exception:
            return 0.0
    
    def _calc_accumulation_bar_intensity(self, data: Any) -> float:
        """
        Accumulation Bar 강도 계산 (0.0 ~ 1.0)
        
        Volume Spike 배수로 강도 계산
        - 2x → 0.0
        - 3x → 0.33
        - 5x → 1.0
        """
        try:
            latest = data.iloc[-1] if hasattr(data, 'iloc') else data[-1]
            
            open_price = float(latest.get('open', latest.get('Open', 0)))
            close_price = float(latest.get('close', latest.get('Close', 0)))
            
            if open_price == 0:
                return 0.0
            
            price_change = abs(close_price - open_price) / open_price
            
            # 가격 변동이 크면 매집봉 아님
            if price_change > 0.025:
                return 0.0
            
            volumes = self._get_column(data, 'volume', 20)
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
    
    def _calc_volume_dryout_intensity(self, data: Any) -> float:
        """
        Volume Dry-out 강도 계산 (0.0 ~ 1.0)
        
        최근 3일 vs 20일 평균 비율로 강도 계산
        - 40% → 0.0 (threshold)
        - 20% → 0.5
        - 0%  → 1.0
        """
        try:
            volumes = self._get_column(data, 'volume', 20)
            
            if len(volumes) < 5:
                return 0.0
            
            avg_20d = np.mean(volumes)
            avg_3d = np.mean(volumes[-3:])
            
            if avg_20d <= 0:
                return 0.0
            
            ratio = avg_3d / avg_20d
            threshold = self.config["dryout_threshold"]["value"]
            
            # threshold(0.4) 이상 → 0, 0 → 1.0
            if ratio >= threshold:
                return 0.0
            
            intensity = 1.0 - (ratio / threshold)
            return round(intensity, 2)
            
        except Exception:
            return 0.0

    # ═══════════════════════════════════════════════════════════════════
    # v3: Pinpoint Algorithm (Z-Score + Boost × Penalty)
    # ═══════════════════════════════════════════════════════════════════
    
    def calculate_watchlist_score_v3(
        self, 
        ticker: str, 
        daily_data: Any,
        current_vwap: Optional[float] = None
    ) -> float:
        """
        v3.2: Pinpoint Algorithm (V3.2 개선)
        
        수식: Score = clip(Base + Harmony Bonus, 0, 100)
        
        V3.2 변경사항:
        - 곱셈 부스트 → 가산 보너스 (스케일 보존)
        - 0~100 클리핑 적용 (스케일 붕괴 방지)
        - Support 이탈 연속 페널티
        
        Args:
            ticker: 종목 코드
            daily_data: 일봉 데이터 (60일 권장)
            current_vwap: Massive API에서 수신한 VWAP (선택)
        
        Returns:
            float: 0.0 ~ 100.0 점수 (V3.2: 클리핑 적용)
        """
        try:
            if daily_data is None or len(daily_data) < 5:
                return 0.0
            
            # V3 강도 계산
            intensities = self._calculate_signal_intensities_v3(daily_data, current_vwap)
            
            # Base Score 계산
            base_score = sum(
                intensities.get(signal, 0.0) * weight
                for signal, weight in V3_WEIGHTS.items()
            ) * 100
            
            # V3.2: 가산 Harmony Bonus 계산
            harmony_bonus = self._calculate_harmony_bonus(intensities)
            
            # V3.2 Phase 3: RedundancyPenalty (죽은 압축 필터링)
            redundancy_penalty = self._calculate_redundancy_penalty(intensities)
            
            # V3.2: 0~100 클리핑 적용
            raw_score = (base_score + harmony_bonus) * redundancy_penalty
            final_score = min(100.0, max(0.0, raw_score))
            return round(final_score, 1)
            
        except Exception:
            return 0.0
    
    def _calculate_signal_intensities_v3(
        self, 
        data: Any,
        current_vwap: Optional[float] = None
    ) -> Dict[str, float]:
        """
        V3 신호 강도 계산 (0.0 ~ 1.0)
        
        V2 대비 변경:
        - Tight Range: Z-Score Sigmoid
        - Volume Dryout: 하방 경직성 추가
        """
        return {
            "tight_range": self._calc_tight_range_intensity_v3(data),
            "obv_divergence": self._calc_obv_divergence_intensity_v3(data),  # V3: Z-Score 표준화
            "accumulation_bar": self._calc_accumulation_bar_intensity_v3(data),  # V3: 로그 스케일
            "volume_dryout": self._calc_volume_dryout_intensity_v3(data),
        }
    
    def _calc_tight_range_intensity_v3(self, data: Any) -> float:
        """
        V3.2 Tight Range 강도 계산 - Percentile 기반 정규화
        
        60일 ATR 히스토리에서 현재 ATR의 상대적 위치를 percentile로 계산.
        레짐 변화에 강건 (Z-Score의 분산 의존성 제거)
        
        percentile 낮을수록(변동성 수축) → 강도 높음
        """
        try:
            lookback = ZSCORE_SIGMOID.lookback_days
            highs = self._get_column(data, 'high', lookback)
            lows = self._get_column(data, 'low', lookback)
            closes = self._get_column(data, 'close', lookback)
            
            if len(highs) < 20:
                return 0.0
            
            # ATR 계산 (모든 일봉에 대해)
            atr_list = []
            for i in range(1, len(highs)):
                h_l = highs[i] - lows[i]
                h_pc = abs(highs[i] - closes[i - 1])
                l_pc = abs(lows[i] - closes[i - 1])
                atr_list.append(max(h_l, h_pc, l_pc))
            
            if len(atr_list) < PERCENTILE_CONFIG.min_samples:
                return 0.0
            
            # 현재 ATR (최근 5일 평균)
            current_atr = np.mean(atr_list[-5:])
            
            if PERCENTILE_CONFIG.use_percentile:
                # V3.2: Percentile 기반 정규화
                # percentile = (현재값보다 작은 값 개수) / 전체 개수
                count_lower = sum(1 for x in atr_list if x < current_atr)
                percentile = count_lower / len(atr_list)
                
                # intensity = 1 - percentile (낮을수록 높은 강도)
                intensity = 1.0 - percentile
            else:
                # 기존: Z-Score Sigmoid
                mean_atr = np.mean(atr_list)
                std_atr = np.std(atr_list)
                
                if std_atr <= 0:
                    return 0.0
                
                z = (current_atr - mean_atr) / std_atr
                k = ZSCORE_SIGMOID.sigmoid_k
                x0 = ZSCORE_SIGMOID.sigmoid_x0
                intensity = 1 / (1 + np.exp(k * (z - x0)))
            
            return round(float(intensity), 2)
            
        except Exception:
            return 0.0
    
    def _calc_volume_dryout_intensity_v3(self, data: Any) -> float:
        """
        V3.2 Volume Dryout 강도 계산 - Sigmoid 연속 페널티
        
        거래량 감소 + 가격 지지 동시 확인
        - Volume Dryout: 최근 3일 vs 20일 비율
        - V3.2: Support 이탈 → Sigmoid 연속 페널티
        
        수식: support_penalty = 1 / (1 + exp(-k * support_dist))
        """
        try:
            volumes = self._get_column(data, 'volume', 20)
            
            if len(volumes) < 5:
                return 0.0
            
            avg_20d = np.mean(volumes)
            avg_3d = np.mean(volumes[-3:])
            
            if avg_20d <= 0:
                return 0.0
            
            ratio = avg_3d / avg_20d
            threshold = self.config["dryout_threshold"]["value"]
            
            # Volume Dryout 기본 강도
            if ratio >= threshold:
                volume_intensity = 0.0
            else:
                volume_intensity = 1.0 - (ratio / threshold)
            
            # V3.2: Sigmoid 기반 연속 Support 페널티
            support_factor = self._calc_support_factor(data)
            
            # support_dist: 임계값(0.4) 기준 거리 정규화
            # support_factor > 0.4 → positive → penalty 높음 (좋음)
            # support_factor < 0.4 → negative → penalty 낮음 (나쁨)
            min_loc = SUPPORT_CONFIG.min_price_location
            support_dist = (support_factor - min_loc) / (1.0 - min_loc)  # -0.67 ~ 1.0 범위
            
            # Sigmoid 변환: 1 / (1 + exp(-k * support_dist))
            k = SUPPORT_CONFIG.penalty_steepness
            support_penalty = 1.0 / (1.0 + np.exp(-k * support_dist))
            
            # 최종 강도 = Volume Dryout × Support Penalty
            intensity = volume_intensity * support_penalty
            
            return round(intensity, 2)
            
        except Exception:
            return 0.0
    
    def _calc_obv_divergence_intensity_v3(self, data: Any) -> float:
        """
        V3.2 Absorption 강도 계산 (OBV Divergence 대체)
        
        핵심 개념: 거래량 많은데 가격 반응 작으면 → 흡수 발생
        
        수식:
        - sv = Σ(sign(returns) × volume)  : Signed Volume
        - pr = Σ(|returns|)               : Price Reaction
        - absorption = sigmoid(z(sv_norm) - z(pr_norm))
        
        Returns:
            float: 0.0 ~ 1.0
        """
        try:
            closes = self._get_column(data, 'close', 20)
            volumes = self._get_column(data, 'volume', 20)
            
            if len(closes) < 10 or len(volumes) < 10:
                return 0.0
            
            # === 1. 최근 10일 Signed Volume 계산 ===
            # sv = sum(sign(returns) * volume)
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
            
            # Price Reaction 정규화 (10일 평균 대비)
            avg_pr = price_reaction / 10 if price_reaction > 0 else 0.01
            
            # === 3. Absorption 계산 ===
            # 거래량 많은데(sv 높음) 가격 반응 작으면(pr 낮음) → 흡수
            # sv_norm이 양수(매수 우세)이고 pr이 작으면 강도 높음
            
            # 5% 초과 상승 시 약한 페널티 (기존: 0점 → 개선: 0.3점)
            if len(closes) >= 6:
                price_change = (closes[-1] - closes[-5]) / closes[-5] if closes[-5] > 0 else 0
                if price_change > 0.05:
                    return 0.3  # 상승 중이면 흡수 약함으로 처리 (0 대신)
            
            # V3.2 Phase 4: 부드러운 페널티 (Option A)
            # 매도 우세도 연속적 스케일로 표현
            if sv_norm <= 0:
                # 매도 우세: 0.0 ~ 0.5 범위
                # sv_norm = -3 → 0.01, sv_norm = 0 → 0.5
                intensity = 0.5 / (1 + np.exp(-sv_norm * 2))
            else:
                # 매수 우세: 0.5 ~ 1.0 범위
                # 중심점 3.0으로 상향 → 1.0 도달 매우 어려움 (헤드룸 확보)
                absorption_score = sv_norm / (avg_pr / 0.02 + 0.1)
                intensity = 0.5 + 0.5 / (1 + np.exp(-absorption_score + 3.0))
            
            return round(float(intensity), 2)
            
        except Exception:
            return 0.5  # 예외 시 중립 반환 (0 대신)
    
    def _calc_accumulation_bar_intensity_v3(
        self, 
        data: Any, 
        float_shares: int = 10_000_000
    ) -> float:
        """
        V3.1 Accumulation Bar 강도 계산 - 시간 분리 + 이상치 내성
        
        특징:
        1. Base 0.5 + 가감점 구조 (중립 기준점)
        2. 과거 10일간의 매집 기간 분석 (Dryout와 시간 분리)
        3. Median + 비율 기반 (이상치에 강건)
        4. Float 기반 동적 기간 계산
        
        Args:
            data: OHLCV 캔들 데이터 (list of dict 또는 DataFrame)
            float_shares: 유통 주식 수 (기본값 10M)
        
        Returns:
            float: 0.0 ~ 1.0 (0.5 = 중립)
        
        참조: docs/Plan/bugfix/03-003_accumbar_v31_redesign.md
        """
        try:
            cfg = ACCUMBAR_CONFIG
            BASE_SCORE = cfg.base_score
            
            # === 1. 동적 기간 계산 ===
            # Float 기반: 3M → 4일, 15M+ → 10일
            dryout_days = min(10, max(3, 3 + float_shares // 3_000_000))
            accum_start = dryout_days + cfg.accum_period_days  # 예: 4 + 10 = 14일 전
            accum_end = dryout_days                            # 예: 4일 전
            
            # 데이터 부족 시 중립 반환
            if len(data) < accum_start:
                return BASE_SCORE
            
            # 매집 기간 데이터 추출 (DataFrame 또는 list 지원)
            if hasattr(data, 'iloc'):
                period = data.iloc[-accum_start:-accum_end]
                period = [row.to_dict() for _, row in period.iterrows()]
            else:
                period = data[-accum_start:-accum_end]
            
            n = len(period)
            if n == 0:
                return BASE_SCORE
            
            adjustment = 0.0
            
            # === 2. 양봉 비율 (카운팅 - 이미 robust) ===
            bullish_count = sum(
                1 for d in period 
                if float(d.get("close", d.get("Close", 0))) > float(d.get("open", d.get("Open", 0)))
            )
            bullish_ratio = bullish_count / n
            
            if bullish_ratio >= cfg.bullish_threshold_high:
                adjustment += cfg.adj_bullish
            elif bullish_ratio <= cfg.bullish_threshold_low:
                adjustment -= cfg.adj_bullish
            
            # === 3. V3.2 방향성 있는 조용함 (Directional Quiet Days) ===
            # 조용한 날 중 상단 마감 비율 측정
            quiet_days_list = []
            for d in period:
                close = float(d.get("close", d.get("Close", 0)))
                high = float(d.get("high", d.get("High", 0)))
                low = float(d.get("low", d.get("Low", 0)))
                if close > 0 and (high - low) / close < cfg.quiet_range_pct:
                    # 조용한 날 발견 - 상단 마감 여부 기록
                    midpoint = (high + low) / 2
                    quiet_days_list.append(close > midpoint)
            
            if quiet_days_list:
                # 조용한 날이 있으면: 상단 마감 비율로 판단
                upper_close_ratio = sum(quiet_days_list) / len(quiet_days_list)
                
                if upper_close_ratio >= cfg.quiet_threshold_high:
                    adjustment += cfg.adj_quiet  # 조용하면서 상단 마감 많음 = 매집
                elif upper_close_ratio <= cfg.bullish_threshold_low:
                    adjustment -= cfg.adj_quiet * 0.67  # 조용한데 하단 마감 = 분배
            # 조용한 날이 없으면 adjustment 변화 없음 (변동성 있는 시장)
            
            # === 4. Body Ratio - Median (이상치 무시) ===
            body_ratios = []
            for d in period:
                high = float(d.get("high", d.get("High", 0)))
                low = float(d.get("low", d.get("Low", 0)))
                open_p = float(d.get("open", d.get("Open", 0)))
                close_p = float(d.get("close", d.get("Close", 0)))
                if high != low:
                    body_ratios.append(abs(close_p - open_p) / (high - low))
            
            if body_ratios:
                body_median = sorted(body_ratios)[len(body_ratios) // 2]
                if body_median >= cfg.body_ratio_high:
                    adjustment += cfg.adj_body
                elif body_median < cfg.body_ratio_low:
                    adjustment -= cfg.adj_body
            
            # === 5. 거래량 - Median (하루 폭발 무시) ===
            accum_vols = [
                float(d.get("volume", d.get("Volume", 0))) 
                for d in period
            ]
            
            # 전체 데이터의 거래량
            if hasattr(data, 'iloc'):
                total_vols = [float(row.get("volume", row.get("Volume", 0))) for _, row in data.iterrows()]
            else:
                total_vols = [float(d.get("volume", d.get("Volume", 0))) for d in data]
            
            if accum_vols and total_vols:
                accum_median = sorted(accum_vols)[len(accum_vols) // 2]
                total_median = sorted(total_vols)[len(total_vols) // 2]
                
                if total_median > 0:
                    if accum_median > total_median * cfg.volume_ratio_high:
                        adjustment += cfg.adj_volume  # 매집 기간에 거래량 높음 = 좋음
                    elif accum_median < total_median * cfg.volume_ratio_low:
                        adjustment -= cfg.adj_volume  # 매집 기간에 거래량 낮음 = 매집 없음
            
            # === 6. 최종 점수 ===
            intensity = max(0.0, min(1.0, BASE_SCORE + adjustment))
            return round(intensity, 2)
            
        except Exception:
            return 0.5  # 예외 시 중립 반환 (0.0 대신)

    
    def _calc_support_factor(self, data: Any) -> float:
        """
        하방 경직성 계산 (Price Location)
        
        Returns:
            float: (Close - Low) / (High - Low), 0~1
        """
        try:
            latest = data.iloc[-1] if hasattr(data, 'iloc') else data[-1]
            
            high = float(latest.get('high', latest.get('High', 0)))
            low = float(latest.get('low', latest.get('Low', 0)))
            close = float(latest.get('close', latest.get('Close', 0)))
            
            if high == low:
                return 0.5
            
            return (close - low) / (high - low)
            
        except Exception:
            return 0.5
    
    def _calculate_harmony_bonus(self, intensities: Dict[str, float]) -> float:
        """
        V3.2 Harmony Bonus 계산 (가산 방식)
        
        수식: harmony_bonus = B * max(0, min_intensity - threshold)
        
        모든 신호가 threshold(0.6) 이상일 때 보너스 부여.
        min_intensity가 1.0일 때 최대 약 8점 추가 (20 * 0.4 = 8).
        
        Args:
            intensities: 각 신호의 강도 (0.0 ~ 1.0)
            
        Returns:
            float: 가산 보너스 점수 (0.0 ~ 8.0)
        """
        values = list(intensities.values())
        if not values:
            return 0.0
        
        cfg = SIGNAL_MODIFIER_CONFIG
        min_intensity = min(values)
        
        # threshold 이하면 보너스 없음
        if min_intensity < cfg.bonus_threshold:
            return 0.0
        
        # harmony_bonus = B * max(0, min_intensity - threshold)
        harmony_bonus = cfg.harmony_bonus_scale * (min_intensity - cfg.bonus_threshold)
        return harmony_bonus
    
    def _calculate_signal_modifier(self, intensities: Dict[str, float]) -> float:
        """
        [Deprecated] V3.1 신호 수정자 (하위 호환용)
        
        V3.2에서는 _calculate_harmony_bonus() 사용.
        이 메서드는 하위 호환을 위해 유지되며 1.0을 반환합니다.
        """
        return 1.0
    
    def _calculate_redundancy_penalty(self, intensities: Dict[str, float]) -> float:
        """
        V3.2 Phase 3 RedundancyPenalty 계산
        
        압축(TR)만 높고 흡수(OBV) 없으면 "죽은 압축" 패턴으로 감점
        
        조건:
        - TR >= 0.6 (압축 상태)
        - OBV <= 0.4 (흡수 없음)
        → 0.7x 페널티
        
        Args:
            intensities: 각 신호의 강도
            
        Returns:
            float: 1.0 (정상) 또는 penalty_multiplier (0.7)
        """
        if not REDUNDANCY_PENALTY_CONFIG.enabled:
            return 1.0
        
        tr = intensities.get("tight_range", 0.0)
        obv = intensities.get("obv_divergence", 0.0)
        
        cfg = REDUNDANCY_PENALTY_CONFIG
        
        # 압축 상태인데 흡수 없으면 죽은 압축
        if tr >= cfg.tr_threshold and obv <= cfg.obv_threshold:
            return cfg.penalty_multiplier  # 0.7
        
        return 1.0

    def calculate_watchlist_score_detailed(
        self, 
        ticker: str, 
        daily_data: Any
    ) -> Dict[str, Any]:
        """
        상세 매집 분석 결과 반환 (메타데이터 포함)
        
        ═══════════════════════════════════════════════════════════════════════
        Step 2.2.5: Trading Restrictions 지원
        ═══════════════════════════════════════════════════════════════════════
        
        기존 calculate_watchlist_score()는 점수만 반환하지만,
        이 메서드는 개별 신호 탐지 결과 + 점수 + stage 정보를 dict로 반환합니다.
        
        Args:
            ticker: 종목 코드 (예: "AAPL")
            daily_data: 일봉 데이터 (pandas DataFrame 또는 list of dict)
                필수 컬럼: open, high, low, close, volume
        
        Returns:
            dict: 상세 분석 결과
                - score: float (0~100)
                - stage: str (Stage 문자열)
                - stage_number: int (1~4)
                - signals: dict (개별 신호 bool)
                - can_trade: bool (Stage 3-4만 True)
        
        Example:
            >>> result = strategy.calculate_watchlist_score_detailed("AAPL", data)
            >>> print(result)
            {
                "score": 80.0,
                "stage": "Stage 4 (Tight Range)",
                "stage_number": 4,
                "signals": {
                    "tight_range": True,
                    "accumulation_bar": False,
                    "obv_divergence": False,
                    "volume_dryout": False
                },
                "can_trade": True
            }
        """
        try:
            # 데이터 유효성 검사
            if daily_data is None or len(daily_data) < 5:
                return self._get_empty_score_result()
            
            # === 4가지 매집 신호 탐지 ===
            has_tight_range = self._check_tight_range(daily_data) > 0.5
            has_accumulation_bar = self._check_accumulation_bar(daily_data) > 0.5
            has_obv_divergence = self._check_obv_divergence(daily_data) > 0.5
            has_volume_dryout = self._check_volume_dryout(daily_data) > 0.5
            
            # 기존 로직으로 점수 계산
            score = self.calculate_watchlist_score(ticker, daily_data)
            
            # Stage 정보 계산
            stage_str = self._score_to_stage_str(score)
            stage_num = self._score_to_stage_number(score)
            
            # Trading Restriction: Stage 3-4만 트레이딩 허용
            # Stage 1 (Volume Dry-out) / Stage 2 (OBV Divergence) = Monitoring Only
            can_trade = stage_num >= 3
            
            # [02-001] v2 연속 점수 및 신호 강도 추가
            score_v2 = self.calculate_watchlist_score_v2(ticker, daily_data)
            intensities = self._calculate_signal_intensities(daily_data)
            
            # [03-001] v3 Pinpoint Algorithm 추가
            score_v3 = self.calculate_watchlist_score_v3(ticker, daily_data)
            intensities_v3 = self._calculate_signal_intensities_v3(daily_data)
            
            return {
                "score": score,
                "score_v2": score_v2,  # [02-001] 연속 점수 추가
                "score_v3": score_v3,  # [03-001] Pinpoint Algorithm
                "stage": stage_str,
                "stage_number": stage_num,
                "signals": {
                    "tight_range": has_tight_range,
                    "accumulation_bar": has_accumulation_bar,
                    "obv_divergence": has_obv_divergence,
                    "volume_dryout": has_volume_dryout,
                },
                "intensities": intensities,  # [02-001] 신호 강도 추가
                "intensities_v3": intensities_v3,  # [03-001] V3 강도
                "can_trade": can_trade,
            }

            
        except Exception:
            return self._get_empty_score_result()
    
    def _get_empty_score_result(self) -> Dict[str, Any]:
        """빈 점수 결과 반환 (오류 시 사용)"""
        return {
            "score": 0.0,
            "stage": "No Signal",
            "stage_number": 0,
            "signals": {
                "tight_range": False,
                "accumulation_bar": False,
                "obv_divergence": False,
                "volume_dryout": False,
            },
            "can_trade": False,
        }
    
    def _score_to_stage_str(self, score: float) -> str:
        """점수를 Stage 문자열로 변환"""
        if score >= 100:
            return "Stage 4 (폭발 임박 🔥)"
        elif score >= 80:
            return "Stage 4 (Tight Range)"
        elif score >= 70:
            return "Stage 3 (관심 대상)"
        elif score >= 50:
            return "Stage 3 (Accum Bar)"
        elif score >= 30:
            return "Stage 2 (OBV Divergence)"
        elif score >= 10:
            return "Stage 1 (Volume Dry-out)"
        else:
            return "No Signal"
    
    def _score_to_stage_number(self, score: float) -> int:
        """
        점수를 Stage 번호로 변환 (Trading Restrictions용)
        
        Returns:
            int: 0 (No Signal), 1, 2, 3, 4
        """
        if score >= 80:  # Stage 4: Tight Range
            return 4
        elif score >= 50:  # Stage 3: Accumulation Bar
            return 3
        elif score >= 30:  # Stage 2: OBV Divergence
            return 2
        elif score >= 10:  # Stage 1: Volume Dry-out
            return 1
        else:
            return 0

    def _check_accumulation_bar(self, data: Any) -> float:
        """
        매집봉 탐지 (30% Weight)
        
        조건:
            - 가격 변동 ±2.5% 이내 (좁은 레인지)
            - 거래량 > 20일 평균의 3배
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            float: 0.0 (미탐지) 또는 1.0 (탐지)
        """
        try:
            # 최근 봉 데이터
            latest = data.iloc[-1] if hasattr(data, 'iloc') else data[-1]
            
            # 가격 변동폭 (시가 대비 종가)
            open_price = float(latest.get('open', latest.get('Open', 0)))
            close_price = float(latest.get('close', latest.get('Close', 0)))
            
            if open_price == 0:
                return 0.0
            
            price_change = abs(close_price - open_price) / open_price
            
            # 20일 평균 거래량
            volumes = self._get_column(data, 'volume', 20)
            if len(volumes) < 5:  # 최소 5일 필요
                return 0.0
            
            avg_volume = np.mean(volumes[:-1])  # 최근 1개 제외한 평균
            current_volume = float(volumes[-1])
            
            spike_multiplier = self.config["spike_volume_multiplier"]["value"]
            
            # 조건: 가격 변동 ±2.5% AND 거래량 > 평균 × spike_multiplier
            if price_change <= 0.025 and current_volume > avg_volume * spike_multiplier:
                return 1.0
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _check_obv_divergence(self, data: Any) -> float:
        """
        OBV Divergence 탐지 (40% Weight)
        
        조건:
            - 주가 기울기 ≤ 0 (하락 또는 횡보)
            - OBV 기울기 > 0 (상승)
        
        이 패턴은 가격은 하락하지만 매수세가 축적되고 있음을 의미합니다.
        "스마트 머니"가 조용히 매집 중인 신호입니다.
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            float: 0.0 (미탐지) 또는 1.0 (탐지)
        """
        try:
            lookback = self.config["obv_lookback"]["value"]
            
            # 종가와 거래량 추출
            closes = self._get_column(data, 'close', lookback)
            volumes = self._get_column(data, 'volume', lookback)
            
            # 최소 5일 데이터 필요
            min_required = min(5, lookback)
            if len(closes) < min_required or len(volumes) < min_required:
                return 0.0
            
            # OBV 계산
            # OBV = 종가 상승 시 거래량 더하고, 하락 시 빼는 누적값
            obv = [0.0]
            for i in range(1, len(closes)):
                if closes[i] > closes[i - 1]:
                    obv.append(obv[-1] + volumes[i])
                elif closes[i] < closes[i - 1]:
                    obv.append(obv[-1] - volumes[i])
                else:
                    obv.append(obv[-1])
            
            # 기울기 계산 (선형 회귀 간소화: 끝점 - 시작점)
            price_slope = (closes[-1] - closes[0]) / len(closes) if len(closes) > 1 else 0
            obv_slope = (obv[-1] - obv[0]) / len(obv) if len(obv) > 1 else 0
            
            # 조건: 주가↓ OBV↑
            if price_slope <= 0 and obv_slope > 0:
                return 1.0
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _check_volume_dryout(self, data: Any) -> float:
        """
        Volume Dry-out (거래량 마름) 탐지 (20% Weight)
        
        조건:
            - 최근 3일 평균 거래량 < 20일 평균의 40%
        
        폭풍 전의 고요함. 급등 직전에 거래량이 급감하는 패턴입니다.
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            float: 0.0 (미탐지) 또는 1.0 (탐지)
        """
        try:
            volumes = self._get_column(data, 'volume', 20)
            
            if len(volumes) < 5:  # 최소 5일 필요
                return 0.0
            
            # 20일 평균
            avg_20d = np.mean(volumes)
            
            # 최근 3일 평균
            avg_3d = np.mean(volumes[-3:])
            
            threshold = self.config["dryout_threshold"]["value"]
            
            # 조건: 최근 3일 < 20일 평균 × threshold
            if avg_3d < avg_20d * threshold:
                return 1.0
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _check_tight_range(self, data: Any) -> float:
        """
        Tight Range / VCP (Volatility Contraction Pattern) 탐지 (10% Weight)
        
        조건:
            - 5일 ATR < 20일 ATR의 50%
        
        변동폭이 줄어드는 삼각수렴 패턴. 폭발 직전의 에너지 축적.
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            float: 0.0 (미탐지) 또는 1.0 (탐지)
        """
        try:
            # ATR 계산에 필요한 데이터
            highs = self._get_column(data, 'high', 20)
            lows = self._get_column(data, 'low', 20)
            closes = self._get_column(data, 'close', 20)
            
            if len(highs) < 5:  # 최소 5일 필요
                return 0.0
            
            # True Range 계산
            # TR = max(H-L, |H-PC|, |L-PC|) where PC = Previous Close
            tr_list = []
            for i in range(1, len(highs)):
                h_l = highs[i] - lows[i]
                h_pc = abs(highs[i] - closes[i - 1])
                l_pc = abs(lows[i] - closes[i - 1])
                tr_list.append(max(h_l, h_pc, l_pc))
            
            if len(tr_list) < 19:  # 20일치 데이터에서 19개 TR
                return 0.0
            
            # ATR = True Range의 평균
            atr_5d = np.mean(tr_list[-5:])   # 최근 5일
            atr_20d = np.mean(tr_list)       # 20일 전체
            
            threshold = self.config["atr_ratio_threshold"]["value"]
            
            # 조건: 5일 ATR < 20일 ATR × threshold
            if atr_20d > 0 and atr_5d < atr_20d * threshold:
                return 1.0
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _get_column(self, data: Any, column: str, length: int) -> List[float]:
        """
        DataFrame 또는 dict에서 컬럼 데이터 추출
        
        Args:
            data: OHLCV 데이터
            column: 컬럼명 (예: 'close', 'volume')
            length: 필요한 데이터 개수
            
        Returns:
            List[float]: 숫자 리스트
        """
        try:
            # pandas DataFrame인 경우
            if hasattr(data, 'iloc'):
                # 대소문자 모두 시도
                col = column.lower()
                if col in data.columns:
                    return data[col].tail(length).tolist()
                col_cap = column.capitalize()
                if col_cap in data.columns:
                    return data[col_cap].tail(length).tolist()
                # Volume 특별 처리
                if column.lower() == 'volume' and 'Volume' in data.columns:
                    return data['Volume'].tail(length).tolist()
            
            # list of dict인 경우
            if isinstance(data, list):
                values = []
                for row in data[-length:]:
                    val = row.get(column, row.get(column.capitalize(), 0))
                    values.append(float(val))
                return values
            
            return []
            
        except Exception:
            return []
    
    def calculate_trigger_score(
        self, 
        ticker: str, 
        tick_data: Any = None, 
        bar_data: Any = None
    ) -> float:
        """
        실시간 Trigger 점수 계산 (Phase 2 - Ignition Score)
        
        ═══════════════════════════════════════════════════════════════════
        masterplan.md 4.1절 기준
        ═══════════════════════════════════════════════════════════════════
        
        4가지 신호의 가중합으로 0~100점 계산:
        
        | 신호 | Weight | 조건 |
        |------|--------|------|
        | Tick Velocity | 35% | 10초 체결 > 1분 평균 × 8 |
        | Volume Burst | 30% | 1분 거래량 > 5분 평균 × 6 |
        | Price Break | 20% | 현재가 > 박스권 상단 + 0.5% |
        | Buy Pressure | 15% | 매수/매도 비율 > 1.8 |
        
        Args:
            ticker: 종목 코드
            tick_data: 실시간 틱 데이터 (Optional, 내부 버퍼 사용 시 None)
            bar_data: 분봉 데이터 (Optional, 내부 버퍼 사용 시 None)
            
        Returns:
            float: 0 ~ 100 사이의 Ignition Score
        """
        try:
            # 각 신호별 점수 계산 (0.0 ~ 1.0)
            tick_velocity_score = self._calculate_tick_velocity(ticker)
            volume_burst_score = self._calculate_volume_burst(ticker)
            price_break_score = self._calculate_price_break(ticker)
            buy_pressure_score = self._calculate_buy_pressure(ticker)
            
            # 가중 합산 (0~100점)
            total_score = (
                tick_velocity_score * 35.0 +
                volume_burst_score * 30.0 +
                price_break_score * 20.0 +
                buy_pressure_score * 15.0
            )
            
            return min(100.0, max(0.0, total_score))
            
        except Exception:
            return 0.0
    
    def _calculate_tick_velocity(self, ticker: str) -> float:
        """
        틱 속도 점수 계산 (35% Weight)
        
        조건: 10초 체결량 > 1분 평균 체결량 × 8
        
        ═══════════════════════════════════════════════════════════════
        쉬운 설명 (ELI5):
        ═══════════════════════════════════════════════════════════════
        갑자기 체결이 빨라지는 것을 감지합니다.
        평소 1분에 100번 체결되는 종목이
        최근 10초 동안 130번 이상 체결되면 "뭔가 터졌다!" 신호입니다.
        
        Args:
            ticker: 종목 코드
            
        Returns:
            float: 0.0 (미충족) ~ 1.0 (충족)
        """
        try:
            if ticker not in self._tick_buffer:
                return 0.0
            
            ticks = self._tick_buffer[ticker]
            if len(ticks) < 10:
                return 0.0
            
            now = datetime.now()
            
            # 최근 10초 틱 수
            ticks_10s = sum(
                1 for t in ticks 
                if (now - t.timestamp).total_seconds() <= 10
            )
            
            # 최근 60초 틱 수 (1분 평균)
            ticks_60s = sum(
                1 for t in ticks 
                if (now - t.timestamp).total_seconds() <= 60
            )
            
            if ticks_60s == 0:
                return 0.0
            
            # 1분 평균 틱/10초
            avg_ticks_per_10s = (ticks_60s / 60) * 10
            
            multiplier = self.config["tick_velocity_multiplier"]["value"]
            
            # 조건: 10초 틱 > 1분 평균 × multiplier
            if avg_ticks_per_10s > 0 and ticks_10s > avg_ticks_per_10s * multiplier:
                return 1.0
            
            # 부분 점수 (절반 이상이면 0.5점)
            if avg_ticks_per_10s > 0 and ticks_10s > avg_ticks_per_10s * (multiplier / 2):
                return 0.5
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_volume_burst(self, ticker: str) -> float:
        """
        거래량 폭발 점수 계산 (30% Weight)
        
        조건: 1분 거래량 > 5분 평균의 6배
        
        ═══════════════════════════════════════════════════════════════
        쉬운 설명 (ELI5):
        ═══════════════════════════════════════════════════════════════
        갑자기 거래량이 폭발하는 것을 감지합니다.
        평소 1분에 1만주 거래되는 종목이
        이번 1분에 6만주 이상 거래되면 "큰 손이 샀다!" 신호입니다.
        
        Args:
            ticker: 종목 코드
            
        Returns:
            float: 0.0 ~ 1.0
        """
        try:
            if ticker not in self._bar_1m or len(self._bar_1m[ticker]) < 5:
                return 0.0
            
            bars = self._bar_1m[ticker]
            
            # 최근 1분 거래량
            current_volume = bars[-1].get("volume", 0)
            
            # 이전 5분 평균 거래량
            prev_volumes = [b.get("volume", 0) for b in bars[-6:-1]]
            if not prev_volumes:
                return 0.0
            
            avg_5m_volume = np.mean(prev_volumes)
            
            if avg_5m_volume == 0:
                return 0.0
            
            multiplier = self.config["volume_burst_multiplier"]["value"]
            
            # 조건: 1분 거래량 > 5분 평균 × multiplier
            if current_volume > avg_5m_volume * multiplier:
                return 1.0
            
            # 부분 점수
            if current_volume > avg_5m_volume * (multiplier / 2):
                return 0.5
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_price_break(self, ticker: str) -> float:
        """
        가격 돌파 점수 계산 (20% Weight)
        
        조건: 현재가 > 박스권 상단 + 0.5%
        
        ═══════════════════════════════════════════════════════════════
        쉬운 설명 (ELI5):
        ═══════════════════════════════════════════════════════════════
        박스권(횡보 구간)을 돌파하는 것을 감지합니다.
        $5.00 ~ $5.50 사이에서 움직이던 종목이
        갑자기 $5.53 이상으로 치고 올라가면 "돌파다!" 신호입니다.
        
        Args:
            ticker: 종목 코드
            
        Returns:
            float: 0.0 ~ 1.0
        """
        try:
            if ticker not in self._box_range or ticker not in self._tick_buffer:
                return 0.0
            
            ticks = self._tick_buffer[ticker]
            if not ticks:
                return 0.0
            
            current_price = ticks[-1].price
            box_high, box_low = self._box_range[ticker]
            
            if box_high == 0:
                return 0.0
            
            break_pct = self.config["price_break_pct"]["value"] / 100.0
            breakout_level = box_high * (1 + break_pct)
            
            # 조건: 현재가 > 박스 상단 + X%
            if current_price > breakout_level:
                return 1.0
            
            # 부분 점수 (상단 터치)
            if current_price > box_high:
                return 0.5
            
            return 0.0
            
        except Exception:
            return 0.0
    
    def _calculate_buy_pressure(self, ticker: str) -> float:
        """
        매수 압력 점수 계산 (15% Weight)
        
        조건: 매수/매도 비율 > 1.8
        
        ═══════════════════════════════════════════════════════════════
        쉬운 설명 (ELI5):
        ═══════════════════════════════════════════════════════════════
        사는 사람이 파는 사람보다 압도적으로 많은지 감지합니다.
        최근 틱 중 매수가 매도의 1.8배 이상이면
        "세력이 싹쓸이 중!" 신호입니다.
        
        Args:
            ticker: 종목 코드
            
        Returns:
            float: 0.0 ~ 1.0
        """
        try:
            if ticker not in self._tick_buffer:
                return 0.0
            
            ticks = self._tick_buffer[ticker]
            if len(ticks) < 10:
                return 0.0
            
            now = datetime.now()
            
            # 최근 60초 틱 중 매수/매도 집계
            buy_volume = 0
            sell_volume = 0
            
            for t in ticks:
                if (now - t.timestamp).total_seconds() <= 60:
                    if t.side == "B":
                        buy_volume += t.volume
                    else:
                        sell_volume += t.volume
            
            if sell_volume == 0:
                return 1.0 if buy_volume > 0 else 0.0
            
            ratio = buy_volume / sell_volume
            target_ratio = self.config["buy_pressure_ratio"]["value"]
            
            # 조건: 매수/매도 > target_ratio
            if ratio > target_ratio:
                return 1.0
            
            # 부분 점수
            if ratio > target_ratio / 2:
                return 0.5
            
            return 0.0
            
        except Exception:
            return 0.0
    
    # ═══════════════════════════════════════════════════════════════════
    # Anti-Trap Filter (Phase 2)
    # ═══════════════════════════════════════════════════════════════════
    
    def get_anti_trap_filter(self) -> dict:
        """
        Anti-Trap 필터 조건 반환
        
        함정에 빠지지 않기 위한 추가 검증 조건입니다.
        
        Returns:
            dict: 필터 조건 (masterplan.md 4.2절)
        """
        return {
            "max_spread_pct": self.config["max_spread_pct"]["value"],
            "min_minutes_after_open": self.config["min_minutes_after_open"]["value"],
            "must_above_vwap": True,
        }
    
    def check_anti_trap_filter(
        self, 
        ticker: str, 
        price: float, 
        bid: float, 
        ask: float, 
        timestamp: datetime
    ) -> Tuple[bool, str]:
        """
        Anti-Trap 필터 검증
        
        3가지 조건을 모두 통과해야 진입 가능:
        1. 스프레드 < 1%
        2. 장 시작 후 15분 경과
        3. VWAP 위에 위치
        
        Args:
            ticker: 종목 코드
            price: 현재가
            bid: 매수호가
            ask: 매도호가
            timestamp: 현재 시간
            
        Returns:
            Tuple[bool, str]: (통과 여부, 실패 사유)
        """
        # 1. 스프레드 체크
        if ask > 0:
            spread_pct = ((ask - bid) / ask) * 100
            max_spread = self.config["max_spread_pct"]["value"]
            if spread_pct > max_spread:
                return False, f"Spread {spread_pct:.2f}% > {max_spread}%"
        
        # 2. 장 시작 시간 체크
        min_minutes = self.config["min_minutes_after_open"]["value"]
        market_open_dt = datetime.combine(timestamp.date(), self._market_open_time)
        minutes_elapsed = (timestamp - market_open_dt).total_seconds() / 60
        
        if minutes_elapsed < min_minutes:
            return False, f"Market open {minutes_elapsed:.0f}min < {min_minutes}min"
        
        # 3. VWAP 체크
        if ticker in self._vwap:
            vwap = self._vwap[ticker]
            if vwap > 0 and price < vwap:
                return False, f"Price {price:.2f} < VWAP {vwap:.2f}"
        
        return True, "OK"
    
    # ═══════════════════════════════════════════════════════════════════
    # Trading Layer
    # ═══════════════════════════════════════════════════════════════════
    
    def initialize(self) -> None:
        """
        전략 초기화 (로드 시 1회 호출)
        
        모든 내부 상태(버퍼)를 초기화합니다.
        Phase 1 (Watchlist) 및 Phase 2 (Trigger) 상태 모두 리셋.
        """
        # Phase 1 상태 초기화
        self._watchlist = []
        self._watchlist_context = {}  # Step 2.3.5: Context도 초기화
        
        # Phase 2 상태 초기화
        self._tick_buffer = {}
        self._bar_1m = {}
        self._vwap = {}
        self._box_range = {}
        
        print(f"[{self.name}] 전략 초기화 완료 (Phase 1 + Phase 2)")
    
    def load_watchlist_context(
        self, 
        watchlist: List[Dict[str, Any]]
    ) -> None:
        """
        Watchlist Context 로드 (Step 2.3.5)
        
        ═══════════════════════════════════════════════════════════════════════
        Scanner에서 생성한 Watchlist의 메타데이터를 Trigger Engine에 로드합니다.
        이 정보는 on_tick()에서 Trading Restrictions 체크에 사용됩니다.
        ═══════════════════════════════════════════════════════════════════════
        
        Args:
            watchlist: Scanner.run_daily_scan()의 반환값
                [
                    {
                        "ticker": "AAPL",
                        "score": 80.0,
                        "stage_number": 4,
                        "can_trade": True,
                        "signals": {...},
                        ...
                    },
                    ...
                ]
        
        Example:
            >>> scanner = Scanner(db)
            >>> watchlist = await scanner.run_daily_scan()
            >>> 
            >>> strategy.load_watchlist_context(watchlist)
            >>> # 이제 on_tick()에서 Stage 정보 활용
        """
        # 기존 context 클리어
        self._watchlist_context = {}
        self._watchlist = []
        
        for item in watchlist:
            ticker = item.get("ticker")
            if not ticker:
                continue
            
            # Watchlist에 티커 추가
            self._watchlist.append(ticker)
            
            # Context 저장
            self._watchlist_context[ticker] = {
                "score": item.get("score", 0.0),
                "stage": item.get("stage", ""),
                "stage_number": item.get("stage_number", 0),
                "can_trade": item.get("can_trade", True),
                "signals": item.get("signals", {}),
                "last_close": item.get("last_close", 0.0),
                "avg_volume": item.get("avg_volume", 0.0),
            }
        
        print(f"[{self.name}] Watchlist Context 로드 완료: {len(self._watchlist)}개 티커")
        
        # Stage별 통계 로그
        stage_counts = {}
        for ctx in self._watchlist_context.values():
            stage_num = ctx.get("stage_number", 0)
            stage_counts[stage_num] = stage_counts.get(stage_num, 0) + 1
        
        tradeable = sum(1 for ctx in self._watchlist_context.values() if ctx.get("can_trade"))
        print(f"  - 거래 가능 (Stage 3-4): {tradeable}개")
        print(f"  - 모니터링 (Stage 1-2): {len(self._watchlist) - tradeable}개")

    
    def on_tick(
        self, 
        ticker: str, 
        price: float, 
        volume: int, 
        timestamp: Any,
        side: str = "B",
        bid: float = 0.0,
        ask: float = 0.0
    ) -> Optional[Signal]:
        """
        틱 데이터 처리 → Signal 반환
        
        ═══════════════════════════════════════════════════════════════════
        Phase 2: Ignition Detection (폭발 감지)
        ═══════════════════════════════════════════════════════════════════
        
        1. 틱을 버퍼에 저장 (최근 60초 유지)
        2. Ignition Score 계산 (4가지 신호 가중합)
        3. Anti-Trap 필터 통과 확인
        4. 조건 충족 시 BUY Signal 반환
        
        Args:
            ticker: 종목 코드
            price: 체결 가격
            volume: 체결 수량
            timestamp: 체결 시간 (datetime 또는 str)
            side: 체결 방향 ("B" = 매수, "S" = 매도)
            bid: 매수호가 (Anti-Trap spread 검증용)
            ask: 매도호가 (Anti-Trap spread 검증용)
            
        Returns:
            Signal: BUY 신호 (조건 충족 시) 또는 None
        """
        # === 타임스탬프 정규화 ===
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                timestamp = datetime.now()
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.now()
        
        # === 틱 버퍼 초기화 (해당 종목 처음 등장 시) ===
        if ticker not in self._tick_buffer:
            # maxlen=1000으로 메모리 제한 (약 60초 × ~15틱/초)
            self._tick_buffer[ticker] = deque(maxlen=1000)
        
        # === 틱 저장 ===
        tick = TickData(
            price=price,
            volume=volume,
            timestamp=timestamp,
            side=side
        )
        self._tick_buffer[ticker].append(tick)
        
        # === 오래된 틱 정리 (60초 초과) ===
        cutoff = timestamp - timedelta(seconds=60)
        while (self._tick_buffer[ticker] and 
               self._tick_buffer[ticker][0].timestamp < cutoff):
            self._tick_buffer[ticker].popleft()
        
        # === Watchlist 종목만 Ignition 체크 ===
        if ticker not in self._watchlist:
            return None
        
        # === Step 2.3.4: Trading Restrictions ===
        # Stage 1-2 종목은 Monitoring Only - Signal 발생 안 함
        context = self._watchlist_context.get(ticker, {})
        can_trade = context.get("can_trade", True)  # 기본값: 거래 허용
        stage_number = context.get("stage_number", 0)
        
        if not can_trade:
            # Stage 1-2는 모니터링만, 로그만 기록 (Signal 발생 X)
            # 디버그용: Ignition Score가 높아도 Stage 1-2는 무시
            # 추후 Stage가 올라가면 거래 가능
            return None
        
        # === Ignition Score 계산 ===
        ignition_score = self.calculate_trigger_score(ticker)
        threshold = self.config["ignition_threshold"]["value"]
        
        if ignition_score < threshold:
            return None
        
        # === Anti-Trap Filter 검증 ===
        filter_passed, reason = self.check_anti_trap_filter(
            ticker, price, bid, ask, timestamp
        )
        
        if not filter_passed:
            # 디버그: 필터 실패 로그 (실제 운영에서는 로그 레벨 조정)
            # print(f"[{self.name}] {ticker} Anti-Trap 실패: {reason}")
            return None
        
        # === 🔥 BUY Signal 생성 ===
        # Step 2.4.3: 기술 지표 메타데이터 추가
        context = self._watchlist_context.get(ticker, {})
        last_close = context.get("last_close", price)
        
        # ATR 계산 (일봉 데이터가 없으면 기본값 사용)
        # 실제로는 context에 일봉 데이터를 저장해서 계산해야 하지만,
        # 여기서는 간단히 현재가 기반으로 춤정
        atr = price * 0.03  # 기본값: 3% 변동성 가정
        
        # SL/TP 레벨 계산
        levels = DynamicStopLoss.calculate_levels(price, atr)
        
        # VWAP (단순화: 일봉 last_close 사용, 실제로는 비동기 계산 필요)
        vwap = last_close
        
        signal = Signal(
            action="BUY",
            ticker=ticker,
            confidence=ignition_score / 100.0,  # 0.0 ~ 1.0
            reason=f"Ignition Score {ignition_score:.1f} >= {threshold}",
            metadata={
                "ignition_score": ignition_score,
                "price": price,
                "volume": volume,
                "timestamp": timestamp.isoformat(),
                # Step 2.4.3: 기술 지표 추가
                "indicators": {
                    "vwap": round(vwap, 4),
                    "atr": round(atr, 4),
                    "above_vwap": price > vwap,
                },
                "sl_tp": {
                    "stop_loss": round(levels.stop_loss, 4),
                    "take_profit_1": round(levels.take_profit_1, 4),
                    "take_profit_2": round(levels.take_profit_2, 4),
                    "take_profit_3": round(levels.take_profit_3, 4),
                    "risk_amount": round(levels.risk_amount, 4),
                },
            }
        )
        
        print(f"[{self.name}] 🔥 BUY Signal: {ticker} @ ${price:.2f} "
              f"(Ignition: {ignition_score:.1f}, SL: ${levels.stop_loss:.2f})")
        
        return signal
    
    def on_bar(self, ticker: str, ohlcv: dict) -> Optional[Signal]:
        """
        분봉/일봉 처리 → Signal 반환
        
        일봉 완성 시 Accumulation Score 재계산에 활용.
        현재는 stub으로 None 반환.
        
        Args:
            ticker: 종목 코드
            ohlcv: OHLCV 딕셔너리
            
        Returns:
            None (미구현)
        """
        # TODO: 일봉 완성 시 Watchlist 갱신
        return None
    
    def on_order_filled(self, order: Any) -> None:
        """
        주문 체결 콜백
        
        체결 시 Double Tap 등 후속 로직에 활용.
        현재는 로그만 출력.
        
        Args:
            order: 체결된 주문 정보
        """
        print(f"[{self.name}] 주문 체결: {order}")
    
    # ═══════════════════════════════════════════════════════════════════
    # Configuration Layer
    # ═══════════════════════════════════════════════════════════════════
    
    def get_config(self) -> dict:
        """
        전략 설정값 반환 (GUI 표시용)
        
        Returns:
            dict: 현재 설정 딕셔너리
        """
        return self.config
    
    def set_config(self, config: dict) -> None:
        """
        전략 설정값 변경 (런타임)
        
        Args:
            config: 변경할 설정 (value만 변경)
        """
        for key, value in config.items():
            if key in self.config:
                if isinstance(value, dict) and "value" in value:
                    self.config[key]["value"] = value["value"]
                else:
                    self.config[key]["value"] = value
    
    # ═══════════════════════════════════════════════════════════════════
    # Watchlist 관리
    # ═══════════════════════════════════════════════════════════════════
    
    def get_watchlist(self) -> List[str]:
        """현재 Watchlist 반환"""
        return self._watchlist
    
    def set_watchlist(self, tickers: List[str]) -> None:
        """Watchlist 설정"""
        self._watchlist = tickers[:50]  # 최대 50개
        print(f"[{self.name}] Watchlist 갱신: {len(self._watchlist)}개 종목")


# ═══════════════════════════════════════════════════════════════════════════
# 단위 테스트 / 데모
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """
    이 스크립트를 직접 실행하면 전략 기능 테스트를 수행합니다.
    
    실행:
        python backend/strategies/seismograph.py
    """
    import pandas as pd
    
    print("=" * 60)
    print("Seismograph Strategy 테스트")
    print("=" * 60)
    
    # 전략 생성
    strategy = SeismographStrategy()
    print(f"\n✓ 전략 생성: {strategy.name} v{strategy.version}")
    print(f"  설명: {strategy.description}")
    
    # Universe Filter 확인
    universe = strategy.get_universe_filter()
    print(f"\n✓ Universe Filter:")
    for key, value in universe.items():
        print(f"    {key}: {value}")
    
    # Mock 일봉 데이터 생성
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=30)
    mock_data = pd.DataFrame({
        'open': 5.0 + np.random.randn(30) * 0.1,
        'high': 5.1 + np.random.randn(30) * 0.1,
        'low': 4.9 + np.random.randn(30) * 0.1,
        'close': 5.0 + np.random.randn(30) * 0.1,
        'volume': [100000] * 27 + [500000, 50000, 30000],  # 마지막에 스파이크 + 드라이아웃
    }, index=dates)
    
    # Accumulation Score 계산
    score = strategy.calculate_watchlist_score("TEST", mock_data)
    print(f"\n✓ Accumulation Score: {score:.1f}점")
    
    # 개별 신호 확인
    print(f"\n개별 신호 점수:")
    print(f"  - 매집봉: {strategy._check_accumulation_bar(mock_data) * 30:.0f}점")
    print(f"  - OBV Divergence: {strategy._check_obv_divergence(mock_data) * 40:.0f}점")
    print(f"  - Volume Dry-out: {strategy._check_volume_dryout(mock_data) * 20:.0f}점")
    print(f"  - Tight Range: {strategy._check_tight_range(mock_data) * 10:.0f}점")
    
    # 설정 변경 테스트
    print(f"\n✓ 설정 변경 테스트:")
    print(f"  변경 전 accumulation_threshold: {strategy.config['accumulation_threshold']['value']}")
    strategy.set_config({"accumulation_threshold": {"value": 55}})
    print(f"  변경 후 accumulation_threshold: {strategy.config['accumulation_threshold']['value']}")
    
    # ═══════════════════════════════════════════════════════════════════
    # Phase 2: Ignition Score 테스트
    # ═══════════════════════════════════════════════════════════════════
    print(f"\n{'=' * 60}")
    print("Phase 2: Ignition Score 테스트")
    print("=" * 60)
    
    # 전략 초기화
    strategy.initialize()
    print(f"\n✓ 전략 초기화 완료")
    
    # Watchlist에 테스트 종목 추가
    strategy.set_watchlist(["TEST"])
    
    # Mock 틱 데이터 생성 (폭발 시나리오)
    print(f"\n✓ Mock 틱 데이터 생성 (폭발 시나리오):")
    now = datetime.now()
    
    # 60초 동안 활발한 틱 시뮬레이션
    for i in range(100):
        tick_time = now - timedelta(seconds=60-i*0.6)
        side = "B" if i % 3 != 0 else "S"  # 66% 매수
        strategy.on_tick(
            ticker="TEST",
            price=5.50 + i * 0.01,
            volume=1000 + i * 100,
            timestamp=tick_time,
            side=side,
            bid=5.48,
            ask=5.52
        )
    
    print(f"  - 틱 버퍼 크기: {len(strategy._tick_buffer.get('TEST', []))}")
    
    # 박스권 설정 (테스트용)
    strategy._box_range["TEST"] = (5.50, 5.00)
    print(f"  - 박스권 설정: 고점=${5.50}, 저점=${5.00}")
    
    # 분봉 버퍼 설정 (테스트용)
    strategy._bar_1m["TEST"] = [
        {"volume": 10000},
        {"volume": 12000},
        {"volume": 11000},
        {"volume": 13000},
        {"volume": 10000},
        {"volume": 80000},  # 최근 1분 폭발!
    ]
    print(f"  - 1분봉 버퍼: 마지막 거래량 80,000 (5분 평균의 ~7배)")
    
    # Ignition Score 계산
    ignition = strategy.calculate_trigger_score("TEST")
    print(f"\n✓ Ignition Score: {ignition:.1f}점")
    
    # 개별 Ignition 신호 확인
    print(f"\n개별 Ignition 신호:")
    print(f"  - Tick Velocity: {strategy._calculate_tick_velocity('TEST') * 35:.1f}점")
    print(f"  - Volume Burst: {strategy._calculate_volume_burst('TEST') * 30:.1f}점")
    print(f"  - Price Break: {strategy._calculate_price_break('TEST') * 20:.1f}점")
    print(f"  - Buy Pressure: {strategy._calculate_buy_pressure('TEST') * 15:.1f}점")
    
    # Anti-Trap 필터 테스트
    print(f"\n✓ Anti-Trap 필터 테스트:")
    # 장 시작 후 충분한 시간이 지난 것으로 설정 (테스트용)
    test_time = datetime.combine(now.date(), dt_time(10, 0))  # 10:00 AM
    passed, reason = strategy.check_anti_trap_filter(
        "TEST", 6.05, 6.02, 6.05, test_time
    )
    print(f"  - 결과: {'통과 ✓' if passed else '실패 ✗'} ({reason})")
    
    print("\n" + "=" * 60)
    print("모든 테스트 완료! ✓")
    print("=" * 60)

