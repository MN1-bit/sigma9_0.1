# ============================================================================
# Event Sequencer - 이벤트 순서 보장
# ============================================================================
# 📌 이 파일의 역할:
#   - 비순차적으로 도착한 이벤트를 event_time 기준으로 재정렬
#   - 버퍼링 후 정렬된 순서로 방출
#
# 📖 사용 예시:
#   >>> from backend.core.event_sequencer import EventSequencer
#   >>> sequencer = EventSequencer(buffer_ms=100)
#   >>> for ordered_event in sequencer.push(event):
#   ...     process_event(ordered_event)
#
# 📖 리팩터링 [08-001] Phase 4:
#   - 신규 파일 생성
# ============================================================================

"""
Event Sequencer

비순차적으로 도착한 이벤트를 event_time 기준으로 재정렬합니다.
"""

import time
from dataclasses import dataclass
from typing import Any, Iterator, List, Optional
from heapq import heappush, heappop

from loguru import logger


@dataclass
class SequencedEvent:
    """
    순서 보장용 이벤트 래퍼

    Attributes:
        event_time_ms: 이벤트 발생 시간 (Unix ms)
        receive_time_ms: 수신 시간 (Unix ms)
        data: 원본 이벤트 데이터
    """

    event_time_ms: int
    receive_time_ms: int
    data: Any

    def __lt__(self, other: "SequencedEvent") -> bool:
        """우선순위 큐 정렬용 (event_time 기준 오름차순)"""
        return self.event_time_ms < other.event_time_ms


class EventSequencer:
    """
    이벤트 순서 보장기

    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    이벤트가 순서대로 오지 않을 때 줄을 세워줍니다.

    네트워크 문제로 "2번 이벤트"가 "1번 이벤트"보다 먼저 도착할 수 있어요.
    이 클래스는 잠깐(100ms) 기다렸다가 시간순으로 정렬해서 내보냅니다.

    실시간 트레이딩에서는 이벤트 순서가 매우 중요해요!
    잘못된 순서로 처리하면 잘못된 결정을 내릴 수 있거든요.

    Attributes:
        buffer_ms: 버퍼링 시간 (밀리초). 이 시간 동안 기다렸다가 정렬.

    Example:
        >>> sequencer = EventSequencer(buffer_ms=100)
        >>> # 순서 뒤바뀐 이벤트 도착
        >>> for e in sequencer.push(event_t=200):
        ...     pass  # 아직 안 나옴 (버퍼링 중)
        >>> for e in sequencer.push(event_t=100):
        ...     pass  # 아직 안 나옴
        >>> for e in sequencer.flush():
        ...     print(e.event_time_ms)  # 100, 200 순서로 출력!
    """

    def __init__(self, buffer_ms: int = 100):
        """
        EventSequencer 초기화

        Args:
            buffer_ms: 버퍼링 시간 (밀리초). 이 시간만큼 기다린 후 방출.
        """
        self.buffer_ms = buffer_ms
        self._heap: List[SequencedEvent] = []  # 우선순위 큐 (min-heap)

        logger.debug(f"EventSequencer initialized: buffer={buffer_ms}ms")

    def push(
        self, event_data: Any, event_time_ms: int, receive_time_ms: Optional[int] = None
    ) -> Iterator[SequencedEvent]:
        """
        이벤트 추가 및 준비된 이벤트 방출

        ═══════════════════════════════════════════════════════════════════
        쉬운 설명 (ELI5):
        ═══════════════════════════════════════════════════════════════════
        새 이벤트를 버퍼에 넣고, 충분히 기다린 이벤트들을 내보냅니다.

        Args:
            event_data: 이벤트 데이터 (틱, 바 등)
            event_time_ms: 이벤트 발생 시간 (Unix ms)
            receive_time_ms: 수신 시간 (Unix ms). None이면 현재 시간.

        Yields:
            SequencedEvent: 버퍼링이 완료된 이벤트 (시간순)
        """
        now_ms = receive_time_ms or int(time.time() * 1000)

        # 새 이벤트를 힙에 추가
        event = SequencedEvent(
            event_time_ms=event_time_ms, receive_time_ms=now_ms, data=event_data
        )
        heappush(self._heap, event)

        # 버퍼링 시간이 지난 이벤트 방출
        deadline = now_ms - self.buffer_ms

        while self._heap and self._heap[0].receive_time_ms <= deadline:
            yield heappop(self._heap)

    def flush(self) -> Iterator[SequencedEvent]:
        """
        버퍼의 모든 이벤트 강제 방출 (시간순)

        프로그램 종료 시 또는 명시적 플러시가 필요할 때 사용.

        Yields:
            SequencedEvent: 버퍼에 남은 모든 이벤트 (시간순)
        """
        while self._heap:
            yield heappop(self._heap)

    def clear(self) -> None:
        """버퍼 초기화"""
        self._heap.clear()

    @property
    def pending_count(self) -> int:
        """버퍼에 대기 중인 이벤트 수"""
        return len(self._heap)

    @property
    def oldest_event_age_ms(self) -> Optional[int]:
        """
        가장 오래된 이벤트의 대기 시간 (밀리초)

        Returns:
            int: 대기 시간 (ms), 버퍼 비어있으면 None
        """
        if not self._heap:
            return None

        now_ms = int(time.time() * 1000)
        oldest = self._heap[0]
        return now_ms - oldest.receive_time_ms


__all__ = ["EventSequencer", "SequencedEvent"]
