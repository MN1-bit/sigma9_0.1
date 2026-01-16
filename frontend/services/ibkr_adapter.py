# ============================================================================
# IBKREventAdapter - Backend Callback ↔ Frontend PyQt Signal Bridge
# ============================================================================
# 📌 이 파일의 역할:
#   Backend의 IBKRConnector가 보내는 callback을 PyQt Signal로 변환하여
#   GUI 위젯에서 안전하게 사용할 수 있도록 합니다.
#
# 📌 [02-003] PyQt6 의존성 분리
#   - Backend Layer는 순수 Python (callback 패턴)
#   - Frontend Layer에서 PyQt Signal로 변환
#   - GUI 위젯은 Signal.connect()로 연결
#
# 📌 사용 예시:
#   >>> from backend.container import container
#   >>> connector = container.ibkr_connector()
#   >>> adapter = IBKREventAdapter(connector)
#   >>> adapter.connected.connect(self._on_ibkr_connected)
# ============================================================================

"""
IBKREventAdapter Module

Backend의 IBKRConnector callback을 Frontend PyQt Signal로 변환합니다.
이를 통해 Backend와 Frontend 간의 레이어 분리를 유지하면서도
GUI에서 안전하게 이벤트를 처리할 수 있습니다.

[02-003] IBKRConnector PyQt6 의존성 제거
"""

from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

if TYPE_CHECKING:
    from backend.broker.ibkr_connector import IBKRConnector


class IBKREventAdapter(QObject):
    """
    IBKRConnector Callback → PyQt Signal 변환 어댑터

    ═══════════════════════════════════════════════════════════════════════
    역할:
    ═══════════════════════════════════════════════════════════════════════
    - Backend의 IBKRConnector는 순수 Python callback을 사용
    - Frontend의 GUI 위젯은 PyQt Signal을 사용해야 함
    - 이 어댑터가 callback → Signal 변환을 담당

    ═══════════════════════════════════════════════════════════════════════
    PyQt Signals:
    ═══════════════════════════════════════════════════════════════════════

    - connected(bool): 연결 상태 변경
    - account_update(dict): 계좌 정보 업데이트
    - error(str): 에러 메시지
    - log_message(str): 로그 메시지
    - order_placed(dict): 주문 접수됨
    - order_filled(dict): 주문 체결됨
    - order_cancelled(dict): 주문 취소됨
    - order_error(str, str): 주문 오류 (order_id, message)
    - positions_update(list): 포지션 목록 변경

    ═══════════════════════════════════════════════════════════════════════
    사용 예시:
    ═══════════════════════════════════════════════════════════════════════

    # DI Container에서 connector 가져오기
    connector = container.ibkr_connector()

    # Adapter 생성 및 연결
    adapter = IBKREventAdapter(connector)

    # GUI에서 Signal 연결
    adapter.connected.connect(self._on_connection_changed)
    adapter.account_update.connect(self._on_account_update)
    adapter.error.connect(self._on_error)
    """

    # ═══════════════════════════════════════════════════════════════════
    # PyQt Signals 정의
    # ═══════════════════════════════════════════════════════════════════

    connected = pyqtSignal(bool)  # 연결 상태 변경
    account_update = pyqtSignal(dict)  # 계좌 정보 업데이트
    error = pyqtSignal(str)  # 에러 메시지
    log_message = pyqtSignal(str)  # 로그 메시지

    # 주문 관련 Signals
    order_placed = pyqtSignal(dict)  # 주문 접수됨
    order_filled = pyqtSignal(dict)  # 주문 체결됨
    order_cancelled = pyqtSignal(dict)  # 주문 취소됨
    order_error = pyqtSignal(str, str)  # 주문 오류 (order_id, message)
    positions_update = pyqtSignal(list)  # 포지션 목록 변경

    def __init__(
        self,
        connector: "IBKRConnector",
        parent: QObject | None = None,
    ) -> None:
        """
        어댑터 초기화

        Args:
            connector: Backend IBKRConnector 인스턴스
            parent: 부모 QObject (선택)
        """
        super().__init__(parent)

        self._connector = connector

        # Backend callback을 이 어댑터의 메서드로 등록
        # 각 메서드는 callback을 받아서 Signal.emit()으로 변환
        self._register_callbacks()

    def _register_callbacks(self) -> None:
        """
        IBKRConnector에 callback 등록

        각 callback은 해당하는 PyQt Signal을 emit합니다.
        이를 통해 Backend → Frontend 이벤트 브릿지가 완성됩니다.
        """
        self._connector.set_on_connected(self._on_connected)
        self._connector.set_on_account_update(self._on_account_update)
        self._connector.set_on_error(self._on_error)
        self._connector.set_on_log_message(self._on_log_message)
        self._connector.set_on_order_placed(self._on_order_placed)
        self._connector.set_on_order_filled(self._on_order_filled)
        self._connector.set_on_order_cancelled(self._on_order_cancelled)
        self._connector.set_on_order_error(self._on_order_error)
        self._connector.set_on_positions_update(self._on_positions_update)

    # ═══════════════════════════════════════════════════════════════════
    # Callback → Signal 변환 메서드
    # ═══════════════════════════════════════════════════════════════════

    def _on_connected(self, is_connected: bool) -> None:
        """연결 상태 변경 callback → Signal"""
        self.connected.emit(is_connected)

    def _on_account_update(self, info: dict) -> None:
        """계좌 업데이트 callback → Signal"""
        self.account_update.emit(info)

    def _on_error(self, message: str) -> None:
        """에러 callback → Signal"""
        self.error.emit(message)

    def _on_log_message(self, message: str) -> None:
        """로그 메시지 callback → Signal"""
        self.log_message.emit(message)

    def _on_order_placed(self, order_info: dict) -> None:
        """주문 접수 callback → Signal"""
        self.order_placed.emit(order_info)

    def _on_order_filled(self, fill_info: dict) -> None:
        """주문 체결 callback → Signal"""
        self.order_filled.emit(fill_info)

    def _on_order_cancelled(self, cancel_info: dict) -> None:
        """주문 취소 callback → Signal"""
        self.order_cancelled.emit(cancel_info)

    def _on_order_error(self, order_id: str, message: str) -> None:
        """주문 에러 callback → Signal"""
        self.order_error.emit(order_id, message)

    def _on_positions_update(self, positions: list) -> None:
        """포지션 업데이트 callback → Signal"""
        self.positions_update.emit(positions)

    # ═══════════════════════════════════════════════════════════════════
    # Connector 접근 메서드 (편의 기능)
    # ═══════════════════════════════════════════════════════════════════

    @property
    def connector(self) -> "IBKRConnector":
        """내부 connector 인스턴스 반환"""
        return self._connector

    def start(self) -> None:
        """연결 시작 (편의 메서드)"""
        self._connector.start()

    def stop(self) -> None:
        """연결 중지 (편의 메서드)"""
        self._connector.stop()

    def is_connected(self) -> bool:
        """연결 상태 확인 (편의 메서드)"""
        return self._connector.is_connected()
