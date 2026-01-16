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
    # [02-001.5] MassiveWebSocketClient: 실시간 WebSocket 클라이언트 (Singleton)
    # ───────────────────────────────────────────────────────────────────────
    @staticmethod
    def _create_massive_ws(
        delayed: bool = False,
        reconnect_interval: int = 5,
    ):
        """
        MassiveWebSocketClient 생성 팩토리

        📌 [02-001.5] Realtime Layer 의존성의 루트
        📌 지연 import로 순환 참조 방지
        📌 API Key는 환경변수에서 자동 로드 (클래스 내부 처리)
        📌 websockets 미설치 시 None 반환 (ImportError 방지)

        Args:
            delayed: True면 15분 지연 데이터 (무료), False면 실시간
            reconnect_interval: 재연결 시도 간격 (초)

        Returns:
            MassiveWebSocketClient 인스턴스 또는 None
        """
        try:
            from backend.data.massive_ws_client import MassiveWebSocketClient
        except ImportError:
            # websockets 라이브러리 미설치
            return None

        try:
            return MassiveWebSocketClient(
                delayed=delayed,
                reconnect_interval=reconnect_interval,
            )
        except ValueError:
            # MASSIVE_API_KEY 환경변수 미설정
            return None

    # MassiveWebSocketClient: 실시간 WebSocket 클라이언트 (Singleton)
    massive_ws = providers.Singleton(_create_massive_ws)

    # ═══════════════════════════════════════════════════════════════════════
    # [02-002] Realtime Layer - Tick Distribution & Subscription
    # ═══════════════════════════════════════════════════════════════════════
    #
    # 📌 Data Flow:
    #   MassiveWebSocketClient
    #       ↓ on_bar / on_tick
    #   TickBroadcaster → ConnectionManager (GUI)
    #       ↓
    #   TickDispatcher → Strategy, TrailingStop, etc.
    #
    # ═══════════════════════════════════════════════════════════════════════

    # ───────────────────────────────────────────────────────────────────────
    # [02-002] TickDispatcher: 틱 데이터 중앙 배포자 (Singleton)
    # ───────────────────────────────────────────────────────────────────────
    @staticmethod
    def _create_tick_dispatcher():
        """
        TickDispatcher 생성 팩토리

        📌 [02-002] 의존성 없음 - 단순 Singleton
        📌 전략, TrailingStop, GUI 등이 이 Dispatcher에 구독
        """
        from backend.core.tick_dispatcher import TickDispatcher

        return TickDispatcher()

    tick_dispatcher = providers.Singleton(_create_tick_dispatcher)

    # ───────────────────────────────────────────────────────────────────────
    # [02-002] SubscriptionManager: Watchlist ↔ Massive 구독 동기화 (Singleton)
    # ───────────────────────────────────────────────────────────────────────
    @staticmethod
    def _create_subscription_manager(massive_ws: Any):
        """
        SubscriptionManager 생성 팩토리

        📌 [02-002] massive_ws는 Optional (나중에 set_massive_ws로 설정 가능)
        📌 Watchlist 변경 시 Massive 구독 자동 동기화
        """
        from backend.core.subscription_manager import SubscriptionManager

        return SubscriptionManager(massive_ws=massive_ws)

    subscription_manager = providers.Singleton(
        _create_subscription_manager,
        massive_ws=massive_ws,
    )

    # ───────────────────────────────────────────────────────────────────────
    # [02-002] TickBroadcaster: Massive → GUI WebSocket Bridge (Callable)
    # ───────────────────────────────────────────────────────────────────────
    @staticmethod
    def _create_tick_broadcaster(
        massive_ws: Any,
        ws_manager: Any,
        tick_dispatcher: Any,
    ):
        """
        TickBroadcaster 생성 팩토리

        📌 [02-002] 서버 lifespan에서 1회 호출하여 생성
        📌 Callable Provider: 호출 시마다 새 인스턴스 (서버당 1개)
        📌 loop는 생성 시 None, set_event_loop()로 나중에 설정
        """
        from backend.core.tick_broadcaster import TickBroadcaster

        return TickBroadcaster(
            massive_ws=massive_ws,
            ws_manager=ws_manager,
            loop=None,  # 서버 시작 후 set_event_loop() 호출
            tick_dispatcher=tick_dispatcher,
        )

    tick_broadcaster = providers.Callable(
        _create_tick_broadcaster,
        massive_ws=massive_ws,
        ws_manager=ws_manager,
        tick_dispatcher=tick_dispatcher,
    )

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

        policy = create_flush_policy(
            actual_policy_type, interval_seconds=actual_interval
        )
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
    # Broker Layer
    # ═══════════════════════════════════════════════════════════════════════════
    #
    # 📌 [02-001] Broker Layer DI 통합
    # 📌 IBKRConnector를 루트로 하는 단방향 의존성 체인
    #
    # ═══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _create_ibkr_connector():
        """
        IBKRConnector 생성 팩토리

        📌 IB Gateway/TWS 연결 관리
        📌 QThread 기반이지만 Container에서 생명주기 관리
        """
        from backend.broker.ibkr_connector import IBKRConnector

        return IBKRConnector()

    # IBKRConnector: IBKR 브로커 연결 (Singleton)
    ibkr_connector = providers.Singleton(_create_ibkr_connector)

    @staticmethod
    def _create_order_manager(connector):
        """
        OrderManager 생성 팩토리

        📌 IBKRConnector를 통해 주문 실행/추적
        """
        from backend.core.order_manager import OrderManager

        return OrderManager(connector=connector)

    # OrderManager: 주문 관리 (Singleton)
    order_manager = providers.Singleton(
        _create_order_manager,
        connector=ibkr_connector,
    )

    @staticmethod
    def _create_risk_manager(connector):
        """
        RiskManager 생성 팩토리

        📌 Kelly Criterion 포지션 사이징
        📌 Kill Switch 기능
        """
        from backend.core.risk_manager import RiskManager

        return RiskManager(connector=connector)

    # RiskManager: 리스크 관리 (Singleton)
    risk_manager = providers.Singleton(
        _create_risk_manager,
        connector=ibkr_connector,
    )

    @staticmethod
    def _create_trailing_stop_manager(connector):
        """
        TrailingStopManager 생성 팩토리

        📌 IBKR 네이티브 Trailing Stop 주문 관리
        """
        from backend.core.trailing_stop import TrailingStopManager

        return TrailingStopManager(connector=connector)

    # TrailingStopManager: Trailing Stop 관리 (Singleton)
    trailing_stop_manager = providers.Singleton(
        _create_trailing_stop_manager,
        connector=ibkr_connector,
    )

    @staticmethod
    def _create_double_tap_manager(connector, order_manager, trailing_manager):
        """
        DoubleTapManager 생성 팩토리

        📌 1차 청산 후 재진입 로직
        📌 Cooldown + HOD 돌파 조건 모니터링
        """
        from backend.core.double_tap import DoubleTapManager

        return DoubleTapManager(
            connector=connector,
            order_manager=order_manager,
            trailing_manager=trailing_manager,
        )

    # DoubleTapManager: 재진입 관리 (Singleton)
    double_tap_manager = providers.Singleton(
        _create_double_tap_manager,
        connector=ibkr_connector,
        order_manager=order_manager,
        trailing_manager=trailing_stop_manager,
    )


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
