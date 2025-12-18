# ============================================================================
# Backtest Engine Tests - 백테스트 엔진 테스트
# ============================================================================
# 📌 이 파일의 역할:
#   - BacktestEngine 클래스 테스트
#   - BacktestReport 클래스 테스트
#   - Trade 데이터클래스 테스트
#   - 성과 메트릭 계산 검증
#
# 📌 실행 방법:
#   pytest tests/test_backtest.py -v
#   pytest tests/test_backtest.py -v -k "test_trade"  # 특정 테스트만
# ============================================================================

"""
Backtest Tests

백테스트 엔진과 관련 클래스들의 단위 테스트입니다.
"""

import sys
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pandas as pd
import numpy as np

# backend 폴더를 경로에 추가
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from core.backtest_report import BacktestReport, Trade
from core.backtest_engine import BacktestEngine, BacktestConfig


# ═══════════════════════════════════════════════════════════════════════════
# Trade 데이터클래스 테스트
# ═══════════════════════════════════════════════════════════════════════════

class TestTrade:
    """Trade 데이터클래스 테스트"""
    
    def test_trade_creation(self):
        """Trade 객체 정상 생성 테스트"""
        trade = Trade(
            ticker="AAPL",
            entry_date="2024-01-01",
            entry_price=150.0,
            stage=4,
            score=85.0,
        )
        
        assert trade.ticker == "AAPL"
        assert trade.entry_price == 150.0
        assert trade.stage == 4
        assert trade.is_closed is False
    
    def test_trade_close_profit(self):
        """수익 청산 테스트"""
        trade = Trade(
            ticker="AAPL",
            entry_date="2024-01-01",
            entry_price=100.0,
        )
        
        pnl = trade.close(
            exit_date="2024-01-05",
            exit_price=110.0,
            exit_reason="profit_target",
        )
        
        assert trade.is_closed is True
        assert trade.is_winner is True
        assert pnl == 10.0  # +10%
        assert trade.exit_reason == "profit_target"
    
    def test_trade_close_loss(self):
        """손실 청산 테스트"""
        trade = Trade(
            ticker="AAPL",
            entry_date="2024-01-01",
            entry_price=100.0,
        )
        
        pnl = trade.close(
            exit_date="2024-01-05",
            exit_price=95.0,
            exit_reason="stop_loss",
        )
        
        assert trade.is_closed is True
        assert trade.is_winner is False
        assert pnl == -5.0  # -5%
    
    def test_trade_to_dict(self):
        """to_dict() 메서드 테스트"""
        trade = Trade(
            ticker="TSLA",
            entry_date="2024-01-01",
            entry_price=200.0,
        )
        
        result = trade.to_dict()
        
        assert isinstance(result, dict)
        assert result["ticker"] == "TSLA"
        assert result["entry_price"] == 200.0


# ═══════════════════════════════════════════════════════════════════════════
# BacktestReport 테스트
# ═══════════════════════════════════════════════════════════════════════════

class TestBacktestReport:
    """BacktestReport 클래스 테스트"""
    
    @pytest.fixture
    def sample_report(self):
        """샘플 리포트 생성"""
        report = BacktestReport(
            start_date="2024-01-01",
            end_date="2024-12-01",
            initial_capital=100_000.0,
            strategy_name="Test Strategy",
        )
        
        # 수익 거래 추가
        for i in range(6):
            trade = Trade(
                ticker=f"WIN{i}",
                entry_date="2024-01-01",
                entry_price=100.0,
            )
            trade.close("2024-01-05", 108.0, "profit_target")  # +8%
            report.add_trade(trade)
        
        # 손실 거래 추가
        for i in range(4):
            trade = Trade(
                ticker=f"LOSE{i}",
                entry_date="2024-01-01",
                entry_price=100.0,
            )
            trade.close("2024-01-05", 95.0, "stop_loss")  # -5%
            report.add_trade(trade)
        
        return report
    
    def test_report_creation(self):
        """BacktestReport 생성 테스트"""
        report = BacktestReport(
            start_date="2024-01-01",
            end_date="2024-12-01",
        )
        
        assert report.start_date == "2024-01-01"
        assert report.total_trades == 0
    
    def test_total_trades(self, sample_report):
        """총 거래 수 테스트"""
        assert sample_report.total_trades == 10
    
    def test_winning_trades(self, sample_report):
        """수익 거래 수 테스트"""
        assert sample_report.winning_trades == 6
    
    def test_losing_trades(self, sample_report):
        """손실 거래 수 테스트"""
        assert sample_report.losing_trades == 4
    
    def test_win_rate(self, sample_report):
        """승률 테스트"""
        # 6승 4패 = 60%
        assert sample_report.win_rate == 60.0
    
    def test_total_pnl(self, sample_report):
        """총 손익 테스트"""
        # 6 * 8% + 4 * (-5%) = 48 - 20 = 28%
        assert sample_report.total_pnl_pct == 28.0
    
    def test_avg_pnl(self, sample_report):
        """평균 손익 테스트"""
        # 28% / 10 = 2.8%
        assert sample_report.avg_pnl_pct == 2.8
    
    def test_profit_factor(self, sample_report):
        """Profit Factor 테스트"""
        # 48% / 20% = 2.4
        assert sample_report.profit_factor == 2.4
    
    def test_max_drawdown_empty(self):
        """빈 equity curve에서 MDD 테스트"""
        report = BacktestReport()
        assert report.calculate_max_drawdown() == 0.0
    
    def test_max_drawdown_calculation(self):
        """MDD 계산 테스트"""
        report = BacktestReport()
        report.equity_curve = [
            {"equity": 100000},
            {"equity": 110000},  # 고점
            {"equity": 99000},   # -10%
            {"equity": 105000},
            {"equity": 115000},  # 새 고점
            {"equity": 103500},  # -10%
        ]
        
        mdd = report.calculate_max_drawdown()
        assert mdd == -10.0  # -10%
    
    def test_get_summary(self, sample_report):
        """get_summary() 테스트"""
        summary = sample_report.get_summary()
        
        assert isinstance(summary, dict)
        assert "total_trades" in summary
        assert "win_rate" in summary
        assert "cagr" in summary
        assert "max_drawdown" in summary
        assert summary["total_trades"] == 10
        assert summary["win_rate"] == 60.0
    
    def test_to_dict(self, sample_report):
        """to_dict() 테스트"""
        result = sample_report.to_dict()
        
        assert "summary" in result
        assert "trades" in result
        assert "equity_curve" in result
        assert len(result["trades"]) == 10


# ═══════════════════════════════════════════════════════════════════════════
# BacktestConfig 테스트
# ═══════════════════════════════════════════════════════════════════════════

class TestBacktestConfig:
    """BacktestConfig 테스트"""
    
    def test_default_config(self):
        """기본 설정 테스트"""
        config = BacktestConfig()
        
        assert config.initial_capital == 100_000.0
        assert config.stop_loss_pct == -5.0
        assert config.profit_target_pct == 8.0
        assert config.time_stop_days == 3
        assert config.entry_stage == 4
    
    def test_custom_config(self):
        """커스텀 설정 테스트"""
        config = BacktestConfig(
            initial_capital=50_000.0,
            stop_loss_pct=-3.0,
            profit_target_pct=10.0,
        )
        
        assert config.initial_capital == 50_000.0
        assert config.stop_loss_pct == -3.0
        assert config.profit_target_pct == 10.0


# ═══════════════════════════════════════════════════════════════════════════
# BacktestEngine 테스트
# ═══════════════════════════════════════════════════════════════════════════

class TestBacktestEngine:
    """BacktestEngine 클래스 테스트"""
    
    def test_engine_initialization(self):
        """엔진 초기화 테스트"""
        engine = BacktestEngine(db_path="test.db")
        
        assert engine.db_path == "test.db"
        assert engine.config.initial_capital == 100_000.0
        assert engine._cash == 100_000.0
    
    def test_engine_with_custom_config(self):
        """커스텀 설정으로 엔진 초기화 테스트"""
        config = BacktestConfig(initial_capital=50_000.0)
        engine = BacktestEngine(db_path="test.db", config=config)
        
        assert engine._cash == 50_000.0
    
    def test_generate_date_range(self):
        """날짜 범위 생성 테스트"""
        engine = BacktestEngine()
        dates = engine._generate_date_range("2024-01-01", "2024-01-07")
        
        # 1월 1일(월) ~ 1월 7일(일) 중 평일만
        assert len(dates) == 5  # 월~금
        assert "2024-01-01" in dates
        assert "2024-01-05" in dates
        # 주말 제외 확인 (2024-01-06, 2024-01-07은 토/일)
        assert "2024-01-06" not in dates
        assert "2024-01-07" not in dates


# ═══════════════════════════════════════════════════════════════════════════
# 통합 테스트 (Mock 사용)
# ═══════════════════════════════════════════════════════════════════════════

class TestBacktestIntegration:
    """통합 테스트 (Mock 데이터 사용)"""
    
    @pytest.fixture
    def mock_data(self):
        """Mock 데이터 생성"""
        # 50일치 데이터 생성
        dates = pd.date_range("2024-01-01", periods=50, freq="B")  # B = 영업일
        
        return pd.DataFrame({
            "date": [d.strftime("%Y-%m-%d") for d in dates],
            "open": [100.0 + i * 0.1 for i in range(50)],
            "high": [102.0 + i * 0.1 for i in range(50)],
            "low": [98.0 + i * 0.1 for i in range(50)],
            "close": [101.0 + i * 0.1 for i in range(50)],
            "volume": [1000000 for _ in range(50)],
        })
    
    @pytest.fixture
    def mock_strategy(self):
        """Mock 전략 생성"""
        strategy = MagicMock()
        strategy.name = "Mock Strategy"
        
        # Stage 4 종목으로 반환 (진입 대상)
        strategy.calculate_watchlist_score_detailed.return_value = {
            "score": 85.0,
            "stage_number": 4,
            "stage": "Tight Range",
            "signals": {"tight_range": True},
        }
        
        return strategy
    
    @pytest.mark.asyncio
    async def test_run_backtest_with_mock(self, mock_data, mock_strategy):
        """Mock 데이터로 백테스트 실행 테스트"""
        engine = BacktestEngine(db_path="mock.db")
        
        # DB Mock
        engine.db = MagicMock()
        engine.db.initialize = AsyncMock()
        engine.db.close = AsyncMock()
        engine.db.get_daily_bars = AsyncMock(return_value=[])
        
        # _load_all_data Mock
        async def mock_load(*args, **kwargs):
            return {"AAPL": mock_data}
        
        engine._load_all_data = mock_load
        
        # 백테스트 실행
        report = await engine.run(
            strategy=mock_strategy,
            tickers=["AAPL"],
            start_date="2024-01-15",
            end_date="2024-02-15",
        )
        
        # 리포트 검증
        assert report is not None
        assert report.strategy_name == "Mock Strategy"
        assert len(report.equity_curve) > 0
    
    @pytest.mark.asyncio
    async def test_stop_loss_trigger(self, mock_strategy):
        """Stop Loss 트리거 테스트"""
        engine = BacktestEngine()
        
        # 5% 하락 데이터
        mock_data = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "open": [100.0, 100.0, 100.0],
            "high": [100.0, 100.0, 100.0],
            "low": [100.0, 94.0, 90.0],  # 6% 하락 (stop loss 트리거)
            "close": [100.0, 95.0, 91.0],
            "volume": [1000000, 1000000, 1000000],
        })
        
        all_data = {"TEST": mock_data}
        
        # 포지션 오픈
        trade = Trade(
            ticker="TEST",
            entry_date="2024-01-01",
            entry_price=100.0,
        )
        engine._open_positions["TEST"] = trade
        engine.report = BacktestReport()
        engine.report.add_trade(trade)
        
        # Stop Loss 체크
        await engine._check_exits("2024-01-02", all_data)
        
        # Stop Loss로 청산되었는지 확인
        assert "TEST" not in engine._open_positions
        assert trade.exit_reason == "stop_loss"


# ═══════════════════════════════════════════════════════════════════════════
# 성과 메트릭 정확성 테스트
# ═══════════════════════════════════════════════════════════════════════════

class TestMetricsAccuracy:
    """성과 메트릭 계산 정확성 테스트"""
    
    def test_cagr_calculation(self):
        """CAGR 계산 정확성 테스트"""
        report = BacktestReport(
            start_date="2023-01-01",
            end_date="2024-01-01",  # 1년
        )
        
        # 시작: 100,000, 종료: 120,000 (20% 수익)
        report.equity_curve = [
            {"equity": 100000},
            {"equity": 120000},
        ]
        
        cagr = report.calculate_cagr()
        
        # 1년 기준 CAGR = 20%
        assert abs(cagr - 20.0) < 1.0  # 약간의 오차 허용
    
    def test_sharpe_ratio_calculation(self):
        """Sharpe Ratio 계산 테스트"""
        report = BacktestReport()
        
        # 변동성 있는 수익 거래 (다양한 수익률)
        returns = [2, 3, 1, 4, 2, 3, 1, 2, 5, 2]  # 양의 수익률 (변동성 있음)
        for i, ret in enumerate(returns):
            trade = Trade(
                ticker=f"T{i}",
                entry_date="2024-01-01",
                entry_price=100.0,
            )
            trade.close("2024-01-05", 100.0 + ret, "profit_target")
            report.add_trade(trade)
        
        sharpe = report.calculate_sharpe_ratio(risk_free_rate=0.0)
        
        # 평균 수익 > 0, 변동성 있음 = positive Sharpe
        assert sharpe > 0
    
    def test_avg_holding_days(self):
        """평균 보유 기간 계산 테스트"""
        report = BacktestReport()
        
        # 3일 보유
        trade1 = Trade(ticker="A", entry_date="2024-01-01", entry_price=100)
        trade1.close("2024-01-04", 105, "profit")  # 3일
        
        # 5일 보유
        trade2 = Trade(ticker="B", entry_date="2024-01-01", entry_price=100)
        trade2.close("2024-01-06", 105, "profit")  # 5일
        
        report.add_trade(trade1)
        report.add_trade(trade2)
        
        avg_days = report.calculate_avg_holding_days()
        
        # (3 + 5) / 2 = 4일
        assert avg_days == 4.0


# ═══════════════════════════════════════════════════════════════════════════
# 실행
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
