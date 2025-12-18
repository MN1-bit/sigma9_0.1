# ============================================================================
# Strategy Template - 새 전략 개발용 템플릿
# ============================================================================
# 📌 사용법:
#   1. 이 파일을 복사하여 새 이름으로 저장 (예: my_strategy.py)
#   2. 클래스 이름과 메타정보 수정
#   3. 모든 abstractmethod 구현
#   4. GUI에서 전략 선택 → 자동 로드!
#
# ⚠️ 주의:
#   - 파일명이 '_'로 시작하면 StrategyLoader가 무시합니다.
#   - 이 파일은 템플릿이므로 '_template.py'로 유지하세요.
# ============================================================================

"""
Strategy Template

새 전략 개발 시 이 파일을 복사하여 사용하세요.
모든 전략은 StrategyBase를 상속받아야 합니다.

Example:
    cp _template.py my_awesome_strategy.py
    # 클래스 구현 후 GUI에서 선택
"""

from typing import Any, Optional

# 상대 경로 import
import sys
from pathlib import Path

# backend 폴더를 경로에 추가
backend_path = Path(__file__).parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from core.strategy_base import StrategyBase, Signal


class TemplateStrategy(StrategyBase):
    """
    전략 템플릿 클래스
    
    ═══════════════════════════════════════════════════════════════════════
    이 클래스를 복사하여 새 전략을 구현하세요.
    아래 모든 abstractmethod를 반드시 구현해야 합니다.
    ═══════════════════════════════════════════════════════════════════════
    
    사용 방법:
    1. 이 파일을 복사: cp _template.py my_strategy.py
    2. 클래스 이름 변경: TemplateStrategy → MyStrategy
    3. 메타정보 수정: name, version, description
    4. 모든 메서드 구현
    5. GUI에서 전략 선택!
    """
    
    # ═══════════════════════════════════════════════════════════════════
    # 전략 메타정보 (필수 - 반드시 수정하세요!)
    # ═══════════════════════════════════════════════════════════════════
    name = "Template Strategy"      # 전략 이름 (GUI 표시용)
    version = "1.0.0"               # 버전
    description = "새 전략 개발 템플릿"  # 설명
    
    def __init__(self):
        """
        전략 초기화
        
        config 딕셔너리: 각 파라미터는 value, min, max, description을 포함
        이 값들은 GUI에서 표시되고 사용자가 조정할 수 있습니다.
        """
        self.config = {
            "example_param": {
                "value": 10,        # 현재 값
                "min": 1,           # 최소값
                "max": 100,         # 최대값
                "description": "예시 파라미터"  # 설명
            }
        }
    
    # ═══════════════════════════════════════════════════════════════════
    # Scanning Layer (Phase 1 & 2)
    # ═══════════════════════════════════════════════════════════════════
    
    def get_universe_filter(self) -> dict:
        """Universe 필터 조건 반환"""
        # TODO: 구현하세요
        return {
            "price_min": 2.00,
            "price_max": 10.00,
            "market_cap_min": 50e6,
            "market_cap_max": 300e6,
            "avg_volume_min": 100000,
        }
    
    def calculate_watchlist_score(self, ticker: str, daily_data: Any) -> float:
        """일봉 기반 Watchlist 점수 계산 (0~100)"""
        # TODO: 구현하세요
        return 0.0
    
    def calculate_trigger_score(
        self, 
        ticker: str, 
        tick_data: Any, 
        bar_data: Any
    ) -> float:
        """실시간 Trigger 점수 계산 (0~100)"""
        # TODO: 구현하세요
        return 0.0
    
    def get_anti_trap_filter(self) -> dict:
        """Anti-Trap 필터 조건 반환"""
        # TODO: 구현하세요
        return {
            "max_spread_pct": 1.0,
            "min_minutes_after_open": 15,
            "must_above_vwap": True,
        }
    
    # ═══════════════════════════════════════════════════════════════════
    # Trading Layer
    # ═══════════════════════════════════════════════════════════════════
    
    def initialize(self) -> None:
        """전략 초기화 (로드 시 1회 호출)"""
        # TODO: 구현하세요
        print(f"[{self.name}] 초기화 완료")
    
    def on_tick(
        self, 
        ticker: str, 
        price: float, 
        volume: int, 
        timestamp: Any
    ) -> Optional[Signal]:
        """틱 데이터 처리 → Signal 반환"""
        # TODO: 구현하세요
        # 예시: 특정 조건에서 BUY 신호 반환
        # if price > some_threshold:
        #     return Signal(
        #         action="BUY",
        #         ticker=ticker,
        #         confidence=0.8,
        #         reason="조건 충족!",
        #         metadata={"price": price}
        #     )
        return None
    
    def on_bar(self, ticker: str, ohlcv: dict) -> Optional[Signal]:
        """분봉/일봉 처리 → Signal 반환"""
        # TODO: 구현하세요
        return None
    
    def on_order_filled(self, order: Any) -> None:
        """주문 체결 콜백"""
        # TODO: 구현하세요
        print(f"[{self.name}] 주문 체결: {order}")
    
    # ═══════════════════════════════════════════════════════════════════
    # Configuration Layer
    # ═══════════════════════════════════════════════════════════════════
    
    def get_config(self) -> dict:
        """전략 설정값 반환 (GUI 표시용)"""
        return self.config
    
    def set_config(self, config: dict) -> None:
        """전략 설정값 변경 (런타임)"""
        for key, value in config.items():
            if key in self.config:
                if isinstance(value, dict) and "value" in value:
                    self.config[key]["value"] = value["value"]
                else:
                    self.config[key]["value"] = value


# ═══════════════════════════════════════════════════════════════════════════
# 모듈 레벨 코드 - 템플릿 로드 시 메시지 출력
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("Strategy Template")
    print("=" * 60)
    print("이 파일을 복사하여 새 전략을 만드세요:")
    print("  cp _template.py my_strategy.py")
    print()
    print("구현해야 할 메서드:")
    print("  - get_universe_filter()")
    print("  - calculate_watchlist_score()")
    print("  - calculate_trigger_score()")
    print("  - get_anti_trap_filter()")
    print("  - initialize()")
    print("  - on_tick()")
    print("  - on_bar()")
    print("  - on_order_filled()")
    print("  - get_config()")
    print("  - set_config()")
else:
    # 모듈로 import될 때 (StrategyLoader에서)
    # 템플릿은 '_'로 시작하므로 실제로 로드되지 않음
    pass
