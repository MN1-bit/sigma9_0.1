# ============================================================================
# Mock Data - IBKR 없이 로컬 테스트를 위한 가상 데이터 생성기
# ============================================================================
# 📌 이 파일의 역할:
#   IBKR(Interactive Brokers)에 연결하지 않고도 전략 로직을 테스트할 수 있도록
#   가상의 주가 데이터를 생성합니다.
#
# 📌 왜 필요한가?
#   - IBKR 연결 없이 개발 초기 단계에서 전략 로직 검증 가능
#   - 다양한 시장 상황(급등, 횡보, 하락 등)을 시뮬레이션
#   - 재현 가능한 테스트 케이스 생성
#
# 📌 지원 모드:
#   - random_walk: 브라운 운동 (일반 시장)
#   - sine_wave: 사인파 (예측 가능한 패턴)
#   - spike: 갑작스런 급등 (Ignition 감지 테스트)
# ============================================================================

"""
Mock Data Generator Module

IBKR 연결 없이 전략을 테스트하기 위한 가상 시장 데이터 생성기입니다.

Example:
    feed = MockPriceFeed(mode="random_walk", initial_price=10.0)

    # 단일 틱 생성
    tick = feed.generate_tick()
    print(tick)  # {"price": 10.05, "volume": 1234, "timestamp": ...}

    # OHLCV 봉 100개 생성
    bars = feed.generate_ohlcv(periods=100)
"""

import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Literal, Optional


# ═══════════════════════════════════════════════════════════════════════════
# MockPriceFeed 설정 클래스
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class MockFeedConfig:
    """
    MockPriceFeed 설정값

    가격 생성에 사용되는 파라미터들을 담고 있습니다.

    Attributes:
        initial_price (float): 시작 가격. 기본값 10.0
        volatility (float): 변동성 (가격 변화폭). 기본값 0.02 (2%)
        volume_base (int): 기본 거래량. 기본값 10000
        volume_variance (float): 거래량 변동폭. 기본값 0.5 (50%)
        tick_per_bar (int): 1개 봉을 만드는 데 필요한 틱 수. 기본값 60
    """

    initial_price: float = 10.0
    volatility: float = 0.02  # 2% 변동성
    volume_base: int = 10000
    volume_variance: float = 0.5  # 50% 변동
    tick_per_bar: int = 60  # 1분봉 = 60틱 가정


# ═══════════════════════════════════════════════════════════════════════════
# MockPriceFeed 메인 클래스
# ═══════════════════════════════════════════════════════════════════════════


class MockPriceFeed:
    """
    가상 주가 데이터 생성기

    IBKR 연결 없이 전략을 테스트하기 위한 Mock 데이터를 생성합니다.
    다양한 시장 상황을 시뮬레이션할 수 있습니다.

    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5 - Explain Like I'm 5):
    ═══════════════════════════════════════════════════════════════════════
    주식 시장은 실제로 열려 있어야 데이터가 들어옵니다.
    하지만 밤에도 개발하고 싶으면 어떻게 할까요?

    MockPriceFeed는 "가짜 주식 시장"을 만들어주는 도구입니다.
    실제 시장처럼 가격이 오르락내리락하고,
    거래량도 생성해줍니다.

    세 가지 모드가 있어요:
    1. random_walk: 랜덤하게 움직이는 주가 (가장 현실적)
    2. sine_wave: 파도처럼 규칙적인 주가 (테스트용)
    3. spike: 갑자기 폭등하는 주가 (Ignition 감지 테스트)

    ═══════════════════════════════════════════════════════════════════════
    사용 예시:
    ═══════════════════════════════════════════════════════════════════════

    >>> # 랜덤 워크 모드로 생성기 만들기
    >>> feed = MockPriceFeed(mode="random_walk", initial_price=10.0)

    >>> # 틱 하나 생성
    >>> tick = feed.generate_tick()
    >>> print(tick)
    {"ticker": "MOCK", "price": 10.12, "volume": 856, "timestamp": ...}

    >>> # OHLCV 봉 100개 생성
    >>> bars = feed.generate_ohlcv(periods=100)
    >>> print(bars[0])
    {"open": 10.0, "high": 10.15, "low": 9.95, "close": 10.08, ...}
    """

    # 지원하는 모드 타입
    ModeType = Literal["random_walk", "sine_wave", "spike"]

    def __init__(
        self,
        mode: ModeType = "random_walk",
        ticker: str = "MOCK",
        initial_price: float = 10.0,
        config: Optional[MockFeedConfig] = None,
        seed: Optional[int] = None,
    ):
        """
        MockPriceFeed 초기화

        Args:
            mode (str):
                가격 생성 모드. 아래 중 하나:
                - "random_walk": 브라운 운동 (랜덤 워크)
                - "sine_wave": 사인파 (규칙적 변동)
                - "spike": 갑작스런 급등 패턴

            ticker (str):
                가상 종목 코드. 기본값 "MOCK"

            initial_price (float):
                시작 가격. 기본값 10.0

            config (MockFeedConfig, optional):
                상세 설정. None이면 기본값 사용

            seed (int, optional):
                난수 시드. 같은 시드 → 같은 결과 (재현성)
        """
        self.mode = mode
        self.ticker = ticker

        # 설정 초기화
        self.config = config or MockFeedConfig(initial_price=initial_price)

        # 현재 상태
        self._current_price = self.config.initial_price
        self._tick_count = 0
        self._bar_count = 0
        self._start_time = datetime.now()

        # 재현성을 위한 시드 설정
        if seed is not None:
            random.seed(seed)

        # 스파이크 모드용 변수
        self._spike_triggered = False
        self._spike_cooldown = 0

    def generate_tick(self) -> dict:
        """
        단일 틱 데이터 생성

        실시간 체결 데이터 하나를 생성합니다.

        ═══════════════════════════════════════════════════════════════
        쉬운 설명:
        ═══════════════════════════════════════════════════════════════
        주식 거래가 한 번 일어날 때마다 "틱"이라고 합니다.
        "AAPL이 150.25달러에 100주 거래됨" 같은 정보예요.

        Returns:
            dict: 틱 데이터
                - ticker (str): 종목 코드
                - price (float): 체결 가격
                - volume (int): 체결 수량
                - timestamp (datetime): 체결 시간

        Example:
            >>> feed = MockPriceFeed()
            >>> tick = feed.generate_tick()
            >>> print(f"가격: ${tick['price']:.2f}")
            가격: $10.05
        """
        # 모드에 따라 가격 변화량 계산
        price_change = self._calculate_price_change()

        # 새 가격 계산 (최소 0.01 보장)
        self._current_price = max(0.01, self._current_price + price_change)

        # 거래량 생성 (기본값 ± 변동폭)
        volume = self._generate_volume()

        # 타임스탬프 (틱 카운트 × 100ms)
        timestamp = self._start_time + timedelta(milliseconds=self._tick_count * 100)

        self._tick_count += 1

        return {
            "ticker": self.ticker,
            "price": round(self._current_price, 4),
            "volume": volume,
            "timestamp": timestamp,
        }

    def generate_ohlcv(self, periods: int = 100) -> List[dict]:
        """
        OHLCV 분봉/일봉 데이터 생성

        지정한 개수만큼의 OHLCV 봉을 생성합니다.

        ═══════════════════════════════════════════════════════════════
        쉬운 설명:
        ═══════════════════════════════════════════════════════════════
        OHLCV는 주식 차트에서 보는 "캔들"입니다.

        - O(pen): 시가 - 그 시간대 첫 거래 가격
        - H(igh): 고가 - 가장 높은 가격
        - L(ow): 저가 - 가장 낮은 가격
        - C(lose): 종가 - 마지막 거래 가격
        - V(olume): 거래량 - 총 거래 수량

        Args:
            periods (int): 생성할 봉 개수. 기본값 100

        Returns:
            List[dict]: OHLCV 봉 리스트

        Example:
            >>> feed = MockPriceFeed()
            >>> bars = feed.generate_ohlcv(periods=5)
            >>> for bar in bars:
            ...     print(f"O:{bar['open']:.2f} H:{bar['high']:.2f} "
            ...           f"L:{bar['low']:.2f} C:{bar['close']:.2f}")
        """
        bars = []

        for i in range(periods):
            # 각 봉에 대해 여러 틱 생성하여 OHLCV 계산
            ticks = [self.generate_tick() for _ in range(self.config.tick_per_bar)]

            prices = [t["price"] for t in ticks]
            volumes = [t["volume"] for t in ticks]

            bar = {
                "ticker": self.ticker,
                "open": prices[0],
                "high": max(prices),
                "low": min(prices),
                "close": prices[-1],
                "volume": sum(volumes),
                "timestamp": ticks[-1]["timestamp"],
                "bar_index": self._bar_count,
            }

            bars.append(bar)
            self._bar_count += 1

        return bars

    def reset(self) -> None:
        """
        생성기 상태 초기화

        가격을 초기값으로 되돌리고 모든 카운터를 리셋합니다.
        """
        self._current_price = self.config.initial_price
        self._tick_count = 0
        self._bar_count = 0
        self._start_time = datetime.now()
        self._spike_triggered = False
        self._spike_cooldown = 0

    def _calculate_price_change(self) -> float:
        """
        모드에 따른 가격 변화량 계산 (내부 메서드)

        Returns:
            float: 가격 변화량 (+ 상승, - 하락)
        """
        if self.mode == "random_walk":
            return self._random_walk_change()
        elif self.mode == "sine_wave":
            return self._sine_wave_change()
        elif self.mode == "spike":
            return self._spike_change()
        else:
            raise ValueError(f"지원하지 않는 모드: {self.mode}")

    def _random_walk_change(self) -> float:
        """
        랜덤 워크 (Random Walk) 가격 변화

        ═══════════════════════════════════════════════════════════════
        쉬운 설명:
        ═══════════════════════════════════════════════════════════════
        동전 던지기와 비슷해요.
        앞면이면 가격이 올라가고, 뒷면이면 내려갑니다.

        이게 "브라운 운동"이라고도 불리는데,
        물 위에 꽃가루를 떨어뜨리면 이리저리 움직이는 것처럼
        주가도 랜덤하게 움직인다는 이론입니다.
        """
        # 가우시안 분포 (정규분포)로 변화량 생성
        # mean=0: 평균적으로 변화 없음
        # std=volatility: 변동성만큼 흔들림
        return random.gauss(0, self.config.volatility * self._current_price)

    def _sine_wave_change(self) -> float:
        """
        사인파 (Sine Wave) 가격 변화

        ═══════════════════════════════════════════════════════════════
        쉬운 설명:
        ═══════════════════════════════════════════════════════════════
        파도처럼 규칙적으로 오르락내리락합니다.
        테스트할 때 예측 가능한 패턴이 필요하면 사용합니다.
        """
        # 주기를 틱 카운트에 맞춤 (100틱 = 1주기)
        phase = (self._tick_count % 100) / 100 * 2 * math.pi

        # 사인값 (-1 ~ 1)을 가격 변화로 변환
        amplitude = self.config.volatility * self._current_price
        return math.sin(phase) * amplitude * 0.1

    def _spike_change(self) -> float:
        """
        스파이크 (Spike) 가격 변화 - 갑작스런 급등 패턴

        ═══════════════════════════════════════════════════════════════
        쉬운 설명:
        ═══════════════════════════════════════════════════════════════
        평소에는 조용히 횡보하다가,
        갑자기 "펑!" 하고 가격이 급등합니다.

        Sigma9의 "Ignition" 감지 기능을 테스트할 때 유용합니다.
        """
        # 쿨다운 중이면 일반 랜덤 워크
        if self._spike_cooldown > 0:
            self._spike_cooldown -= 1
            return self._random_walk_change() * 0.3  # 약한 변동

        # 1% 확률로 스파이크 발생
        if random.random() < 0.01 and not self._spike_triggered:
            self._spike_triggered = True
            self._spike_cooldown = 50  # 50틱 동안 쿨다운

            # 급등: 현재 가격의 3~8% 상승
            spike_pct = random.uniform(0.03, 0.08)
            return self._current_price * spike_pct

        # 평소: 아주 작은 변동
        self._spike_triggered = False
        return self._random_walk_change() * 0.3

    def _generate_volume(self) -> int:
        """
        거래량 생성 (내부 메서드)

        Returns:
            int: 생성된 거래량
        """
        # 기본 거래량 ± 변동폭
        variance = random.uniform(
            1 - self.config.volume_variance, 1 + self.config.volume_variance
        )
        base_volume = int(self.config.volume_base * variance)

        # 스파이크 모드에서 급등 시 거래량 폭발
        if self.mode == "spike" and self._spike_triggered:
            base_volume *= random.randint(5, 10)  # 5~10배

        return max(1, base_volume // self.config.tick_per_bar)

    @property
    def current_price(self) -> float:
        """현재 가격 조회"""
        return self._current_price

    @property
    def tick_count(self) -> int:
        """생성된 총 틱 수"""
        return self._tick_count


# ═══════════════════════════════════════════════════════════════════════════
# 모듈 레벨 테스트 코드
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("MockPriceFeed 테스트")
    print("=" * 60)

    # 1. 랜덤 워크 모드 테스트
    print("\n1. Random Walk 모드:")
    feed_rw = MockPriceFeed(mode="random_walk", initial_price=10.0, seed=42)
    for i in range(5):
        tick = feed_rw.generate_tick()
        print(f"  Tick {i + 1}: ${tick['price']:.4f}, Vol: {tick['volume']}")

    # 2. 사인파 모드 테스트
    print("\n2. Sine Wave 모드:")
    feed_sw = MockPriceFeed(mode="sine_wave", initial_price=10.0)
    for i in range(5):
        tick = feed_sw.generate_tick()
        print(f"  Tick {i + 1}: ${tick['price']:.4f}, Vol: {tick['volume']}")

    # 3. OHLCV 생성 테스트
    print("\n3. OHLCV 생성 (5개 봉):")
    feed_ohlcv = MockPriceFeed(mode="random_walk", initial_price=10.0, seed=123)
    bars = feed_ohlcv.generate_ohlcv(periods=5)
    for bar in bars:
        print(
            f"  O:{bar['open']:.2f} H:{bar['high']:.2f} "
            f"L:{bar['low']:.2f} C:{bar['close']:.2f} V:{bar['volume']}"
        )

    # 4. 스파이크 모드 테스트
    print("\n4. Spike 모드 (급등 감지 테스트):")
    feed_spike = MockPriceFeed(mode="spike", initial_price=10.0, seed=999)
    max_price = 10.0
    for i in range(200):
        tick = feed_spike.generate_tick()
        if tick["price"] > max_price * 1.03:  # 3% 이상 상승 시
            print(
                f"  🔥 급등 감지! Tick {i + 1}: ${tick['price']:.4f} "
                f"(+{((tick['price'] / max_price) - 1) * 100:.1f}%)"
            )
            max_price = tick["price"]

    print("\n모든 테스트 완료! ✓")
