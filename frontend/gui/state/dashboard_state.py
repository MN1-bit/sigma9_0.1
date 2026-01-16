# ==============================================================================
# dashboard_state.py - Dashboard 중앙 상태 관리
# ==============================================================================
# 📌 이 파일의 역할:
#    Sigma9 Dashboard에서 사용하는 공유 상태를 중앙화합니다.
#    싱글톤 패턴 대신 의존성 주입(DI)을 통해 상태를 공유합니다.
#
# 📌 관리하는 상태:
#    - Tier 2 캐시: Hot Zone 종목 정보
#    - Ignition Score 캐시: 종목별 Ignition Score
#    - 가격 캐시: 실시간 가격 정보
#    - 차트 상태: 현재 표시 중인 종목 및 타임프레임
# ==============================================================================
from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

# [REFAC Phase 4] Tier2Item을 tier2_panel.py로 이동
from ..panels.tier2_panel import Tier2Item

if TYPE_CHECKING:
    pass

# 하위 호환성을 위해 re-export
__all__ = ["DashboardState", "Tier2Item"]


class DashboardState(QObject):
    """
    Dashboard 중앙 상태 관리자

    ELI5: 대시보드의 모든 부품들이 공유하는 "공용 게시판"이에요.
    각 패널이 이 게시판을 통해 정보를 주고받습니다.

    ═══════════════════════════════════════════════════════════════════════════
    쉬운 설명:
    ═══════════════════════════════════════════════════════════════════════════
    예전에는 Dashboard가 모든 상태를 직접 관리했어요.
    이제는 이 DashboardState가 상태만 관리하고,
    각 패널은 필요한 상태를 여기서 가져갑니다.

    장점:
    - 코드가 깔끔해짐 (각 패널이 자기 일만 함)
    - 테스트가 쉬워짐 (상태만 테스트 가능)
    - 버그 찾기 쉬움 (상태 변경이 한 곳에서만 일어남)
    ═══════════════════════════════════════════════════════════════════════════
    """

    # =========================================================================
    # 시그널 (Signal) - 상태 변경을 알림
    # =========================================================================
    # Tier 2 종목이 추가/제거될 때
    tier2_updated = pyqtSignal(str)  # ticker

    # Ignition Score가 업데이트될 때
    ignition_updated = pyqtSignal(str, float)  # ticker, score

    # 가격이 업데이트될 때
    price_updated = pyqtSignal(str, float)  # ticker, price

    # 현재 차트 종목이 변경될 때
    chart_ticker_changed = pyqtSignal(str)  # ticker

    # 로그 메시지
    log_message = pyqtSignal(str)  # message

    # =========================================================================
    # 📌 [09-009] Ticker Selection Event Bus
    # =========================================================================
    # 활성 티커 변경 시그널: (ticker, source)
    ticker_changed = pyqtSignal(str, str)

    class TickerSource:
        """티커 변경 출처 (디버깅/로깅용)"""

        WATCHLIST = "watchlist"
        TIER2 = "tier2"
        SEARCH = "search"
        CHART = "chart"
        EXTERNAL = "external"
        UNKNOWN = "unknown"

    def __init__(self, ws_adapter=None):
        super().__init__()

        # 📌 [09-009] WebSocket adapter for backend sync
        self._ws = ws_adapter

        # =====================================================================
        # Tier 2 Hot Zone 캐시 (ticker -> Tier2Item)
        # Hot Zone에 승격된 종목들의 정보를 저장
        # =====================================================================
        self._tier2_cache: dict[str, Tier2Item] = {}

        # =====================================================================
        # Ignition Score 캐시 (ticker -> score)
        # 각 종목의 최신 Ignition Score를 저장
        # =====================================================================
        self._ignition_cache: dict[str, float] = {}

        # =====================================================================
        # 실시간 가격 캐시 (ticker -> price)
        # WebSocket으로 수신한 최신 가격을 저장
        # =====================================================================
        self._price_cache: dict[str, float] = {}

        # =====================================================================
        # 차트 상태
        # 현재 표시 중인 종목과 타임프레임
        # =====================================================================
        self._current_chart_ticker: str | None = None

        # =====================================================================
        # 📌 [09-009] 활성 티커 상태 (차트 티커와 별개)
        # =====================================================================
        self._current_ticker: str | None = None
        self._previous_ticker: str | None = None
        self._current_timeframe: str = "1D"

        # =====================================================================
        # 스로틀링용 대기 틱
        # 실시간 틱이 너무 빠르면 마지막 값만 사용
        # =====================================================================
        self._pending_tick: dict | None = None

    # =========================================================================
    # Tier 2 캐시 메서드
    # =========================================================================
    def get_tier2_items(self) -> dict[str, Tier2Item]:
        """모든 Tier 2 종목 반환"""
        return self._tier2_cache.copy()

    def get_tier2_item(self, ticker: str) -> Tier2Item | None:
        """특정 Tier 2 종목 조회"""
        return self._tier2_cache.get(ticker)

    def add_tier2_item(self, item: Tier2Item) -> None:
        """Tier 2에 종목 추가"""
        self._tier2_cache[item.ticker] = item
        self.tier2_updated.emit(item.ticker)

    def remove_tier2_item(self, ticker: str) -> bool:
        """Tier 2에서 종목 제거, 제거 성공 시 True"""
        if ticker in self._tier2_cache:
            del self._tier2_cache[ticker]
            self.tier2_updated.emit(ticker)
            return True
        return False

    def is_in_tier2(self, ticker: str) -> bool:
        """종목이 Tier 2에 있는지 확인"""
        return ticker in self._tier2_cache

    def tier2_count(self) -> int:
        """Tier 2 종목 수"""
        return len(self._tier2_cache)

    # =========================================================================
    # Ignition Score 캐시 메서드
    # =========================================================================
    def get_ignition_score(self, ticker: str) -> float:
        """종목의 Ignition Score 조회, 없으면 0.0"""
        return self._ignition_cache.get(ticker, 0.0)

    def set_ignition_score(self, ticker: str, score: float) -> None:
        """Ignition Score 설정"""
        self._ignition_cache[ticker] = score
        self.ignition_updated.emit(ticker, score)

    # =========================================================================
    # 가격 캐시 메서드
    # =========================================================================
    def get_price(self, ticker: str) -> float:
        """종목의 현재 가격 조회, 없으면 0.0"""
        return self._price_cache.get(ticker, 0.0)

    def set_price(self, ticker: str, price: float) -> None:
        """가격 설정"""
        self._price_cache[ticker] = price
        self.price_updated.emit(ticker, price)

    # =========================================================================
    # 차트 상태 메서드
    # =========================================================================
    @property
    def current_chart_ticker(self) -> str | None:
        """현재 차트에 표시 중인 종목"""
        return self._current_chart_ticker

    @current_chart_ticker.setter
    def current_chart_ticker(self, ticker: str | None) -> None:
        """현재 차트 종목 변경"""
        if self._current_chart_ticker != ticker:
            self._current_chart_ticker = ticker
            if ticker:
                self.chart_ticker_changed.emit(ticker)

    @property
    def current_timeframe(self) -> str:
        """현재 타임프레임"""
        return self._current_timeframe

    @current_timeframe.setter
    def current_timeframe(self, timeframe: str) -> None:
        """타임프레임 변경"""
        self._current_timeframe = timeframe

    # =========================================================================
    # 스로틀링 대기 틱 메서드
    # =========================================================================
    @property
    def pending_tick(self) -> dict | None:
        """대기 중인 틱"""
        return self._pending_tick

    @pending_tick.setter
    def pending_tick(self, tick: dict | None) -> None:
        """대기 틱 설정"""
        self._pending_tick = tick

    # =========================================================================
    # 로깅 헬퍼
    # =========================================================================
    def log(self, message: str) -> None:
        """로그 메시지 발행"""
        self.log_message.emit(message)

    # =========================================================================
    # 📌 [09-009] Ticker Selection Methods
    # =========================================================================
    @property
    def current_ticker(self) -> str | None:
        """현재 선택된 활성 티커 (읽기 전용)"""
        return self._current_ticker

    @property
    def previous_ticker(self) -> str | None:
        """이전 활성 티커"""
        return self._previous_ticker

    def select_ticker(self, ticker: str, source: str = "unknown") -> None:
        """
        티커 선택 (Optimistic Update 패턴)

        1. 즉시 로컬 상태 업데이트 → UI 즉각 반응
        2. Backend에 비동기 전송 → 상태 동기화

        Args:
            ticker: 선택할 티커 심볼
            source: 변경 출처 (TickerSource 참조)
        """
        if self._current_ticker == ticker:
            return  # 동일 티커면 무시

        self._previous_ticker = self._current_ticker
        self._current_ticker = ticker

        # 1. 📢 즉시 UI 업데이트 (Optimistic)
        # ELI5: 서버 응답 기다리지 않고 일단 화면부터 바꿈
        self.ticker_changed.emit(ticker, source)

        # 2. 🌐 Backend 동기화 (비동기)
        if self._ws and hasattr(self._ws, "send"):
            self._ws.send(
                {
                    "type": "SET_ACTIVE_TICKER",
                    "ticker": ticker,
                    "source": source,
                }
            )

    def _handle_active_ticker_changed(self, ticker: str, source: str) -> None:
        """
        Backend에서 ACTIVE_TICKER_CHANGED 수신 시 처리

        다른 클라이언트가 티커를 변경했을 때 동기화
        """
        if self._current_ticker != ticker:
            self._previous_ticker = self._current_ticker
            self._current_ticker = ticker
            self.ticker_changed.emit(ticker, source)
