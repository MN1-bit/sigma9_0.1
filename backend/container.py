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

    # ───────────────────────────────────────────────────────────────────────
    # [11-002] ParquetManager: Parquet I/O 관리자 (Singleton)
    # ───────────────────────────────────────────────────────────────────────
    @staticmethod
    def _create_parquet_manager(base_dir: str | None = None):
        """
        ParquetManager 생성 팩토리

        📌 [11-002] DataRepository의 Low-Level I/O 담당
        """
        from backend.data.parquet_manager import ParquetManager

        # config 미설정 시 기본값 사용
        actual_dir = base_dir or "data/parquet"
        return ParquetManager(base_dir=actual_dir)

    parquet_manager = providers.Singleton(_create_parquet_manager)

    # ───────────────────────────────────────────────────────────────────────
    # [11-002] DataRepository: 통합 데이터 접근 레이어 (Singleton)
    # ───────────────────────────────────────────────────────────────────────
    @staticmethod
    def _create_data_repository(
        parquet_manager: Any,
        massive_client: Any,
        flush_policy_type: str | None = None,
        flush_interval: float | None = None,
    ):
        """
        DataRepository 생성 팩토리

        📌 [11-002] 모든 데이터 접근은 이 레이어를 통해
        📌 Gap Fill, Indicator 캐싱, Score Flush 지원
        """
        from backend.data.data_repository import DataRepository
        from backend.data.flush_policy import create_flush_policy

        # config 미설정 시 기본값 사용
        actual_policy_type = flush_policy_type or "interval"
        actual_interval = flush_interval if flush_interval is not None else 30.0

        policy = create_flush_policy(actual_policy_type, interval_seconds=actual_interval)
        return DataRepository(
            parquet_manager=parquet_manager,
            massive_client=massive_client,
            flush_policy=policy,
        )

    data_repository = providers.Singleton(
        _create_data_repository,
        parquet_manager=parquet_manager,
        massive_client=massive_client,
    )

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

    # ───────────────────────────────────────────────────────────────────────
    # [02-004] WatchlistStore: Watchlist 저장소 (Singleton)
    # ───────────────────────────────────────────────────────────────────────
    @staticmethod
    def _create_watchlist_store():
        """
        WatchlistStore 생성 팩토리

        📌 [02-004] 싱글톤 패턴 제거, Container로 관리
        📌 Watchlist JSON 저장/로드 담당
        """
        from backend.data.watchlist_store import WatchlistStore

        return WatchlistStore()

    watchlist_store = providers.Singleton(_create_watchlist_store)

    # ───────────────────────────────────────────────────────────────────────
    # [15-001] TickerInfoService: 티커 종합 정보 서비스 (Singleton)
    # ───────────────────────────────────────────────────────────────────────
    @staticmethod
    def _create_ticker_info_service():
        """
        TickerInfoService 생성 팩토리

        📌 [15-001] Massive API 기반 13개 카테고리 티커 정보 조회
        📌 SQLite 캐싱으로 UX 최적화
        """
        from backend.data.ticker_info_service import TickerInfoService

        return TickerInfoService()

    ticker_info_service = providers.Singleton(_create_ticker_info_service)

    # ───────────────────────────────────────────────────────────────────────
    # [02-005] SymbolMapper: 심볼 매핑 서비스 (Singleton)
    # ───────────────────────────────────────────────────────────────────────
    @staticmethod
    def _create_symbol_mapper():
        """
        SymbolMapper 생성 팩토리

        📌 [02-005] 싱글톤 패턴 제거, Container로 관리
        📌 Massive ↔ IBKR 심볼 변환 담당
        """
        from backend.data.symbol_mapper import SymbolMapper

        return SymbolMapper()

    symbol_mapper = providers.Singleton(_create_symbol_mapper)

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

    # ───────────────────────────────────────────────────────────────────────
    # [09-009] TradingContext: 활성 티커 컨텍스트 (Singleton)
    # ───────────────────────────────────────────────────────────────────────
    @staticmethod
    def _create_trading_context():
        """
        TradingContext 생성 팩토리

        📌 [09-009] Frontend ↔ Backend 활성 티커 상태 관리
        📌 모든 Backend 서비스가 공유하는 "현재 상태"
        """
        from backend.core.trading_context import TradingContext

        return TradingContext()

    trading_context = providers.Singleton(_create_trading_context)

    @staticmethod
    def _create_realtime_scanner(
        massive_client: Any,
        ws_manager: Any,
        data_repository: Any,  # [11-002] DataRepository 주입
        scoring_strategy: Any,
        poll_interval: float = 1.0,
    ):
        """
        RealtimeScanner 생성 팩토리

        📌 [11-002] DataRepository를 통해 데이터 접근
        📌 Singleton 패턴 제거 - Container가 생명주기 관리
        """
        from backend.core.realtime_scanner import RealtimeScanner

        return RealtimeScanner(
            massive_client=massive_client,
            ws_manager=ws_manager,
            data_repository=data_repository,  # [11-002]
            ignition_monitor=None,  # 순환 참조 방지: 나중에 설정
            poll_interval=poll_interval,
            scoring_strategy=scoring_strategy,
        )

    # RealtimeScanner: 실시간 스캐너 (Singleton)
    realtime_scanner = providers.Singleton(
        _create_realtime_scanner,
        massive_client=massive_client,
        ws_manager=ws_manager,
        data_repository=data_repository,  # [11-002] DataRepository 주입
        scoring_strategy=scoring_strategy,
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
