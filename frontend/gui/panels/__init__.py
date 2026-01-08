# frontend/gui/panels 패키지
# =============================================================================
# 📌 이 패키지의 역할:
#    Sigma9 Dashboard의 패널 위젯들을 개별 모듈로 분리하여 관리합니다.
#    각 패널은 독립적인 QWidget 서브클래스로 구현됩니다.
#
# 📌 구조:
#    panels/
#    ├── __init__.py         # 이 파일 - 패널 모듈 내보내기
#    ├── watchlist_panel.py  # Tier 1 Watchlist + Tier 2 Hot Zone
#    ├── chart_panel.py      # 차트 컨테이너 (TODO)
#    └── log_panel.py        # 로그 콘솔
# =============================================================================

from .watchlist_panel import WatchlistPanel
from .tier2_panel import Tier2Panel, NumericTableWidgetItem
from .log_panel import LogPanel

__all__ = [
    "WatchlistPanel",
    "Tier2Panel",
    "NumericTableWidgetItem",
    "LogPanel",
]
