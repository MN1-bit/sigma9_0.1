# ============================================================================
# Backtest Models - 백테스트 관련 데이터 구조체
# ============================================================================
# 📌 이 파일의 역할:
#   - BacktestConfig, Trade, BacktestReport 데이터클래스 정의
#   - 백테스트 설정, 거래 기록, 결과 리포트 관리
#
# 📖 사용 예시:
#   >>> from backend.models import BacktestConfig, Trade
#   >>> config = BacktestConfig(initial_capital=100_000)
#
# 📖 리팩터링 [07-001]:
#   - core/backtest_engine.py → BacktestConfig 이동
#   - core/backtest_report.py → Trade, BacktestReport 이동
# ============================================================================

"""
Backtest Models

백테스트 설정, 거래 기록, 결과 리포트 데이터클래스입니다.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BacktestConfig:
    """
    백테스트 설정

    Attributes:
        initial_capital: 초기 자본금 (USD)
        position_size_pct: 포지션 크기 (계좌 대비 %)
        max_positions: 최대 동시 보유 포지션 수
        stop_loss_pct: 스탑로스 비율 (%)
        profit_target_pct: 이익실현 비율 (%)
        time_stop_days: 시간 기반 청산 (일)
        entry_stage: 진입 가능 Stage (기본값 Stage 4)
        min_score: 최소 진입 스코어
    """

    initial_capital: float = 100_000.0
    position_size_pct: float = 10.0
    max_positions: int = 5
    stop_loss_pct: float = -5.0
    profit_target_pct: float = 8.0
    time_stop_days: int = 3
    entry_stage: int = 4
    min_score: float = 80.0


@dataclass
class Trade:
    """
    개별 거래 기록

    Attributes:
        ticker: 종목 심볼
        entry_date: 진입 날짜
        entry_price: 진입 가격
        exit_date: 청산 날짜 (미청산 시 None)
        exit_price: 청산 가격
        exit_reason: 청산 이유 (stop_loss, profit_target, time_stop, forced)
        pnl_pct: 손익률 (%)
        stage: 진입 시 Stage
        score: 진입 시 Score
        metadata: 추가 메타데이터
    """

    ticker: str
    entry_date: str
    entry_price: float
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl_pct: Optional[float] = None
    stage: int = 0
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def close(self, exit_date: str, exit_price: float, exit_reason: str) -> float:
        """
        거래 청산

        Args:
            exit_date: 청산 날짜
            exit_price: 청산 가격
            exit_reason: 청산 이유

        Returns:
            float: 손익률 (%)
        """
        self.exit_date = exit_date
        self.exit_price = exit_price
        self.exit_reason = exit_reason
        self.pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100
        return self.pnl_pct

    def is_closed(self) -> bool:
        """거래가 청산되었는지 확인"""
        return self.exit_date is not None

    def is_winner(self) -> bool:
        """수익 거래인지 확인"""
        return self.pnl_pct is not None and self.pnl_pct > 0

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "ticker": self.ticker,
            "entry_date": self.entry_date,
            "entry_price": self.entry_price,
            "exit_date": self.exit_date,
            "exit_price": self.exit_price,
            "exit_reason": self.exit_reason,
            "pnl_pct": self.pnl_pct,
            "stage": self.stage,
            "score": self.score,
            "metadata": self.metadata,
        }


@dataclass
class BacktestReport:
    """
    백테스트 결과 리포트

    모든 거래 기록과 성과 메트릭을 관리합니다.

    Attributes:
        start_date: 백테스트 시작일
        end_date: 백테스트 종료일
        initial_capital: 초기 자본금
        strategy_name: 전략 이름
        trades: 거래 기록 리스트
        equity_curve: 자산 곡선 데이터
    """

    start_date: str = ""
    end_date: str = ""
    initial_capital: float = 100_000.0
    strategy_name: str = ""
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)

    def add_trade(self, trade: Trade) -> None:
        """거래 추가"""
        self.trades.append(trade)

    def get_open_trades(self) -> List[Trade]:
        """미청산 거래 조회"""
        return [t for t in self.trades if not t.is_closed()]

    def get_closed_trades(self) -> List[Trade]:
        """청산 완료된 거래 조회"""
        return [t for t in self.trades if t.is_closed()]

    @property
    def total_trades(self) -> int:
        """총 거래 횟수 (청산 완료된 것만)"""
        return len(self.get_closed_trades())

    @property
    def winning_trades(self) -> int:
        """수익 거래 수"""
        return len([t for t in self.get_closed_trades() if t.is_winner()])

    @property
    def losing_trades(self) -> int:
        """손실 거래 수"""
        return len([t for t in self.get_closed_trades() if not t.is_winner()])

    @property
    def win_rate(self) -> float:
        """승률 (%)"""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100

    @property
    def total_pnl_pct(self) -> float:
        """총 손익률 (%) - 단순 합산"""
        closed = self.get_closed_trades()
        return sum(t.pnl_pct for t in closed if t.pnl_pct is not None)

    @property
    def avg_pnl_pct(self) -> float:
        """평균 손익률 (%)"""
        if self.total_trades == 0:
            return 0.0
        return self.total_pnl_pct / self.total_trades


__all__ = ["BacktestConfig", "Trade", "BacktestReport"]
