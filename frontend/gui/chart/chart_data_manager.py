# ============================================================================
# Chart Data Manager - 2-Tier Cache for Dynamic Data Loading (Step 2.7.4)
# ============================================================================
# 📌 이 파일의 역할:
#   - 차트 Pan/Zoom 시 2-Tier Cache를 활용한 동적 데이터 로딩 관리
#   - L1: Memory Cache (현재 뷰포트 + 버퍼)
#   - L2: SQLite Database (과거 데이터)
#   - L3: Massive API (DB에 없는 데이터 fetch)
#
# 🏗️ 아키텍처:
#   Viewport Changed → needs_more_data() → L1 Miss → L2 Query → L3 Fetch
#                                                         ↓
#                                                    Save to L2
# ============================================================================

"""
Chart Data Manager

Pan/Zoom 시 동적 데이터 로딩을 위한 2-Tier Cache 관리자입니다.

Features:
    - 뷰포트 범위 기반 데이터 필요 여부 판단
    - Memory + SQLite 2-tier 캐싱
    - 데이터 병합 (prepend/append)
    - 버퍼링으로 부드러운 스크롤 경험
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import pandas as pd
from loguru import logger


@dataclass
class LoadedRange:
    """로드된 데이터 범위 추적"""
    start_idx: int
    end_idx: int
    start_timestamp: int  # Unix ms
    end_timestamp: int    # Unix ms


class ChartDataManager:
    """
    차트 데이터 캐싱 및 동적 로딩 관리자
    
    ═══════════════════════════════════════════════════════════════════════
    ELI5 (쉬운 설명):
    ═══════════════════════════════════════════════════════════════════════
    
    차트를 스크롤하면 보이지 않는 과거 데이터가 필요합니다.
    이 클래스는 "어떤 데이터가 필요한지" 판단하고,
    "DB에서 가져올지, API에서 가져올지" 결정합니다.
    
    L1: 메모리 (빠름, 용량 작음) - 지금 보이는 데이터
    L2: SQLite (중간) - 과거 저장된 데이터
    L3: API (느림) - DB에 없으면 API 호출
    
    Attributes:
        FETCH_BUFFER: 뷰포트 양쪽에 미리 로드할 바 수
        MIN_FETCH_SIZE: 최소 fetch 크기 (API 효율성)
    """
    
    FETCH_BUFFER = 50  # 뷰포트 양쪽에 미리 로드할 바 수
    MIN_FETCH_SIZE = 100  # 최소 fetch 크기 (API 효율성)
    
    def __init__(self):
        """ChartDataManager 초기화"""
        self._loaded_range: Optional[LoadedRange] = None
        self._data_cache: List[Dict[str, Any]] = []  # L1: Memory Cache
        self._current_ticker: Optional[str] = None
        self._current_timeframe: str = "1D"
        
        logger.debug("📊 ChartDataManager 초기화")
    
    @property
    def loaded_range(self) -> Optional[LoadedRange]:
        """현재 로드된 데이터 범위"""
        return self._loaded_range
    
    @property
    def data_cache(self) -> List[Dict[str, Any]]:
        """현재 캐시된 데이터 (L1)"""
        return self._data_cache
    
    def reset(self, ticker: str = None, timeframe: str = None):
        """
        타임프레임 또는 종목 변경 시 캐시 초기화
        
        Args:
            ticker: 새 종목 심볼
            timeframe: 새 타임프레임
        """
        self._loaded_range = None
        self._data_cache = []
        
        if ticker:
            self._current_ticker = ticker
        if timeframe:
            self._current_timeframe = timeframe
        
        logger.debug(f"🔄 Cache 초기화: {self._current_ticker} / {self._current_timeframe}")
    
    def set_initial_data(self, data: List[Dict[str, Any]]):
        """
        초기 데이터 설정
        
        Args:
            data: 차트 데이터 리스트 [{"time": timestamp, "open": float, ...}, ...]
        """
        if not data:
            return
        
        self._data_cache = data.copy()
        
        # 범위 계산
        timestamps = [d.get("time", 0) for d in data]
        if timestamps:
            self._loaded_range = LoadedRange(
                start_idx=0,
                end_idx=len(data) - 1,
                start_timestamp=int(min(timestamps) * 1000),  # seconds → ms
                end_timestamp=int(max(timestamps) * 1000)
            )
        
        logger.debug(
            f"📥 초기 데이터 설정: {len(data)} bars, "
            f"range=[{self._loaded_range.start_idx}:{self._loaded_range.end_idx}]"
        )
    
    def needs_more_data(self, view_start: int, view_end: int) -> bool:
        """
        추가 데이터 로드 필요 여부 확인
        
        뷰포트가 버퍼 범위 밖으로 나가면 True 반환
        
        Args:
            view_start: 뷰포트 시작 인덱스
            view_end: 뷰포트 끝 인덱스
        
        Returns:
            bool: 추가 데이터 필요 여부
        """
        if self._loaded_range is None:
            return True
        
        # 뷰포트가 버퍼 범위 밖으로 나갔는지 확인
        buffer_start = self._loaded_range.start_idx + self.FETCH_BUFFER
        buffer_end = self._loaded_range.end_idx - self.FETCH_BUFFER
        
        needs_left = view_start < buffer_start and view_start < 0
        needs_right = view_end > buffer_end  # 오른쪽은 미래 → 보통 필요 없음
        
        # 왼쪽(과거) 방향으로만 동적 로딩 지원 (오른쪽은 최신 데이터)
        return needs_left
    
    def calculate_fetch_range(
        self, 
        view_start: int, 
        view_end: int
    ) -> tuple[int, int, int, int]:
        """
        Fetch할 데이터 범위 계산
        
        Args:
            view_start: 뷰포트 시작 인덱스
            view_end: 뷰포트 끝 인덱스
        
        Returns:
            (fetch_start_idx, fetch_end_idx, start_ts, end_ts)
            - fetch_start_idx: 인덱스 시작 (음수 가능)
            - fetch_end_idx: 인덱스 끝
            - start_ts: 시작 타임스탬프 (밀리초)
            - end_ts: 끝 타임스탬프 (밀리초)
        """
        if self._loaded_range is None:
            return 0, self.MIN_FETCH_SIZE, 0, 0
        
        # 뷰포트 + 버퍼 범위 계산
        desired_start = view_start - self.FETCH_BUFFER * 2
        
        # 이미 로드된 범위 제외 → 왼쪽(과거)만 fetch
        fetch_start_idx = desired_start
        fetch_end_idx = self._loaded_range.start_idx - 1
        
        # 최소 fetch 크기 보장
        if fetch_end_idx - fetch_start_idx < self.MIN_FETCH_SIZE:
            fetch_start_idx = fetch_end_idx - self.MIN_FETCH_SIZE
        
        # 타임스탬프 계산 (인덱스 → 타임스탬프)
        # 현재 데이터의 평균 간격을 기준으로 추정
        avg_interval = self._estimate_bar_interval()
        
        start_ts = self._loaded_range.start_timestamp - abs(fetch_end_idx - fetch_start_idx) * avg_interval
        end_ts = self._loaded_range.start_timestamp - avg_interval
        
        return fetch_start_idx, fetch_end_idx, int(start_ts), int(end_ts)
    
    def _estimate_bar_interval(self) -> int:
        """
        바 간격 추정 (밀리초)
        
        현재 타임프레임 기준으로 바 간격을 반환합니다.
        """
        tf = self._current_timeframe.lower()
        
        if tf == "1m":
            return 60 * 1000
        elif tf == "5m":
            return 5 * 60 * 1000
        elif tf == "15m":
            return 15 * 60 * 1000
        elif tf == "1h":
            return 60 * 60 * 1000
        elif tf == "1d":
            return 24 * 60 * 60 * 1000
        else:
            # 기본값: 5분
            return 5 * 60 * 1000
    
    def merge_data(self, new_data: List[Dict[str, Any]], prepend: bool = False):
        """
        새 데이터를 기존 캐시에 병합
        
        Args:
            new_data: 새로 로드된 데이터
            prepend: True면 앞쪽(과거), False면 뒤쪽(미래)에 추가
        """
        if not new_data:
            return
        
        if not self._data_cache:
            self.set_initial_data(new_data)
            return
        
        if prepend:
            # 앞쪽(과거)에 추가
            self._data_cache = new_data + self._data_cache
            
            # 범위 업데이트
            if self._loaded_range:
                self._loaded_range.start_idx -= len(new_data)
                new_timestamps = [d.get("time", 0) for d in new_data]
                if new_timestamps:
                    self._loaded_range.start_timestamp = int(min(new_timestamps) * 1000)
            
            logger.debug(f"⬅️ {len(new_data)} bars prepended, new start_idx={self._loaded_range.start_idx}")
        else:
            # 뒤쪽(미래)에 추가
            self._data_cache.extend(new_data)
            
            # 범위 업데이트
            if self._loaded_range:
                self._loaded_range.end_idx += len(new_data)
                new_timestamps = [d.get("time", 0) for d in new_data]
                if new_timestamps:
                    self._loaded_range.end_timestamp = int(max(new_timestamps) * 1000)
            
            logger.debug(f"➡️ {len(new_data)} bars appended, new end_idx={self._loaded_range.end_idx}")
    
    def get_visible_data(
        self, 
        start_idx: int, 
        end_idx: int
    ) -> List[Dict[str, Any]]:
        """
        뷰포트에 표시할 데이터 반환
        
        Args:
            start_idx: 시작 인덱스 (음수 가능 = 과거 방향)
            end_idx: 끝 인덱스
        
        Returns:
            list[dict]: 해당 범위의 데이터
        """
        if not self._data_cache or self._loaded_range is None:
            return []
        
        # 캐시 내 상대 인덱스로 변환
        relative_start = max(0, start_idx - self._loaded_range.start_idx)
        relative_end = min(
            len(self._data_cache),
            end_idx - self._loaded_range.start_idx + 1
        )
        
        if relative_start >= relative_end:
            return []
        
        return self._data_cache[relative_start:relative_end]
    
    def get_cache_stats(self) -> dict:
        """캐시 통계 반환 (디버그용)"""
        return {
            "ticker": self._current_ticker,
            "timeframe": self._current_timeframe,
            "cache_size": len(self._data_cache),
            "loaded_range": {
                "start_idx": self._loaded_range.start_idx if self._loaded_range else None,
                "end_idx": self._loaded_range.end_idx if self._loaded_range else None,
            } if self._loaded_range else None
        }
