# ============================================================================
# Sigma9 DI Container - 의존성 주입 컨테이너
# ============================================================================
# 📌 이 파일의 역할:
#   - dependency-injector 라이브러리 기반 DI Container 정의
#   - Singleton Anti-Pattern 제거 및 테스트 용이성 확보
#   - 전역 상태 오염 방지
#
# 📌 사용 예시:
#   >>> from backend.container import Container
#   >>> container = Container()
#   >>> container.wire(modules=["backend.api.routes"])
#   >>> scanner = container.realtime_scanner()
#
# 📖 리팩터링 [02-001]:
#   - 기존 Singleton 패턴 (_instance, get_*_instance) 제거
#   - DI Container로 중앙 관리
#   - Mock 주입으로 테스트 용이성 확보
# ============================================================================

"""
Sigma9 DI Container Module

dependency-injector 라이브러리를 사용하여 의존성을 중앙에서 관리합니다.
Singleton Anti-Pattern을 제거하고 테스트 용이성을 확보합니다.

[02-001] DI Container 도입 리팩터링
"""

from typing import Any, Optional
from dependency_injector import containers, providers

# ═══════════════════════════════════════════════════════════════════════════
# 지연 Import (순환 의존성 방지)
# ═══════════════════════════════════════════════════════════════════════════
#
# 📌 왜 지연 Import를 사용하는가?
#
# Container가 모듈 로드 시점에 모든 클래스를 import하면
# 순환 참조가 발생할 수 있습니다. Factory/Singleton provider에서
# 문자열 경로로 클래스를 참조하거나, 함수 내에서 import합니다.
#
# ═══════════════════════════════════════════════════════════════════════════


class Container(containers.DeclarativeContainer):
    """
    Sigma9 DI Container

    ═══════════════════════════════════════════════════════════════════════
    역할:
    ═══════════════════════════════════════════════════════════════════════
    - 모든 핵심 서비스의 생명주기 관리
    - 의존성 주입으로 느슨한 결합 실현
    - 테스트 시 Mock 주입 용이

    ═══════════════════════════════════════════════════════════════════════
    계층 구조:
    ═══════════════════════════════════════════════════════════════════════

    Container
    ├── Config (Configuration)
    ├── Data Layer
    │   ├── massive_client (MassiveClient)
    │   └── database (MarketDB)
    ├── Strategy Layer
    │   └── scoring_strategy (SeismographStrategy → ScoringStrategy)
    └── Core Layer
        ├── realtime_scanner (RealtimeScanner)
        └── ignition_monitor (IgnitionMonitor)

    ═══════════════════════════════════════════════════════════════════════
    사용 예시:
    ═══════════════════════════════════════════════════════════════════════

    # 일반 사용
    >>> container = Container()
    >>> container.config.from_dict({"api_key": "xxx"})
    >>> scanner = container.realtime_scanner()

    # 테스트용 Mock 주입
    >>> from unittest.mock import Mock
    >>> with container.realtime_scanner.override(Mock()):
    >>>     test_function()  # Mock이 주입됨
    """

    # ═══════════════════════════════════════════════════════════════════════
    # Configuration (설정)
    # ═══════════════════════════════════════════════════════════════════════
    #
    # 📌 외부 설정을 주입받아 사용
    # config.api_key, config.db_path 등으로 접근
    #
    config = providers.Configuration()

    # ═══════════════════════════════════════════════════════════════════════
    # WebSocket Manager (외부 주입)
    # ═══════════════════════════════════════════════════════════════════════
    #
    # 📌 ws_manager는 FastAPI 라우터에서 생성되므로 외부에서 주입
    # container.ws_manager.override(actual_manager)
    #
    ws_manager = providers.Object(None)

    # ═══════════════════════════════════════════════════════════════════════
    # Data Layer
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _create_massive_client():
        """
        MassiveClient 생성 팩토리

        📌 지연 import로 순환 참조 방지
        📌 API Key는 환경변수에서 로드
        """
        import os
        from backend.data.massive_client import MassiveClient

        api_key = os.getenv("MASSIVE_API_KEY", "")
        if not api_key:
            return None
        return MassiveClient(api_key)

    # MassiveClient: API 클라이언트 (Singleton)
    massive_client = providers.Singleton(_create_massive_client)

    @staticmethod
    def _create_database(db_path: Optional[str] = None):
        """
        MarketDB 생성 팩토리

        📌 DB 경로는 config에서 주입받거나 기본값 사용
        """
        from backend.data.database import MarketDB

        path = db_path or "data/market_data.db"
        return MarketDB(path)

    # MarketDB: 데이터베이스 (Singleton)
    database = providers.Singleton(
        _create_database,
        db_path=config.market_data.db_path,
    )

    # ═══════════════════════════════════════════════════════════════════════
    # Strategy Layer (인터페이스 → 구현체)
    # ═══════════════════════════════════════════════════════════════════════
    #
    # 📌 ScoringStrategy 인터페이스를 SeismographStrategy가 구현
    # 테스트 시 Mock ScoringStrategy로 교체 가능
    #

    @staticmethod
    def _create_scoring_strategy():
        """
        ScoringStrategy 생성 팩토리

        📌 SeismographStrategy를 ScoringStrategy 인터페이스로 제공
        📌 테스트 시 Mock으로 쉽게 교체 가능
        """
        from backend.strategies.seismograph import SeismographStrategy

        return SeismographStrategy()

    # ScoringStrategy: 스코어링 전략 (Singleton)
    scoring_strategy = providers.Singleton(_create_scoring_strategy)

    # ═══════════════════════════════════════════════════════════════════════
    # Core Layer
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _create_realtime_scanner(
        massive_client: Any,
        ws_manager: Any,
        database: Any,
        scoring_strategy: Any,
        poll_interval: float = 1.0,
    ):
        """
        RealtimeScanner 생성 팩토리

        📌 모든 의존성을 명시적으로 주입받음
        📌 Singleton 패턴 제거 - Container가 생명주기 관리
        """
        from backend.core.realtime_scanner import RealtimeScanner

        return RealtimeScanner(
            massive_client=massive_client,
            ws_manager=ws_manager,
            db=database,
            ignition_monitor=None,  # 순환 참조 방지: 나중에 설정
            poll_interval=poll_interval,
            scoring_strategy=scoring_strategy,
        )

    # RealtimeScanner: 실시간 스캐너 (Singleton)
    realtime_scanner = providers.Singleton(
        _create_realtime_scanner,
        massive_client=massive_client,
        ws_manager=ws_manager,
        database=database,
        scoring_strategy=scoring_strategy,
        poll_interval=config.scanner.poll_interval.as_float(),
    )

    @staticmethod
    def _create_ignition_monitor(
        strategy: Any, ws_manager: Any, poll_interval: float = 1.0
    ):
        """
        IgnitionMonitor 생성 팩토리

        📌 SeismographStrategy와 WebSocket Manager 주입
        📌 Singleton 패턴 제거
        """
        from backend.core.ignition_monitor import IgnitionMonitor

        return IgnitionMonitor(
            strategy=strategy,
            ws_manager=ws_manager,
            poll_interval=poll_interval,
        )

    # IgnitionMonitor: Ignition Score 모니터 (Singleton)
    ignition_monitor = providers.Singleton(
        _create_ignition_monitor,
        strategy=scoring_strategy,
        ws_manager=ws_manager,
        poll_interval=config.ignition.poll_interval.as_float(),
    )

    # ═══════════════════════════════════════════════════════════════════════
    # [08-001] Time Sync & Audit Services
    # ═══════════════════════════════════════════════════════════════════════

    @staticmethod
    def _create_audit_logger(log_dir: str = "data/audit"):
        """
        AuditLogger 생성 팩토리

        📌 의사결정 감사 로그 기록
        """
        from backend.core.audit_logger import AuditLogger

        return AuditLogger(log_dir=log_dir)

    # AuditLogger: 의사결정 감사 로거 (Singleton - 파일 핸들 공유)
    audit_logger = providers.Singleton(_create_audit_logger)

    @staticmethod
    def _create_event_deduplicator(window_seconds: int = 60):
        """
        EventDeduplicator 생성 팩토리

        📌 이벤트 중복 제거
        """
        from backend.core.deduplicator import EventDeduplicator

        return EventDeduplicator(window_seconds=window_seconds)

    # EventDeduplicator: 이벤트 중복 제거 (Factory - 상태 있음)
    event_deduplicator = providers.Factory(_create_event_deduplicator)

    @staticmethod
    def _create_event_sequencer(buffer_ms: int = 100):
        """
        EventSequencer 생성 팩토리

        📌 이벤트 순서 보장
        """
        from backend.core.event_sequencer import EventSequencer

        return EventSequencer(buffer_ms=buffer_ms)

    # EventSequencer: 이벤트 순서 보장 (Factory - 상태 있음)
    event_sequencer = providers.Factory(_create_event_sequencer)


# ═══════════════════════════════════════════════════════════════════════════
# Container 인스턴스 (전역)
# ═══════════════════════════════════════════════════════════════════════════
#
# 📌 서버 시작 시 초기화하여 사용
# 📌 테스트에서는 별도 Container 인스턴스 생성
#
container = Container()


def get_container() -> Container:
    """
    전역 Container 인스턴스 반환

    📌 FastAPI Depends에서 사용
    📌 테스트에서는 override 사용
    """
    return container
