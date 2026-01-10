# ============================================================================
# Flush Policy - 캐시 Flush 전략 패턴
# ============================================================================
# 📌 이 파일의 역할:
#   - 스코어/보조지표 캐시를 Parquet에 저장하는 정책 정의
#   - Strategy Pattern으로 정책 교체 가능
#   - 설정(settings.yaml)에서 flush_policy 선택
#
# 📖 사용 예시:
#   >>> policy = IntervalFlush(interval_seconds=30)
#   >>> if policy.should_flush(last_flush, update_count):
#   >>>     flush_to_parquet()
#
# 📌 [11-002] DataRepository 리팩터링의 일부
# ============================================================================

from abc import ABC, abstractmethod
from dataclasses import dataclass
import time


# ═══════════════════════════════════════════════════════════════════════════
# FlushPolicy ABC (추상 베이스 클래스)
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class FlushPolicy(ABC):
    """
    캐시 Flush 정책 인터페이스 (Strategy Pattern)

    ELI5: "언제 메모리에 있는 데이터를 파일로 저장할까?"를 결정하는 규칙

    구현체:
        - ImmediateFlush: 매번 즉시 저장 (안전, 느림)
        - IntervalFlush: N초마다 저장 (권장)
        - CountFlush: N번 업데이트마다 저장
        - HybridFlush: 시간 + 횟수 조합
    """

    @abstractmethod
    def should_flush(self, last_flush_time: float, update_count: int) -> bool:
        """
        Flush 여부 판단

        Args:
            last_flush_time: 마지막 Flush Unix timestamp
            update_count: 마지막 Flush 이후 업데이트 횟수

        Returns:
            bool: True면 지금 Flush 해야 함
        """
        ...


# ═══════════════════════════════════════════════════════════════════════════
# 구현체: ImmediateFlush
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class ImmediateFlush(FlushPolicy):
    """
    즉시 Flush 정책

    ELI5: 데이터가 바뀔 때마다 바로 파일에 저장
          (안전하지만 디스크 I/O가 많아서 느림)

    사용 시나리오:
        - 데이터 손실이 절대 허용되지 않는 경우
        - 업데이트 빈도가 낮은 경우
    """

    def should_flush(self, last_flush_time: float, update_count: int) -> bool:
        # 항상 True (ELI5: 업데이트 할 때마다 무조건 저장)
        return True


# ═══════════════════════════════════════════════════════════════════════════
# 구현체: IntervalFlush (권장)
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class IntervalFlush(FlushPolicy):
    """
    시간 기반 Flush 정책 (권장)

    ELI5: "마지막 저장 후 N초 지났으면 저장해"

    사용 시나리오:
        - 일정 주기로 데이터를 저장하고 싶을 때
        - I/O와 데이터 안전성 균형이 필요할 때

    Attributes:
        interval_seconds: Flush 주기 (초), 기본 30초
    """

    interval_seconds: float = 30.0

    def should_flush(self, last_flush_time: float, update_count: int) -> bool:
        # 마지막 Flush로부터 지정된 시간이 경과했는지 확인
        elapsed = time.time() - last_flush_time
        return elapsed >= self.interval_seconds


# ═══════════════════════════════════════════════════════════════════════════
# 구현체: CountFlush
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class CountFlush(FlushPolicy):
    """
    횟수 기반 Flush 정책

    ELI5: "N번 업데이트되면 저장해"

    사용 시나리오:
        - 업데이트 빈도가 예측 가능할 때
        - 일정 건수마다 저장하고 싶을 때

    Attributes:
        threshold: Flush 트리거 업데이트 횟수, 기본 100회
    """

    threshold: int = 100

    def should_flush(self, last_flush_time: float, update_count: int) -> bool:
        # 업데이트 횟수가 임계값 이상인지 확인
        return update_count >= self.threshold


# ═══════════════════════════════════════════════════════════════════════════
# 구현체: HybridFlush
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class HybridFlush(FlushPolicy):
    """
    복합 Flush 정책 (시간 OR 횟수)

    ELI5: "30초 지났거나 50번 업데이트됐으면 저장해" (둘 중 하나만 충족해도 OK)

    사용 시나리오:
        - 업데이트 빈도가 불규칙할 때
        - 시간과 횟수 모두 고려하고 싶을 때

    Attributes:
        interval_seconds: 시간 트리거 (초), 기본 30초
        count_threshold: 횟수 트리거, 기본 50회
    """

    interval_seconds: float = 30.0
    count_threshold: int = 50

    def should_flush(self, last_flush_time: float, update_count: int) -> bool:
        # 시간 조건 체크
        time_trigger = (time.time() - last_flush_time) >= self.interval_seconds
        # 횟수 조건 체크
        count_trigger = update_count >= self.count_threshold
        # 둘 중 하나라도 충족하면 Flush
        return time_trigger or count_trigger


# ═══════════════════════════════════════════════════════════════════════════
# 팩토리 함수: 설정에서 정책 생성
# ═══════════════════════════════════════════════════════════════════════════


def create_flush_policy(
    policy_type: str = "interval",
    interval_seconds: float = 30.0,
    count_threshold: int = 100,
) -> FlushPolicy:
    """
    설정에서 FlushPolicy 인스턴스 생성

    Args:
        policy_type: "immediate" | "interval" | "count" | "hybrid"
        interval_seconds: 시간 기반 정책의 주기
        count_threshold: 횟수 기반 정책의 임계값

    Returns:
        FlushPolicy: 해당 정책 인스턴스

    Example:
        >>> policy = create_flush_policy("interval", interval_seconds=60)
        >>> policy = create_flush_policy("hybrid", interval_seconds=30, count_threshold=50)
    """
    policy_type = policy_type.lower()

    if policy_type == "immediate":
        return ImmediateFlush()
    elif policy_type == "interval":
        return IntervalFlush(interval_seconds=interval_seconds)
    elif policy_type == "count":
        return CountFlush(threshold=count_threshold)
    elif policy_type == "hybrid":
        return HybridFlush(
            interval_seconds=interval_seconds,
            count_threshold=count_threshold,
        )
    else:
        # 알 수 없는 타입은 기본값 IntervalFlush
        return IntervalFlush(interval_seconds=interval_seconds)
