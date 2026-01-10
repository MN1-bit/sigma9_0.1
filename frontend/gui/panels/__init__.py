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
#    ├── tier2_panel.py      # Tier 2 데이터 모델 및 테이블
#    ├── chart_panel.py      # 차트 영역 패널
#    ├── position_panel.py   # Positions & P&L 패널
#    ├── oracle_panel.py     # Oracle (LLM 분석) 패널
#    ├── log_panel.py        # 로그 콘솔
#    └── resample_panel.py   # 리샘플링 제어 패널 (09-002)
# =============================================================================

from .watchlist_panel import WatchlistPanel
from .tier2_panel import Tier2Panel, Tier2Item, NumericTableWidgetItem
from .log_panel import LogPanel
from .chart_panel import ChartPanel
from .position_panel import PositionPanel
from .oracle_panel import OraclePanel
from .resample_panel import ResamplePanel

__all__ = [
    "WatchlistPanel",
    "Tier2Panel",
    "Tier2Item",
    "NumericTableWidgetItem",
    "LogPanel",
    "ChartPanel",
    "PositionPanel",
    "OraclePanel",
    "ResamplePanel",
]

