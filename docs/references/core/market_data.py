"""
============================================
시장 데이터 수집기 - 로컬 DB 캐싱
============================================
- SQLite로 히스토리컬 데이터 저장
- 252일치 최초 다운로드 후 증분 업데이트
- VIX 현물/선물 조회
- IBKR 실패 시 yfinance 폴백
============================================
"""

# ============================================
# 필수 라이브러리 임포트
# ============================================
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from PyQt6.QtCore import QThread, pyqtSignal

# .env 파일 로드
load_dotenv()

# 데이터베이스 경로
DB_PATH = Path(__file__).parent.parent / "data" / "market_data.db"


class MarketDataManager(QThread):
    """
    시장 데이터 관리자
    
    히스토리컬 데이터를 SQLite에 캐싱하고,
    VIX 데이터 및 Z-Score를 계산합니다.
    
    Signals:
        data_ready(str): 데이터 준비 완료 시 (심볼)
        log_message(str): 로그 메시지
        vix_update(dict): VIX 데이터 업데이트 시
    """
    
    # === PyQt Signals ===
    data_ready = pyqtSignal(str)        # 심볼 데이터 준비 완료
    log_message = pyqtSignal(str)       # 로그 메시지
    vix_update = pyqtSignal(dict)       # VIX 데이터
    
    # === 관리 대상 심볼 ===
    SYMBOLS = ["SPY", "QQQ", "^VIX"]   # 기본 심볼 (VIX는 yfinance용)
    
    def __init__(self, ib=None, parent=None) -> None:
        """
        초기화
        
        Args:
            ib: IBKRBridge에서 전달받은 IB 객체 (선택)
            parent: 부모 QObject
        """
        super().__init__(parent)
        self.ib = ib          # IBKR IB 객체 (연결된 경우)
        self.bridge = None    # IBKRBridge 참조 (VIX 선물용)
        self.conn: Optional[sqlite3.Connection] = None
        self._is_running = False
        
        # === 하이브리드 캐싱 변수 (1일 1회 갱신) ===
        self._cached_mean: Optional[float] = None      # VIX 평균
        self._cached_std: Optional[float] = None       # VIX 표준편차
        self._cache_date: Optional[datetime] = None    # 캐시 날짜
        self._last_vix: float = 0.0                    # 마지막 VIX (이벤트용)
        self.VIX_CHANGE_THRESHOLD = 0.5                # VIX 변동 임계값
    
    # ============================================
    # 데이터베이스 관련
    # ============================================
    
    def initialize_database(self) -> None:
        """
        데이터베이스 초기화
        
        - DB 파일이 없으면 생성
        - 테이블이 없으면 생성
        - 데이터가 없으면 252일치 다운로드
        """
        self.log_message.emit("📁 데이터베이스 초기화 중...")
        
        # data 폴더 생성
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # DB 연결 (check_same_thread=False: 멀티스레드 허용)
        self.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        
        # 테이블 생성
        self._create_tables()
        
        # 데이터 확인 및 다운로드
        for symbol in self.SYMBOLS:
            count = self._get_data_count(symbol)
            if count < 200:  # 데이터가 부족하면
                self.log_message.emit(f"📥 {symbol} 히스토리컬 데이터 다운로드 중...")
                self._download_historical(symbol, days=252)
            else:
                self.log_message.emit(f"✅ {symbol}: {count}일치 데이터 캐시됨")
        
        self.log_message.emit("✅ 데이터베이스 초기화 완료")
    
    def _create_tables(self) -> None:
        """테이블 생성"""
        cursor = self.conn.cursor()
        
        # 히스토리컬 가격 테이블 (일봉)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historical_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                UNIQUE(symbol, date)
            )
        """)
        
        # 인덱스 생성 (빠른 조회용)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbol_date 
            ON historical_prices(symbol, date)
        """)
        
        # 인트라데이 가격 테이블 (5분봉)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS intraday_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                datetime TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume INTEGER DEFAULT 0,
                UNIQUE(symbol, datetime)
            )
        """)
        
        # 5분봉 인덱스
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_intraday_symbol_datetime 
            ON intraday_prices(symbol, datetime)
        """)
        
        self.conn.commit()
    
    def _get_data_count(self, symbol: str) -> int:
        """심볼의 데이터 개수 조회"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM historical_prices WHERE symbol = ?",
            (symbol,)
        )
        return cursor.fetchone()[0]
    
    def _get_last_date(self, symbol: str) -> Optional[str]:
        """심볼의 마지막 날짜 조회"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT MAX(date) FROM historical_prices WHERE symbol = ?",
            (symbol,)
        )
        result = cursor.fetchone()[0]
        return result
    
    def _download_historical(self, symbol: str, days: int = 252) -> bool:
        """
        yfinance로 히스토리컬 데이터 다운로드
        
        IBKR API가 복잡하므로 yfinance 사용 (안정적)
        """
        try:
            # yfinance로 다운로드
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=f"{days}d")
            
            if df.empty:
                self.log_message.emit(f"⚠️ {symbol}: 데이터 없음")
                return False
            
            # DB에 저장
            cursor = self.conn.cursor()
            for date, row in df.iterrows():
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO historical_prices 
                        (symbol, date, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        symbol,
                        date.strftime("%Y-%m-%d"),
                        row["Open"],
                        row["High"],
                        row["Low"],
                        row["Close"],
                        int(row["Volume"]) if row["Volume"] else 0
                    ))
                except Exception:
                    continue
            
            self.conn.commit()
            self.log_message.emit(f"✅ {symbol}: {len(df)}일치 데이터 저장됨")
            return True
            
        except Exception as e:
            self.log_message.emit(f"❌ {symbol} 다운로드 실패: {str(e)}")
            return False
    
    def update_historical_data(self) -> None:
        """
        증분 업데이트 (장 시작 전 호출)
        
        마지막 날짜 이후 데이터만 다운로드
        """
        if not self.conn:
            self.initialize_database()
            return
        
        for symbol in self.SYMBOLS:
            last_date = self._get_last_date(symbol)
            
            if not last_date:
                # 데이터 없으면 전체 다운로드
                self._download_historical(symbol, days=252)
                continue
            
            # 마지막 날짜 이후 데이터만 다운로드
            last = datetime.strptime(last_date, "%Y-%m-%d")
            today = datetime.now()
            days_diff = (today - last).days
            
            if days_diff > 1:  # 1일 이상 차이나면 업데이트
                self.log_message.emit(f"📊 {symbol}: +{days_diff}일 업데이트 중...")
                self._download_historical(symbol, days=days_diff + 5)  # 여유분 추가
    
    # ============================================
    # 데이터 조회
    # ============================================
    
    def get_historical_prices(self, symbol: str, days: int = 252) -> pd.DataFrame:
        """
        히스토리컬 가격 조회
        
        Args:
            symbol: 심볼 (예: "SPY")
            days: 조회 일수
            
        Returns:
            OHLCV DataFrame
        """
        if not self.conn:
            self.initialize_database()
        
        query = """
            SELECT date, open, high, low, close, volume
            FROM historical_prices
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT ?
        """
        
        df = pd.read_sql_query(
            query, 
            self.conn, 
            params=(symbol, days),
            parse_dates=["date"]
        )
        
        # 날짜 오름차순 정렬
        df = df.sort_values("date").reset_index(drop=True)
        df.set_index("date", inplace=True)
        
        return df
    
    # ============================================
    # VIX 관련
    # ============================================
    
    def get_vix_data(self) -> Dict[str, Any]:
        """
        VIX 데이터 조회
        
        Returns:
            {"spot": float, "front_month": float, "back_month": float}
        """
        try:
            # yfinance로 VIX 현물
            vix = yf.Ticker("^VIX")
            spot = vix.info.get("regularMarketPrice", 0)
            
            # IBKR에서 VIX 선물 가격 가져오기
            front_month = spot or 0.0
            back_month = spot or 0.0
            
            if self.bridge:
                vix_futures = self.bridge.get_vix_futures()
                if vix_futures.get("front_month", 0) > 0:
                    front_month = vix_futures["front_month"]
                if vix_futures.get("back_month", 0) > 0:
                    back_month = vix_futures["back_month"]
            
            return {
                "spot": spot or 0.0,
                "front_month": front_month,
                "back_month": back_month,
            }
            
        except Exception as e:
            self.log_message.emit(f"⚠️ VIX 조회 실패: {str(e)}")
            return {"spot": 0.0, "front_month": 0.0, "back_month": 0.0}
    
    def get_vix_term_structure(self) -> str:
        """
        VIX 기간구조 판단
        
        Returns:
            "CONTANGO" 또는 "BACKWARDATION"
        """
        vix_data = self.get_vix_data()
        
        front = vix_data["front_month"]
        back = vix_data["back_month"]
        
        # 디버그 로그
        self.log_message.emit(f"📊 VIX Term: front={front:.2f}, back={back:.2f}")
        
        if front < back:
            return "CONTANGO"
        else:
            return "BACKWARDATION"
    
    def calculate_z_score(self, window: int = 126) -> float:
        """
        VIX Z-Score 계산
        
        Args:
            window: 계산 기간 (기본 126일 = 6개월)
            
        Returns:
            Z-Score 값
        """
        try:
            # VIX 히스토리 조회
            df = self.get_historical_prices("^VIX", days=window)
            
            if len(df) < 20:  # 최소 데이터 필요
                return 0.0
            
            # 현재 VIX
            current_vix = df["close"].iloc[-1]
            
            # 평균 및 표준편차
            mean = df["close"].mean()
            std = df["close"].std()
            
            if std == 0:
                return 0.0
            
            # Z-Score 계산
            z_score = (current_vix - mean) / std
            
            return round(z_score, 2)
            
        except Exception as e:
            self.log_message.emit(f"⚠️ Z-Score 계산 실패: {str(e)}")
            return 0.0
    
    # ============================================
    # 하이브리드 업데이트 메서드 (신규)
    # ============================================
    
    def _refresh_cache_if_needed(self) -> bool:
        """
        일봉 통계 캐시 갱신 (1일 1회)
        
        평균/표준편차를 하루에 한 번만 계산하여 캐싱합니다.
        
        Returns:
            True = 캐시 갱신됨, False = 기존 캐시 사용
        """
        today = datetime.now().date()
        
        # 캐시가 오늘 날짜면 갱신 불필요
        if self._cache_date and self._cache_date.date() == today:
            return False
        
        try:
            # VIX 126일 히스토리 조회
            df = self.get_historical_prices("^VIX", days=126)
            
            if len(df) < 20:
                self.log_message.emit("⚠️ VIX 데이터 부족, 캐시 갱신 실패")
                return False
            
            # 평균/표준편차 캐싱
            self._cached_mean = df["close"].mean()
            self._cached_std = df["close"].std()
            self._cache_date = datetime.now()
            
            self.log_message.emit(f"📊 일봉 통계 캐시 갱신: Mean={self._cached_mean:.2f}, Std={self._cached_std:.2f}")
            return True
            
        except Exception as e:
            self.log_message.emit(f"⚠️ 캐시 갱신 실패: {str(e)}")
            return False
    
    def calculate_z_score_hybrid(self, realtime_vix: float) -> float:
        """
        하이브리드 Z-Score 계산
        
        일봉 통계(캐시됨) + 실시간 VIX로 Z-Score 계산
        
        Args:
            realtime_vix: 실시간 VIX 가격
            
        Returns:
            Z-Score 값
        """
        # 캐시 확인/갱신
        self._refresh_cache_if_needed()
        
        # 캐시가 없으면 기존 방식 사용
        if self._cached_mean is None or self._cached_std is None:
            return self.calculate_z_score()
        
        if self._cached_std == 0:
            return 0.0
        
        z_score = (realtime_vix - self._cached_mean) / self._cached_std
        return round(z_score, 2)
    
    def should_update_on_vix_change(self, current_vix: float) -> bool:
        """
        VIX 변동 시 즉시 업데이트 필요 여부
        
        VIX가 임계값(0.5pt) 이상 변동하면 True
        
        Args:
            current_vix: 현재 VIX 가격
            
        Returns:
            True = 즉시 업데이트 필요
        """
        if abs(current_vix - self._last_vix) >= self.VIX_CHANGE_THRESHOLD:
            self._last_vix = current_vix
            return True
        return False
    
    def get_recommended_interval(self, z_score: float) -> int:
        """
        Z-Score에 따른 권장 업데이트 주기
        
        Args:
            z_score: 현재 Z-Score
            
        Returns:
            권장 주기 (밀리초)
        """
        if abs(z_score) >= 1.0:
            return 1000   # 1초 (레짐 전환 임박)
        else:
            return 5000   # 5초 (안정적)
    
    # ============================================
    # 스레드 실행
    # ============================================
    
    def run(self) -> None:
        """스레드 메인 (데이터 초기화)"""
        self._is_running = True
        
        try:
            # DB 초기화
            self.initialize_database()
            
            # 증분 업데이트
            self.update_historical_data()
            
            # VIX 데이터 전송
            vix_data = self.get_vix_data()
            vix_data["z_score"] = self.calculate_z_score()
            vix_data["term_structure"] = self.get_vix_term_structure()
            self.vix_update.emit(vix_data)
            
            self.data_ready.emit("ALL")
            
        except Exception as e:
            self.log_message.emit(f"❌ 데이터 초기화 오류: {str(e)}")
        
        # 주의: 연결을 닫지 않음! (메인 스레드에서 계속 사용)
    
    def stop(self) -> None:
        """스레드 중지"""
        self._is_running = False
        if self.conn:
            self.conn.close()
        self.wait(5000)
    
    # ============================================
    # 적응형 오버나이트 지표
    # ============================================
    
    def get_atr(self, symbol: str = "SPY", period: int = 20) -> float:
        """
        ATR (Average True Range) 계산
        
        적응형 오버나이트 판단에 사용:
        - 과열 판단: daily_return > ATR × 2
        
        Args:
            symbol: 심볼
            period: ATR 기간 (기본 20일)
            
        Returns:
            ATR 값 (소수점)
        """
        try:
            df = self.get_historical_prices(symbol, days=period + 5)
            
            if len(df) < period:
                return 0.0
            
            # True Range 계산
            df["prev_close"] = df["close"].shift(1)
            df["tr1"] = df["high"] - df["low"]
            df["tr2"] = abs(df["high"] - df["prev_close"])
            df["tr3"] = abs(df["low"] - df["prev_close"])
            df["tr"] = df[["tr1", "tr2", "tr3"]].max(axis=1)
            
            # ATR = TR의 이동평균
            atr = df["tr"].tail(period).mean()
            
            return round(atr, 4)
            
        except Exception as e:
            self.log_message.emit(f"⚠️ ATR 계산 실패: {str(e)}")
            return 0.0
    
    def get_vix_stats(self, window: int = 126) -> dict:
        """
        VIX 역사적 통계 (평균, 표준편차)
        
        적응형 오버나이트 판단에 사용:
        - VIX 위험 판단: vix > vix_mean + vix_std
        
        Args:
            window: 기간 (기본 126일 = 6개월)
            
        Returns:
            {"mean": float, "std": float}
        """
        # 캐시 확인
        self._refresh_cache_if_needed()
        
        if self._cached_mean is not None and self._cached_std is not None:
            return {
                "mean": round(self._cached_mean, 2),
                "std": round(self._cached_std, 2)
            }
        
        # 캐시가 없으면 직접 계산
        try:
            df = self.get_historical_prices("^VIX", days=window)
            
            if len(df) < 20:
                return {"mean": 20.0, "std": 5.0}  # 기본값
            
            return {
                "mean": round(df["close"].mean(), 2),
                "std": round(df["close"].std(), 2)
            }
        except Exception:
            return {"mean": 20.0, "std": 5.0}
    
    def get_daily_range_pct(self, symbol: str = "SPY") -> float:
        """
        당일 변동폭 (%)
        
        적응형 오버나이트 판단에 사용:
        - 목표 근접: VWAP 거리 < daily_range × 0.5
        
        Args:
            symbol: 심볼
            
        Returns:
            변동폭 % (예: 0.015 = 1.5%)
        """
        try:
            df = self.get_historical_prices(symbol, days=2)
            
            if len(df) < 1:
                return 0.01  # 기본값 1%
            
            latest = df.iloc[-1]
            open_price = latest["open"]
            high = latest["high"]
            low = latest["low"]
            
            if open_price == 0:
                return 0.01
            
            range_pct = (high - low) / open_price
            
            return round(range_pct, 4)
            
        except Exception:
            return 0.01
    
    # ============================================
    # 5분봉 데이터 (인트라데이)
    # ============================================
    
    # 인트라데이 데이터 관리 대상 심볼
    INTRADAY_SYMBOLS = ["TQQQ", "SOXL", "TECL", "FNGU", "SPY", "QQQ"]
    
    def download_intraday_history(self, symbol: str, use_ibkr: bool = False) -> bool:
        """
        1년치 5분봉 데이터 다운로드
        
        Args:
            symbol: 심볼 (예: "TQQQ")
            use_ibkr: True=IBKR API, False=yfinance (기본값)
            
        Returns:
            성공 여부
        """
        self.log_message.emit(f"📥 {symbol} 5분봉 데이터 다운로드 중... (1년치)")
        
        try:
            if use_ibkr and self.bridge and self.bridge.ib:
                # IBKR API 사용 (프리미엄)
                return self._download_intraday_ibkr(symbol)
            else:
                # yfinance 사용 (무료, 제한적)
                return self._download_intraday_yfinance(symbol)
                
        except Exception as e:
            self.log_message.emit(f"❌ {symbol} 5분봉 다운로드 실패: {str(e)}")
            return False
    
    def _download_intraday_yfinance(self, symbol: str) -> bool:
        """yfinance로 5분봉 다운로드 (최대 60일)"""
        try:
            import yfinance as yf
            
            ticker = yf.Ticker(symbol)
            
            # yfinance 5분봉 최대 기간: 60일
            df = ticker.history(period="60d", interval="5m")
            
            if df.empty:
                self.log_message.emit(f"⚠️ {symbol} 5분봉 데이터 없음")
                return False
            
            # DB에 저장
            cursor = self.conn.cursor()
            count = 0
            
            for dt, row in df.iterrows():
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO intraday_prices 
                        (symbol, datetime, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        symbol,
                        dt.strftime("%Y-%m-%d %H:%M:%S"),
                        row["Open"],
                        row["High"],
                        row["Low"],
                        row["Close"],
                        int(row["Volume"]) if row["Volume"] else 0
                    ))
                    count += 1
                except Exception:
                    continue
            
            self.conn.commit()
            self.log_message.emit(f"✅ {symbol}: {count}개 5분봉 저장됨 (yfinance)")
            return True
            
        except Exception as e:
            self.log_message.emit(f"❌ {symbol} yfinance 5분봉 실패: {str(e)}")
            return False
    
    def _download_intraday_ibkr(self, symbol: str) -> bool:
        """IBKR API로 5분봉 다운로드 (최대 1년)"""
        try:
            from ib_insync import Stock
            
            contract = Stock(symbol, 'SMART', 'USD')
            
            bars = self.bridge.ib.reqHistoricalData(
                contract,
                endDateTime='',
                durationStr='1 Y',        # 1년
                barSizeSetting='5 mins',  # 5분봉
                whatToShow='TRADES',
                useRTH=True               # 정규 시간만
            )
            
            if not bars:
                self.log_message.emit(f"⚠️ {symbol} IBKR 5분봉 데이터 없음")
                return False
            
            cursor = self.conn.cursor()
            count = 0
            
            for bar in bars:
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO intraday_prices 
                        (symbol, datetime, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        symbol,
                        bar.date.strftime("%Y-%m-%d %H:%M:%S"),
                        bar.open,
                        bar.high,
                        bar.low,
                        bar.close,
                        bar.volume
                    ))
                    count += 1
                except Exception:
                    continue
            
            self.conn.commit()
            self.log_message.emit(f"✅ {symbol}: {count}개 5분봉 저장됨 (IBKR)")
            return True
            
        except Exception as e:
            self.log_message.emit(f"❌ {symbol} IBKR 5분봉 실패: {str(e)}")
            return False
    
    def update_intraday(self, symbol: str) -> bool:
        """
        5분봉 증분 업데이트 (당일)
        
        마지막 저장 시점 이후 데이터만 추가
        """
        try:
            # 마지막 저장 시간 조회
            last_dt = self._get_last_intraday_datetime(symbol)
            
            if not last_dt:
                # 데이터 없으면 전체 다운로드
                return self.download_intraday_history(symbol)
            
            # yfinance로 최근 데이터 가져오기
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="1d", interval="5m")
            
            if df.empty:
                return True  # 새 데이터 없음
            
            cursor = self.conn.cursor()
            new_count = 0
            
            for dt, row in df.iterrows():
                dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                if dt_str > last_dt:
                    cursor.execute("""
                        INSERT OR REPLACE INTO intraday_prices 
                        (symbol, datetime, open, high, low, close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        symbol, dt_str,
                        row["Open"], row["High"], row["Low"], row["Close"],
                        int(row["Volume"]) if row["Volume"] else 0
                    ))
                    new_count += 1
            
            self.conn.commit()
            
            if new_count > 0:
                self.log_message.emit(f"📊 {symbol}: +{new_count}개 5분봉 추가됨")
            
            return True
            
        except Exception as e:
            self.log_message.emit(f"⚠️ {symbol} 5분봉 업데이트 실패: {str(e)}")
            return False
    
    def _get_last_intraday_datetime(self, symbol: str) -> Optional[str]:
        """5분봉의 마지막 시간 조회"""
        if not self.conn:
            return None
            
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT MAX(datetime) FROM intraday_prices WHERE symbol = ?",
            (symbol,)
        )
        result = cursor.fetchone()[0]
        return result
    
    def _get_intraday_count(self, symbol: str) -> int:
        """5분봉 데이터 개수 조회"""
        if not self.conn:
            return 0
            
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM intraday_prices WHERE symbol = ?",
            (symbol,)
        )
        return cursor.fetchone()[0]
    
    def get_intraday_prices(self, symbol: str, days: int = 1) -> pd.DataFrame:
        """
        5분봉 데이터 조회
        
        Args:
            symbol: 심볼
            days: 조회 일수 (기본 1 = 당일)
            
        Returns:
            OHLCV DataFrame (index=datetime)
        """
        if not self.conn:
            self.initialize_database()
        
        query = """
            SELECT datetime, open, high, low, close, volume
            FROM intraday_prices
            WHERE symbol = ?
            ORDER BY datetime DESC
            LIMIT ?
        """
        
        # 5분봉 개수 계산 (1일 = ~78개)
        limit = days * 78
        
        df = pd.read_sql_query(
            query, 
            self.conn, 
            params=(symbol, limit),
            parse_dates=["datetime"]
        )
        
        if df.empty:
            return df
        
        # 시간순 정렬
        df = df.sort_values("datetime").reset_index(drop=True)
        df.set_index("datetime", inplace=True)
        
        return df
    
    def resample_ohlcv(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        5분봉 → 다른 타임프레임으로 변환
        
        Args:
            df: 5분봉 DataFrame (index=datetime)
            timeframe: '15min', '1H', '4H', '1D'
        
        Returns:
            리샘플링된 OHLCV DataFrame
        """
        if df.empty:
            return df
        
        return df.resample(timeframe).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
    
    def initialize_intraday_data(self) -> None:
        """
        5분봉 데이터 초기화
        
        모든 대상 심볼의 5분봉 데이터를 확인하고 필요 시 다운로드
        """
        self.log_message.emit("📊 5분봉 데이터 초기화 중...")
        
        for symbol in self.INTRADAY_SYMBOLS:
            count = self._get_intraday_count(symbol)
            
            if count < 100:  # 데이터 부족
                self.download_intraday_history(symbol)
            else:
                self.log_message.emit(f"✅ {symbol}: {count}개 5분봉 캐시됨")
                # 증분 업데이트
                self.update_intraday(symbol)
        
        self.log_message.emit("✅ 5분봉 데이터 초기화 완료")


# ============================================
# 단위 테스트
# ============================================
if __name__ == "__main__":
    import sys
    from PyQt6.QtCore import QCoreApplication
    
    app = QCoreApplication(sys.argv)
    
    manager = MarketDataManager()
    
    # 시그널 연결
    manager.log_message.connect(lambda x: print(f"[LOG] {x}"))
    manager.vix_update.connect(lambda x: print(f"[VIX] {x}"))
    manager.data_ready.connect(lambda x: print(f"[READY] {x}"))
    
    # 실행
    manager.start()
    manager.wait()
    
    # 데이터 조회 테스트
    manager.initialize_database()
    df = manager.get_historical_prices("SPY", days=20)
    print("\n=== SPY 최근 20일 ===")
    print(df.tail())
    
    print("\n=== VIX 데이터 ===")
    print(manager.get_vix_data())
    print(f"Z-Score: {manager.calculate_z_score()}")
    print(f"Term Structure: {manager.get_vix_term_structure()}")
    
    sys.exit(0)
