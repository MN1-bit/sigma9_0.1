# ============================================================================
# Sigma9 Watchlist Model - Model/View 아키텍처 기반 Watchlist 데이터 모델
# ============================================================================
# 📌 이 파일의 역할:
#   - QStandardItemModel 기반의 Watchlist 데이터 관리
#   - QTableView와 분리된 데이터 레이어로 정렬 안정성 보장
#   - ticker→row 매핑으로 빠른 조회 지원
#
# 📌 해결하는 문제:
#   - QTableWidget에서 setSortingEnabled(True) 상태로 setItem() 호출 시
#     정렬에 의해 행 인덱스가 변경되어 데이터가 잘못된 행에 삽입되는 문제
#
# 📌 관련 문서:
#   - docs/Plan/bugfix/01-004_watchlist_model_view_architecture.md
# ============================================================================

"""
Watchlist Model

QStandardItemModel 기반의 Watchlist 데이터 모델입니다.
QTableView와 함께 사용하여 Model/View 아키텍처를 구현합니다.
"""

from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor
from PyQt6.QtCore import Qt


class WatchlistModel(QStandardItemModel):
    """
    Watchlist 데이터 모델
    
    QTableWidget의 데이터+뷰 결합 방식 대신,
    Model/View 분리를 통해 정렬 시 인덱스 안정성을 보장합니다.
    
    Features:
        - ticker→row 매핑으로 O(1) 조회
        - update_item()으로 개별 항목 upsert
        - UserRole에 숫자값 저장으로 올바른 정렬 지원
        - Transparency Protocol: 데이터 누락 시 ⚠️ 표시
    """
    
    # 컬럼 정의 (인덱스)
    COL_TICKER = 0
    COL_CHANGE = 1
    COL_DOLVOL = 2
    COL_SCORE = 3
    COL_IGNITION = 4
    
    # 컬럼 헤더
    HEADERS = ["Ticker", "Chg%", "DolVol", "Score", "Ign"]
    
    def __init__(self, parent=None):
        """모델 초기화"""
        super().__init__(parent)
        self.setHorizontalHeaderLabels(self.HEADERS)
        
        # ticker → row 매핑 (빠른 조회용)
        self._ticker_to_row: dict[str, int] = {}
        
        # [02-001 FIX] 설정은 lazy loading으로 변경 (GUI 초기화 블로킹 방지)
        self._settings = None
        self._use_v2 = None  # 첫 호출 시 로드
        
        # 색상 설정 (테마에서 가져오기)
        try:
            from .theme import theme
            self._color_success = QColor(theme.get_color('success'))
            self._color_danger = QColor(theme.get_color('danger'))
            self._color_warning = QColor(255, 165, 0)  # 주황색
        except ImportError:
            # 테마 없을 경우 기본값
            self._color_success = QColor('#22c55e')
            self._color_danger = QColor('#ef4444')
            self._color_warning = QColor(255, 165, 0)
    
    def update_item(self, item_data: dict) -> int:
        """
        단일 항목 업데이트 (있으면 수정, 없으면 추가)
        
        Args:
            item_data: dict with keys:
                - ticker: str (필수)
                - change_pct: float
                - dollar_volume: float
                - score: float
                - ignition: float
        
        Returns:
            int: 업데이트된 행 번호
        """
        ticker = item_data.get("ticker")
        if not ticker:
            return -1
        
        if ticker in self._ticker_to_row:
            # 기존 항목 업데이트
            row = self._ticker_to_row[ticker]
            self._set_row_data(row, item_data)
        else:
            # 새 항목 추가
            row = self.rowCount()
            self.insertRow(row)
            self._ticker_to_row[ticker] = row
            self._set_row_data(row, item_data)
        
        return row
    
    def update_all(self, items: list):
        """
        전체 목록 업데이트
        
        Args:
            items: List[dict] - 각 dict는 update_item과 동일한 형식
        """
        for item in items:
            self.update_item(item)
    
    def clear_all(self):
        """모든 데이터 삭제"""
        self.setRowCount(0)
        self._ticker_to_row.clear()
    
    def remove_ticker(self, ticker: str) -> bool:
        """
        특정 종목 제거
        
        Args:
            ticker: 제거할 종목 심볼
            
        Returns:
            bool: 제거 성공 여부
        """
        if ticker not in self._ticker_to_row:
            return False
        
        row = self._ticker_to_row[ticker]
        self.removeRow(row)
        
        # 매핑 재구성 (제거된 행 이후의 모든 행 인덱스 감소)
        del self._ticker_to_row[ticker]
        for t, r in list(self._ticker_to_row.items()):
            if r > row:
                self._ticker_to_row[t] = r - 1
        
        return True
    
    def get_ticker_at_row(self, row: int) -> str:
        """특정 행의 ticker 반환"""
        item = self.item(row, self.COL_TICKER)
        return item.text() if item else ""
    
    def _set_row_data(self, row: int, data: dict):
        """
        행 데이터 설정
        
        UserRole에 숫자값을 저장하여 정렬 시 올바른 비교가 이루어지도록 합니다.
        Transparency Protocol: 데이터 누락 시 ⚠️ 경고 아이콘 표시
        """
        # Ticker (텍스트)
        ticker_item = QStandardItem(data.get("ticker", ""))
        self.setItem(row, self.COL_TICKER, ticker_item)
        
        # Change % (숫자, 색상 적용)
        change = data.get("change_pct", 0) or 0
        sign = "+" if change >= 0 else ""
        change_item = QStandardItem(f"{sign}{change:.1f}%")
        change_item.setData(change, Qt.ItemDataRole.UserRole)  # 정렬용 숫자값
        if change >= 0:
            change_item.setForeground(self._color_success)
        else:
            change_item.setForeground(self._color_danger)
        self.setItem(row, self.COL_CHANGE, change_item)
        
        # Dollar Volume (Transparency Protocol)
        dolvol = data.get("dollar_volume", 0) or 0
        if dolvol > 0:
            dolvol_item = QStandardItem(self._format_dolvol(dolvol))
            dolvol_item.setData(dolvol, Qt.ItemDataRole.UserRole)
        else:
            dolvol_item = QStandardItem("⚠️")
            dolvol_item.setToolTip("Dollar Volume 데이터 없음")
            dolvol_item.setForeground(self._color_warning)
            dolvol_item.setData(0, Qt.ItemDataRole.UserRole)
        self.setItem(row, self.COL_DOLVOL, dolvol_item)
        
        # Score (설정에 따라 v1 또는 v2 사용)
        # [02-001 FIX] Lazy loading - 첫 호출 시에만 설정 로드
        if self._use_v2 is None:
            from ..config.loader import load_settings
            self._settings = load_settings()
            self._use_v2 = self._settings.get("score_version", "v2") == "v2"
        
        score_v2 = data.get("score_v2")
        score_v1 = data.get("score", 0) or 0
        
        if self._use_v2:
            if score_v2 is not None and score_v2 > 0:
                display_text = f"{score_v2:.1f}"
                score_item = QStandardItem(display_text)
                score_item.setData(score_v2, Qt.ItemDataRole.UserRole)
            elif score_v2 == -1:
                # [Phase 7] 신규/IPO 종목 (일봉 5일 미만)
                score_item = QStandardItem("🆕")
                score_item.setToolTip("신규/IPO 종목 - 일봉 데이터 부족 (5일 미만)")
                score_item.setForeground(self._color_warning)
                score_item.setData(-1, Qt.ItemDataRole.UserRole)
            elif score_v2 == 0:
                # [Phase 8] 매집 신호 없음 (score_v2 = 0)
                score_item = QStandardItem("➖")
                score_item.setToolTip("매집 신호 없음 (Warrant 또는 패턴 미탐지)")
                score_item.setForeground(self._color_warning)
                score_item.setData(0, Qt.ItemDataRole.UserRole)
            else:
                # score_v2가 None → 계산 오류
                score_item = QStandardItem("⚠️")
                score_item.setToolTip("score_v2 계산 실패")
                score_item.setForeground(self._color_warning)
                score_item.setData(0, Qt.ItemDataRole.UserRole)
        else:
            if score_v1 > 0:
                display_text = str(int(score_v1))
                score_item = QStandardItem(display_text)
                score_item.setData(score_v1, Qt.ItemDataRole.UserRole)
            else:
                score_item = QStandardItem("⚠️")
                score_item.setToolTip("Score 데이터 없음")
                score_item.setForeground(self._color_warning)
                score_item.setData(0, Qt.ItemDataRole.UserRole)
        self.setItem(row, self.COL_SCORE, score_item)

        
        # Ignition (Transparency Protocol)
        ign = data.get("ignition", 0) or 0
        if ign > 0:
            ign_item = QStandardItem(f"🔥{int(ign)}")
            ign_item.setData(ign, Qt.ItemDataRole.UserRole)
            if ign >= 70:
                ign_item.setBackground(QColor(255, 193, 7, 80))  # 노란색 하이라이트
        else:
            ign_item = QStandardItem("-")
            ign_item.setData(0, Qt.ItemDataRole.UserRole)
        self.setItem(row, self.COL_IGNITION, ign_item)
    
    def _format_dolvol(self, value: float) -> str:
        """
        Dollar Volume K/M/B 포맷팅
        
        Args:
            value: 달러 볼륨 값
            
        Returns:
            str: 포맷팅된 문자열 (예: $1.2B, $450M, $50K)
        """
        if value >= 1_000_000_000:
            return f"${value/1_000_000_000:.1f}B"
        elif value >= 1_000_000:
            return f"${value/1_000_000:.1f}M"
        elif value >= 1_000:
            return f"${value/1_000:.0f}K"
        elif value > 0:
            return f"${value:.0f}"
        return "⚠️"
