# ============================================================================
# Ticker Info Window - 티커 종합 정보 독립 창
# ============================================================================
# [15-001] Ticker Info Viewer 구현
#
# 역할:
#   - 13개 카테고리 티커 정보를 카드 UI로 표시
#   - Dashboard ticker_changed 시그널에 연동하여 자동 업데이트
#   - Dynamic 데이터(Snapshot) 1초 자동 갱신
#   - ThemeManager 연동 (Hot Reload)
#
# 패턴:
#   - Stable Layout: 티커 변경 시 레이아웃 유지, 값만 업데이트
#   - InfoCard: 카테고리별 작은 카드 컴포넌트
# ============================================================================

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from frontend.gui.state.dashboard_state import DashboardState

try:
    from PySide6.QtCore import Qt, QTimer, Slot, Signal, QObject
    from PySide6.QtWidgets import (
        QDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QScrollArea,
        QSizeGrip,
        QSizePolicy,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    from PyQt6.QtCore import Qt, QTimer, pyqtSlot as Slot, pyqtSignal as Signal, QObject  # noqa: F401
    from PyQt6.QtWidgets import (
        QDialog,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QScrollArea,
        QSizeGrip,
        QSizePolicy,
        QVBoxLayout,
        QWidget,
    )

from loguru import logger

from backend.container import get_container
from backend.models.ticker_info import TickerInfo, get_filing_description
from frontend.gui.theme import theme
from frontend.gui.window_effects import WindowsEffects

# 국가 → 플래그 매핑
COUNTRY_FLAGS: dict[str, str] = {
    "South Korea": "🇰🇷",
    "Korea": "🇰🇷",
    "Israel": "🇮🇱",
    "China": "🇨🇳",
    "Japan": "🇯🇵",
    "United Kingdom": "🇬🇧",
    "UK": "🇬🇧",
    "Germany": "🇩🇪",
    "Canada": "🇨🇦",
    "France": "🇫🇷",
    "Brazil": "🇧🇷",
    "India": "🇮🇳",
    "Taiwan": "🇹🇼",
    "Netherlands": "🇳🇱",
    "Switzerland": "🇨🇭",
    "Ireland": "🇮🇪",
    "Australia": "🇦🇺",
    "Singapore": "🇸🇬",
    "Hong Kong": "🇭🇰",
    "Mexico": "🇲🇽",
    "Argentina": "🇦🇷",
    # USA는 기본 (ADR 아닌 이상 표시 안 함)
}

def extract_country_from_description(description: str) -> tuple[str, str] | None:
    """
    Description에서 국가명 추출 후 (플래그, 국가명) 반환.
    
    패턴:
    1. "South Korea's largest..." → South Korea
    2. "headquartered in ..., Israel." → Israel
    3. COUNTRY_FLAGS 키 직접 매칭
    """
    import re
    if not description:
        return None
    
    # 패턴 1: "COUNTRY's ..." (소유격, 문장 시작)
    match = re.match(r"^([A-Z][\w\s]+?)'s\s", description)
    if match:
        country = match.group(1)
        if country in COUNTRY_FLAGS:
            return (COUNTRY_FLAGS[country], country)
    
    # 패턴 2: "in/from CITY, COUNTRY." or "in COUNTRY."
    match = re.search(r'(?:headquartered|based|located|operations?)\s+in\s+[^.]*?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\.\s*$', description, re.IGNORECASE)
    if match:
        possible_country = match.group(1)
        for country, flag in COUNTRY_FLAGS.items():
            if country.lower() == possible_country.lower():
                return (flag, country)
    
    # 패턴 3: known countries 직접 검색 (전체 description에서)
    for country, flag in COUNTRY_FLAGS.items():
        if country in description:
            return (flag, country)
    
    return None


class InfoCard(QFrame):
    """
    카테고리별 정보 카드.

    타이틀과 값을 표시하는 작은 카드 컴포넌트.
    테마 연동으로 색상 자동 적용.
    """

    def __init__(self, title: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._title = title
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self) -> None:
        """UI 구성."""
        self.setFixedHeight(60)  # 100→60 축소
        self.setMinimumWidth(150)  # 180→150 축소

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        # 타이틀
        self._title_label = QLabel(self._title)
        self._title_label.setStyleSheet(f"color: {theme.get_color('text_secondary')}; font-size: 9px;")
        layout.addWidget(self._title_label)

        # 메인 값
        self._value_label = QLabel("--")
        self._value_label.setStyleSheet(f"color: {theme.get_color('text')}; font-size: 13px; font-weight: bold;")
        layout.addWidget(self._value_label)

        # 서브 값
        self._sub_label = QLabel("")
        self._sub_label.setStyleSheet(f"color: {theme.get_color('text_muted')}; font-size: 9px;")
        layout.addWidget(self._sub_label)

        layout.addStretch()

    def _apply_theme(self) -> None:
        """테마 적용."""
        c = theme.colors
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['surface_elevated']};
                border: 1px solid {c['border']};
                border-radius: 8px;
            }}
        """)

    def set_value(self, value: str, sub_value: str = "") -> None:
        """값 업데이트. '--' 또는 빈 값이면 '정보 없음' 표시."""
        if value in ("--", "", None):
            self._value_label.setText("정보 없음")
            self._value_label.setStyleSheet(f"color: {theme.get_color('text_muted')}; font-size: 11px;")
        else:
            self._value_label.setText(value)
            self._value_label.setStyleSheet(f"color: {theme.get_color('text')}; font-size: 13px; font-weight: bold;")
        self._sub_label.setText(sub_value)


class DetailTable(QFrame):
    """
    키-값 쌍 상세 정보 테이블.

    Profile, Float 등의 상세 필드를 2열 테이블로 표시.
    """

    def __init__(self, title: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._title = title
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self) -> None:
        """UI 구성."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # [14-004] 자동 높이 조절: 콘텐츠에 맞게 높이 최소화
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        # 타이틀
        self._title_label = QLabel(self._title)
        self._title_label.setStyleSheet(f"color: {theme.get_color('primary')}; font-size: 11px; font-weight: bold;")
        layout.addWidget(self._title_label)

        # 테이블 레이아웃
        self._grid = QGridLayout()
        self._grid.setSpacing(4)
        self._grid.setColumnStretch(0, 1)
        self._grid.setColumnStretch(1, 2)
        layout.addLayout(self._grid)

    def _apply_theme(self) -> None:
        """테마 적용."""
        c = theme.colors
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['surface']};
                border: 1px solid {c['border']};
                border-radius: 6px;
            }}
        """)

    def set_data(self, data: list[tuple[str, str]]) -> None:
        """
        [14-004] 데이터 설정. data = [(key, value), ...]
        
        각 행의 높이가 콘텐츠에 맞게 자동 조절됨.
        """
        # 기존 아이템 제거
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 새 아이템 추가
        for row, (key, value) in enumerate(data):
            key_label = QLabel(key)
            key_label.setStyleSheet(f"color: {theme.get_color('text_muted')}; font-size: 10px;")
            
            val_label = QLabel(str(value) if value else "--")
            val_label.setStyleSheet(f"color: {theme.get_color('text')}; font-size: 10px;")
            val_label.setWordWrap(True)
            # [14-004] 동적 높이: 콘텐츠에 맞게 행 높이 자동 조절
            val_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            val_label.setMinimumHeight(0)
            
            self._grid.addWidget(key_label, row, 0)
            self._grid.addWidget(val_label, row, 1)
            # 행 stretch 비활성화
            self._grid.setRowStretch(row, 0)


class ListSection(QFrame):
    """
    리스트형 정보 섹션.

    SEC Filings, News 등 리스트 데이터를 테이블 형태로 표시.
    """

    def __init__(self, title: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._title = title
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self) -> None:
        """UI 구성."""
        self.setMinimumHeight(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # 타이틀
        self._title_label = QLabel(self._title)
        self._title_label.setStyleSheet(f"color: {theme.get_color('text_secondary')}; font-size: 11px;")
        layout.addWidget(self._title_label)

        # 콘텐츠 영역
        self._content_layout = QVBoxLayout()
        self._content_layout.setSpacing(8)  # [14-004] 아이템 간 간격 증가
        layout.addLayout(self._content_layout)

        layout.addStretch()

    def _apply_theme(self) -> None:
        """테마 적용."""
        c = theme.colors
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['surface_elevated']};
                border: 1px solid {c['border']};
                border-radius: 8px;
            }}
        """)

    def set_items(self, items: list[str]) -> None:
        """리스트 아이템 설정."""
        # 기존 아이템 제거
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 새 아이템 추가
        for text in items:  # 전체 표시
            label = QLabel(text)
            label.setStyleSheet(f"color: {theme.get_color('text')}; font-size: 11px;")
            label.setWordWrap(True)
            self._content_layout.addWidget(label)

        if not items:
            no_data = QLabel("정보 없음")
            no_data.setStyleSheet(f"color: {theme.get_color('text_muted')}; font-size: 11px;")
            self._content_layout.addWidget(no_data)


class RelatedTickersGrid(QFrame):
    """
    [14-004] Related Tickers 4열 그리드 위젯.

    관련 종목을 4열 그리드로 배치하여 가독성 향상.
    각 티커는 클릭 가능한 라벨로 표시 (향후 클릭 이벤트 연결 가능).
    """

    # 그리드 열 개수
    GRID_COLUMNS = 4

    def __init__(self, title: str = "🔗 Related", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._title = title
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self) -> None:
        """UI 구성."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        # 타이틀
        self._title_label = QLabel(self._title)
        self._title_label.setStyleSheet(
            f"color: {theme.get_color('text_secondary')}; font-size: 11px;"
        )
        layout.addWidget(self._title_label)

        # 4열 그리드
        self._grid = QGridLayout()
        self._grid.setSpacing(4)
        layout.addLayout(self._grid)

    def _apply_theme(self) -> None:
        """테마 적용."""
        c = theme.colors
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {c['surface_elevated']};
                border: 1px solid {c['border']};
                border-radius: 8px;
            }}
        """)

    def set_tickers(self, tickers: list[str]) -> None:
        """
        [14-004] 관련 종목을 4열 그리드로 표시.

        Args:
            tickers: 관련 종목 리스트 (최대 12개 권장)
        """
        # 기존 아이템 제거
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not tickers:
            no_data = QLabel("관련 종목 없음")
            no_data.setStyleSheet(
                f"color: {theme.get_color('text_muted')}; font-size: 10px;"
            )
            self._grid.addWidget(no_data, 0, 0)
            return

        # 4열 그리드로 티커 배치
        for i, ticker in enumerate(tickers[:12]):  # 최대 12개
            row = i // self.GRID_COLUMNS
            col = i % self.GRID_COLUMNS

            label = QLabel(ticker)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet(f"""
                color: {theme.get_color('primary')};
                font-size: 10px;
                padding: 2px 4px;
                background-color: {theme.get_color('surface')};
                border: 1px solid {theme.get_color('border')};
                border-radius: 4px;
            """)
            label.setCursor(Qt.CursorShape.PointingHandCursor)
            self._grid.addWidget(label, row, col)


class TickerInfoWindow(QDialog):
    """
    티커 종합 정보 독립 창.

    13개 카테고리의 티커 정보를 카드 UI로 표시합니다.
    Dashboard의 ticker_changed 시그널에 연결하여 자동 업데이트됩니다.

    Features:
        - Stable Layout: 티커 변경 시 값만 업데이트
        - Dynamic Refresh: Snapshot 1초 자동 갱신
        - Theme Hot Reload: ThemeManager 연동
    """

    # 스레드 안전 UI 업데이트 시그널
    _ticker_info_loaded = Signal(object)  # TickerInfo
    _dynamic_data_loaded = Signal(dict)
    _load_failed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_ticker: str = ""
        self._pending_ticker: str = ""  # [14-001] Pending ticker for lazy load
        self._service = get_container().ticker_info_service()
        self._dynamic_fail_count: int = 0  # 연속 실패 카운트

        self._setup_window()
        self._setup_ui()
        self._setup_timer()
        self._connect_theme()
        self._connect_signals()

        logger.debug("TickerInfoWindow 초기화 완료")

    def _connect_signals(self) -> None:
        """내부 시그널 연결."""
        self._ticker_info_loaded.connect(self._update_ui)
        self._dynamic_data_loaded.connect(self._apply_dynamic_data)
        self._load_failed.connect(lambda msg: self._name_label.setText(msg))

    def _setup_window(self) -> None:
        """창 설정 (Frameless + Acrylic 효과)."""
        self.setWindowTitle("Ticker Info")
        self.setMinimumSize(700, 600)
        self.resize(800, 700)
        
        # Frameless + TranslucentBackground (Settings Dialog와 동일)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # [14-004] 마우스 트래킹 활성화 (리사이즈 커서 변경에 필요)
        self.setMouseTracking(True)
        
        # Acrylic 효과 적용
        self._window_effects = WindowsEffects()
        neutral_tint = "181818CC"  # Dark gray + alpha
        self._window_effects.add_acrylic_effect(self.winId(), neutral_tint)
        
        # 드래그/리사이즈 상태
        self._drag_pos = None
        self._resizing = False

    def _setup_ui(self) -> None:
        """
        [14-002] 3-Column 레이아웃 UI 구성.

        레이아웃:
        +-----------------------------------------------------------------------+
        |  Ticker | Name | $Price (+%) | 시총 $X | [Refresh] [X]                |
        +-----------------------+-------------------------------+---------------+
        | [Col 1: 프로필]       | [Col 2: 탭 (재무/배당/공시)]  | [Col 3: 뉴스] |
        +-----------------------+-------------------------------+---------------+
        """
        # 메인 레이아웃
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # Container
        self._container = QFrame()
        self._container.setObjectName("tickerInfoContainer")
        self._container.setStyleSheet("""
            #tickerInfoContainer {
                background-color: rgba(0, 0, 0, 0.01);
                border-radius: 12px;
            }
        """)
        outer_layout.addWidget(self._container)

        # Container 내부 레이아웃
        main_layout = QVBoxLayout(self._container)
        main_layout.setContentsMargins(16, 12, 16, 12)
        main_layout.setSpacing(12)

        # [14-002] 새 Header
        self._setup_header_v2(main_layout)

        # [14-004] 3-Column 본문 (스크롤 지원)
        self._setup_3column_body(main_layout)

        # [14-004] 리사이즈 그립 (Frameless 창 우하단)
        size_grip = QSizeGrip(self)
        size_grip.setStyleSheet("background: transparent;")
        grip_layout = QHBoxLayout()
        grip_layout.addStretch()
        grip_layout.addWidget(size_grip)
        main_layout.addLayout(grip_layout)

    # =========================================================================
    # [14-002] New Header & 3-Column Layout Methods
    # =========================================================================

    def _setup_header_v2(self, layout: QVBoxLayout) -> None:
        """
        [14-002] 새 헤더: Ticker | Name | Price (+%) | 시총 | Refresh | X
        """
        header = QHBoxLayout()
        header.setSpacing(12)

        # 티커
        self._ticker_label = QLabel("--")
        self._ticker_label.setStyleSheet(f"""
            color: {theme.get_color('primary')};
            font-size: 20px;
            font-weight: bold;
        """)
        header.addWidget(self._ticker_label)

        # 거래소
        self._exchange_label = QLabel("")
        self._exchange_label.setStyleSheet(f"""
            color: {theme.get_color('text_muted')};
            font-size: 11px;
        """)
        header.addWidget(self._exchange_label)

        # [14-004] 회사명 삭제 - 프로필에서 표시됨
        # self._name_label 유지 (에러 메시지 표시용)
        self._name_label = QLabel("")
        self._name_label.hide()  # 숨김

        # 국가 플래그 + 국가명
        self._country_label = QLabel("")
        self._country_label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 14px;
            font-family: 'Segoe UI Emoji', 'Noto Color Emoji', sans-serif;
        """)
        header.addWidget(self._country_label)

        header.addStretch()

        # 가격 + 등락
        self._price_label = QLabel("--")
        self._price_label.setStyleSheet(f"""
            color: {theme.get_color('text')};
            font-size: 16px;
            font-weight: bold;
        """)
        header.addWidget(self._price_label)

        self._change_label = QLabel("")
        self._change_label.setStyleSheet(f"""
            color: {theme.get_color('text_secondary')};
            font-size: 12px;
        """)
        header.addWidget(self._change_label)

        # 시가총액
        self._mcap_label = QLabel("")
        self._mcap_label.setStyleSheet(f"""
            color: {theme.get_color('text_muted')};
            font-size: 11px;
        """)
        header.addWidget(self._mcap_label)

        # Refresh 버튼
        refresh_btn = QPushButton("↻")
        refresh_btn.setFixedSize(28, 28)
        refresh_btn.setStyleSheet(theme.get_button_style("primary"))
        refresh_btn.clicked.connect(self._on_refresh_clicked)
        header.addWidget(refresh_btn)

        # 닫기 버튼
        close_btn = QPushButton("×")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(theme.get_button_style("danger"))
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)

        layout.addLayout(header)

    def _setup_3column_body(self, layout: QVBoxLayout) -> None:
        """
        [14-004] 3-Column 본문 레이아웃 + QScrollArea 래핑.

        Col1: 프로필/메타 (200px)
        Col2: 탭 (재무/배당/공시/유동성) (stretch)
        Col3: 뉴스/관련종목 (220px)

        QScrollArea로 감싸서 콘텐츠가 창을 초과해도 스크롤 가능.
        """
        # [14-004] 스크롤 영역
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                width: 8px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                min-height: 20px;
            }
        """)

        # 3-Column body widget
        body_widget = QWidget()
        body_widget.setStyleSheet("background: transparent;")
        body = QHBoxLayout(body_widget)
        body.setSpacing(12)
        body.setContentsMargins(0, 0, 0, 0)

        # Column 1: 프로필
        col1 = self._create_column1_profile()
        col1.setFixedWidth(200)
        body.addWidget(col1)

        # Column 2: 탭
        col2 = self._create_column2_tabs()
        body.addWidget(col2, stretch=1)

        # Column 3: 뉴스
        col3 = self._create_column3_news()
        col3.setFixedWidth(220)
        body.addWidget(col3)

        scroll_area.setWidget(body_widget)
        layout.addWidget(scroll_area, stretch=1)

    def _create_column1_profile(self) -> QFrame:
        """[14-002] Column 1: 프로필/메타 정보. 순서: 프로필↑, 설명↓."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.get_color('surface')};
                border: 1px solid {theme.get_color('border')};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Profile Table (위)
        self._profile_table = DetailTable("Profile")
        layout.addWidget(self._profile_table)

        # 구분선
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {theme.get_color('border')};")
        layout.addWidget(sep)

        # 회사 설명 (아래)
        self._desc_label = QLabel("회사 설명")
        self._desc_label.setWordWrap(True)
        self._desc_label.setStyleSheet(f"color: {theme.get_color('text')}; font-size: 11px;")
        layout.addWidget(self._desc_label)

        # [14-004] addStretch 제거하여 콘텐츠 높이에 맞게 조절
        return frame

    def _create_column2_tabs(self) -> QFrame:
        """[14-002] Column 2: 재무/배당/공시/유동성 (탭 없이 한번에 표시)."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.get_color('surface')};
                border: 1px solid {theme.get_color('border')};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 재무
        self._financials_table = DetailTable("Financials")
        layout.addWidget(self._financials_table)

        # 배당
        self._dividends_table = DetailTable("Dividends")
        layout.addWidget(self._dividends_table)

        # [14-004] 주식 분할
        self._splits_table = DetailTable("Stock Splits")
        layout.addWidget(self._splits_table)

        # 유동성
        self._float_table = DetailTable("Float & Short")
        layout.addWidget(self._float_table)

        # 공시
        self._filings_section = ListSection("SEC Filings")
        layout.addWidget(self._filings_section)

        layout.addStretch()
        return frame

    def _create_column3_news(self) -> QFrame:
        """
        [14-004] Column 3: 뉴스/관련종목.

        순서 변경: News 먼저, Related 아래로.
        Related는 4열 Grid로 표시.
        """
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme.get_color('surface')};
                border: 1px solid {theme.get_color('border')};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # [14-004] 뉴스 먼저 (위)
        self._news_section = ListSection("News")
        layout.addWidget(self._news_section)

        # [14-004] 관련 종목 아래 (4열 그리드)
        self._related_grid = RelatedTickersGrid("Related")
        layout.addWidget(self._related_grid)

        layout.addStretch()
        return frame

    def _setup_timer(self) -> None:
        """Dynamic 데이터 갱신 타이머."""
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_dynamic_data)

    def _connect_theme(self) -> None:
        """테마 변경 연결 및 초기 적용."""
        theme.theme_changed.connect(self._apply_theme)
        self._apply_theme()  # 초기 테마 적용

    def _apply_theme(self) -> None:
        """테마 적용 (opacity만, 배경은 Acrylic으로 처리)."""
        logger.debug(f"[INFO_WINDOW] _apply_theme called: opacity={theme.opacity}")
        self.setWindowOpacity(theme.opacity)

    # =========================================================================
    # Public Methods
    # =========================================================================

    def load_ticker(self, ticker: str) -> None:
        """
        티커 정보 로드.

        Args:
            ticker: 종목 심볼
        """
        if not ticker:
            return

        self._current_ticker = ticker.upper()
        self._ticker_label.setText(self._current_ticker)
        self._name_label.setText("Loading...")

        # 스레드에서 로드
        self._run_in_thread(self._load_ticker_sync)

    @Slot(str)
    def on_ticker_changed(self, ticker: str) -> None:
        """
        Dashboard ticker_changed 시그널 슬롯 (레거시 호환).

        Args:
            ticker: 변경된 티커
        """
        if self.isVisible():
            self.load_ticker(ticker)

    # =========================================================================
    # 📌 [09-009] Event Bus 연결
    # =========================================================================
    def connect_to_state(self, state: "DashboardState") -> None:
        """
        DashboardState의 ticker_changed 시그널 구독

        창이 열려있을 때만 티커 정보 자동 업데이트

        Args:
            state: DashboardState 인스턴스
        """
        state.ticker_changed.connect(self._on_ticker_changed)

    def _on_ticker_changed(self, ticker: str, source: str) -> None:
        """
        [09-009] 티커 변경 시 자동 업데이트

        [14-001] Pending Ticker 패턴:
        - 창이 visible: 즉시 로드
        - 창이 hidden: _pending_ticker에 저장 → showEvent에서 로드
        """
        self._pending_ticker = ticker
        if self.isVisible():
            self.load_ticker(ticker)

    def showEvent(self, event) -> None:
        """창 표시 시 타이머 시작 및 pending 티커 로드."""
        super().showEvent(event)
        
        # [14-002] Opacity 버그 수정: re-open 시 theme.opacity로 재설정
        logger.debug(f"[showEvent] Setting opacity to theme.opacity={theme.opacity}")
        self.setWindowOpacity(theme.opacity)
        
        # [14-001] Pending ticker 로드 (창 닫혀있을 때 변경된 티커)
        if self._pending_ticker:
            self.load_ticker(self._pending_ticker)
            self._pending_ticker = ""  # 로드 후 초기화
        self._refresh_timer.start(1000)  # 1초
        logger.debug("TickerInfoWindow 표시됨, Dynamic 갱신 시작")

    def closeEvent(self, event) -> None:
        """창 닫힘 시 타이머 정지."""
        self._refresh_timer.stop()
        logger.debug("TickerInfoWindow 닫힘, Dynamic 갱신 중지")
        super().closeEvent(event)

    # =========================================================================
    # Private Methods - Threading
    # =========================================================================

    def _run_in_thread(self, func) -> None:
        """백그라운드 스레드에서 함수 실행."""
        import threading
        thread = threading.Thread(target=func, daemon=True)
        thread.start()

    def _load_ticker_sync(self) -> None:
        """동기적 티커 정보 로드 (스레드에서 실행)."""
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                info = loop.run_until_complete(
                    self._service.get_ticker_info(self._current_ticker)
                )
                # 시그널 emit -> 메인 스레드에서 슬롯 실행
                self._ticker_info_loaded.emit(info)
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"티커 정보 로드 실패: {e}")
            self._load_failed.emit("Load failed")

    def _update_ui(self, info: TickerInfo) -> None:
        """[14-002] UI 업데이트 - 새 3-Column 레이아웃에 맞게 데이터 바인딩."""
        logger.debug(f"_update_ui 호출됨: {info.ticker}, profile={info.profile}")

        profile = info.profile
        snap = info.snapshot

        # =====================================================================
        # [14-002] Header 업데이트
        # =====================================================================
        # 회사명
        name = profile.get("name", "")
        self._name_label.setText(name if name else "")

        # 거래소
        exchange = profile.get("primary_exchange", "")
        self._exchange_label.setText(f"({exchange})" if exchange else "")

        # 국가 플래그 + 국가명 (외국 기업만 표시)
        desc = profile.get("description", "")
        country_info = extract_country_from_description(desc)
        if country_info:
            flag, country_name = country_info
            self._country_label.setText(f"{flag} {country_name}")
        else:
            self._country_label.setText("")

        # 가격 + 등락
        price = snap.get("price")
        change = snap.get("change_pct")
        if price:
            self._price_label.setText(f"${price:,.2f}")
            if change:
                color = theme.get_color('success') if change >= 0 else theme.get_color('danger')
                self._change_label.setText(f"({change:+.2f}%)")
                self._change_label.setStyleSheet(f"color: {color}; font-size: 12px;")
            else:
                self._change_label.setText("")
        else:
            self._price_label.setText("--")
            self._change_label.setText("")

        # 시가총액
        market_cap = profile.get("market_cap")
        if market_cap:
            mc_str = f"${market_cap/1e12:.2f}T" if market_cap >= 1e12 else \
                     f"${market_cap/1e9:.1f}B" if market_cap >= 1e9 else \
                     f"${market_cap/1e6:.0f}M"
            self._mcap_label.setText(f"시총 {mc_str}")
        else:
            self._mcap_label.setText("")

        # =====================================================================
        # [14-002] Column 1: 프로필
        # =====================================================================
        # 회사 설명 (3줄 요약)
        desc = profile.get("description", "")
        self._desc_label.setText(desc if desc else "회사 정보 없음")

        # Profile 상세 테이블
        def fmt_num(v):
            if v is None:
                return "--"
            if v >= 1e12:
                return f"${v/1e12:.2f}T"
            if v >= 1e9:
                return f"${v/1e9:.2f}B"
            if v >= 1e6:
                return f"${v/1e6:.2f}M"
            return f"{v:,.0f}"

        # 발행주: share_class_shares_outstanding 없으면 weighted_shares_outstanding 사용
        shares = profile.get("share_class_shares_outstanding") or profile.get("weighted_shares_outstanding")
        
        # 본사 위치: API address 필드 우선, 없으면 description에서 파싱
        address = profile.get("address", {})
        if address and isinstance(address, dict):
            # address 객체에서 city, state 추출
            city = address.get("city", "")
            state = address.get("state", "")
            if city and state:
                hq_location = f"{city}, {state}"
            elif city:
                hq_location = city
            else:
                hq_location = "--"
        else:
            # fallback: description에서 파싱
            desc_text = profile.get("description", "") or ""
            hq_location = "--"
            import re
            patterns = [
                r'(?:headquartered|based|located)\s+in\s+([^.]+?)(?:\.|$)',
                r'headquarters?\s+in\s+([^.]+?)(?:\.|$)',
            ]
            for pattern in patterns:
                match = re.search(pattern, desc_text, re.IGNORECASE)
                if match:
                    hq_location = match.group(1).strip()
                    break
        
        profile_data = [
            ("이름", profile.get("name", "--")),
            ("본사", hq_location),
            ("거래소", profile.get("primary_exchange", "--")),
            ("시가총액", fmt_num(profile.get("market_cap"))),
            ("발행주", fmt_num(shares)),
            ("직원수", f"{profile.get('total_employees', 0):,}" if profile.get("total_employees") else "--"),
            ("업종 (SIC)", f"{profile.get('sic_code', '--')} - {profile.get('sic_description', '')}"),
            ("상장일", profile.get("list_date", "--")),
            ("CIK", profile.get("cik", "--")),
            ("홈페이지", profile.get("homepage_url", "--")),
        ]
        self._profile_table.set_data(profile_data)

        # Float 상세 테이블
        float_data = info.float_data
        float_table_data = [
            ("Free Float", fmt_num(float_data.get("free_float"))),
            ("Float 비율", f"{float_data.get('free_float_percent', 0):.2f}%" if float_data.get("free_float_percent") else "--"),
            ("기준일", float_data.get("as_of_date", "--")),
        ]
        self._float_table.set_data(float_table_data)

        # Financials 상세 테이블
        fin_table_data = []
        for fin in info.financials:
            period = fin.get("fiscal_period", "")
            year = fin.get("fiscal_year", "")
            income = fin.get("financials", {}).get("income_statement", {})
            rev = income.get("revenues", {}).get("value")
            net = income.get("net_income_loss", {}).get("value")
            fin_table_data.append((f"{period} {year}", f"매출: {fmt_num(rev)}, 순이익: {fmt_num(net)}"))
        self._financials_table.set_data(fin_table_data if fin_table_data else [("데이터 없음", "--")])

        # [14-002] Dividends → _dividends_table
        div_data = []
        for div in info.dividends:
            amount = div.get("cash_amount", 0)
            date = div.get("ex_dividend_date", "")
            div_data.append((date, f"${amount:.4f}"))
        if div_data:
            self._dividends_table.set_data(div_data)
        else:
            self._dividends_table.set_data([("No dividends", "--")])

        # [14-004] Splits → _splits_table
        splits_data = []
        for s in getattr(info, 'splits', []):
            exec_date = s.get("execution_date", "")
            split_from = s.get("split_from", "")
            split_to = s.get("split_to", "")
            if exec_date and split_from and split_to:
                splits_data.append((exec_date, f"{split_from}:{split_to}"))
        if splits_data:
            self._splits_table.set_data(splits_data)
        else:
            self._splits_table.set_data([("No splits", "--")])

        # [14-002] Float & Short → _float_table (유동성 탭)
        float_short_data = [
            ("Free Float", fmt_num(info.float_data.get("free_float"))),
            ("Float %", f"{info.float_data.get('free_float_percent', 0):.2f}%" if info.float_data.get("free_float_percent") else "--"),
        ]
        if info.short_interest:
            si = info.short_interest[0]
            float_short_data.append(("Short Interest", f"{si.get('short_percent_of_float', 0):.2f}%"))
        if info.short_volume:
            sv = info.short_volume[0]
            vol = sv.get("short_volume", 0)
            total = sv.get("total_volume", 1)
            pct = (vol / total * 100) if total else 0
            float_short_data.append(("Short Volume", f"{pct:.1f}%"))
        self._float_table.set_data(float_short_data)

        # SEC Filings
        filings_items = []
        for f in info.filings:
            f_type = f.get("type", "")
            desc = get_filing_description(f_type)
            date = f.get("filing_date", "")
            filings_items.append(f"{date}  {f_type}  {desc}")
        self._filings_section.set_items(filings_items)

        # [14-004] News (날짜 줄바꿈 + 내용)
        news_items = []
        for n in info.news:
            title = n.get("title", "")
            source = n.get("source", "")
            # 날짜/시간 파싱 (published 필드)
            pub_time = n.get("published", "")
            if pub_time:
                try:
                    time_str = pub_time[:16].replace("T", " ")
                except Exception:
                    time_str = pub_time[:10] if len(pub_time) >= 10 else ""
                # 날짜 + 줄바꿈 + 내용
                news_items.append(f"[{time_str}]\n{title} ({source})")
            else:
                news_items.append(f"{title} ({source})")
        self._news_section.set_items(news_items)

        # [14-004] Related Companies (4열 그리드)
        related = [r.get("ticker", "") for r in info.related_companies]
        self._related_grid.set_tickers(related)

    def _on_refresh_clicked(self) -> None:
        """새로고침 버튼 클릭."""
        if self._current_ticker:
            self._run_in_thread(self._force_refresh_sync)

    def _force_refresh_sync(self) -> None:
        """강제 갱신 (스레드에서 실행)."""
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                info = loop.run_until_complete(
                    self._service.get_ticker_info(self._current_ticker, force_refresh=True)
                )
                self._ticker_info_loaded.emit(info)
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"강제 갱신 실패: {e}")

    def _refresh_dynamic_data(self) -> None:
        """Dynamic 데이터 갱신 (1초마다)."""
        if self._current_ticker:
            self._run_in_thread(self._update_dynamic_sync)

    def _update_dynamic_sync(self) -> None:
        """Dynamic 데이터만 업데이트 (스레드에서 실행)."""
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                data = loop.run_until_complete(
                    self._service.get_dynamic_data(self._current_ticker)
                )
                self._dynamic_data_loaded.emit(data)
            finally:
                loop.close()
        except Exception as e:
            logger.debug(f"Dynamic 갱신 실패: {e}")

    def _apply_dynamic_data(self, data: dict) -> None:
        """
        [14-004] Dynamic 데이터 UI 적용 (메인 스레드에서 실행).
        
        Header의 가격/등락 라벨을 업데이트합니다.
        """
        snap = data.get("snapshot", {})
        
        if not snap:
            self._dynamic_fail_count += 1
            if self._dynamic_fail_count >= 3:
                logger.debug("Dynamic 데이터 3회 연속 없음 - 자동 갱신 중지")
                self._refresh_timer.stop()
            return
        else:
            self._dynamic_fail_count = 0
        
        # Header 가격/등락 업데이트
        price = snap.get("price")
        change = snap.get("change_pct")
        if price:
            self._price_label.setText(f"${price:,.2f}")
            if change:
                color = theme.get_color('success') if change >= 0 else theme.get_color('danger')
                self._change_label.setText(f"({change:+.2f}%)")
                self._change_label.setStyleSheet(f"color: {color}; font-size: 12px;")

    # =========================================================================
    # Mouse Events (Frameless Window Drag + Resize)
    # =========================================================================

    # [14-004] 리사이즈 영역 크기 (우하단 코너)
    RESIZE_MARGIN = 16

    def mousePressEvent(self, event):
        """마우스 드래그/리사이즈 시작."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            # [14-004] 우하단 코너인지 확인 (리사이즈 영역)
            if (self.width() - pos.x() < self.RESIZE_MARGIN and 
                self.height() - pos.y() < self.RESIZE_MARGIN):
                self._resizing = True
                self._resize_start = event.globalPosition().toPoint()
                self._resize_start_size = self.size()
            else:
                self._resizing = False
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """마우스 드래그/리사이즈 중."""
        if event.buttons() == Qt.MouseButton.LeftButton:
            if getattr(self, '_resizing', False):
                # [14-004] 리사이즈 모드
                delta = event.globalPosition().toPoint() - self._resize_start
                new_width = max(self.minimumWidth(), self._resize_start_size.width() + delta.x())
                new_height = max(self.minimumHeight(), self._resize_start_size.height() + delta.y())
                self.resize(new_width, new_height)
            elif self._drag_pos:
                # 드래그 모드
                self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            # [14-004] 커서 변경: 우하단 코너에서만 리사이즈 커서
            pos = event.position().toPoint()
            if (self.width() - pos.x() < self.RESIZE_MARGIN and 
                self.height() - pos.y() < self.RESIZE_MARGIN):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            else:
                self.unsetCursor()

    def mouseReleaseEvent(self, event):
        """마우스 드래그/리사이즈 종료."""
        self._drag_pos = None
        self._resizing = False
        self.unsetCursor()
