# ============================================================================
# Time Display Widget - 시간 표시 위젯
# ============================================================================
# 📌 이 파일의 역할:
#   - GUI 상단바에 현재 시간 및 지연 시간(Latency) 표시
#   - 백엔드 시간 (EST/EDT), 로컬 시간 (KST), 데이터 지연 시간 표시
#
# 📖 사용 예시:
#   >>> from frontend.gui.widgets.time_display_widget import TimeDisplayWidget
#   >>> widget = TimeDisplayWidget()
#   >>> widget.update_from_heartbeat({"server_time_utc": "...", "sent_at": ...})
#
# 📖 리팩터링 [08-001] Phase 1:
#   - 신규 파일 생성
# ============================================================================

"""
Time Display Widget

GUI 상단바에 시간 정보를 표시하는 위젯입니다.
"""

from datetime import datetime
from typing import Optional
import time

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import QTimer, pyqtSignal


class TimeDisplayWidget(QWidget):
    """
    시간 표시 위젯

    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    미국 거래소 시간과 한국 시간을 동시에 보여줍니다.
    데이터가 얼마나 늦게 도착하는지 지연 시간도 표시합니다.

    표시 형식:
      🇺🇸 02:31 PM  |  🇰🇷 03:31 AM  |  ⏱ 47ms

    Attributes:
        time_updated: 시간 업데이트 시그널 (dict 전달)

    Example:
        >>> widget = TimeDisplayWidget()
        >>> widget.update_from_heartbeat({
        ...     "server_time_utc": "2026-01-08T10:30:00Z",
        ...     "sent_at": 1736330000000
        ... })
    """

    # 시그널: 시간 업데이트 시 발생
    time_updated = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None, theme=None):
        """
        TimeDisplayWidget 초기화

        Args:
            parent: 부모 위젯
            theme: 테마 매니저 (None이면 기본 스타일 사용)
        """
        super().__init__(parent)

        # 테마 저장 (None이면 기본 색상 사용)
        self._theme = theme

        # 상태 변수
        self._server_time_utc: Optional[datetime] = None  # 백엔드 시간 (UTC)
        self._local_time: datetime = datetime.now()  # 로컬 시간
        self._latency_ms: int = 0  # Backend → Frontend 지연
        self._last_heartbeat_time: float = 0  # 마지막 heartbeat 수신 시간

        self._setup_ui()
        self._start_timer()

    def _setup_ui(self) -> None:
        """UI 초기화"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(8)

        # 기본 색상 (테마가 없을 때 사용)
        text_color = self._get_color("text_secondary", "#888888")
        text_primary = self._get_color("text", "#FFFFFF")

        # 스타일 문자열
        label_style = f"""
            color: {text_color}; 
            font-size: 11px;
            background: transparent;
            border: none;
        """
        time_style = f"""
            color: {text_primary}; 
            font-size: 11px;
            font-weight: bold;
            font-family: 'Consolas', 'Monaco', monospace;
            background: transparent;
            border: none;
        """

        # 🇺🇸 미국 시간 (EST/EDT)
        self._us_icon = QLabel("🇺🇸")
        self._us_icon.setStyleSheet(label_style)
        layout.addWidget(self._us_icon)

        self._us_time_label = QLabel("--:-- --")
        self._us_time_label.setStyleSheet(time_style)
        self._us_time_label.setToolTip("미국 동부 시간 (EST/EDT)")
        layout.addWidget(self._us_time_label)

        # 구분자
        sep1 = QLabel("|")
        sep1.setStyleSheet(label_style)
        layout.addWidget(sep1)

        # 🇰🇷 한국 시간 (KST)
        self._kr_icon = QLabel("🇰🇷")
        self._kr_icon.setStyleSheet(label_style)
        layout.addWidget(self._kr_icon)

        self._kr_time_label = QLabel("--:-- --")
        self._kr_time_label.setStyleSheet(time_style)
        self._kr_time_label.setToolTip("한국 표준시 (KST)")
        layout.addWidget(self._kr_time_label)

        # 구분자
        sep2 = QLabel("|")
        sep2.setStyleSheet(label_style)
        layout.addWidget(sep2)

        # ⏱ 지연 시간 (Latency)
        self._latency_icon = QLabel("⏱")
        self._latency_icon.setStyleSheet(label_style)
        layout.addWidget(self._latency_icon)

        self._latency_label = QLabel("--ms")
        self._latency_label.setStyleSheet(time_style)
        self._latency_label.setToolTip("Backend → Frontend 지연 시간")
        layout.addWidget(self._latency_label)

    def _get_color(self, key: str, default: str) -> str:
        """테마 색상 가져오기 (테마 없으면 기본값)"""
        if self._theme and hasattr(self._theme, "get_color"):
            return self._theme.get_color(key)
        return default

    def _start_timer(self) -> None:
        """
        1초 타이머 시작

        로컬 시간을 매초 업데이트합니다.
        서버 시간은 WebSocket heartbeat로만 업데이트됩니다.
        """
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_local_time)
        self._timer.start(1000)  # 1초

    def _update_local_time(self) -> None:
        """로컬 시간 업데이트 (1초마다)"""
        self._local_time = datetime.now()
        self._refresh_display()

    def _refresh_display(self) -> None:
        """시간 라벨 새로고침"""
        # 한국 시간 (KST = UTC+9)
        kr_time_str = self._local_time.strftime("%I:%M %p")
        self._kr_time_label.setText(kr_time_str)

        # 미국 동부 시간 (EST = UTC-5, EDT = UTC-4)
        if self._server_time_utc:
            # 서버 시간을 EST/EDT로 변환 (간단히 UTC-5 사용)
            from datetime import timedelta

            est_time = self._server_time_utc - timedelta(hours=5)
            us_time_str = est_time.strftime("%I:%M %p")
            self._us_time_label.setText(us_time_str)
        else:
            # 서버 시간 미수신 시 로컬 기준으로 추정
            from datetime import timedelta

            # KST (UTC+9) → EST (UTC-5) = -14시간
            est_time = self._local_time - timedelta(hours=14)
            us_time_str = est_time.strftime("%I:%M %p")
            self._us_time_label.setText(us_time_str)
            self._us_time_label.setStyleSheet(
                self._us_time_label.styleSheet().replace(
                    self._get_color("text", "#FFFFFF"),
                    self._get_color("text_secondary", "#888888"),
                )
            )

        # 지연 시간
        if self._latency_ms > 0:
            latency_str = f"{self._latency_ms}ms"
            # 지연에 따른 색상 (< 100ms: 녹색, < 500ms: 노랑, >= 500ms: 빨강)
            if self._latency_ms < 100:
                color = self._get_color("success", "#4CAF50")
            elif self._latency_ms < 500:
                color = self._get_color("warning", "#FF9800")
            else:
                color = self._get_color("danger", "#F44336")
            self._latency_label.setText(latency_str)
            self._latency_label.setStyleSheet(f"""
                color: {color}; 
                font-size: 11px;
                font-weight: bold;
                font-family: 'Consolas', 'Monaco', monospace;
                background: transparent;
                border: none;
            """)
        else:
            self._latency_label.setText("--ms")

    def update_from_heartbeat(self, data: dict) -> None:
        """
        WebSocket heartbeat 메시지로 시간 업데이트

        ═══════════════════════════════════════════════════════════════════
        쉬운 설명 (ELI5):
        ═══════════════════════════════════════════════════════════════════
        백엔드에서 "지금 내 시간은 이거야!" 라고 보내주면,
        그걸 받아서 화면에 표시하고, 얼마나 늦게 도착했는지도 계산해요.

        Args:
            data: heartbeat 메시지 딕셔너리
                - server_time_utc: 서버 시간 (ISO 형식 문자열)
                - sent_at: 전송 시점 (Unix ms timestamp)

        Example:
            >>> widget.update_from_heartbeat({
            ...     "server_time_utc": "2026-01-08T10:30:00+00:00",
            ...     "sent_at": 1736330000000
            ... })
        """
        now_ms = int(time.time() * 1000)

        # 서버 시간 파싱
        server_time_str = data.get("server_time_utc")
        if server_time_str:
            try:
                # ISO 형식 파싱
                self._server_time_utc = datetime.fromisoformat(
                    server_time_str.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        # 지연 시간 계산 (Backend → Frontend)
        sent_at = data.get("sent_at")
        if sent_at:
            self._latency_ms = now_ms - int(sent_at)
            self._last_heartbeat_time = now_ms / 1000

        # 화면 새로고침
        self._refresh_display()

        # 시그널 발생
        self.time_updated.emit(
            {
                "server_time_utc": self._server_time_utc,
                "local_time": self._local_time,
                "latency_ms": self._latency_ms,
            }
        )

    @property
    def latency_ms(self) -> int:
        """현재 지연 시간 (ms)"""
        return self._latency_ms

    @property
    def server_time(self) -> Optional[datetime]:
        """서버 시간 (UTC)"""
        return self._server_time_utc


__all__ = ["TimeDisplayWidget"]
