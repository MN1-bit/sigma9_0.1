"""
============================================
킬 스위치 & 리스크 매니저
============================================
- 킬 스위치: 시장 위험 감지 시 거래 중단
- 포지션 사이징: Half-Kelly 기반 동적 조절
- 변동성 타겟팅: 포트폴리오 위험 관리
- 모든 주문은 반드시 approve_order() 통과 필수!
============================================
"""

# ============================================
# 필수 라이브러리 임포트
# ============================================
import os
import math
from datetime import datetime
from typing import List, Dict, Optional, Tuple

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from PyQt6.QtCore import QObject, pyqtSignal

# .env 파일 로드
load_dotenv()


class RiskManager(QObject):
    """
    리스크 매니저
    
    모든 거래 관련 리스크를 관리합니다.
    주문은 반드시 approve_order()를 통과해야 합니다!
    
    Signals:
        kill_switch_triggered(str): 킬 스위치 발동 시 (상태)
        log_message(str): 로그 메시지
        decision_logged(dict): 의사결정 로그
    """
    
    # === PyQt Signals ===
    kill_switch_triggered = pyqtSignal(str)   # 킬 스위치 상태
    log_message = pyqtSignal(str)             # 로그
    decision_logged = pyqtSignal(dict)        # 의사결정 로그
    
    # === 설정값 (.env에서 로드) ===
    RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.02"))     # 2%
    DAILY_LOSS_LIMIT = float(os.getenv("DAILY_LOSS_LIMIT", "0.05"))  # 5%
    HALF_KELLY = float(os.getenv("HALF_KELLY", "0.5"))              # 50%
    MAX_POSITION_PCT = 0.25   # 계좌의 최대 25%
    TARGET_VOLATILITY = 0.20  # 목표 변동성 20%
    
    def __init__(self, parent=None) -> None:
        """초기화"""
        super().__init__(parent)
        self._current_kill_status: str = "CLEAR"
        self._daily_pnl: float = 0.0
        self._decision_log: List[Dict] = []
    
    # ============================================
    # 킬 스위치
    # ============================================
    
    def check_kill_switch(self, vix_1m: float, vix_3m: float, 
                         tnx_change: float = 0.0,
                         spy_up: bool = False, 
                         hyg_ief_down: bool = False) -> str:
        """
        킬 스위치 상태 확인
        
        우선순위:
        1. HALT_ALL: VIX 백워데이션 (근월 > 원월 = 공포)
        2. HALT_LONG: 금리 급등 (TNX > 5%)
        3. HALT_NEW: 다이버전스 (SPY↑ + 신용↓)
        4. CLEAR: 정상
        
        Args:
            vix_1m: VIX 근월물 가격
            vix_3m: VIX 원월물 가격
            tnx_change: 10년 국채 수익률 변화율
            spy_up: SPY 당일 상승 여부
            hyg_ief_down: HYG/IEF 하락 여부 (신용 리스크)
            
        Returns:
            킬 스위치 상태
        """
        # 1. HALT_ALL: VIX 백워데이션 (최우선)
        if vix_1m > vix_3m:
            self._current_kill_status = "HALT_ALL"
            self.log_message.emit(f"🚨 킬 스위치: HALT_ALL - VIX 백워데이션 (1M:{vix_1m:.2f} > 3M:{vix_3m:.2f})")
            self.kill_switch_triggered.emit("HALT_ALL")
            return "HALT_ALL"
        
        # 2. HALT_LONG: 금리 급등
        if tnx_change > 0.05:  # 5% 이상 변화
            self._current_kill_status = "HALT_LONG"
            self.log_message.emit(f"⚠️ 킬 스위치: HALT_LONG - 금리 급등 ({tnx_change*100:.1f}%)")
            self.kill_switch_triggered.emit("HALT_LONG")
            return "HALT_LONG"
        
        # 3. HALT_NEW: 다이버전스 (SPY↑ + 신용↓)
        if spy_up and hyg_ief_down:
            self._current_kill_status = "HALT_NEW"
            self.log_message.emit("⚠️ 킬 스위치: HALT_NEW - 다이버전스 감지")
            self.kill_switch_triggered.emit("HALT_NEW")
            return "HALT_NEW"
        
        # 4. CLEAR: 정상
        self._current_kill_status = "CLEAR"
        return "CLEAR"
    
    def get_kill_status(self) -> str:
        """현재 킬 스위치 상태 반환"""
        return self._current_kill_status
    
    # ============================================
    # 변동성 계산 (Yang-Zhang)
    # ============================================
    
    def calculate_yang_zhang_volatility(self, high: List[float], low: List[float],
                                        close: List[float], open_: List[float],
                                        period: int = 20) -> float:
        """
        Yang-Zhang 변동성 계산
        
        가장 정확한 일중 변동성 측정 방법입니다.
        공식: σ² = σ_overnight² + k × σ_open² + (1-k) × σ_close²
        
        Args:
            high: 고가 리스트
            low: 저가 리스트
            close: 종가 리스트
            open_: 시가 리스트
            period: 계산 기간
            
        Returns:
            연환산 변동성 (예: 0.20 = 20%)
        """
        try:
            n = min(len(high), len(low), len(close), len(open_), period)
            if n < 5:
                return 0.0
            
            # 최근 n일 데이터
            h = np.array(high[-n:])
            l = np.array(low[-n:])
            c = np.array(close[-n:])
            o = np.array(open_[-n:])
            
            # 로그 수익률
            log_hl = np.log(h / l)           # High-Low
            log_co = np.log(c / o)           # Close-Open
            log_oc = np.log(o[1:] / c[:-1])  # Overnight
            
            # 분산 계산
            var_close = np.var(log_co, ddof=1)
            var_open = np.var(log_oc, ddof=1) if len(log_oc) > 1 else 0
            var_rs = np.mean(log_hl ** 2) / (4 * np.log(2))  # Rogers-Satchell
            
            # Yang-Zhang 공식
            k = 0.34 / (1.34 + (n + 1) / (n - 1))
            yz_var = var_open + k * var_close + (1 - k) * var_rs
            
            # 연환산 (일일 → 연간, 252 거래일)
            annual_vol = np.sqrt(yz_var * 252)
            
            return round(float(annual_vol), 4)
            
        except Exception as e:
            self.log_message.emit(f"⚠️ 변동성 계산 오류: {str(e)}")
            return 0.20  # 기본값 20%
    
    # ============================================
    # 포지션 사이징 (Half-Kelly)
    # ============================================
    
    def calculate_position_size(self, account: float, price: float, 
                               yang_zhang_vol: float) -> int:
        """
        동적 포지션 사이징 (Half-Kelly)
        
        공식: Shares = (Account × 2%) / (YZ_Vol × Price) × 0.5
        
        Args:
            account: 계좌 잔고 (USD)
            price: 현재 가격
            yang_zhang_vol: Yang-Zhang 변동성
            
        Returns:
            주문 수량 (정수)
        """
        if account <= 0 or price <= 0 or yang_zhang_vol <= 0:
            return 0
        
        # 기본 공식
        risk_amount = account * self.RISK_PER_TRADE  # 계좌의 2%
        dollar_volatility = yang_zhang_vol * price
        
        if dollar_volatility == 0:
            return 0
        
        full_position = risk_amount / dollar_volatility
        
        # Half-Kelly 적용 (50%)
        half_kelly_position = full_position * self.HALF_KELLY
        
        # 최대 포지션 제한 (계좌의 25%)
        max_shares = (account * self.MAX_POSITION_PCT) / price
        
        # 최소 1주, 최대 제한 적용
        final_shares = max(1, min(int(half_kelly_position), int(max_shares)))
        
        self.log_message.emit(
            f"📊 포지션 사이징: {final_shares}주 "
            f"(계좌: ${account:,.0f}, 가격: ${price:.2f}, 변동성: {yang_zhang_vol*100:.1f}%)"
        )
        
        return final_shares
    
    # ============================================
    # 변동성 타겟팅
    # ============================================
    
    def apply_volatility_targeting(self, current_volatility: float,
                                   target_vol: float = None) -> float:
        """
        변동성 타겟팅
        
        현재 변동성이 목표보다 높으면 비중을 축소합니다.
        
        Args:
            current_volatility: 현재 변동성
            target_vol: 목표 변동성 (기본 20%)
            
        Returns:
            비중 조절 계수 (0~1)
        """
        if target_vol is None:
            target_vol = self.TARGET_VOLATILITY
        
        if current_volatility <= 0:
            return 1.0
        
        weight = target_vol / current_volatility
        weight = min(1.0, max(0.1, weight))  # 10%~100% 범위
        
        if weight < 1.0:
            self.log_message.emit(
                f"📉 변동성 타겟팅: 비중 {weight*100:.0f}% "
                f"(현재: {current_volatility*100:.1f}%, 목표: {target_vol*100:.0f}%)"
            )
        
        return round(weight, 4)
    
    # ============================================
    # 주문 승인 (필수!)
    # ============================================
    
    def approve_order(self, kill_status: str, daily_loss: float, 
                     account: float) -> bool:
        """
        주문 승인 (모든 주문은 이 함수를 통과해야 함!)
        
        조건:
        - 킬 스위치가 CLEAR 상태
        - 일일 손실이 한도(5%) 미만
        
        Args:
            kill_status: 킬 스위치 상태
            daily_loss: 당일 손실 금액 (양수)
            account: 계좌 잔고
            
        Returns:
            True = 주문 승인, False = 주문 거부
        """
        # 킬 스위치 체크
        if kill_status != "CLEAR":
            self.log_decision("REJECTED", f"킬 스위치 활성: {kill_status}")
            return False
        
        # 일일 손실 한도 체크
        if account > 0:
            loss_ratio = daily_loss / account
            if loss_ratio > self.DAILY_LOSS_LIMIT:
                self.log_decision("REJECTED", f"일일 손실 한도 초과: {loss_ratio*100:.1f}%")
                return False
        
        self.log_decision("APPROVED", "모든 조건 충족")
        return True
    
    # ============================================
    # 의사결정 로깅
    # ============================================
    
    def log_decision(self, decision: str, reason: str) -> None:
        """
        의사결정 로깅
        
        모든 거래 결정을 기록하여 나중에 AI 피드백에 활용합니다.
        
        Args:
            decision: 결정 (APPROVED/REJECTED/EXECUTED 등)
            reason: 사유
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "decision": decision,
            "reason": reason,
            "kill_status": self._current_kill_status,
        }
        
        self._decision_log.append(log_entry)
        self.decision_logged.emit(log_entry)
        
        emoji = "✅" if decision == "APPROVED" else "❌"
        self.log_message.emit(f"{emoji} 주문 {decision}: {reason}")
    
    def get_decision_log(self) -> List[Dict]:
        """의사결정 로그 반환"""
        return self._decision_log
    
    def update_daily_pnl(self, pnl: float) -> None:
        """일일 손익 업데이트"""
        self._daily_pnl = pnl
    
    def reset_daily(self) -> None:
        """일일 초기화 (장 시작 시 호출)"""
        self._daily_pnl = 0.0
        self._decision_log = []
        self.log_message.emit("🔄 일일 리스크 초기화")


# ============================================
# 단위 테스트
# ============================================
if __name__ == "__main__":
    print("=" * 50)
    print("리스크 매니저 테스트")
    print("=" * 50)
    
    rm = RiskManager()
    rm.log_message.connect(lambda x: print(f"[LOG] {x}"))
    
    # 킬 스위치 테스트
    print("\n📋 킬 스위치 테스트:")
    print(f"  HALT_ALL: {rm.check_kill_switch(20, 18)}")         # 백워데이션
    print(f"  HALT_LONG: {rm.check_kill_switch(15, 18, 0.06)}")  # 금리 급등
    print(f"  HALT_NEW: {rm.check_kill_switch(15, 18, 0, True, True)}")  # 다이버전스
    print(f"  CLEAR: {rm.check_kill_switch(15, 18)}")            # 정상
    
    # 포지션 사이징 테스트
    print("\n📋 포지션 사이징 테스트:")
    shares = rm.calculate_position_size(
        account=10000,   # $10,000
        price=100,       # $100
        yang_zhang_vol=0.02  # 2% 변동성
    )
    print(f"  결과: {shares}주")
    
    # 변동성 타겟팅 테스트
    print("\n📋 변동성 타겟팅 테스트:")
    weight = rm.apply_volatility_targeting(0.40)  # 40% 변동성
    print(f"  결과: {weight*100:.0f}% 비중")
    
    # 주문 승인 테스트
    print("\n📋 주문 승인 테스트:")
    print(f"  정상: {rm.approve_order('CLEAR', 100, 10000)}")
    print(f"  킬스위치: {rm.approve_order('HALT_ALL', 100, 10000)}")
    print(f"  손실한도: {rm.approve_order('CLEAR', 600, 10000)}")
