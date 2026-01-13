# ============================================================================
# Time Display Widget - 시간 표시 위젯
# ============================================================================
# 📌 이 파일의 역할:
#   - GUI 상단바에 현재 시간 및 지연 시간(Latency) 표시
#   - 미국 시간 (EST/EDT), 한국 시간 (KST), 데이터 지연 시간 표시
#   - 위아래 2줄 배치: 🇺🇸 US / 🇰🇷 KR
#
# 📖 리팩터링 [08-001] Phase 1 + UI 개선:
#   - 좌우 배치 → 위아래 배치로 변경
#   - 시간 포맷: YY/MM/DD - AM/PM HH:MM:SS.ms
# ============================================================================

"""
Time Display Widget

GUI 상단바에 시간 정보를 표시하는 위젯입니다.
"""

from datetime import datetime, timedelta
from typing import Optional
import time

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import QTimer, pyqtSignal


class TimeDisplayWidget(QWidget):
    """
    시간 표시 위젯 (위아래 배치)

    표시 형식:
      🇺🇸 26/01/07 - PM 11:31:42.123  ⏱ 47ms
      🇰🇷 26/01/08 - PM 01:31:42.123
    """

    time_updated = pyqtSignal(dict)

    def __init__(self, parent: Optional[QWidget] = None, theme=None):
        super().__init__(parent)
        self._theme = theme

        # 상태 변수
        self._server_time_utc: Optional[datetime] = None
        self._local_time: datetime = datetime.now()
        self._latency_ms: int = 0  # B⏱ 서버 전송 → 프론트엔드 수신 레이턴시
        self._event_latency_ms: int = 0  # E⏱ 이벤트 발생 → 백엔드 처리 레이턴시
        self._last_heartbeat_time: float = 0
        self._last_event_time: int = 0  # [08-001] 이전 event_time (변경 감지용)

        self._setup_ui()
        self._start_timer()

    def _setup_ui(self) -> None:
        """UI 초기화 - 위아래 2줄 레이아웃"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(4, 2, 4, 2)
        main_layout.setSpacing(0)

        # 색상
        text_color = self._get_color("text_secondary", "#888888")
        text_primary = self._get_color("text", "#FFFFFF")

        label_style = f"""
            color: {text_color}; 
            font-size: 10px;
            background: transparent;
            border: none;
        """
        time_style = f"""
            color: {text_primary}; 
            font-size: 10px;
            font-weight: bold;
            font-family: 'Consolas', 'Monaco', monospace;
            background: transparent;
            border: none;
        """

        # ═══════════════════════════════════════════════════════════════
        # 1줄: 🇺🇸 US 시간 + Latency
        # ═══════════════════════════════════════════════════════════════
        us_row = QHBoxLayout()
        us_row.setContentsMargins(0, 0, 0, 0)
        us_row.setSpacing(4)

        self._us_icon = QLabel("🇺🇸")
        self._us_icon.setStyleSheet(label_style)
        us_row.addWidget(self._us_icon)

        self._us_time_label = QLabel("--/--/-- - --:--:--.---")
        self._us_time_label.setStyleSheet(time_style)
        self._us_time_label.setToolTip("미국 동부 시간 (EST/EDT)")
        us_row.addWidget(self._us_time_label)

        us_row.addStretch(1)

        # Backend Latency (B→FE) - 1줄 (US 시간과 같은 줄)
        self._backend_latency_label = QLabel("B⏱--ms")
        self._backend_latency_label.setStyleSheet(time_style)
        self._backend_latency_label.setToolTip("백엔드 전송 → 프론트엔드 수신 지연")
        us_row.addWidget(self._backend_latency_label)

        main_layout.addLayout(us_row)

        # ═══════════════════════════════════════════════════════════════
        # 2줄: 🇰🇷 KR 시간 + Event Latency
        # ═══════════════════════════════════════════════════════════════
        kr_row = QHBoxLayout()
        kr_row.setContentsMargins(0, 0, 0, 0)
        kr_row.setSpacing(4)

        self._kr_icon = QLabel("🇰🇷")
        self._kr_icon.setStyleSheet(label_style)
        kr_row.addWidget(self._kr_icon)

        self._kr_time_label = QLabel("--/--/-- - --:--:--.---")
        self._kr_time_label.setStyleSheet(time_style)
        self._kr_time_label.setToolTip("한국 표준시 (KST)")
        kr_row.addWidget(self._kr_time_label)

        kr_row.addStretch(1)

        # Event Latency (E→BE) - 2줄 (KR 시간과 같은 줄)
        self._event_latency_label = QLabel("E⏱--ms")
        self._event_latency_label.setStyleSheet(time_style)
        self._event_latency_label.setToolTip(
            "이벤트 발생 → 백엔드 처리 지연 (Massive Event → Server)"
        )
        kr_row.addWidget(self._event_latency_label)

        main_layout.addLayout(kr_row)

    def _get_color(self, key: str, default: str) -> str:
        """테마 색상 가져오기"""
        if self._theme and hasattr(self._theme, "get_color"):
            return self._theme.get_color(key)
        return default

    def _start_timer(self) -> None:
        """100ms 타이머 시작 (밀리초 표시용)"""
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_local_time)
        self._timer.start(100)  # 100ms 간격

    def _update_local_time(self) -> None:
        """로컬 시간 업데이트"""
        self._local_time = datetime.now()
        self._refresh_display()

    def _format_time(self, dt: datetime) -> str:
        """
        시간을 YY/MM/DD - AM/PM HH:MM:SS.ms 형식으로 포맷

        예: 26/01/08 - PM 01:31:42.123
        """
        # AM/PM
        am_pm = "AM" if dt.hour < 12 else "PM"
        hour_12 = dt.hour % 12
        if hour_12 == 0:
            hour_12 = 12

        # 밀리초
        ms = dt.microsecond // 1000

        return f"{dt.strftime('%y/%m/%d')} - {am_pm} {hour_12:02d}:{dt.minute:02d}:{dt.second:02d}.{ms:03d}"

    def _refresh_display(self) -> None:
        """시간 라벨 새로고침"""
        # 한국 시간 (KST = 현재 로컬)
        kr_time_str = self._format_time(self._local_time)
        self._kr_time_label.setText(kr_time_str)

        # 미국 동부 시간 (백엔드 서버 시간 기반 - fallback 없음)
        if self._server_time_utc:
            est_time = self._server_time_utc - timedelta(hours=5)
            us_time_str = self._format_time(est_time)
            self._us_time_label.setText(us_time_str)
        else:
            # 백엔드 시간 미수신 시 대기 표시
            self._us_time_label.setText("--/--/-- - -- --:--:--.---")

        # 레이턴시 표시 (E⏱ / B⏱)
        self._update_latency_label(
            self._event_latency_label, "E", self._event_latency_ms
        )
        self._update_latency_label(self._backend_latency_label, "B", self._latency_ms)

    def _update_latency_label(
        self, label: QLabel, prefix: str, latency_ms: int
    ) -> None:
        """
        레이턴시 라벨 업데이트 (색상 포함)

        Args:
            label: 업데이트할 QLabel
            prefix: 접두사 ("E" 또는 "B")
            latency_ms: 레이턴시 (ms)
        """
        if latency_ms > 0:
            text = f"{prefix}⏱{latency_ms}ms"
            if latency_ms < 100:
                color = self._get_color("success", "#4CAF50")
            elif latency_ms < 500:
                color = self._get_color("warning", "#FF9800")
            else:
                color = self._get_color("danger", "#F44336")
        else:
            text = f"{prefix}⏱--ms"
            color = self._get_color("text_secondary", "#888888")

        label.setText(text)
        label.setStyleSheet(f"""
            color: {color}; 
            font-size: 10px;
            font-weight: bold;
            font-family: 'Consolas', 'Monaco', monospace;
            background: transparent;
            border: none;
            margin-left: 4px;
        """)

    def update_from_heartbeat(self, data: dict) -> None:
        """
        Heartbeat 메시지로 시간 업데이트

        Args:
            data: {
                "server_time_utc": str,  # 서버 현재 시간 (ISO format)
                "sent_at": int,  # 서버 전송 시각 (Unix ms)
                "event_time": int  # (선택) 이벤트 발생 시각 (Unix ms)
            }

        레이턴시 계산:
            B⏱ = 프론트엔드 수신 시각 - 서버 전송 시각 (네트워크 지연)
            E⏱ = 서버 전송 시각 - 이벤트 발생 시각 (이벤트 처리 지연)
        """
        now_ms = int(time.time() * 1000)
        print(f"[DEBUG] TimeDisplayWidget.update_from_heartbeat called: {data}")

        # 서버 시간 파싱
        server_time_str = data.get("server_time_utc")
        if server_time_str:
            try:
                self._server_time_utc = datetime.fromisoformat(
                    server_time_str.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        # B⏱: 서버 전송 → 프론트엔드 수신 레이턴시 (네트워크 지연)
        sent_at = data.get("sent_at")
        if sent_at:
            self._latency_ms = now_ms - int(sent_at)
            self._last_heartbeat_time = now_ms / 1000

        # E⏱: Massive API 데이터 발생 → 백엔드 수신 레이턴시
        # [08-001] event_latency_ms가 직접 전달되면 바로 사용 (가장 정확, 안정적)
        event_latency_ms = data.get("event_latency_ms")
        if event_latency_ms is not None:
            self._event_latency_ms = int(event_latency_ms)
        else:
            # Fallback: event_time 기반 계산
            event_time = data.get("event_time")
            if event_time and sent_at:
                event_time_int = int(event_time)
                if event_time_int != self._last_event_time:
                    self._event_latency_ms = int(sent_at) - event_time_int
                    self._last_event_time = event_time_int

        self._refresh_display()


__all__ = ["TimeDisplayWidget"]
