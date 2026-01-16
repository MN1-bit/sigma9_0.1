# ============================================================================
# Ticker Filter - 제외 티커 필터링
# ============================================================================
# 📌 이 파일의 역할:
#   - YAML 설정 기반 티커 제외 판정
#   - Warrant, Preferred Stock, Rights, Units 등 자동 제외
#   - 수동 제외/화이트리스트 지원
#
# 📖 사용 예시:
#   >>> from backend.core.ticker_filter import get_ticker_filter
#   >>> tf = get_ticker_filter()
#   >>> candidates = tf.filter(["AAPL", "TSLA", "AAPLW", "MSFT+"])
#   >>> # ["AAPL", "TSLA"]
#
# 📌 [12-001] Full Universe Scan 지원
# ============================================================================

from pathlib import Path
from typing import Any
import yaml
from loguru import logger


# ═══════════════════════════════════════════════════════════════════════════
# TickerFilter 클래스
# ═══════════════════════════════════════════════════════════════════════════


class TickerFilter:
    """
    티커 제외 필터

    YAML 설정 파일을 기반으로 Warrant, Preferred Stock 등
    거래 대상에서 제외할 티커를 필터링합니다.

    Attributes:
        patterns: 패턴 매칭 규칙 리스트
        manual_exclusions: 수동 제외 티커 집합
        whitelist: 패턴 예외 티커 집합 (무조건 통과)

    Example:
        >>> tf = TickerFilter.from_yaml("config/ticker_exclusions.yaml")
        >>> tf.is_excluded("AAPLW")   # True (W suffix)
        >>> tf.is_excluded("AAPL")    # False
        >>> tf.filter(["AAPL", "AAPLW", "TSLA"])  # ["AAPL", "TSLA"]
    """

    def __init__(
        self,
        patterns: list[dict[str, str]] | None = None,
        manual_exclusions: list[str] | None = None,
        whitelist: list[str] | None = None,
    ):
        """
        TickerFilter 초기화

        Args:
            patterns: 패턴 매칭 규칙 [{"type": "suffix", "value": "W"}, ...]
            manual_exclusions: 수동 제외 티커 리스트
            whitelist: 패턴 예외 티커 리스트
        """
        self.patterns = patterns or []
        self.manual_exclusions = set(manual_exclusions or [])
        self.whitelist = set(whitelist or [])

        logger.debug(
            f"🔧 TickerFilter 초기화: "
            f"{len(self.patterns)} patterns, "
            f"{len(self.manual_exclusions)} manual, "
            f"{len(self.whitelist)} whitelist"
        )

    # ═══════════════════════════════════════════════════════════════════════
    # Factory Methods
    # ═══════════════════════════════════════════════════════════════════════

    @classmethod
    def from_yaml(cls, path: str | Path) -> "TickerFilter":
        """
        YAML 파일에서 TickerFilter 로드

        Args:
            path: YAML 설정 파일 경로

        Returns:
            TickerFilter: 설정이 적용된 인스턴스

        Raises:
            FileNotFoundError: 설정 파일이 없을 때
        """
        path = Path(path)

        if not path.exists():
            logger.warning(f"⚠️ 설정 파일 없음: {path} - 빈 필터 사용")
            return cls()

        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        return cls(
            patterns=config.get("patterns", []),
            manual_exclusions=config.get("manual_exclusions", []),
            whitelist=config.get("whitelist", []),
        )

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> "TickerFilter":
        """
        딕셔너리에서 TickerFilter 생성

        Args:
            config: 설정 딕셔너리

        Returns:
            TickerFilter: 설정이 적용된 인스턴스
        """
        return cls(
            patterns=config.get("patterns", []),
            manual_exclusions=config.get("manual_exclusions", []),
            whitelist=config.get("whitelist", []),
        )

    # ═══════════════════════════════════════════════════════════════════════
    # 필터링 메서드
    # ═══════════════════════════════════════════════════════════════════════

    def is_excluded(self, ticker: str) -> bool:
        """
        티커가 제외 대상인지 판정

        판정 순서:
        1. whitelist에 있으면 → False (제외 안함)
        2. manual_exclusions에 있으면 → True (제외)
        3. patterns 매칭되면 → True (제외)

        Args:
            ticker: 티커 심볼

        Returns:
            bool: True면 제외 대상
        """
        # 1. Whitelist 우선 (무조건 통과)
        if ticker in self.whitelist:
            return False

        # 2. 수동 제외 체크
        if ticker in self.manual_exclusions:
            return True

        # 3. 패턴 매칭 체크
        for pattern in self.patterns:
            if self._match_pattern(ticker, pattern):
                return True

        return False

    def filter(self, tickers: list[str]) -> list[str]:
        """
        티커 리스트에서 제외 대상 필터링

        Args:
            tickers: 티커 리스트

        Returns:
            list[str]: 제외 대상이 아닌 티커만 반환
        """
        result = [t for t in tickers if not self.is_excluded(t)]

        excluded_count = len(tickers) - len(result)
        if excluded_count > 0:
            logger.debug(
                f"🔍 TickerFilter: {len(tickers)}개 중 {excluded_count}개 제외"
            )

        return result

    # ═══════════════════════════════════════════════════════════════════════
    # Private Methods
    # ═══════════════════════════════════════════════════════════════════════

    def _match_pattern(self, ticker: str, pattern: dict[str, str]) -> bool:
        """
        패턴 매칭 체크

        Args:
            ticker: 티커 심볼
            pattern: 패턴 규칙 {"type": "suffix", "value": "W"}

        Returns:
            bool: 패턴 매칭 여부
        """
        pattern_type = pattern.get("type", "")
        value = pattern.get("value", "")

        if not value:
            return False

        # ELI5: 패턴 타입에 따라 문자열 매칭
        # suffix: 끝이 value로 끝나면 True
        # prefix: 시작이 value로 시작하면 True
        # contains: value가 포함되면 True
        # exact: 정확히 같으면 True
        if pattern_type == "suffix":
            return ticker.endswith(value)
        elif pattern_type == "prefix":
            return ticker.startswith(value)
        elif pattern_type == "contains":
            return value in ticker
        elif pattern_type == "exact":
            return ticker == value
        else:
            logger.warning(f"⚠️ 알 수 없는 패턴 타입: {pattern_type}")
            return False


# ═══════════════════════════════════════════════════════════════════════════
# 편의 함수
# ═══════════════════════════════════════════════════════════════════════════

# 모듈 레벨 캐시
_ticker_filter_instance: TickerFilter | None = None


def get_ticker_filter() -> TickerFilter:
    """
    기본 설정 TickerFilter 반환 (캐시됨)

    Returns:
        TickerFilter: 기본 설정이 적용된 인스턴스
    """
    global _ticker_filter_instance

    if _ticker_filter_instance is None:
        config_path = Path(__file__).parent.parent / "config" / "ticker_exclusions.yaml"
        _ticker_filter_instance = TickerFilter.from_yaml(config_path)

    return _ticker_filter_instance


def reset_ticker_filter() -> None:
    """
    캐시된 TickerFilter 인스턴스 초기화

    테스트나 설정 변경 후 사용
    """
    global _ticker_filter_instance
    _ticker_filter_instance = None
