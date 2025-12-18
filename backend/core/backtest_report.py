# ============================================================================
# Backtest Report - 백테스트 결과 데이터클래스
# ============================================================================
# 📌 이 파일의 역할:
#   - 백테스트 결과를 담는 데이터 구조 정의
#   - 성과 메트릭 계산 (CAGR, MDD, Win Rate 등)
#   - Trade 로그 관리
#
# 📖 사용 예시:
#   >>> from backend.core.backtest_report import BacktestReport, Trade
#   >>> report = BacktestReport()
#   >>> report.add_trade(trade)
#   >>> print(report.get_summary())
# ============================================================================

"""
Backtest Report Module

백테스트 성과 리포트 및 거래 로그를 관리합니다.

Metrics:
    - Total Trades: 총 거래 횟수
    - Win Rate: 승률 (%)
    - Total P&L: 총 손익 (%)
    - CAGR: 연환산 수익률
    - Max Drawdown: 최대 낙폭
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional, Dict, Any
import numpy as np


# ═══════════════════════════════════════════════════════════════════════════
# Trade 데이터 구조
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Trade:
    """
    개별 거래 기록
    
    Attributes:
        ticker: 종목 심볼
        entry_date: 진입 날짜
        entry_price: 진입 가격
        exit_date: 청산 날짜 (미청산 시 None)
        exit_price: 청산 가격 (미청산 시 None)
        exit_reason: 청산 이유 ("stop_loss", "time_stop", "profit_target", "trailing")
        pnl_pct: 손익률 (%) - 청산 후 계산
        stage: 진입 시 Stage (1~4)
        score: 진입 시 Accumulation Score
    """
    ticker: str
    entry_date: str  # YYYY-MM-DD
    entry_price: float
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl_pct: Optional[float] = None
    stage: int = 0
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # ─────────────────────────────────────────────────────────────────────
    # 거래 완료 처리
    # ─────────────────────────────────────────────────────────────────────
    
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
        
        # 손익률 계산
        if self.entry_price > 0:
            self.pnl_pct = ((exit_price - self.entry_price) / self.entry_price) * 100
        else:
            self.pnl_pct = 0.0
            
        return self.pnl_pct
    
    @property
    def is_closed(self) -> bool:
        """거래가 청산되었는지 확인"""
        return self.exit_date is not None
    
    @property
    def is_winner(self) -> bool:
        """수익 거래인지 확인"""
        return self.pnl_pct is not None and self.pnl_pct > 0
    
    def to_dict(self) -> Dict[str, Any]:
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
        }


# ═══════════════════════════════════════════════════════════════════════════
# BacktestReport 클래스
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class BacktestReport:
    """
    백테스트 결과 리포트
    
    모든 거래 기록과 성과 메트릭을 관리합니다.
    
    Attributes:
        start_date: 백테스트 시작일
        end_date: 백테스트 종료일
        initial_capital: 초기 자본 (USD)
        strategy_name: 사용된 전략 이름
        trades: 거래 기록 리스트
        equity_curve: 일별 자산가치 추이
    
    Example:
        >>> report = BacktestReport(
        ...     start_date="2024-01-01",
        ...     end_date="2024-12-01",
        ...     strategy_name="Seismograph"
        ... )
        >>> report.add_trade(trade)
        >>> summary = report.get_summary()
        >>> print(f"Win Rate: {summary['win_rate']:.1f}%")
    """
    start_date: str = ""
    end_date: str = ""
    initial_capital: float = 100_000.0
    strategy_name: str = ""
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    
    # ─────────────────────────────────────────────────────────────────────
    # 거래 관리
    # ─────────────────────────────────────────────────────────────────────
    
    def add_trade(self, trade: Trade) -> None:
        """거래 추가"""
        self.trades.append(trade)
    
    def get_open_trades(self) -> List[Trade]:
        """미청산 거래 조회"""
        return [t for t in self.trades if not t.is_closed]
    
    def get_closed_trades(self) -> List[Trade]:
        """청산 완료된 거래 조회"""
        return [t for t in self.trades if t.is_closed]
    
    # ─────────────────────────────────────────────────────────────────────
    # 성과 메트릭 계산
    # ─────────────────────────────────────────────────────────────────────
    
    @property
    def total_trades(self) -> int:
        """총 거래 횟수 (청산 완료된 것만)"""
        return len(self.get_closed_trades())
    
    @property
    def winning_trades(self) -> int:
        """수익 거래 수"""
        return sum(1 for t in self.get_closed_trades() if t.is_winner)
    
    @property
    def losing_trades(self) -> int:
        """손실 거래 수"""
        return self.total_trades - self.winning_trades
    
    @property
    def win_rate(self) -> float:
        """승률 (%)"""
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100
    
    @property
    def total_pnl_pct(self) -> float:
        """
        총 손익률 (%) - 단순 합산
        
        Note:
            실제 복리 계산이 아닌 단순 합산입니다.
            정확한 복리 수익률은 equity_curve에서 계산합니다.
        """
        return sum(t.pnl_pct or 0 for t in self.get_closed_trades())
    
    @property
    def avg_pnl_pct(self) -> float:
        """평균 손익률 (%)"""
        if self.total_trades == 0:
            return 0.0
        return self.total_pnl_pct / self.total_trades
    
    @property
    def avg_win_pct(self) -> float:
        """평균 수익률 (승리 거래만)"""
        winners = [t for t in self.get_closed_trades() if t.is_winner]
        if not winners:
            return 0.0
        return sum(t.pnl_pct or 0 for t in winners) / len(winners)
    
    @property
    def avg_loss_pct(self) -> float:
        """평균 손실률 (손실 거래만)"""
        losers = [t for t in self.get_closed_trades() if not t.is_winner]
        if not losers:
            return 0.0
        return sum(t.pnl_pct or 0 for t in losers) / len(losers)
    
    @property
    def profit_factor(self) -> float:
        """
        Profit Factor (총 수익 / 총 손실)
        
        Returns:
            float: 0보다 크면 수익, 1보다 크면 양호, 2 이상이면 우수
        """
        total_wins = sum(t.pnl_pct or 0 for t in self.get_closed_trades() if t.is_winner)
        total_losses = abs(sum(t.pnl_pct or 0 for t in self.get_closed_trades() if not t.is_winner))
        
        if total_losses == 0:
            return float('inf') if total_wins > 0 else 0.0
        return total_wins / total_losses
    
    def calculate_cagr(self) -> float:
        """
        CAGR (Compound Annual Growth Rate) 계산
        
        Formula:
            CAGR = (Ending Value / Beginning Value) ^ (1 / Years) - 1
        
        Returns:
            float: 연환산 수익률 (%)
        """
        if not self.equity_curve or len(self.equity_curve) < 2:
            # equity_curve가 없으면 단순 수익률로 추정
            return self.total_pnl_pct
        
        beginning_value = self.equity_curve[0]["equity"]
        ending_value = self.equity_curve[-1]["equity"]
        
        if beginning_value <= 0:
            return 0.0
        
        # 기간 계산 (년 단위)
        try:
            start = datetime.strptime(self.start_date, "%Y-%m-%d")
            end = datetime.strptime(self.end_date, "%Y-%m-%d")
            years = (end - start).days / 365.25
        except:
            years = 1.0  # 기본값
        
        if years <= 0:
            return 0.0
        
        # CAGR 공식 적용
        cagr = ((ending_value / beginning_value) ** (1 / years) - 1) * 100
        return cagr
    
    def calculate_max_drawdown(self) -> float:
        """
        MDD (Maximum Drawdown) 계산
        
        고점 대비 최대 하락폭을 계산합니다.
        
        Returns:
            float: 최대 낙폭 (%, 음수)
        """
        if not self.equity_curve or len(self.equity_curve) < 2:
            return 0.0
        
        equities = [e["equity"] for e in self.equity_curve]
        
        # 이전 고점 (running maximum) 계산
        peak = equities[0]
        max_dd = 0.0
        
        for equity in equities:
            if equity > peak:
                peak = equity
            
            if peak > 0:
                drawdown = (equity - peak) / peak * 100
                if drawdown < max_dd:
                    max_dd = drawdown
        
        return max_dd
    
    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """
        Sharpe Ratio 계산
        
        Args:
            risk_free_rate: 무위험 이자율 (연간, 기본값 2%)
            
        Returns:
            float: 샤프 비율
        """
        closed_trades = self.get_closed_trades()
        if len(closed_trades) < 2:
            return 0.0
        
        returns = [t.pnl_pct or 0 for t in closed_trades]
        
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        # 연환산 (거래당 수익률을 연간으로 변환하지 않음 - 단순화)
        sharpe = (avg_return - risk_free_rate) / std_return
        return sharpe
    
    def calculate_avg_holding_days(self) -> float:
        """평균 보유 기간 (일)"""
        closed_trades = self.get_closed_trades()
        if not closed_trades:
            return 0.0
        
        total_days = 0
        count = 0
        
        for trade in closed_trades:
            try:
                entry = datetime.strptime(trade.entry_date, "%Y-%m-%d")
                exit = datetime.strptime(trade.exit_date, "%Y-%m-%d")
                total_days += (exit - entry).days
                count += 1
            except:
                continue
        
        return total_days / count if count > 0 else 0.0
    
    # ─────────────────────────────────────────────────────────────────────
    # 리포트 생성
    # ─────────────────────────────────────────────────────────────────────
    
    def get_summary(self) -> Dict[str, Any]:
        """
        전체 성과 요약 반환
        
        Returns:
            dict: 모든 성과 메트릭을 포함하는 딕셔너리
        """
        return {
            "strategy_name": self.strategy_name,
            "period": f"{self.start_date} ~ {self.end_date}",
            "initial_capital": self.initial_capital,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": round(self.win_rate, 2),
            "total_pnl_pct": round(self.total_pnl_pct, 2),
            "avg_pnl_pct": round(self.avg_pnl_pct, 2),
            "avg_win_pct": round(self.avg_win_pct, 2),
            "avg_loss_pct": round(self.avg_loss_pct, 2),
            "profit_factor": round(self.profit_factor, 2),
            "cagr": round(self.calculate_cagr(), 2),
            "max_drawdown": round(self.calculate_max_drawdown(), 2),
            "sharpe_ratio": round(self.calculate_sharpe_ratio(), 2),
            "avg_holding_days": round(self.calculate_avg_holding_days(), 1),
        }
    
    def print_summary(self) -> None:
        """성과 요약 출력"""
        summary = self.get_summary()
        
        print("\n" + "=" * 60)
        print(f"📊 Backtest Report: {summary['strategy_name']}")
        print("=" * 60)
        print(f"📅 Period: {summary['period']}")
        print(f"💰 Initial Capital: ${summary['initial_capital']:,.0f}")
        print("-" * 60)
        print(f"📈 Total Trades: {summary['total_trades']}")
        print(f"✅ Winning: {summary['winning_trades']} | ❌ Losing: {summary['losing_trades']}")
        print(f"🎯 Win Rate: {summary['win_rate']}%")
        print("-" * 60)
        print(f"💵 Total P&L: {summary['total_pnl_pct']:+.2f}%")
        print(f"📊 Avg P&L: {summary['avg_pnl_pct']:+.2f}%")
        print(f"🏆 Avg Win: {summary['avg_win_pct']:+.2f}% | 📉 Avg Loss: {summary['avg_loss_pct']:.2f}%")
        print(f"⚖️ Profit Factor: {summary['profit_factor']:.2f}")
        print("-" * 60)
        print(f"📈 CAGR: {summary['cagr']:+.2f}%")
        print(f"📉 Max Drawdown: {summary['max_drawdown']:.2f}%")
        print(f"📐 Sharpe Ratio: {summary['sharpe_ratio']:.2f}")
        print(f"⏱️ Avg Holding: {summary['avg_holding_days']:.1f} days")
        print("=" * 60 + "\n")
    
    def to_dict(self) -> Dict[str, Any]:
        """전체 리포트를 딕셔너리로 변환 (JSON 저장용)"""
        return {
            "summary": self.get_summary(),
            "trades": [t.to_dict() for t in self.trades],
            "equity_curve": self.equity_curve,
        }
