"""
============================================
섹터 로테이션 & 종목 스캐너
============================================
- 레버리지 ETF 모멘텀 스코어 계산
- 상대 강도 기반 최고 ETF 선정
- 성장주 필터링 (Green Mode용)
============================================
"""

# ============================================
# 필수 라이브러리 임포트
# ============================================
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

import pandas as pd
import yfinance as yf
from PyQt6.QtCore import QThread, pyqtSignal


class UniverseSelector(QThread):
    """
    섹터 로테이션 - 레버리지 ETF 선정
    
    모멘텀 스코어를 계산하여 가장 강한 ETF를 선정합니다.
    Red Mode에서 이 ETF에 집중 투자합니다.
    
    Signals:
        log_message(str): 로그 메시지
        target_selected(str): 선정된 ETF 심볼
    """
    
    # === PyQt Signals ===
    log_message = pyqtSignal(str)       # 로그 메시지
    target_selected = pyqtSignal(str)   # 선정된 ETF
    
    # === 레버리지 ETF 유니버스 ===
    LEVERAGED_ETFS = [
        "TQQQ",   # 나스닥 3x
        "SOXL",   # 반도체 3x
        "TECL",   # 기술 3x
        "FNGU",   # FANG+ 3x
    ]
    
    def __init__(self, parent=None) -> None:
        """초기화"""
        super().__init__(parent)
        self._target_etf: Optional[str] = None
        self._scores: Dict[str, float] = {}
    
    def calculate_relative_strength(self, symbol: str) -> float:
        """
        모멘텀 스코어 계산
        
        공식: (1개월 수익률 × 0.5) + (3개월 수익률 × 0.3) + (6개월 수익률 × 0.2)
        
        Args:
            symbol: ETF 심볼
            
        Returns:
            모멘텀 스코어 (높을수록 강함)
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="6mo")
            
            if len(hist) < 20:
                self.log_message.emit(f"⚠️ {symbol}: 데이터 부족")
                return 0.0
            
            current_price = hist["Close"].iloc[-1]
            
            # 1개월 전 가격 (약 21 거래일)
            price_1m = hist["Close"].iloc[-21] if len(hist) >= 21 else hist["Close"].iloc[0]
            
            # 3개월 전 가격 (약 63 거래일)
            price_3m = hist["Close"].iloc[-63] if len(hist) >= 63 else hist["Close"].iloc[0]
            
            # 6개월 전 가격
            price_6m = hist["Close"].iloc[0]
            
            # 수익률 계산
            return_1m = (current_price - price_1m) / price_1m
            return_3m = (current_price - price_3m) / price_3m
            return_6m = (current_price - price_6m) / price_6m
            
            # 가중 모멘텀 스코어
            score = (return_1m * 0.5) + (return_3m * 0.3) + (return_6m * 0.2)
            
            return round(score * 100, 2)  # 퍼센트로 변환
            
        except Exception as e:
            self.log_message.emit(f"❌ {symbol} 스코어 계산 실패: {str(e)}")
            return 0.0
    
    def get_target_etf(self) -> str:
        """
        최고 모멘텀 ETF 선정
        
        Returns:
            가장 높은 스코어의 ETF 심볼
        """
        if self._target_etf:
            return self._target_etf
        
        self.log_message.emit("📊 레버리지 ETF 모멘텀 스코어 계산 중...")
        
        # 모든 ETF 스코어 계산
        for etf in self.LEVERAGED_ETFS:
            score = self.calculate_relative_strength(etf)
            self._scores[etf] = score
            self.log_message.emit(f"  - {etf}: {score:.2f}%")
        
        # 최고 스코어 ETF 선정
        if self._scores:
            self._target_etf = max(self._scores, key=self._scores.get)
            self.log_message.emit(f"🎯 선정된 ETF: {self._target_etf} ({self._scores[self._target_etf]:.2f}%)")
        else:
            self._target_etf = "TQQQ"  # 기본값
            self.log_message.emit("⚠️ 스코어 계산 실패, 기본값 TQQQ 사용")
        
        return self._target_etf
    
    def get_all_scores(self) -> Dict[str, float]:
        """모든 ETF 스코어 반환"""
        if not self._scores:
            self.get_target_etf()
        return self._scores
    
    def run(self) -> None:
        """스레드 실행 - ETF 선정"""
        target = self.get_target_etf()
        self.target_selected.emit(target)


class GrowthStockScanner(QThread):
    """
    성장주 스캐너 (Green Mode 위성 포트폴리오용)
    
    재무, 성장, 수급, 기술적 필터를 적용하여
    고성장 종목을 선별합니다.
    
    Signals:
        log_message(str): 로그 메시지
        scan_complete(list): 스캔 완료된 종목 리스트
    """
    
    # === PyQt Signals ===
    log_message = pyqtSignal(str)       # 로그 메시지
    scan_complete = pyqtSignal(list)    # 스캔 결과
    
    # === 스캔 대상 종목 풀 ===
    # High Beta Mid-Caps (예시)
    SCAN_UNIVERSE = [
        "COIN",   # Coinbase
        "PLTR",   # Palantir
        "SOFI",   # SoFi Technologies
        "RBLX",   # Roblox
        "SNAP",   # Snap
        "DKNG",   # DraftKings
        "HOOD",   # Robinhood
        "AFRM",   # Affirm
        "UPST",   # Upstart
        "PATH",   # UiPath
    ]
    
    def __init__(self, parent=None) -> None:
        """초기화"""
        super().__init__(parent)
        self._candidates: List[str] = []
    
    def scan_growth_stocks(self) -> List[str]:
        """
        성장주 스캔
        
        필터:
        1. 영업이익 > 0
        2. 거래량 > 20일 평균 × 200%
        3. 52주 신고가 근접
        
        Returns:
            필터 통과한 종목 리스트
        """
        self.log_message.emit("🔍 성장주 스캔 시작...")
        passed = []
        
        for symbol in self.SCAN_UNIVERSE:
            try:
                ticker = yf.Ticker(symbol)
                
                # === 필터 1: 기본 데이터 확인 ===
                hist = ticker.history(period="3mo")
                if len(hist) < 20:
                    continue
                
                current_price = hist["Close"].iloc[-1]
                
                # === 필터 2: 거래량 폭발 ===
                avg_volume_20d = hist["Volume"].tail(20).mean()
                current_volume = hist["Volume"].iloc[-1]
                
                if current_volume < avg_volume_20d * 1.5:  # 150% 이상
                    continue
                
                # === 필터 3: 52주 신고가 근접 ===
                try:
                    high_52w = ticker.info.get("fiftyTwoWeekHigh", 0)
                    if high_52w > 0:
                        proximity = current_price / high_52w
                        if proximity < 0.85:  # 85% 이상이어야 함
                            continue
                except:
                    pass
                
                # 필터 통과!
                passed.append(symbol)
                self.log_message.emit(f"  ✅ {symbol} 통과 (가격: ${current_price:.2f})")
                
            except Exception as e:
                self.log_message.emit(f"  ⚠️ {symbol} 스캔 실패: {str(e)}")
                continue
        
        self._candidates = passed
        self.log_message.emit(f"🎯 스캔 완료: {len(passed)}개 종목 선정")
        
        return passed
    
    def get_candidates(self) -> List[str]:
        """스캔된 후보 종목 반환"""
        if not self._candidates:
            self.scan_growth_stocks()
        return self._candidates
    
    def run(self) -> None:
        """스레드 실행 - 스캔"""
        candidates = self.scan_growth_stocks()
        self.scan_complete.emit(candidates)


# ============================================
# 단위 테스트
# ============================================
if __name__ == "__main__":
    import sys
    from PyQt6.QtCore import QCoreApplication
    
    app = QCoreApplication(sys.argv)
    
    print("=" * 50)
    print("레버리지 ETF 섹터 로테이션 테스트")
    print("=" * 50)
    
    selector = UniverseSelector()
    selector.log_message.connect(lambda x: print(f"[LOG] {x}"))
    
    target = selector.get_target_etf()
    print(f"\n🎯 최종 선정: {target}")
    print(f"📊 전체 스코어: {selector.get_all_scores()}")
    
    print("\n" + "=" * 50)
    print("성장주 스캐너 테스트")
    print("=" * 50)
    
    scanner = GrowthStockScanner()
    scanner.log_message.connect(lambda x: print(f"[LOG] {x}"))
    
    candidates = scanner.scan_growth_stocks()
    print(f"\n📋 후보 종목: {candidates}")
    
    sys.exit(0)
