# ============================================================================
# Time Sync Tests - 시간 동기화 테스트
# ============================================================================
# 📌 이 파일의 역할:
#   - TickData 모델 하위 호환성 테스트
#   - EventDeduplicator 테스트
#   - EventSequencer 테스트
#
# 📖 리팩터링 [08-001]:
#   - 신규 테스트 파일
# ============================================================================

"""
Time Synchronization Tests

08-001 리팩터링 관련 테스트 케이스입니다.
"""

import time
from datetime import datetime, timedelta

import pytest


class TestTickDataBackwardCompatibility:
    """TickData 모델 하위 호환성 테스트"""

    def test_event_time_required(self):
        """event_time은 필수 필드"""
        from backend.models import TickData

        now = datetime.now()
        tick = TickData(price=10.50, volume=1000, event_time=now)

        assert tick.event_time == now
        assert tick.price == 10.50
        assert tick.volume == 1000

    def test_timestamp_property_returns_event_time(self):
        """timestamp 프로퍼티는 event_time을 반환 (하위 호환성)"""
        from backend.models import TickData

        event_time = datetime(2026, 1, 8, 10, 30, 0)
        tick = TickData(price=10.50, volume=1000, event_time=event_time)

        # 하위 호환성: tick.timestamp는 event_time을 반환
        assert tick.timestamp == event_time

    def test_receive_time_defaults_to_now(self):
        """receive_time은 기본값으로 현재 시간"""
        from backend.models import TickData

        before = datetime.now()
        tick = TickData(price=10.50, volume=1000, event_time=datetime.now())
        after = datetime.now()

        assert before <= tick.receive_time <= after

    def test_latency_ms_calculation(self):
        """latency_ms는 receive_time - event_time (ms)"""
        from backend.models import TickData

        event_time = datetime.now() - timedelta(milliseconds=100)
        receive_time = datetime.now()

        tick = TickData(
            price=10.50,
            volume=1000,
            event_time=event_time,
            receive_time=receive_time,
        )

        # 약 100ms 지연
        assert 90 <= tick.latency_ms <= 200  # 허용 오차


class TestEventDeduplicator:
    """EventDeduplicator 테스트"""

    def test_first_event_is_not_duplicate(self):
        """첫 이벤트는 중복 아님"""
        from backend.core.deduplicator import EventDeduplicator

        dedup = EventDeduplicator(window_seconds=60)

        assert dedup.is_duplicate("event_1") is False

    def test_same_event_within_window_is_duplicate(self):
        """윈도우 내 같은 이벤트는 중복"""
        from backend.core.deduplicator import EventDeduplicator

        dedup = EventDeduplicator(window_seconds=60)

        assert dedup.is_duplicate("event_1") is False
        assert dedup.is_duplicate("event_1") is True  # 중복!

    def test_different_events_are_not_duplicates(self):
        """다른 이벤트는 중복 아님"""
        from backend.core.deduplicator import EventDeduplicator

        dedup = EventDeduplicator(window_seconds=60)

        assert dedup.is_duplicate("event_1") is False
        assert dedup.is_duplicate("event_2") is False

    def test_event_expires_after_window(self):
        """윈도우 지나면 만료"""
        from backend.core.deduplicator import EventDeduplicator

        dedup = EventDeduplicator(window_seconds=1)  # 1초 윈도우

        # 과거 시간으로 이벤트 등록
        past = time.time() - 2  # 2초 전
        now = time.time()

        assert dedup.is_duplicate("event_1", event_time=past) is False
        # 현재 시간으로 같은 이벤트 확인 → 윈도우 지났으므로 새 이벤트
        assert dedup.is_duplicate("event_1", event_time=now) is False

    def test_make_event_id(self):
        """event_id 생성 헬퍼"""
        from backend.core.deduplicator import EventDeduplicator

        event_id = EventDeduplicator.make_event_id("AAPL", "tick", 1736330000000)
        assert event_id == "AAPL_tick_1736330000000"


class TestEventSequencer:
    """EventSequencer 테스트"""

    def test_events_are_ordered_by_event_time(self):
        """이벤트는 event_time 순으로 정렬"""
        from backend.core.event_sequencer import EventSequencer

        sequencer = EventSequencer(buffer_ms=0)  # 즉시 방출

        # 순서 뒤바뀌어서 도착
        now_ms = int(time.time() * 1000)

        events_out = []
        for e in sequencer.push(
            "B", event_time_ms=now_ms + 200, receive_time_ms=now_ms
        ):
            events_out.append(e)
        for e in sequencer.push(
            "A", event_time_ms=now_ms + 100, receive_time_ms=now_ms
        ):
            events_out.append(e)

        # flush로 남은 이벤트 방출
        events_out.extend(sequencer.flush())

        # event_time 순으로 정렬되어야 함
        assert [e.data for e in events_out] == ["A", "B"]

    def test_buffer_delays_emission(self):
        """버퍼링으로 방출 지연"""
        from backend.core.event_sequencer import EventSequencer

        sequencer = EventSequencer(buffer_ms=100)  # 100ms 버퍼

        now_ms = int(time.time() * 1000)

        # 이벤트 추가 - 아직 방출 안 됨
        events_out = list(
            sequencer.push("A", event_time_ms=now_ms, receive_time_ms=now_ms)
        )

        assert len(events_out) == 0  # 버퍼링 중
        assert sequencer.pending_count == 1

    def test_flush_emits_all_events(self):
        """flush는 모든 이벤트 방출"""
        from backend.core.event_sequencer import EventSequencer

        sequencer = EventSequencer(buffer_ms=1000)  # 긴 버퍼

        now_ms = int(time.time() * 1000)
        list(sequencer.push("A", event_time_ms=now_ms, receive_time_ms=now_ms))
        list(sequencer.push("B", event_time_ms=now_ms + 100, receive_time_ms=now_ms))

        assert sequencer.pending_count == 2

        # flush
        events = list(sequencer.flush())

        assert len(events) == 2
        assert sequencer.pending_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
