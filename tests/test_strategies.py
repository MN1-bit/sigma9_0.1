# ============================================================================
# Sigma9 Strategy Tests - 전략 인터페이스 테스트
# ============================================================================
# 📌 이 파일의 역할:
#   - StrategyBase ABC 인터페이스 검증
#   - Signal 데이터 클래스 테스트
#   - MockPriceFeed 동작 확인
#   - RandomWalker 전략 테스트
#
# 📌 실행 방법:
#   pytest tests/test_strategies.py -v
#   pytest tests/test_strategies.py -v -k "test_signal"  # 특정 테스트만
# ============================================================================

"""
Strategy Tests

전략 인터페이스와 관련 클래스들의 단위 테스트입니다.
"""

import sys
from pathlib import Path
from datetime import datetime

import pytest

# backend 폴더를 경로에 추가
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from core.strategy_base import StrategyBase, Signal
from core.mock_data import MockPriceFeed
from strategies.random_walker import RandomWalkerStrategy


# ═══════════════════════════════════════════════════════════════════════════
# Signal 데이터 클래스 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestSignal:
    """Signal 데이터 클래스 테스트"""

    def test_signal_creation_success(self):
        """Signal 객체 정상 생성 테스트"""
        signal = Signal(
            action="BUY", ticker="AAPL", confidence=0.85, reason="테스트 신호"
        )

        assert signal.action == "BUY"
        assert signal.ticker == "AAPL"
        assert signal.confidence == 0.85
        assert signal.reason == "테스트 신호"
        assert signal.metadata == {}  # 기본값
        assert isinstance(signal.timestamp, datetime)

    def test_signal_with_metadata(self):
        """메타데이터 포함 Signal 생성 테스트"""
        metadata = {"price": 150.25, "volume": 1000}
        signal = Signal(
            action="SELL",
            ticker="TSLA",
            confidence=0.7,
            reason="수익 실현",
            metadata=metadata,
        )

        assert signal.metadata == metadata

    def test_signal_invalid_action_raises_error(self):
        """잘못된 action 값에 대해 ValueError 발생 확인"""
        with pytest.raises(ValueError, match="action은"):
            Signal(action="INVALID", ticker="AAPL", confidence=0.5, reason="테스트")

    def test_signal_invalid_confidence_too_high(self):
        """confidence > 1.0 일 때 ValueError 발생 확인"""
        with pytest.raises(ValueError, match="confidence는"):
            Signal(
                action="BUY",
                ticker="AAPL",
                confidence=1.5,  # 범위 초과
                reason="테스트",
            )

    def test_signal_invalid_confidence_too_low(self):
        """confidence < 0.0 일 때 ValueError 발생 확인"""
        with pytest.raises(ValueError, match="confidence는"):
            Signal(
                action="SELL",
                ticker="AAPL",
                confidence=-0.1,  # 음수
                reason="테스트",
            )

    def test_signal_to_dict(self):
        """Signal.to_dict() 메서드 테스트"""
        signal = Signal(action="HOLD", ticker="NVDA", confidence=0.5, reason="관망")

        result = signal.to_dict()

        assert isinstance(result, dict)
        assert result["action"] == "HOLD"
        assert result["ticker"] == "NVDA"
        assert result["confidence"] == 0.5
        assert "timestamp" in result


# ═══════════════════════════════════════════════════════════════════════════
# StrategyBase ABC 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestStrategyBase:
    """StrategyBase 추상 클래스 테스트"""

    def test_cannot_instantiate_directly(self):
        """StrategyBase를 직접 인스턴스화하면 TypeError 발생 확인"""
        with pytest.raises(TypeError):
            StrategyBase()

    def test_must_implement_all_abstract_methods(self):
        """abstractmethod 미구현 시 TypeError 발생 확인"""

        class IncompleteStrategy(StrategyBase):
            """일부 메서드만 구현한 불완전한 전략"""

            name = "Incomplete"
            version = "1.0.0"
            description = "불완전"

            def get_universe_filter(self):
                return {}

            # 나머지 메서드 미구현

        with pytest.raises(TypeError):
            IncompleteStrategy()

    def test_class_attributes_exist(self):
        """StrategyBase에 필수 클래스 속성이 존재하는지 확인"""
        assert hasattr(StrategyBase, "name")
        assert hasattr(StrategyBase, "version")
        assert hasattr(StrategyBase, "description")


# ═══════════════════════════════════════════════════════════════════════════
# MockPriceFeed 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestMockPriceFeed:
    """MockPriceFeed 가상 데이터 생성기 테스트"""

    def test_generate_tick_returns_dict(self):
        """generate_tick()이 올바른 형식의 dict를 반환하는지 확인"""
        feed = MockPriceFeed(mode="random_walk", seed=42)
        tick = feed.generate_tick()

        assert isinstance(tick, dict)
        assert "ticker" in tick
        assert "price" in tick
        assert "volume" in tick
        assert "timestamp" in tick

    def test_generate_tick_price_positive(self):
        """생성된 가격이 항상 양수인지 확인"""
        feed = MockPriceFeed(mode="random_walk", initial_price=0.1, seed=42)

        for _ in range(100):
            tick = feed.generate_tick()
            assert tick["price"] > 0

    def test_generate_ohlcv_returns_list(self):
        """generate_ohlcv()가 올바른 형식의 list를 반환하는지 확인"""
        feed = MockPriceFeed(mode="random_walk", seed=42)
        bars = feed.generate_ohlcv(periods=10)

        assert isinstance(bars, list)
        assert len(bars) == 10

    def test_generate_ohlcv_structure(self):
        """OHLCV 데이터 구조 확인"""
        feed = MockPriceFeed(mode="random_walk", seed=42)
        bars = feed.generate_ohlcv(periods=5)

        for bar in bars:
            assert "open" in bar
            assert "high" in bar
            assert "low" in bar
            assert "close" in bar
            assert "volume" in bar
            assert "timestamp" in bar

            # high >= low 확인
            assert bar["high"] >= bar["low"]

    def test_random_walk_mode(self):
        """random_walk 모드 동작 확인"""
        feed = MockPriceFeed(mode="random_walk", seed=42)
        prices = [feed.generate_tick()["price"] for _ in range(50)]

        # 가격이 변동하는지 확인 (모두 같으면 안 됨)
        assert len(set(prices)) > 1

    def test_sine_wave_mode(self):
        """sine_wave 모드 동작 확인"""
        feed = MockPriceFeed(mode="sine_wave", initial_price=10.0)
        prices = [feed.generate_tick()["price"] for _ in range(100)]

        # 가격이 변동하는지 확인
        assert len(set(prices)) > 1

    def test_spike_mode(self):
        """spike 모드에서 급등이 발생하는지 확인"""
        feed = MockPriceFeed(mode="spike", initial_price=10.0, seed=999)

        max_change = 0
        prev_price = 10.0

        for _ in range(500):
            tick = feed.generate_tick()
            change = (tick["price"] - prev_price) / prev_price if prev_price > 0 else 0
            max_change = max(max_change, change)
            prev_price = tick["price"]

        # 최소한 한 번은 3% 이상 상승이 있어야 함
        assert max_change >= 0.03

    def test_seed_reproducibility(self):
        """같은 시드로 같은 결과가 나오는지 확인 (재현성)"""
        # 같은 피드를 리셋해서 사용하면 재현성 보장
        feed = MockPriceFeed(mode="random_walk", seed=123)

        prices1 = [feed.generate_tick()["price"] for _ in range(10)]

        # 리셋 후 같은 시드 설정
        import random

        random.seed(123)
        feed.reset()

        prices2 = [feed.generate_tick()["price"] for _ in range(10)]

        assert prices1 == prices2

    def test_reset(self):
        """reset() 메서드로 상태 초기화 확인"""
        feed = MockPriceFeed(mode="random_walk", initial_price=10.0, seed=42)

        # 틱 생성
        for _ in range(50):
            feed.generate_tick()

        # 리셋
        feed.reset()

        assert feed.tick_count == 0
        assert feed.current_price == 10.0


# ═══════════════════════════════════════════════════════════════════════════
# RandomWalkerStrategy 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestRandomWalkerStrategy:
    """RandomWalker 전략 테스트"""

    def test_inherits_strategy_base(self):
        """StrategyBase를 상속하는지 확인"""
        assert issubclass(RandomWalkerStrategy, StrategyBase)

    def test_can_instantiate(self):
        """인스턴스 생성 가능 확인"""
        strategy = RandomWalkerStrategy()
        assert strategy is not None

    def test_has_required_attributes(self):
        """필수 클래스 속성 확인"""
        strategy = RandomWalkerStrategy()

        assert hasattr(strategy, "name")
        assert hasattr(strategy, "version")
        assert hasattr(strategy, "description")
        assert strategy.name == "Random Walker"

    def test_initialize(self):
        """initialize() 호출 가능 확인"""
        strategy = RandomWalkerStrategy()
        strategy.set_config({"random_seed": {"value": 42}})

        # 에러 없이 호출 가능해야 함
        strategy.initialize()

    def test_on_tick_returns_signal_or_none(self):
        """on_tick()이 Signal 또는 None을 반환하는지 확인"""
        strategy = RandomWalkerStrategy()
        strategy.set_config({"random_seed": {"value": 42}})
        strategy.initialize()

        for i in range(100):
            result = strategy.on_tick(
                ticker="MOCK",
                price=10.0 + i * 0.01,
                volume=100,
                timestamp=datetime.now(),
            )

            assert result is None or isinstance(result, Signal)

    def test_on_tick_generates_signals(self):
        """on_tick()이 실제로 신호를 생성하는지 확인"""
        strategy = RandomWalkerStrategy()
        strategy.set_config(
            {
                "signal_probability": {"value": 0.5},  # 50% 확률
                "random_seed": {"value": 42},
            }
        )
        strategy.initialize()

        signals = []
        for i in range(100):
            result = strategy.on_tick("MOCK", 10.0, 100, datetime.now())
            if result:
                signals.append(result)

        # 50% 확률이면 대략 40~60개 신호 발생 예상
        assert len(signals) > 0

    def test_get_config(self):
        """get_config() 반환값 확인"""
        strategy = RandomWalkerStrategy()
        config = strategy.get_config()

        assert isinstance(config, dict)
        assert "signal_probability" in config

    def test_set_config(self):
        """set_config()로 설정 변경 확인"""
        strategy = RandomWalkerStrategy()

        strategy.set_config({"signal_probability": {"value": 0.20}})

        assert strategy.config["signal_probability"]["value"] == 0.20

    def test_get_stats(self):
        """get_stats() 메서드 확인"""
        strategy = RandomWalkerStrategy()
        strategy.initialize()

        # 틱 처리
        for i in range(10):
            strategy.on_tick("MOCK", 10.0, 100, datetime.now())

        stats = strategy.get_stats()

        assert "tick_count" in stats
        assert "signal_count" in stats
        assert "signal_ratio" in stats
        assert stats["tick_count"] == 10


# ═══════════════════════════════════════════════════════════════════════════
# 통합 테스트
# ═══════════════════════════════════════════════════════════════════════════


class TestIntegration:
    """전략 + Mock 데이터 통합 테스트"""

    def test_strategy_with_mock_feed(self):
        """전략과 Mock 데이터 생성기 연동 테스트"""
        # Mock 데이터 생성기
        feed = MockPriceFeed(mode="random_walk", seed=42)

        # 전략
        strategy = RandomWalkerStrategy()
        strategy.set_config(
            {"signal_probability": {"value": 0.10}, "random_seed": {"value": 42}}
        )
        strategy.initialize()

        # 100개 틱 처리
        signals = []
        for _ in range(100):
            tick = feed.generate_tick()
            result = strategy.on_tick(
                ticker=tick["ticker"],
                price=tick["price"],
                volume=tick["volume"],
                timestamp=tick["timestamp"],
            )
            if result:
                signals.append(result)

        # 10% 확률이면 대략 5~15개 신호 예상
        assert len(signals) >= 1

        # 모든 신호가 올바른 타입인지 확인
        for signal in signals:
            assert isinstance(signal, Signal)
            assert signal.action in {"BUY", "SELL", "HOLD"}


# ═══════════════════════════════════════════════════════════════════════════
# StrategyLoader 테스트 (Step 2.5)
# ═══════════════════════════════════════════════════════════════════════════


class TestStrategyLoader:
    """StrategyLoader 플러그인 시스템 테스트"""

    @pytest.fixture
    def loader(self):
        """StrategyLoader 인스턴스 생성"""
        from core.strategy_loader import StrategyLoader

        return StrategyLoader()

    def test_discover_strategies(self, loader):
        """discover_strategies()가 전략 목록을 반환하는지 확인"""
        strategies = loader.discover_strategies()

        assert isinstance(strategies, list)
        assert "seismograph" in strategies or "random_walker" in strategies

    def test_discover_excludes_underscore(self, loader):
        """'_'로 시작하는 파일이 제외되는지 확인"""
        strategies = loader.discover_strategies()

        # _template.py는 제외되어야 함
        for name in strategies:
            assert not name.startswith("_")

    def test_load_strategy_success(self, loader):
        """전략 로드 성공 테스트"""
        strategies = loader.discover_strategies()
        if not strategies:
            pytest.skip("No strategies found")

        strategy = loader.load_strategy(strategies[0])

        assert strategy is not None
        assert hasattr(strategy, "name")
        assert hasattr(strategy, "version")
        assert isinstance(strategy, StrategyBase)

    def test_load_strategy_not_found(self, loader):
        """존재하지 않는 전략 로드 시 FileNotFoundError 발생"""
        with pytest.raises(FileNotFoundError):
            loader.load_strategy("nonexistent_strategy_xyz")

    def test_reload_strategy(self, loader):
        """전략 리로드 테스트"""
        strategies = loader.discover_strategies()
        if not strategies:
            pytest.skip("No strategies found")

        # 먼저 로드
        strategy1 = loader.load_strategy(strategies[0])

        # 리로드
        strategy2 = loader.reload_strategy(strategies[0])

        # 새 인스턴스가 생성되었는지 확인
        assert strategy2 is not None
        assert strategy2.name == strategy1.name

    def test_get_strategy_cached(self, loader):
        """캐시된 전략 반환 테스트"""
        strategies = loader.discover_strategies()
        if not strategies:
            pytest.skip("No strategies found")

        # 로드
        strategy1 = loader.load_strategy(strategies[0])

        # 캐시에서 가져오기
        strategy2 = loader.get_strategy(strategies[0])

        # 같은 인스턴스여야 함
        assert strategy1 is strategy2

    def test_list_loaded(self, loader):
        """로드된 전략 목록 테스트"""
        strategies = loader.discover_strategies()
        if not strategies:
            pytest.skip("No strategies found")

        loader.load_strategy(strategies[0])
        loaded = loader.list_loaded()

        assert isinstance(loaded, list)
        assert len(loaded) >= 1
        assert "name" in loaded[0]
        assert "version" in loaded[0]


# ═══════════════════════════════════════════════════════════════════════════
# 실행
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
