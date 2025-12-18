# ============================================================================
# Random Walker Strategy - 테스트용 더미 전략
# ============================================================================
# 📌 이 파일의 역할:
#   StrategyBase 인터페이스가 제대로 작동하는지 테스트하기 위한 더미 전략입니다.
#   무작위로 BUY/SELL 신호를 생성하므로, 실제 거래에는 절대 사용하면 안 됩니다!
#
# 📌 왜 필요한가?
#   - StrategyBase ABC의 모든 abstractmethod가 구현 가능한지 확인
#   - 엔진-전략 연동 테스트
#   - GUI 전략 선택 기능 테스트
#
# ⚠️ 경고: 이 전략은 테스트 전용입니다. 실제 거래 금지!
# ============================================================================

"""
Random Walker Strategy

무작위로 BUY/SELL 신호를 생성하는 테스트 전용 전략입니다.
StrategyBase 인터페이스 검증용으로만 사용하세요.

⚠️ WARNING: DO NOT USE FOR REAL TRADING!
"""

import random
from datetime import datetime
from typing import Any, Optional

# 상대 경로 import (backend 폴더에서 실행 시)
# 전략 파일은 strategies/ 폴더에 있고, StrategyBase는 core/ 폴더에 있음
import sys
from pathlib import Path

# backend 폴더를 경로에 추가 (상대 import 지원)
backend_path = Path(__file__).parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from core.strategy_base import StrategyBase, Signal


class RandomWalkerStrategy(StrategyBase):
    """
    Random Walker - 테스트용 더미 전략
    
    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    동전 던지기로 매매 결정을 하는 "전략"입니다.
    
    물론 이건 진짜 전략이 아니에요! 😅
    "전략 인터페이스가 제대로 작동하나?" 테스트용입니다.
    
    - 5% 확률로 BUY 신호
    - 5% 확률로 SELL 신호
    - 90% 확률로 아무것도 안 함 (None 반환)
    
    ⚠️ 절대로 실제 돈으로 이 전략을 사용하지 마세요!
    
    ═══════════════════════════════════════════════════════════════════════
    사용 예시:
    ═══════════════════════════════════════════════════════════════════════
    
    >>> strategy = RandomWalkerStrategy()
    >>> strategy.initialize()
    >>> 
    >>> # 틱 데이터 처리
    >>> signal = strategy.on_tick("AAPL", 150.25, 100, datetime.now())
    >>> if signal:
    ...     print(f"신호: {signal.action} - {signal.reason}")
    """
    
    # ═══════════════════════════════════════════════════════════════════
    # 전략 메타정보
    # ═══════════════════════════════════════════════════════════════════
    
    name = "Random Walker"
    version = "1.0.0"
    description = "테스트용 무작위 신호 생성 전략 (실거래 금지!)"
    
    def __init__(self):
        """
        전략 초기화
        
        설정 파라미터:
        - signal_probability: 신호 발생 확률 (기본 5%)
        - random_seed: 난수 시드 (재현성용)
        """
        # 설정값 정의 (value, min, max, description)
        self.config = {
            "signal_probability": {
                "value": 0.05,      # 5% 확률
                "min": 0.01,
                "max": 0.50,
                "description": "틱당 신호 발생 확률 (0.05 = 5%)"
            },
            "random_seed": {
                "value": None,
                "min": None,
                "max": None,
                "description": "난수 시드 (None이면 랜덤)"
            }
        }
        
        # 내부 상태
        self._tick_count = 0
        self._signal_count = 0
        self._last_signal: Optional[Signal] = None
    
    # ═══════════════════════════════════════════════════════════════════
    # Scanning Layer (Phase 1 & 2) - 더미 구현
    # ═══════════════════════════════════════════════════════════════════
    
    def get_universe_filter(self) -> dict:
        """
        Universe 필터 조건 반환 (더미)
        
        RandomWalker는 아무 종목이나 받으므로,
        필터 조건을 매우 넓게 설정합니다.
        """
        return {
            "price_min": 0.01,       # 거의 모든 종목
            "price_max": 10000.0,
            "market_cap_min": 0,
            "market_cap_max": float("inf"),
            "avg_volume_min": 0,
        }
    
    def calculate_watchlist_score(self, ticker: str, daily_data: Any) -> float:
        """
        Watchlist 점수 계산 (더미)
        
        무작위 점수를 반환합니다.
        """
        return random.uniform(0, 100)
    
    def calculate_trigger_score(
        self, 
        ticker: str, 
        tick_data: Any, 
        bar_data: Any
    ) -> float:
        """
        Trigger 점수 계산 (더미)
        
        무작위 점수를 반환합니다.
        """
        return random.uniform(0, 100)
    
    def get_anti_trap_filter(self) -> dict:
        """
        Anti-Trap 필터 조건 반환 (더미)
        
        필터를 거의 통과시킵니다.
        """
        return {
            "max_spread_pct": 100.0,       # 스프레드 제한 없음
            "min_minutes_after_open": 0,   # 개장 직후도 OK
            "must_above_vwap": False,      # VWAP 조건 무시
        }
    
    # ═══════════════════════════════════════════════════════════════════
    # Trading Layer - 핵심 로직
    # ═══════════════════════════════════════════════════════════════════
    
    def initialize(self) -> None:
        """
        전략 초기화
        
        난수 시드 설정 및 카운터 초기화.
        """
        seed = self.config["random_seed"]["value"]
        if seed is not None:
            random.seed(seed)
        
        self._tick_count = 0
        self._signal_count = 0
        self._last_signal = None
        
        print(f"[{self.name}] 초기화 완료 (signal_prob: "
              f"{self.config['signal_probability']['value']:.1%})")
    
    def on_tick(
        self, 
        ticker: str, 
        price: float, 
        volume: int, 
        timestamp: Any
    ) -> Optional[Signal]:
        """
        틱 데이터 처리 → Signal 반환
        
        ═══════════════════════════════════════════════════════════════
        구현 로직:
        ═══════════════════════════════════════════════════════════════
        1. 틱 카운터 증가
        2. signal_probability 확률로 신호 생성 여부 결정
        3. 신호 생성 시 BUY/SELL 랜덤 선택 (50:50)
        4. Signal 객체 생성 및 반환
        
        Args:
            ticker: 종목 코드
            price: 체결 가격
            volume: 체결 수량
            timestamp: 체결 시간
        
        Returns:
            Signal 또는 None
        """
        self._tick_count += 1
        prob = self.config["signal_probability"]["value"]
        
        # 확률적으로 신호 생성
        if random.random() < prob:
            # BUY 또는 SELL 랜덤 선택
            action = random.choice(["BUY", "SELL"])
            
            # 신뢰도도 랜덤 (0.5 ~ 1.0)
            confidence = random.uniform(0.5, 1.0)
            
            signal = Signal(
                action=action,
                ticker=ticker,
                confidence=confidence,
                reason=f"RandomWalker 무작위 신호 (tick #{self._tick_count})",
                metadata={
                    "price": price,
                    "volume": volume,
                    "tick_count": self._tick_count,
                    "strategy": self.name,
                }
            )
            
            self._signal_count += 1
            self._last_signal = signal
            
            return signal
        
        return None
    
    def on_bar(self, ticker: str, ohlcv: dict) -> Optional[Signal]:
        """
        분봉/일봉 처리 → Signal 반환
        
        RandomWalker는 틱 레벨에서만 동작하므로,
        봉 데이터는 무시하고 None을 반환합니다.
        """
        # 봉 데이터는 무시
        return None
    
    def on_order_filled(self, order: Any) -> None:
        """
        주문 체결 콜백
        
        체결 정보를 로그로 출력합니다.
        """
        print(f"[{self.name}] 주문 체결: {order}")
    
    # ═══════════════════════════════════════════════════════════════════
    # Configuration Layer
    # ═══════════════════════════════════════════════════════════════════
    
    def get_config(self) -> dict:
        """
        전략 설정값 반환
        """
        return self.config
    
    def set_config(self, config: dict) -> None:
        """
        전략 설정값 변경
        
        Args:
            config: 변경할 설정 (예: {"signal_probability": {"value": 0.1}})
        """
        for key, value in config.items():
            if key in self.config:
                if isinstance(value, dict) and "value" in value:
                    self.config[key]["value"] = value["value"]
                else:
                    self.config[key]["value"] = value
        
        print(f"[{self.name}] 설정 변경됨: {config}")
    
    # ═══════════════════════════════════════════════════════════════════
    # 추가 유틸리티 메서드
    # ═══════════════════════════════════════════════════════════════════
    
    def get_stats(self) -> dict:
        """
        전략 통계 반환
        
        Returns:
            dict: 틱 수, 신호 수, 신호 비율 등
        """
        return {
            "tick_count": self._tick_count,
            "signal_count": self._signal_count,
            "signal_ratio": (
                self._signal_count / self._tick_count 
                if self._tick_count > 0 else 0
            ),
            "last_signal": (
                self._last_signal.to_dict() 
                if self._last_signal else None
            ),
        }


# ═══════════════════════════════════════════════════════════════════════════
# 모듈 레벨 테스트 코드
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from core.mock_data import MockPriceFeed
    
    print("=" * 60)
    print("RandomWalker 전략 테스트")
    print("=" * 60)
    
    # 1. 전략 인스턴스 생성
    strategy = RandomWalkerStrategy()
    print(f"\n전략 정보:")
    print(f"  이름: {strategy.name}")
    print(f"  버전: {strategy.version}")
    print(f"  설명: {strategy.description}")
    
    # 2. 초기화
    strategy.set_config({"random_seed": {"value": 42}})
    strategy.initialize()
    
    # 3. Mock 데이터로 틱 처리 테스트
    print("\n틱 처리 테스트 (100 ticks):")
    feed = MockPriceFeed(mode="random_walk", seed=42)
    
    signals_generated = []
    for i in range(100):
        tick = feed.generate_tick()
        signal = strategy.on_tick(
            ticker=tick["ticker"],
            price=tick["price"],
            volume=tick["volume"],
            timestamp=tick["timestamp"]
        )
        if signal:
            signals_generated.append(signal)
            print(f"  🎯 신호 발생! {signal.action} @ ${tick['price']:.2f} "
                  f"(conf: {signal.confidence:.2f})")
    
    # 4. 통계 출력
    stats = strategy.get_stats()
    print(f"\n통계:")
    print(f"  처리된 틱: {stats['tick_count']}")
    print(f"  생성된 신호: {stats['signal_count']}")
    print(f"  신호 비율: {stats['signal_ratio']:.1%}")
    
    # 5. 설정 변경 테스트
    print("\n설정 변경 테스트:")
    strategy.set_config({"signal_probability": {"value": 0.20}})
    print(f"  새 확률: {strategy.config['signal_probability']['value']:.0%}")
    
    print("\n모든 테스트 완료! ✓")
