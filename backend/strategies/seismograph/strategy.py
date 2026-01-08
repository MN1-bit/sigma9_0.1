# ============================================================================
# Seismograph Strategy - 매집 탐지 + 폭발 포착 전략
# ============================================================================
# 📌 [03-002] 완전 마이그레이션:
#   - 기존 2,286줄 → ~400줄 (signals/, scoring/ 모듈 사용)
#   - 원본 백업: docs/archive/seismograph_backup.py
# ============================================================================

"""
Seismograph Strategy Module

미국 마이크로캡 주식에서 세력의 매집(Accumulation)을 사전 탐지하고,
폭발 순간(Ignition)을 포착하는 2단계 전략입니다.

[03-002] 리팩터링:
- signals/ 모듈: 개별 시그널 강도 계산
- scoring/ 모듈: 점수 계산 (V1, V2, V3)
"""

from typing import Any, Optional, Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta, time as dt_time
from collections import deque

from backend.core.strategy_base import StrategyBase, Signal
from backend.core.interfaces.scoring import ScoringStrategy

# 분리된 모듈 임포트
from .signals import (
    calc_tight_range_intensity,
    calc_obv_divergence_intensity,
    calc_accumulation_bar_intensity,
    calc_volume_dryout_intensity,
    calc_tight_range_intensity_v3,
    calc_absorption_intensity_v3,
    calc_accumulation_bar_intensity_v3,
    calc_volume_dryout_intensity_v3,
)
from .scoring import (
    calculate_score_v1,
    calculate_score_v2,
    calculate_score_v3,
    SCORE_WEIGHTS,
    V3_WEIGHTS,
)
from backend.models import TickData, WatchlistItem


class SeismographStrategy(StrategyBase, ScoringStrategy):
    """
    Seismograph (지진계) 전략
    
    세력의 매집을 탐지하는 것이 마치 지진 전 미세한 진동을 감지하는 것과 같아서
    "Seismograph"라는 이름이 붙었습니다.
    
    ═══════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════
    큰 지진(주가 급등) 전에는 미세한 진동(매집 신호)이 있습니다.
    이 전략은 그 진동을 감지해서 "곧 폭발할 종목"을 미리 찾아냅니다.
    
    1. Phase 1 (매일 아침):
       - 모든 종목을 스캔해서 "매집 점수" 계산
       - 점수 높은 50개를 Watchlist에 추가
    
    2. Phase 2 (장중 실시간):
       - Watchlist 종목들을 실시간 감시
       - "폭발 순간" 포착되면 매수 신호
    """
    
    # ═══════════════════════════════════════════════════════════════════
    # 클래스 속성 (메타정보)
    # ═══════════════════════════════════════════════════════════════════
    
    name = "Seismograph"
    version = "2.0.0"  # 03-002 마이그레이션 버전
    description = "매집 탐지 + 폭발 포착 2단계 전략 (Sigma9 Core)"
    
    def __init__(self) -> None:
        """
        전략 초기화
        
        설정 파라미터를 초기화합니다.
        각 파라미터는 value(현재값), min(최소), max(최대), description(설명)을 가집니다.
        """
        # === Scanning 파라미터 (Phase 1) ===
        self.config: Dict[str, Dict[str, Any]] = {
            "accumulation_threshold": {
                "value": 60, "min": 40, "max": 80,
                "description": "Watchlist 진입 기준 점수 (0~100)"
            },
            "spike_volume_multiplier": {
                "value": 3.0, "min": 2.0, "max": 5.0,
                "description": "매집봉 인식 거래량 배수"
            },
            "obv_lookback": {
                "value": 20, "min": 10, "max": 30,
                "description": "OBV 다이버전스 관찰 기간 (일)"
            },
            "dryout_threshold": {
                "value": 0.4, "min": 0.3, "max": 0.6,
                "description": "거래량 마름 기준 (평균 대비 비율)"
            },
            "atr_ratio_threshold": {
                "value": 0.5, "min": 0.3, "max": 0.7,
                "description": "Tight Range 인식 ATR 비율"
            },
        }
        
        # === Trigger 파라미터 (Phase 2) ===
        self.config.update({
            "ignition_threshold": {
                "value": 70, "min": 50, "max": 90,
                "description": "진입 신호 기준 점수 (0~100)"
            },
            "tick_velocity_multiplier": {
                "value": 8.0, "min": 4.0, "max": 15.0,
                "description": "틱 속도 인식 배수"
            },
            "volume_burst_multiplier": {
                "value": 6.0, "min": 3.0, "max": 12.0,
                "description": "거래량 폭발 인식 배수"
            },
            "price_break_pct": {
                "value": 0.5, "min": 0.3, "max": 1.0,
                "description": "박스권 돌파 인식 퍼센트 (%)"
            },
            "buy_pressure_ratio": {
                "value": 1.8, "min": 1.5, "max": 2.5,
                "description": "매수 압력 비율 (매수/매도)"
            },
            "max_spread_pct": {
                "value": 1.0, "min": 0.5, "max": 2.0,
                "description": "최대 허용 스프레드 (%)"
            },
            "min_minutes_after_open": {
                "value": 15, "min": 5, "max": 30,
                "description": "개장 후 최소 경과 시간 (분)"
            },
        })
        
        # === 내부 상태 ===
        self._watchlist: List[str] = []
        self._watchlist_context: Dict[str, Dict[str, Any]] = {}
        self._tick_buffer: Dict[str, deque] = {}
        self._bar_1m: Dict[str, List[Dict]] = {}
        self._vwap: Dict[str, float] = {}
        self._box_range: Dict[str, Tuple[float, float]] = {}
        self._market_open_time = dt_time(9, 30)
    
    # ═══════════════════════════════════════════════════════════════════
    # Scanning Layer (Phase 1)
    # ═══════════════════════════════════════════════════════════════════
    
    def get_universe_filter(self) -> dict:
        """Universe 필터 조건 반환"""
        return {
            "price_min": 2.00,
            "price_max": 10.00,
            "market_cap_min": 50_000_000,
            "market_cap_max": 300_000_000,
            "float_max": 15_000_000,
            "avg_volume_min": 100_000,
            "change_pct_min": 0.0,
            "change_pct_max": 5.0,
        }
    
    # ═══════════════════════════════════════════════════════════════════
    # Score Calculation (signals/, scoring/ 모듈 사용)
    # ═══════════════════════════════════════════════════════════════════
    
    def _calculate_signal_intensities(self, data: Any) -> Dict[str, float]:
        """
        V2 시그널 강도 계산 - signals/ 모듈 호출
        
        [03-002] 기존 내부 메서드 → 외부 모듈 호출로 변경
        """
        return {
            "tight_range": calc_tight_range_intensity(data),
            "obv_divergence": calc_obv_divergence_intensity(
                data, 
                obv_lookback=self.config["obv_lookback"]["value"]
            ),
            "accumulation_bar": calc_accumulation_bar_intensity(data),
            "volume_dryout": calc_volume_dryout_intensity(
                data,
                dryout_threshold=self.config["dryout_threshold"]["value"]
            ),
        }
    
    def _calculate_signal_intensities_v3(
        self, 
        data: Any,
        current_vwap: Optional[float] = None
    ) -> Dict[str, float]:
        """
        V3 시그널 강도 계산 - signals/ 모듈 호출
        """
        return {
            "tight_range": calc_tight_range_intensity_v3(data),
            "obv_divergence": calc_absorption_intensity_v3(data),
            "accumulation_bar": calc_accumulation_bar_intensity_v3(data),
            "volume_dryout": calc_volume_dryout_intensity_v3(
                data,
                dryout_threshold=self.config["dryout_threshold"]["value"]
            ),
        }
    
    def calculate_watchlist_score(self, ticker: str, daily_data: Any) -> float:
        """
        V1: Stage-Based Priority 점수 계산
        
        [03-002] scoring/ 모듈 위임
        """
        signal_funcs = {
            "tight_range": calc_tight_range_intensity,
            "accumulation_bar": calc_accumulation_bar_intensity,
            "obv_divergence": lambda d: calc_obv_divergence_intensity(d, self.config["obv_lookback"]["value"]),
            "volume_dryout": lambda d: calc_volume_dryout_intensity(d, self.config["dryout_threshold"]["value"]),
        }
        return calculate_score_v1(daily_data, signal_funcs)
    
    def calculate_watchlist_score_v2(self, ticker: str, daily_data: Any) -> float:
        """
        V2: 가중합 기반 연속 점수 계산
        
        [03-002] scoring/ 모듈 위임
        """
        if daily_data is None or len(daily_data) < 5:
            return 0.0
        
        intensities = self._calculate_signal_intensities(daily_data)
        return calculate_score_v2(daily_data, intensities)
    
    def calculate_watchlist_score_v3(
        self, 
        ticker: str, 
        daily_data: Any,
        current_vwap: Optional[float] = None
    ) -> float:
        """
        V3: Pinpoint Algorithm
        
        [03-002] scoring/ 모듈 위임
        """
        if daily_data is None or len(daily_data) < 5:
            return 0.0
        
        intensities = self._calculate_signal_intensities_v3(daily_data, current_vwap)
        return calculate_score_v3(daily_data, intensities)
    
    # ═══════════════════════════════════════════════════════════════════
    # Phase 2: Trigger Detection (기존 로직 유지)
    # ═══════════════════════════════════════════════════════════════════
    
    def add_tick(self, ticker: str, tick: TickData) -> None:
        """틱 데이터 추가"""
        if ticker not in self._tick_buffer:
            self._tick_buffer[ticker] = deque(maxlen=1000)
        self._tick_buffer[ticker].append(tick)
    
    def calculate_trigger_score(self, ticker: str) -> float:
        """
        Ignition Score 계산 (Phase 2)
        
        실시간 틱 데이터 기반으로 폭발 순간을 감지합니다.
        """
        if ticker not in self._tick_buffer or len(self._tick_buffer[ticker]) < 10:
            return 0.0
        
        ticks = list(self._tick_buffer[ticker])
        
        # 간단한 Trigger Score 계산
        recent_volume = sum(t.volume for t in ticks[-10:])
        older_volume = sum(t.volume for t in ticks[-60:-10]) if len(ticks) >= 60 else recent_volume
        
        if older_volume <= 0:
            return 0.0
        
        volume_burst = recent_volume / (older_volume / 5)  # 10초 vs 평균 50초
        
        # 0~100 스케일로 변환
        score = min(100.0, volume_burst * 20)
        return round(score, 1)
    
    def get_watchlist(self) -> List[str]:
        """현재 Watchlist 반환"""
        return self._watchlist.copy()
    
    def set_watchlist(self, tickers: List[str]) -> None:
        """Watchlist 설정"""
        self._watchlist = tickers.copy()
    
    # ═══════════════════════════════════════════════════════════════════
    # StrategyBase 추상 메서드 구현
    # ═══════════════════════════════════════════════════════════════════
    
    def initialize(self) -> None:
        """전략 초기화 (1회 호출)"""
        self._watchlist = []
        self._watchlist_context = {}
        self._tick_buffer = {}
        self._bar_1m = {}
        self._vwap = {}
        self._box_range = {}
    
    def on_tick(
        self, 
        ticker: str, 
        price: float, 
        volume: int, 
        timestamp: datetime
    ) -> Optional[Signal]:
        """틱 데이터 처리 → Signal 반환"""
        # 틱 버퍼에 추가
        # [08-001] timestamp → event_time 변경
        tick = TickData(price=price, volume=volume, event_time=timestamp)
        self.add_tick(ticker, tick)
        
        # Trigger Score 계산
        trigger_score = self.calculate_trigger_score(ticker)
        threshold = self.config["ignition_threshold"]["value"]
        
        if trigger_score >= threshold:
            return Signal(
                action="BUY",
                ticker=ticker,
                price=price,
                quantity=0,  # 추후 position sizing
                timestamp=timestamp,
                reason=f"Ignition Score {trigger_score:.1f} >= {threshold}",
            )
        return None
    
    def on_bar(
        self, 
        ticker: str, 
        bar_data: Dict[str, Any]
    ) -> Optional[Signal]:
        """분봉/일봉 처리 → Signal 반환"""
        # 현재는 틱 기반이므로 Pass
        return None
    
    def on_order_filled(
        self, 
        ticker: str, 
        order_id: str, 
        filled_price: float, 
        filled_quantity: int
    ) -> None:
        """주문 체결 시 콜백"""
        # 로깅 또는 포지션 업데이트
        pass
    
    def get_config(self) -> Dict[str, Dict[str, Any]]:
        """현재 설정값 반환"""
        return self.config.copy()
    
    def set_config(self, key: str, value: Any) -> None:
        """설정값 변경 (런타임)"""
        if key in self.config:
            self.config[key]["value"] = value
    
    def get_anti_trap_filter(self) -> Dict[str, Any]:
        """Anti-Trap 필터 조건 반환"""
        return {
            "max_spread_pct": self.config["max_spread_pct"]["value"],
            "min_minutes_after_open": self.config["min_minutes_after_open"]["value"],
        }
    
    def calculate_watchlist_score_detailed(
        self, 
        ticker: str, 
        daily_data: Any
    ) -> Dict[str, Any]:
        """상세 점수 계산 (개별 시그널 포함)
        
        [03-002 FIX] score_v3, intensities_v3 추가
        """
        if daily_data is None or len(daily_data) < 5:
            return {
                "ticker": ticker,
                "score": 0.0,
                "score_v2": 0.0,
                "score_v3": -1,  # 데이터 부족
                "intensities": {},
                "intensities_v3": {},
                "stage": "신규/IPO (데이터 부족)",
                "stage_number": 0,
                "signals": {},
                "can_trade": False,
            }
        
        # V2 계산
        intensities = self._calculate_signal_intensities(daily_data)
        score = calculate_score_v2(daily_data, intensities)
        
        # V3 계산 [03-002 FIX]
        intensities_v3 = self._calculate_signal_intensities_v3(daily_data)
        score_v3 = calculate_score_v3(daily_data, intensities_v3)
        
        # Stage 결정
        tr = intensities.get("tight_range", 0)
        obv = intensities.get("obv_divergence", 0)
        
        if tr > 0.5 and obv > 0.5:
            stage = "Stage 4 (Tight Range + OBV)"
            stage_number = 4
        elif tr > 0.5:
            stage = "Stage 4 (Tight Range)"
            stage_number = 4
        elif obv > 0.5:
            stage = "Stage 2 (OBV Divergence)"
            stage_number = 2
        else:
            stage = "Stage 1 (Monitoring)"
            stage_number = 1
        
        # Signals 구성
        signals = {
            "tight_range": tr > 0.3,
            "accumulation_bar": intensities.get("accumulation_bar", 0) > 0.3,
            "obv_divergence": obv > 0.3,
            "volume_dryout": intensities.get("volume_dryout", 0) > 0.3,
        }
        
        # can_trade 결정 (Stage 4면 거래 가능)
        can_trade = stage_number >= 4 or score_v3 > 50
        
        return {
            "ticker": ticker,
            "score": score,
            "score_v2": score,
            "score_v3": score_v3,           # [03-002 FIX] V3 점수 추가
            "intensities": intensities,
            "intensities_v3": intensities_v3,  # [03-002 FIX] V3 강도 추가
            "stage": stage,
            "stage_number": stage_number,
            "signals": signals,
            "can_trade": can_trade,
        }

