# ============================================================================
# Resample Panel - 리샘플링 제어 패널
# ============================================================================
# 📌 이 파일의 역할:
#   - 전체 티커 일괄 리샘플링 제어 UI
#   - Start/Pause/Stop/Resume 버튼
#   - Progress Bar + 현재/전체 티커 수 표시
#   - 최대 이력 설정 (숫자 + 단위)
#
# 📍 위치: frontend.gui.panels.resample_panel
# 📅 생성일: 2026-01-10 (09-002)
# ============================================================================

from datetime import timedelta
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..theme import theme


# ═══════════════════════════════════════════════════════════════════════════
# Worker Thread - 백그라운드 리샘플링
# ═══════════════════════════════════════════════════════════════════════════


class ResampleWorker(QThread):
    """
    백그라운드 리샘플링 워커

    ELI5: GUI가 멈추지 않도록 별도 스레드에서 리샘플링을 수행합니다.
    """

    # 시그널 정의
    progress = pyqtSignal(str, int, int)  # (ticker, current, total)
    finished = pyqtSignal(int)  # success_count
    error = pyqtSignal(str)  # error_message

    def __init__(
        self,
        parquet_manager: "ParquetManager",  # noqa: F821
        target_tf: str,
        max_history: timedelta,
    ):
        super().__init__()
        self._pm = parquet_manager
        self._target_tf = target_tf
        self._max_history = max_history
        self._paused = False
        self._stopped = False

    def run(self) -> None:
        """리샘플링 실행"""
        try:
            success = self._pm.resample_all_tickers(
                self._target_tf,
                callback=self._progress_callback,
                max_history=self._max_history,
            )
            self.finished.emit(success)
        except Exception as e:
            self.error.emit(str(e))

    def _progress_callback(self, ticker: str, current: int, total: int) -> None:
        """진행 상황 콜백 (Pause/Stop 체크 포함)"""
        # Stop 요청 시 예외 발생으로 중단
        if self._stopped:
            raise InterruptedError("Resample stopped by user")

        # Pause 상태면 대기
        while self._paused and not self._stopped:
            self.msleep(100)

        self.progress.emit(ticker, current, total)

    def pause(self) -> None:
        """일시 정지"""
        self._paused = True

    def resume(self) -> None:
        """재개"""
        self._paused = False

    def stop(self) -> None:
        """완전 중단"""
        self._stopped = True
        self._paused = False  # pause 상태에서 stop 시 해제


# ═══════════════════════════════════════════════════════════════════════════
# ResamplePanel - 리샘플링 제어 패널
# ═══════════════════════════════════════════════════════════════════════════


class ResamplePanel(QWidget):
    """
    리샘플링 제어 패널 (수동 일괄 리샘플)

    Features:
        - Start/Pause/Stop/Resume 버튼
        - Progress Bar (현재/전체 + %)
        - 타임프레임 선택
        - 최대 이력 설정 (숫자 + 단위)
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._worker: Optional[ResampleWorker] = None
        self._pm: Optional["ParquetManager"] = None  # noqa: F821
        self._setup_ui()

    def set_parquet_manager(self, pm: "ParquetManager") -> None:  # noqa: F821
        """ParquetManager 인스턴스 설정 (DI)"""
        self._pm = pm

    def _setup_ui(self) -> None:
        """UI 구성"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 그룹박스
        group = QGroupBox("📊 Resample Settings")
        group.setStyleSheet(theme.get_stylesheet("panel"))
        group_layout = QVBoxLayout(group)

        # ─────────────────────────────────────────────────────
        # Row 1: 진행 컨트롤 버튼
        # ─────────────────────────────────────────────────────
        btn_row = QHBoxLayout()

        self.btn_start = QPushButton("▶ Start")
        self.btn_start.setStyleSheet(theme.get_button_style("success"))
        self.btn_start.clicked.connect(self._on_start)

        self.btn_pause = QPushButton("⏸ Pause")
        self.btn_pause.setStyleSheet(theme.get_button_style("primary"))
        self.btn_pause.clicked.connect(self._on_pause)
        self.btn_pause.setEnabled(False)

        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.setStyleSheet(theme.get_button_style("danger"))
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_stop.setEnabled(False)

        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_pause)
        btn_row.addWidget(self.btn_stop)
        group_layout.addLayout(btn_row)

        # ─────────────────────────────────────────────────────
        # Row 2: Progress Bar
        # ─────────────────────────────────────────────────────
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {theme.get_color('border')};
                border-radius: 4px;
                background: {theme.get_color('surface')};
                height: 20px;
            }}
            QProgressBar::chunk {{
                background: {theme.get_color('primary')};
                border-radius: 3px;
            }}
        """)
        group_layout.addWidget(self.progress_bar)

        # ─────────────────────────────────────────────────────
        # Row 3: 진행 상태 라벨
        # ─────────────────────────────────────────────────────
        self.label_status = QLabel("Ready")
        self.label_status.setStyleSheet(f"color: {theme.get_color('text_secondary')};")
        self.label_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        group_layout.addWidget(self.label_status)

        # ─────────────────────────────────────────────────────
        # Row 4: 최대 이력 설정
        # ─────────────────────────────────────────────────────
        history_row = QHBoxLayout()

        history_label = QLabel("Max History:")
        history_label.setStyleSheet(f"color: {theme.get_color('text')};")

        self.combo_amount = QComboBox()
        self.combo_amount.setEditable(True)
        self.combo_amount.addItems(["1", "2", "3", "7", "14", "30"])
        self.combo_amount.setCurrentText("2")
        self.combo_amount.setStyleSheet(theme.get_stylesheet("combobox"))

        self.combo_unit = QComboBox()
        self.combo_unit.addItems(["Hours", "Days", "Weeks"])
        self.combo_unit.setCurrentText("Weeks")
        self.combo_unit.setStyleSheet(theme.get_stylesheet("combobox"))

        history_row.addWidget(history_label)
        history_row.addWidget(self.combo_amount)
        history_row.addWidget(self.combo_unit)
        history_row.addStretch()
        group_layout.addLayout(history_row)

        # ─────────────────────────────────────────────────────
        # Row 5: 타임프레임 체크박스 (여러 TF 선택 가능)
        # ─────────────────────────────────────────────────────
        tf_label = QLabel("Target Timeframes:")
        tf_label.setStyleSheet(f"color: {theme.get_color('text')};")
        group_layout.addWidget(tf_label)

        tf_row = QHBoxLayout()
        self._tf_checkboxes: dict[str, QCheckBox] = {}
        for tf in ["3m", "5m", "15m", "4h", "1W"]:
            chk = QCheckBox(tf)
            chk.setChecked(tf in ["3m", "5m", "15m"])  # 기본값
            chk.setStyleSheet(f"color: {theme.get_color('text')};")
            self._tf_checkboxes[tf] = chk
            tf_row.addWidget(chk)
        tf_row.addStretch()
        group_layout.addLayout(tf_row)

        layout.addWidget(group)

    def _get_max_history(self) -> timedelta:
        """최대 이력 timedelta 반환"""
        try:
            amount = int(self.combo_amount.currentText())
        except ValueError:
            amount = 2

        unit = self.combo_unit.currentText()
        if unit == "Hours":
            return timedelta(hours=amount)
        elif unit == "Days":
            return timedelta(days=amount)
        else:  # Weeks
            return timedelta(weeks=amount)

    def _on_start(self) -> None:
        """Start 버튼 클릭"""
        if self._pm is None:
            self.label_status.setText("❌ ParquetManager not set")
            return

        if self._worker and self._worker.isRunning():
            # Resume
            self._worker.resume()
            self.btn_pause.setText("⏸ Pause")
            return

        # 선택된 타임프레임 확인
        selected_tfs = self._get_selected_timeframes()
        if not selected_tfs:
            self.label_status.setText("❌ No timeframe selected")
            return

        # 새 작업 시작 (첫 번째 TF부터)
        max_history = self._get_max_history()

        # 여러 TF 순차 처리를 위해 대기열 저장
        self._pending_tfs = selected_tfs.copy()
        self._start_next_tf(max_history)

    def _get_selected_timeframes(self) -> list[str]:
        """체크된 타임프레임 목록 반환"""
        return [tf for tf, chk in self._tf_checkboxes.items() if chk.isChecked()]

    def _start_next_tf(self, max_history: timedelta) -> None:
        """다음 TF 리샘플링 시작"""
        if not self._pending_tfs:
            self._reset_ui()
            self.label_status.setText("✅ All completed!")
            return

        target_tf = self._pending_tfs.pop(0)
        remaining = len(self._pending_tfs)
        self.label_status.setText(f"Starting {target_tf}... ({remaining} more)")

        self._current_max_history = max_history
        self._worker = ResampleWorker(self._pm, target_tf, max_history)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_tf_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

        # 버튼 상태 업데이트
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)

    def _on_pause(self) -> None:
        """Pause/Resume 토글"""
        if self._worker and self._worker.isRunning():
            if self.btn_pause.text().startswith("⏸"):
                self._worker.pause()
                self.btn_pause.setText("▶ Resume")
                self.label_status.setText("Paused")
            else:
                self._worker.resume()
                self.btn_pause.setText("⏸ Pause")

    def _on_stop(self) -> None:
        """Stop 버튼 클릭"""
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(3000)  # 최대 3초 대기

        self._reset_ui()
        self.label_status.setText("Stopped")

    def _on_progress(self, ticker: str, current: int, total: int) -> None:
        """진행 상황 업데이트"""
        pct = int(current / total * 100) if total > 0 else 0
        self.progress_bar.setValue(pct)
        self.label_status.setText(f"{ticker} ({current}/{total})")

    def _on_tf_finished(self, success_count: int) -> None:
        """단일 TF 완료 - 다음 TF 자동 시작"""
        self.progress_bar.setValue(100)
        # 다음 TF로 진행
        if hasattr(self, "_current_max_history"):
            self._start_next_tf(self._current_max_history)

    def _on_finished(self, success_count: int) -> None:
        """완료 처리"""
        self._reset_ui()
        self.progress_bar.setValue(100)
        self.label_status.setText(f"✅ Completed: {success_count} tickers")

    def _on_error(self, error_msg: str) -> None:
        """에러 처리"""
        self._pending_tfs = []  # 에러 시 대기열 비우기
        self._reset_ui()
        self.label_status.setText(f"❌ Error: {error_msg}")

    def _reset_ui(self) -> None:
        """UI 상태 리셋"""
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("⏸ Pause")
        self.btn_stop.setEnabled(False)
        self._worker = None
        self._pending_tfs = []

