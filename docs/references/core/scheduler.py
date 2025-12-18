"""
============================================
트레이딩 스케줄러 - 자동 시작/종료 관리
============================================
미국 주식 시장 시간에 맞춰 시스템을 자동 관리합니다.

시장 시간 (미국 동부):
- 프리마켓: 04:00 ~ 09:30
- 정규장: 09:30 ~ 16:00
- 애프터마켓: 16:00 ~ 20:00
============================================
"""

# ============================================
# 필수 라이브러리 임포트
# ============================================
from datetime import datetime, time, timedelta
from typing import Optional, Callable
import pytz
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

# pandas_market_calendars 임포트 (휴장일 체크)
try:
    import pandas_market_calendars as mcal
    HAS_MCAL = True
except ImportError:
    HAS_MCAL = False


class TradingScheduler(QObject):
    """
    트레이딩 스케줄러
    
    미국 주식 시장 시간에 맞춰 자동으로:
    - 장 시작 전 시스템 준비
    - 장 마감 시 청산 결정
    - 휴장일 스킵
    
    Signals:
        market_open: 장 시작 시
        market_close: 장 마감 시
        pre_market_warn: 장 마감 10분 전 경고
        log_message: 로그 메시지
    """
    
    # === PyQt Signals ===
    market_open = pyqtSignal()           # 장 시작
    market_close = pyqtSignal()          # 장 마감
    pre_close_warn = pyqtSignal()        # 마감 10분 전 경고
    prepare_system = pyqtSignal()        # 시스템 준비 (장 시작 15분 전)
    execute_close_logic = pyqtSignal(str) # 청산 로직 실행 (레짐 전달)
    log_message = pyqtSignal(str)        # 로그
    
    # === 미국 동부 시간대 ===
    US_EASTERN = pytz.timezone("US/Eastern")
    
    # === 시장 시간 (미국 동부 기준) ===
    MARKET_OPEN = time(9, 30)       # 정규장 시작
    MARKET_CLOSE = time(16, 0)      # 정규장 마감
    PRE_CLOSE_WARN = time(15, 50)   # 청산 경고 (마감 10분 전)
    PREPARE_TIME = time(9, 15)      # 시스템 준비 (시작 15분 전)
    
    def __init__(self, parent=None) -> None:
        """초기화"""
        super().__init__(parent)
        
        # 캘린더 (휴장일 체크용)
        if HAS_MCAL:
            self.calendar = mcal.get_calendar("NYSE")
        else:
            self.calendar = None
            self.log_message.emit("⚠️ pandas_market_calendars 없음 - 휴장일 체크 불가")
        
        # 체크 타이머 (1분마다 확인)
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self._check_market_status)
        
        # 상태 플래그
        self._is_market_open = False
        self._warned_pre_close = False
        self._prepared_today = False
    
    def start(self) -> None:
        """스케줄러 시작"""
        self.log_message.emit("⏰ 트레이딩 스케줄러 시작")
        self.check_timer.start(60000)  # 1분마다 체크
        self._check_market_status()    # 즉시 1회 체크
    
    def stop(self) -> None:
        """스케줄러 중지"""
        self.check_timer.stop()
        self.log_message.emit("⏰ 트레이딩 스케줄러 중지")
    
    # ============================================
    # 시장 시간 체크
    # ============================================
    
    def is_market_open(self) -> bool:
        """
        현재 정규장 진행 중인지 확인
        
        Returns:
            True: 정규장 시간
        """
        now = datetime.now(self.US_EASTERN)
        current_time = now.time()
        
        # 주말 체크
        if now.weekday() >= 5:  # 토(5), 일(6)
            return False
        
        # 휴장일 체크
        if self._is_holiday(now.date()):
            return False
        
        # 시간 체크
        return self.MARKET_OPEN <= current_time < self.MARKET_CLOSE
    
    def _is_holiday(self, date) -> bool:
        """휴장일 여부 확인"""
        if not self.calendar:
            return False
        
        try:
            schedule = self.calendar.schedule(
                start_date=date,
                end_date=date
            )
            return schedule.empty
        except Exception:
            return False
    
    def get_market_status(self) -> str:
        """
        현재 시장 상태 반환
        
        Returns:
            "OPEN", "CLOSED", "PRE_MARKET", "AFTER_MARKET"
        """
        now = datetime.now(self.US_EASTERN)
        current_time = now.time()
        
        # 주말/휴장일
        if now.weekday() >= 5 or self._is_holiday(now.date()):
            return "CLOSED"
        
        if current_time < time(4, 0):
            return "CLOSED"
        elif current_time < self.MARKET_OPEN:
            return "PRE_MARKET"
        elif current_time < self.MARKET_CLOSE:
            return "OPEN"
        elif current_time < time(20, 0):
            return "AFTER_MARKET"
        else:
            return "CLOSED"
    
    def get_next_market_open(self) -> Optional[datetime]:
        """
        다음 장 시작 시간 반환
        
        Returns:
            다음 장 시작 datetime (US/Eastern)
        """
        now = datetime.now(self.US_EASTERN)
        
        # 오늘 장 시작 시간
        today_open = now.replace(
            hour=self.MARKET_OPEN.hour,
            minute=self.MARKET_OPEN.minute,
            second=0,
            microsecond=0
        )
        
        # 아직 오늘 장 시작 전이면
        if now.time() < self.MARKET_OPEN and now.weekday() < 5:
            if not self._is_holiday(now.date()):
                return today_open
        
        # 그렇지 않으면 다음 영업일
        next_day = now + timedelta(days=1)
        while next_day.weekday() >= 5 or self._is_holiday(next_day.date()):
            next_day += timedelta(days=1)
        
        return next_day.replace(
            hour=self.MARKET_OPEN.hour,
            minute=self.MARKET_OPEN.minute,
            second=0,
            microsecond=0
        )
    
    def get_time_to_close(self) -> Optional[timedelta]:
        """
        장 마감까지 남은 시간
        
        Returns:
            timedelta 또는 None (장 열려있지 않으면)
        """
        if not self.is_market_open():
            return None
        
        now = datetime.now(self.US_EASTERN)
        close_dt = now.replace(
            hour=self.MARKET_CLOSE.hour,
            minute=self.MARKET_CLOSE.minute,
            second=0
        )
        
        return close_dt - now
    
    # ============================================
    # 스케줄 체크 (1분마다)
    # ============================================
    
    def _check_market_status(self) -> None:
        """시장 상태 체크 (타이머 콜백)"""
        now = datetime.now(self.US_EASTERN)
        current_time = now.time()
        status = self.get_market_status()
        
        # === 시스템 준비 (09:15) ===
        if current_time >= self.PREPARE_TIME and not self._prepared_today:
            if status in ["PRE_MARKET", "OPEN"]:
                self._prepared_today = True
                self.log_message.emit("🔧 시스템 준비 시작 (장 시작 15분 전)")
                self.prepare_system.emit()
        
        # === 장 시작 체크 ===
        if status == "OPEN" and not self._is_market_open:
            self._is_market_open = True
            self.log_message.emit("🔔 정규장 시작!")
            self.market_open.emit()
        
        # === 마감 10분 전 경고 (15:50) ===
        if current_time >= self.PRE_CLOSE_WARN and not self._warned_pre_close:
            if status == "OPEN":
                self._warned_pre_close = True
                self.log_message.emit("⚠️ 장 마감 10분 전 - 청산 결정 필요")
                self.pre_close_warn.emit()
        
        # === 장 마감 체크 ===
        if status != "OPEN" and self._is_market_open:
            self._is_market_open = False
            self._warned_pre_close = False
            self._prepared_today = False
            self.log_message.emit("🔔 정규장 마감!")
            self.market_close.emit()
    
    # ============================================
    # 청산 로직
    # ============================================
    
    def get_close_action(self, regime: str) -> str:
        """
        레짐별 청산 규칙 반환
        
        Args:
            regime: "횡보", "상승", "위기"
            
        Returns:
            "LIQUIDATE_ALL", "TRAILING_STOP", "IMMEDIATE"
        """
        if regime == "횡보":
            return "LIQUIDATE_ALL"  # 전량 청산
        elif regime == "상승":
            return "TRAILING_STOP"  # 트레일링 스탑 유지
        elif regime == "위기":
            return "IMMEDIATE"      # 즉시 청산
        else:
            return "LIQUIDATE_ALL"  # 기본: 전량 청산
    
    def request_close_logic(self, regime: str) -> None:
        """
        청산 로직 실행 요청
        
        Args:
            regime: 현재 레짐
        """
        action = self.get_close_action(regime)
        self.log_message.emit(f"📤 청산 로직 요청: {regime} → {action}")
        self.execute_close_logic.emit(action)


# ============================================
# 테스트 코드
# ============================================
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    print("=" * 50)
    print("TradingScheduler 테스트")
    print("=" * 50)
    
    scheduler = TradingScheduler()
    scheduler.log_message.connect(lambda x: print(x))
    
    # 시장 상태 확인
    print(f"\n📊 현재 시장 상태: {scheduler.get_market_status()}")
    print(f"📊 장 열림 여부: {scheduler.is_market_open()}")
    
    # 다음 장 시작
    next_open = scheduler.get_next_market_open()
    if next_open:
        print(f"📊 다음 장 시작: {next_open.strftime('%Y-%m-%d %H:%M')} (US/Eastern)")
    
    # 레짐별 청산 규칙
    print("\n📋 레짐별 청산 규칙:")
    for regime in ["횡보", "상승", "위기"]:
        action = scheduler.get_close_action(regime)
        print(f"   {regime}: {action}")
    
    print("\n✅ 테스트 완료")
