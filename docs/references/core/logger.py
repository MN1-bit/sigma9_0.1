"""
============================================
파일 기반 로깅 시스템
============================================
시스템 로그와 거래 내역을 파일로 저장합니다.

로그 구조:
logs/
├── system/     시스템 로그 (.log)
├── trades/     거래 로그 (.json)
└── errors/     에러 로그 (.log)
============================================
"""

# ============================================
# 필수 라이브러리 임포트
# ============================================
import os
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from logging.handlers import RotatingFileHandler


# ============================================
# 경로 설정
# ============================================
BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / "logs"
SYSTEM_LOG_DIR = LOGS_DIR / "system"
TRADE_LOG_DIR = LOGS_DIR / "trades"
ERROR_LOG_DIR = LOGS_DIR / "errors"


class OmnissiahLogger:
    """
    Omnissiah 로깅 시스템
    
    시스템 로그, 거래 로그, 에러 로그를 분리 관리합니다.
    
    사용법:
        logger = OmnissiahLogger()
        logger.info("시스템 시작")
        logger.log_trade({"symbol": "SPY", "action": "BUY", ...})
        logger.error("에러 발생!")
    """
    
    LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    def __init__(self, log_level: int = logging.INFO) -> None:
        """
        초기화
        
        Args:
            log_level: 로그 레벨 (기본 INFO)
        """
        # 디렉토리 생성
        self._create_directories()
        
        # 오늘 날짜
        self._today = datetime.now().strftime("%Y-%m-%d")
        
        # 시스템 로거 설정
        self._system_logger = self._create_system_logger(log_level)
        
        # 에러 로거 설정
        self._error_logger = self._create_error_logger()
        
        # 거래 로그 파일 경로
        self._trade_log_path = TRADE_LOG_DIR / f"{self._today}.json"
        self._trades: List[Dict] = []
        
        # 기존 거래 로그 로드
        self._load_trades()
    
    def _create_directories(self) -> None:
        """로그 디렉토리 생성"""
        for dir_path in [SYSTEM_LOG_DIR, TRADE_LOG_DIR, ERROR_LOG_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def _create_system_logger(self, log_level: int) -> logging.Logger:
        """시스템 로거 생성"""
        logger = logging.getLogger("omnissiah.system")
        logger.setLevel(log_level)
        
        # 기존 핸들러 제거
        logger.handlers.clear()
        
        # 파일 핸들러
        log_file = SYSTEM_LOG_DIR / f"{self._today}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(
            logging.Formatter(self.LOG_FORMAT, self.DATE_FORMAT)
        )
        logger.addHandler(file_handler)
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter(self.LOG_FORMAT, self.DATE_FORMAT)
        )
        logger.addHandler(console_handler)
        
        return logger
    
    def _create_error_logger(self) -> logging.Logger:
        """에러 로거 생성"""
        logger = logging.getLogger("omnissiah.error")
        logger.setLevel(logging.ERROR)
        
        # 기존 핸들러 제거
        logger.handlers.clear()
        
        # 파일 핸들러
        log_file = ERROR_LOG_DIR / f"{self._today}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setFormatter(
            logging.Formatter(self.LOG_FORMAT, self.DATE_FORMAT)
        )
        logger.addHandler(file_handler)
        
        return logger
    
    def _load_trades(self) -> None:
        """기존 거래 로그 로드"""
        if self._trade_log_path.exists():
            try:
                with open(self._trade_log_path, "r", encoding="utf-8") as f:
                    self._trades = json.load(f)
            except Exception:
                self._trades = []
    
    def _save_trades(self) -> None:
        """거래 로그 저장"""
        with open(self._trade_log_path, "w", encoding="utf-8") as f:
            json.dump(self._trades, f, ensure_ascii=False, indent=2)
    
    # ============================================
    # 시스템 로깅
    # ============================================
    
    def debug(self, message: str) -> None:
        """DEBUG 로그"""
        self._system_logger.debug(message)
    
    def info(self, message: str) -> None:
        """INFO 로그"""
        self._system_logger.info(message)
    
    def warning(self, message: str) -> None:
        """WARNING 로그"""
        self._system_logger.warning(message)
    
    def error(self, message: str, exc_info: bool = False) -> None:
        """ERROR 로그 (에러 파일에도 저장)"""
        self._system_logger.error(message, exc_info=exc_info)
        self._error_logger.error(message, exc_info=exc_info)
    
    def critical(self, message: str, exc_info: bool = False) -> None:
        """CRITICAL 로그"""
        self._system_logger.critical(message, exc_info=exc_info)
        self._error_logger.critical(message, exc_info=exc_info)
    
    # ============================================
    # 거래 로깅
    # ============================================
    
    def log_trade(self, trade: Dict) -> None:
        """
        거래 로그 저장
        
        Args:
            trade: {
                "time": datetime or str,
                "symbol": str,
                "action": "BUY" or "SELL",
                "quantity": int,
                "price": float,
                "pnl": float,
                "regime": str
            }
        """
        # 시간 변환
        if isinstance(trade.get("time"), datetime):
            trade["time"] = trade["time"].isoformat()
        elif "time" not in trade:
            trade["time"] = datetime.now().isoformat()
        
        # 저장
        self._trades.append(trade)
        self._save_trades()
        
        # 시스템 로그에도 기록
        action = trade.get("action", "")
        symbol = trade.get("symbol", "")
        qty = trade.get("quantity", 0)
        price = trade.get("price", 0)
        pnl = trade.get("pnl", 0)
        
        self.info(f"📝 거래: {action} {qty} {symbol} @ ${price:.2f}, PnL: ${pnl:+.2f}")
    
    def get_today_trades(self) -> List[Dict]:
        """오늘 거래 내역 반환"""
        return self._trades.copy()
    
    # ============================================
    # 유틸리티
    # ============================================
    
    def cleanup_old_logs(self, days: int = 30) -> int:
        """
        오래된 로그 정리
        
        Args:
            days: 보관 일수 (기본 30일)
            
        Returns:
            삭제된 파일 수
        """
        cutoff = datetime.now() - timedelta(days=days)
        deleted = 0
        
        for dir_path in [SYSTEM_LOG_DIR, TRADE_LOG_DIR, ERROR_LOG_DIR]:
            if not dir_path.exists():
                continue
            
            for file_path in dir_path.iterdir():
                if file_path.is_file():
                    file_date_str = file_path.stem  # 2024-12-16
                    try:
                        file_date = datetime.strptime(file_date_str, "%Y-%m-%d")
                        if file_date < cutoff:
                            file_path.unlink()
                            deleted += 1
                    except ValueError:
                        pass  # 형식이 다른 파일 무시
        
        if deleted > 0:
            self.info(f"🗑️ 오래된 로그 {deleted}개 삭제됨")
        
        return deleted


# ============================================
# 싱글톤 인스턴스
# ============================================
_logger_instance: Optional[OmnissiahLogger] = None


def get_logger() -> OmnissiahLogger:
    """로거 인스턴스 반환 (싱글톤)"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = OmnissiahLogger()
    return _logger_instance


# ============================================
# 테스트 코드
# ============================================
if __name__ == "__main__":
    print("=" * 50)
    print("로깅 시스템 테스트")
    print("=" * 50)
    
    logger = get_logger()
    
    # 시스템 로그 테스트
    logger.debug("디버그 메시지")
    logger.info("정보 메시지")
    logger.warning("경고 메시지")
    logger.error("에러 메시지")
    
    # 거래 로그 테스트
    logger.log_trade({
        "symbol": "SPY",
        "action": "BUY",
        "quantity": 10,
        "price": 450.00,
        "pnl": 0,
        "regime": "횡보"
    })
    
    logger.log_trade({
        "symbol": "SPY",
        "action": "SELL",
        "quantity": 10,
        "price": 452.50,
        "pnl": 25.00,
        "regime": "횡보"
    })
    
    print(f"\n오늘 거래: {len(logger.get_today_trades())}건")
    print(f"로그 위치: {LOGS_DIR}")
    
    print("\n✅ 테스트 완료")
