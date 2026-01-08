# ============================================================================
# Risk Manager - 리스크 관리 및 Kill Switch
# ============================================================================
# 📌 이 파일의 역할:
#   - 포지션 사이징 (Kelly Criterion / 고정 비율)
#   - 일일/주간 손실 한도 체크
#   - Kill Switch (긴급 청산)
#
# 📖 사용 예시:
#   >>> from backend.core.risk_manager import RiskManager
#   >>> manager = RiskManager(connector, config)
#   >>> size = manager.calculate_position_size("AAPL", 150.0)
#   >>> if not manager.is_trading_allowed():
#   ...     print("거래 불가 - 한도 도달")
# ============================================================================

"""
Risk Manager Module

리스크 관리 및 포지션 사이징을 담당합니다.

Features:
    - Kelly Criterion 기반 포지션 사이징
    - 일일/주간 손실 한도 모니터링
    - Kill Switch (긴급 전량 청산)
"""

from datetime import datetime, date, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
import asyncio

from loguru import logger

from backend.models import RiskConfig


# ═══════════════════════════════════════════════════════════════════════════
# 손익 기록
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DailyPnL:
    """일일 손익 기록"""
    date: str
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    trade_count: int = 0
    
    @property
    def total_pnl(self) -> float:
        return self.realized_pnl + self.unrealized_pnl


# ═══════════════════════════════════════════════════════════════════════════
# RiskManager 클래스
# ═══════════════════════════════════════════════════════════════════════════

class RiskManager:
    """
    리스크 관리자
    
    포지션 사이징, 손실 한도 체크, Kill Switch를 담당합니다.
    
    Attributes:
        connector: IBKRConnector 인스턴스
        config: RiskConfig 설정
        
    Example:
        >>> from backend.core.risk_config import RiskConfig
        >>> config = RiskConfig(max_position_pct=10.0)
        >>> manager = RiskManager(connector, config)
        >>> 
        >>> # 포지션 사이즈 계산
        >>> qty = manager.calculate_position_size("AAPL", 150.0)
        >>> 
        >>> # 거래 가능 여부 체크
        >>> if manager.is_trading_allowed():
        ...     order_manager.execute_entry("AAPL", qty, "BUY")
    """
    
    def __init__(
        self,
        connector=None,
        config: Optional[RiskConfig] = None,
    ):
        """
        RiskManager 초기화
        
        Args:
            connector: IBKRConnector 인스턴스 (None이면 Mock 모드)
            config: RiskConfig 설정 (None이면 기본값)
        """
        self.connector = connector
        self.config = config or RiskConfig()
        
        # ─────────────────────────────────────────────────────────────────
        # 상태 추적
        # ─────────────────────────────────────────────────────────────────
        
        # 일일 손익
        self._daily_pnl: Dict[str, DailyPnL] = {}
        
        # 거래 기록 (Kelly 계산용)
        self._trade_history: List[Dict[str, Any]] = []
        
        # Kill Switch 상태
        self._is_killed: bool = False
        self._kill_reason: Optional[str] = None
        self._kill_timestamp: Optional[datetime] = None
        
        # 거래 가능 상태
        self._trading_enabled: bool = True
        
        # 시작 잔고 (일일 손실 계산용)
        self._starting_balance: float = 0.0
        self._current_balance: float = 0.0
        
        logger.debug("⚖️ RiskManager 초기화 완료")
    
    # ═══════════════════════════════════════════════════════════════════
    # 초기화
    # ═══════════════════════════════════════════════════════════════════
    
    def set_starting_balance(self, balance: float) -> None:
        """
        시작 잔고 설정 (일일 손실 계산 기준)
        
        Args:
            balance: 시작 잔고 (USD)
        """
        self._starting_balance = balance
        self._current_balance = balance
        logger.info(f"💰 시작 잔고 설정: ${balance:,.2f}")
    
    def update_balance(self, balance: float) -> None:
        """현재 잔고 업데이트"""
        self._current_balance = balance
    
    # ═══════════════════════════════════════════════════════════════════
    # 포지션 사이징
    # ═══════════════════════════════════════════════════════════════════
    
    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        account_balance: Optional[float] = None,
    ) -> int:
        """
        포지션 사이즈 계산
        
        Args:
            symbol: 종목 심볼
            entry_price: 예상 진입 가격
            account_balance: 계좌 잔고 (None이면 내부값 사용)
            
        Returns:
            int: 주문 수량 (주)
            
        Note:
            - use_kelly=True: Kelly Criterion 적용
            - use_kelly=False: 고정 비율 사용 (max_position_pct)
        """
        if entry_price <= 0:
            logger.warning("⚠️ 진입 가격이 0 이하")
            return 0
        
        balance = account_balance or self._current_balance
        if balance <= 0:
            logger.warning("⚠️ 계좌 잔고가 0 이하")
            return 0
        
        # ─────────────────────────────────────────────────────────────────
        # 포지션 비율 결정
        # ─────────────────────────────────────────────────────────────────
        
        if self.config.use_kelly and len(self._trade_history) >= self.config.kelly_min_trades:
            # Kelly Criterion
            position_pct = self._calculate_kelly_fraction()
        else:
            # 고정 비율
            position_pct = self.config.max_position_pct / 100.0
        
        # 최대 비율 제한
        position_pct = min(position_pct, self.config.max_position_pct / 100.0)
        
        # ─────────────────────────────────────────────────────────────────
        # 수량 계산
        # ─────────────────────────────────────────────────────────────────
        
        position_value = balance * position_pct
        qty = int(position_value / entry_price)
        
        logger.debug(f"📊 Position Size: {symbol} = {qty}주 (${position_value:,.0f} @ ${entry_price:.2f})")
        
        return max(1, qty)  # 최소 1주
    
    def _calculate_kelly_fraction(self) -> float:
        """
        Kelly Criterion 계산
        
        Formula:
            f* = (bp - q) / b
            b = 승수 (평균 수익 / 평균 손실)
            p = 승률
            q = 1 - p
            
        Returns:
            float: Kelly 비율 (0.0 ~ 0.25)
        """
        if len(self._trade_history) < self.config.kelly_min_trades:
            return self.config.max_position_pct / 100.0
        
        # 승/패 분리
        wins = [t["pnl_pct"] for t in self._trade_history if t["pnl_pct"] > 0]
        losses = [t["pnl_pct"] for t in self._trade_history if t["pnl_pct"] <= 0]
        
        if not wins or not losses:
            return self.config.max_position_pct / 100.0
        
        # 통계 계산
        win_rate = len(wins) / len(self._trade_history)
        avg_win = sum(wins) / len(wins)
        avg_loss = abs(sum(losses) / len(losses))
        
        if avg_loss == 0:
            return self.config.max_position_pct / 100.0
        
        # Kelly 공식
        b = avg_win / avg_loss
        p = win_rate
        q = 1 - p
        
        kelly = (b * p - q) / b
        
        # Fractional Kelly (1/4 Kelly 권장)
        adjusted_kelly = kelly * self.config.kelly_fraction
        
        # 범위 제한 (0 ~ 25%)
        return max(0.0, min(adjusted_kelly, 0.25))
    
    # ═══════════════════════════════════════════════════════════════════
    # 손실 한도 체크
    # ═══════════════════════════════════════════════════════════════════
    
    def get_daily_pnl_pct(self) -> float:
        """
        금일 손익률 (%)
        
        Returns:
            float: 손익률 (음수 = 손실)
        """
        if self._starting_balance <= 0:
            return 0.0
        
        pnl = self._current_balance - self._starting_balance
        return (pnl / self._starting_balance) * 100
    
    def check_daily_limit(self) -> bool:
        """
        일일 손실 한도 체크
        
        Returns:
            bool: True면 한도 도달 (거래 중지 필요)
        """
        daily_pnl_pct = self.get_daily_pnl_pct()
        limit_reached = daily_pnl_pct <= self.config.daily_loss_limit_pct
        
        if limit_reached:
            logger.warning(f"🔴 일일 손실 한도 도달: {daily_pnl_pct:.2f}% (한도: {self.config.daily_loss_limit_pct}%)")
            
            # 자동 Kill Switch
            if self.config.auto_kill_on_daily_limit and not self._is_killed:
                self.kill_switch("Daily Loss Limit")
        
        return limit_reached
    
    def check_weekly_limit(self) -> bool:
        """
        주간 손실 한도 체크
        
        Returns:
            bool: True면 한도 도달 (수동 리뷰 필요)
        """
        # 주간 손익 계산 (이번 주 월~금)
        weekly_pnl = self._calculate_weekly_pnl()
        limit_reached = weekly_pnl <= self.config.weekly_loss_limit_pct
        
        if limit_reached:
            logger.warning(f"🔴 주간 손실 한도 도달: {weekly_pnl:.2f}% (한도: {self.config.weekly_loss_limit_pct}%)")
        
        return limit_reached
    
    def _calculate_weekly_pnl(self) -> float:
        """이번 주 손익률 계산"""
        # 이번 주 월요일부터의 거래 집계
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        
        weekly_pnl = 0.0
        for date_str, daily in self._daily_pnl.items():
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d").date()
                if d >= monday:
                    weekly_pnl += daily.realized_pnl
            except:
                pass
        
        if self._starting_balance > 0:
            return (weekly_pnl / self._starting_balance) * 100
        return 0.0
    
    # ═══════════════════════════════════════════════════════════════════
    # 거래 가능 여부
    # ═══════════════════════════════════════════════════════════════════
    
    def is_trading_allowed(self) -> bool:
        """
        거래 가능 여부 체크
        
        다음 조건을 모두 통과해야 거래 가능:
        - Kill Switch 발동 안 됨
        - 일일 손실 한도 미도달
        - 일일 거래 횟수 미도달
        - 최대 포지션 수 미도달
        
        Returns:
            bool: True면 거래 가능
        """
        # 1. Kill Switch 체크
        if self._is_killed:
            logger.debug("🚫 거래 불가: Kill Switch 발동됨")
            return False
        
        # 2. 수동 비활성화 체크
        if not self._trading_enabled:
            logger.debug("🚫 거래 불가: 수동 비활성화")
            return False
        
        # 3. 일일 손실 한도 체크
        if self.check_daily_limit():
            return False
        
        # 4. 일일 거래 횟수 체크
        today = date.today().strftime("%Y-%m-%d")
        if today in self._daily_pnl:
            if self._daily_pnl[today].trade_count >= self.config.max_daily_trades:
                logger.debug(f"🚫 거래 불가: 일일 거래 한도 ({self.config.max_daily_trades}회)")
                return False
        
        return True
    
    def get_position_count(self) -> int:
        """현재 포지션 수 조회"""
        if not self.connector:
            return 0
        
        try:
            positions = self.connector.get_positions()
            return len([p for p in positions if p.get("qty", 0) != 0])
        except:
            return 0
    
    def can_open_position(self) -> bool:
        """새 포지션 오픈 가능 여부"""
        if not self.is_trading_allowed():
            return False
        
        current_positions = self.get_position_count()
        return current_positions < self.config.max_positions
    
    # ═══════════════════════════════════════════════════════════════════
    # Kill Switch
    # ═══════════════════════════════════════════════════════════════════
    
    def kill_switch(self, reason: str = "Manual") -> Dict[str, Any]:
        """
        Kill Switch 발동
        
        모든 미체결 주문을 취소하고 전 포지션을 시장가 청산합니다.
        
        Args:
            reason: 발동 이유
            
        Returns:
            dict: 결과 {cancelled_orders, liquidated_positions, success}
        """
        logger.warning(f"🔴 KILL SWITCH 발동: {reason}")
        
        self._is_killed = True
        self._kill_reason = reason
        self._kill_timestamp = datetime.now()
        self._trading_enabled = False
        
        result = {
            "success": True,
            "reason": reason,
            "timestamp": self._kill_timestamp.isoformat(),
            "cancelled_orders": 0,
            "liquidated_positions": [],
        }
        
        if not self.connector:
            logger.warning("⚠️ Connector 없음 - Kill Switch 시뮬레이션만")
            return result
        
        try:
            # 1. 모든 미체결 주문 취소
            result["cancelled_orders"] = self.connector.cancel_all_orders()
            logger.info(f"🚫 {result['cancelled_orders']}개 주문 취소 요청")
            
            # 2. 모든 포지션 청산
            positions = self.connector.get_positions()
            for pos in positions:
                symbol = pos.get("symbol")
                qty = pos.get("qty", 0)
                
                if qty > 0:
                    # Long 포지션 청산
                    self.connector.place_market_order(symbol, qty, "SELL")
                    result["liquidated_positions"].append({"symbol": symbol, "qty": qty, "action": "SELL"})
                    logger.info(f"📤 청산: SELL {qty} {symbol}")
                elif qty < 0:
                    # Short 포지션 청산
                    self.connector.place_market_order(symbol, abs(qty), "BUY")
                    result["liquidated_positions"].append({"symbol": symbol, "qty": abs(qty), "action": "BUY"})
                    logger.info(f"📤 청산: BUY {abs(qty)} {symbol}")
            
            logger.warning(f"✅ Kill Switch 완료: {len(result['liquidated_positions'])}개 포지션 청산")
            
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            logger.error(f"❌ Kill Switch 실패: {e}")
        
        return result
    
    def reset_kill_switch(self) -> None:
        """Kill Switch 상태 리셋"""
        self._is_killed = False
        self._kill_reason = None
        self._kill_timestamp = None
        self._trading_enabled = True
        logger.info("🟢 Kill Switch 리셋 - 거래 재개 가능")
    
    def enable_trading(self) -> None:
        """거래 활성화"""
        if self._is_killed:
            logger.warning("⚠️ Kill Switch가 발동 중입니다. 먼저 reset_kill_switch()를 호출하세요.")
            return
        self._trading_enabled = True
        logger.info("🟢 거래 활성화")
    
    def disable_trading(self) -> None:
        """거래 비활성화 (Kill Switch 없이)"""
        self._trading_enabled = False
        logger.info("🟡 거래 비활성화")
    
    # ═══════════════════════════════════════════════════════════════════
    # 거래 기록
    # ═══════════════════════════════════════════════════════════════════
    
    def record_trade(
        self,
        symbol: str,
        pnl: float,
        pnl_pct: float,
    ) -> None:
        """
        거래 기록 추가
        
        Args:
            symbol: 종목 심볼
            pnl: 손익 (USD)
            pnl_pct: 손익률 (%)
        """
        today = date.today().strftime("%Y-%m-%d")
        
        # 일일 손익 업데이트
        if today not in self._daily_pnl:
            self._daily_pnl[today] = DailyPnL(date=today)
        
        self._daily_pnl[today].realized_pnl += pnl
        self._daily_pnl[today].trade_count += 1
        
        # 거래 히스토리 추가 (Kelly 계산용)
        self._trade_history.append({
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
        })
        
        logger.debug(f"📝 거래 기록: {symbol} P&L {pnl_pct:+.2f}%")
    
    # ═══════════════════════════════════════════════════════════════════
    # 상태 조회
    # ═══════════════════════════════════════════════════════════════════
    
    def get_status(self) -> Dict[str, Any]:
        """
        현재 리스크 상태 조회
        
        Returns:
            dict: 상태 정보
        """
        return {
            "is_killed": self._is_killed,
            "kill_reason": self._kill_reason,
            "trading_enabled": self._trading_enabled and not self._is_killed,
            "starting_balance": self._starting_balance,
            "current_balance": self._current_balance,
            "daily_pnl_pct": self.get_daily_pnl_pct(),
            "daily_limit_pct": self.config.daily_loss_limit_pct,
            "position_count": self.get_position_count(),
            "max_positions": self.config.max_positions,
            "config": self.config.to_dict(),
        }
