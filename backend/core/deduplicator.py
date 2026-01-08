# ============================================================================
# Event Deduplicator - 이벤트 중복 제거
# ============================================================================
# 📌 이 파일의 역할:
#   - 실시간 이벤트 스트림에서 중복 이벤트 제거
#   - event_id 기반 시간 윈도우 중복 검사
#
# 📖 사용 예시:
#   >>> from backend.core.deduplicator import EventDeduplicator
#   >>> dedup = EventDeduplicator(window_seconds=60)
#   >>> if not dedup.is_duplicate("AAPL_buy_1736330000"):
#   ...     process_event()
#
# 📖 리팩터링 [08-001] Phase 3:
#   - 신규 파일 생성
# ============================================================================

"""
Event Deduplicator

실시간 이벤트 스트림에서 중복 이벤트를 제거합니다.
"""

import time
from typing import Dict, Optional

from loguru import logger


class EventDeduplicator:
    """
    이벤트 중복 제거기

    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    같은 이벤트가 여러 번 들어오면 한 번만 처리해요.

    예를 들어, 네트워크 문제로 같은 틱 데이터가 두 번 왔다면,
    두 번째는 "중복이니까 무시해" 라고 알려줍니다.

    시간 윈도우(기본 60초)가 지나면 같은 event_id도 새 이벤트로 처리해요.

    Attributes:
        window_seconds: 중복 검사 시간 윈도우 (초)

    Example:
        >>> dedup = EventDeduplicator(window_seconds=60)
        >>> dedup.is_duplicate("tick_123")  # False (최초)
        >>> dedup.is_duplicate("tick_123")  # True (중복!)
        >>> dedup.is_duplicate("tick_456")  # False (다른 이벤트)
    """

    def __init__(self, window_seconds: int = 60):
        """
        EventDeduplicator 초기화

        Args:
            window_seconds: 중복 검사 시간 윈도우 (초)
        """
        self.window_seconds = window_seconds
        # event_id -> last_seen_timestamp
        self._seen: Dict[str, float] = {}
        self._last_cleanup: float = time.time()
        self._cleanup_interval: float = window_seconds * 2  # 2배 윈도우마다 정리

        logger.debug(f"EventDeduplicator initialized: window={window_seconds}s")

    def is_duplicate(self, event_id: str, event_time: Optional[float] = None) -> bool:
        """
        이벤트 중복 여부 확인

        ═══════════════════════════════════════════════════════════════════
        쉬운 설명 (ELI5):
        ═══════════════════════════════════════════════════════════════════
        "이거 전에 본 적 있어?" 라고 물어봅니다.
        - True: "응, 60초 안에 본 적 있어 (중복)"
        - False: "아니, 새로 온 거야 (처리해)"

        Args:
            event_id: 이벤트 고유 ID (예: "AAPL_tick_1736330000")
            event_time: 이벤트 시간 (Unix timestamp). None이면 현재 시간 사용.

        Returns:
            bool: True면 중복, False면 신규
        """
        now = event_time or time.time()

        # 주기적 정리
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup(now)

        # 중복 검사
        if event_id in self._seen:
            last_seen = self._seen[event_id]
            if now - last_seen <= self.window_seconds:
                return True  # 중복!

        # 신규 이벤트 등록
        self._seen[event_id] = now
        return False

    def _cleanup(self, now: float) -> None:
        """
        만료된 이벤트 정리

        메모리 누수 방지를 위해 윈도우가 지난 이벤트 제거
        """
        expired = [
            event_id
            for event_id, last_seen in self._seen.items()
            if now - last_seen > self.window_seconds
        ]

        for event_id in expired:
            del self._seen[event_id]

        self._last_cleanup = now

        if expired:
            logger.debug(f"EventDeduplicator cleanup: {len(expired)} events expired")

    def mark_seen(self, event_id: str, event_time: Optional[float] = None) -> None:
        """
        이벤트를 "본 것으로" 표시 (중복 검사 없이)

        Args:
            event_id: 이벤트 고유 ID
            event_time: 이벤트 시간
        """
        self._seen[event_id] = event_time or time.time()

    def clear(self) -> None:
        """모든 기록 초기화"""
        self._seen.clear()
        self._last_cleanup = time.time()

    @property
    def size(self) -> int:
        """현재 추적 중인 이벤트 수"""
        return len(self._seen)

    @staticmethod
    def make_event_id(ticker: str, event_type: str, timestamp_ms: int) -> str:
        """
        표준 event_id 생성 헬퍼

        Args:
            ticker: 종목 코드
            event_type: 이벤트 유형 (tick, bar, etc.)
            timestamp_ms: 이벤트 시간 (Unix ms)

        Returns:
            str: 이벤트 ID (예: "AAPL_tick_1736330000000")
        """
        return f"{ticker}_{event_type}_{timestamp_ms}"


__all__ = ["EventDeduplicator"]
