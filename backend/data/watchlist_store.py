# ============================================================================
# Watchlist Persistence - Watchlist 저장/로드 서비스
# ============================================================================
# 📌 이 파일의 역할:
#   - Watchlist를 JSON 파일로 저장/로드
#   - 스캔 결과 히스토리 관리
#   - 재시작 시 마지막 Watchlist 복원
#
# 📖 사용 예시:
#   >>> from backend.data.watchlist_store import WatchlistStore
#   >>> store = WatchlistStore()
#   >>> store.save(watchlist)
#   >>> loaded = store.load()
# ============================================================================

"""
Watchlist Persistence Module

Watchlist 데이터의 JSON 저장/로드 기능을 제공합니다.

주요 기능:
    - save(): Watchlist를 JSON 파일로 저장
    - load(): 저장된 Watchlist 로드
    - get_history(): 과거 Watchlist 히스토리 조회
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from loguru import logger


# ═══════════════════════════════════════════════════════════════════════════
# 기본 설정
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_DATA_DIR = Path("data/watchlist")
CURRENT_WATCHLIST_FILE = "watchlist_current.json"
HISTORY_DIR = "history"


# ═══════════════════════════════════════════════════════════════════════════
# WatchlistStore 클래스
# ═══════════════════════════════════════════════════════════════════════════

class WatchlistStore:
    """
    Watchlist 저장소
    
    Watchlist 데이터를 JSON 파일로 저장하고 로드합니다.
    히스토리 기능으로 과거 Watchlist도 조회 가능합니다.
    
    Attributes:
        data_dir: 데이터 저장 디렉토리
        
    Example:
        >>> store = WatchlistStore()
        >>> store.save(watchlist)
        >>> loaded = store.load()
        >>> print(f"Loaded {len(loaded)} items")
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        저장소 초기화
        
        Args:
            data_dir: 데이터 저장 디렉토리 (기본값: data/watchlist)
        """
        self.data_dir = Path(data_dir) if data_dir else DEFAULT_DATA_DIR
        self.history_dir = self.data_dir / HISTORY_DIR
        
        # 디렉토리 생성
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"📁 WatchlistStore 초기화 (경로: {self.data_dir})")
    
    # ═══════════════════════════════════════════════════════════════════════
    # 저장/로드
    # ═══════════════════════════════════════════════════════════════════════
    
    def save(
        self, 
        watchlist: List[Dict[str, Any]], 
        save_history: bool = True
    ) -> Path:
        """
        Watchlist를 JSON 파일로 저장
        
        Args:
            watchlist: Watchlist 데이터 (list of dict)
            save_history: 히스토리에도 저장할지 여부
        
        Returns:
            Path: 저장된 파일 경로
        
        Example:
            >>> store.save(watchlist)
            PosixPath('data/watchlist/watchlist_current.json')
        """
        timestamp = datetime.now()
        
        # 메타데이터 추가
        data = {
            "version": "1.0",
            "generated_at": timestamp.isoformat(),
            "item_count": len(watchlist),
            "watchlist": watchlist,
        }
        
        # 현재 Watchlist 저장
        current_path = self.data_dir / CURRENT_WATCHLIST_FILE
        with open(current_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Watchlist 저장: {len(watchlist)}개 항목 → {current_path}")
        
        # 히스토리 저장
        if save_history:
            history_filename = f"watchlist_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            history_path = self.history_dir / history_filename
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"📜 히스토리 저장: {history_path}")
        
        return current_path
    
    def load(self) -> List[Dict[str, Any]]:
        """
        저장된 Watchlist 로드
        
        Returns:
            list[dict]: Watchlist 데이터, 파일이 없으면 빈 리스트
        
        Example:
            >>> watchlist = store.load()
            >>> print(f"Loaded {len(watchlist)} items")
        """
        current_path = self.data_dir / CURRENT_WATCHLIST_FILE
        
        if not current_path.exists():
            logger.warning(f"⚠️ Watchlist 파일 없음: {current_path}")
            return []
        
        try:
            with open(current_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            watchlist = data.get("watchlist", [])
            generated_at = data.get("generated_at", "unknown")
            
            logger.info(f"📂 Watchlist 로드: {len(watchlist)}개 항목 (생성: {generated_at})")
            return watchlist
            
        except Exception as e:
            logger.error(f"❌ Watchlist 로드 실패: {e}")
            return []
    
    def load_with_metadata(self) -> Dict[str, Any]:
        """
        메타데이터 포함 Watchlist 로드
        
        Returns:
            dict: 전체 데이터 (version, generated_at, item_count, watchlist)
        """
        current_path = self.data_dir / CURRENT_WATCHLIST_FILE
        
        if not current_path.exists():
            return {"watchlist": [], "item_count": 0}
        
        try:
            with open(current_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Watchlist 로드 실패: {e}")
            return {"watchlist": [], "item_count": 0}
    
    # ═══════════════════════════════════════════════════════════════════════
    # 히스토리
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_history_files(self, limit: int = 10) -> List[Path]:
        """
        히스토리 파일 목록 조회 (최신순)
        
        Args:
            limit: 반환할 최대 개수
        
        Returns:
            list[Path]: 히스토리 파일 경로 리스트
        """
        files = sorted(
            self.history_dir.glob("watchlist_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        return files[:limit]
    
    def load_history(self, filename: str) -> List[Dict[str, Any]]:
        """
        특정 히스토리 파일 로드
        
        Args:
            filename: 히스토리 파일명
        
        Returns:
            list[dict]: Watchlist 데이터
        """
        history_path = self.history_dir / filename
        
        if not history_path.exists():
            logger.warning(f"⚠️ 히스토리 파일 없음: {history_path}")
            return []
        
        try:
            with open(history_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("watchlist", [])
        except Exception as e:
            logger.error(f"❌ 히스토리 로드 실패: {e}")
            return []
    
    def cleanup_history(self, keep_days: int = 7):
        """
        오래된 히스토리 파일 정리
        
        Args:
            keep_days: 보관할 일수
        """
        import time
        
        cutoff = time.time() - (keep_days * 24 * 60 * 60)
        removed = 0
        
        for file_path in self.history_dir.glob("watchlist_*.json"):
            if file_path.stat().st_mtime < cutoff:
                file_path.unlink()
                removed += 1
        
        if removed > 0:
            logger.info(f"🗑️ 히스토리 정리: {removed}개 파일 삭제")
    
    # ═══════════════════════════════════════════════════════════════════════
    # 유틸리티
    # ═══════════════════════════════════════════════════════════════════════
    
    def exists(self) -> bool:
        """현재 Watchlist 파일 존재 여부"""
        return (self.data_dir / CURRENT_WATCHLIST_FILE).exists()
    
    def get_stats(self) -> Dict[str, Any]:
        """저장소 통계 조회"""
        current_path = self.data_dir / CURRENT_WATCHLIST_FILE
        history_files = list(self.history_dir.glob("watchlist_*.json"))
        
        stats = {
            "current_exists": current_path.exists(),
            "history_count": len(history_files),
            "data_dir": str(self.data_dir),
        }
        
        if current_path.exists():
            data = self.load_with_metadata()
            stats["current_item_count"] = data.get("item_count", 0)
            stats["current_generated_at"] = data.get("generated_at")
        
        return stats


# ═══════════════════════════════════════════════════════════════════════════
# 싱글톤 인스턴스
# ═══════════════════════════════════════════════════════════════════════════

_store_instance: Optional[WatchlistStore] = None


def get_watchlist_store() -> WatchlistStore:
    """전역 WatchlistStore 인스턴스 반환"""
    global _store_instance
    if _store_instance is None:
        _store_instance = WatchlistStore()
    return _store_instance


# ═══════════════════════════════════════════════════════════════════════════
# 편의 함수
# ═══════════════════════════════════════════════════════════════════════════

def save_watchlist(watchlist: List[Dict[str, Any]]) -> Path:
    """편의 함수: Watchlist 저장"""
    return get_watchlist_store().save(watchlist)


def load_watchlist() -> List[Dict[str, Any]]:
    """편의 함수: Watchlist 로드"""
    return get_watchlist_store().load()


# ═══════════════════════════════════════════════════════════════════════════
# 테스트
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """독립 실행 테스트"""
    import sys
    import tempfile
    
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")
    
    # 임시 디렉토리에서 테스트
    with tempfile.TemporaryDirectory() as tmpdir:
        store = WatchlistStore(data_dir=Path(tmpdir))
        
        # 테스트 데이터
        test_watchlist = [
            {
                "ticker": "AAPL",
                "score": 80.0,
                "stage": "Stage 4 (Tight Range)",
                "stage_number": 4,
                "signals": {"tight_range": True, "accumulation_bar": False},
                "can_trade": True,
                "last_close": 5.50,
                "avg_volume": 150000,
            },
            {
                "ticker": "TSLA",
                "score": 30.0,
                "stage": "Stage 2 (OBV Divergence)",
                "stage_number": 2,
                "signals": {"obv_divergence": True},
                "can_trade": False,
                "last_close": 8.25,
                "avg_volume": 200000,
            },
        ]
        
        print("\n" + "=" * 60)
        print("📋 Watchlist Persistence Test")
        print("=" * 60)
        
        # 저장
        saved_path = store.save(test_watchlist)
        print(f"\n✅ 저장 완료: {saved_path}")
        
        # 로드
        loaded = store.load()
        print(f"✅ 로드 완료: {len(loaded)}개 항목")
        
        # 통계
        stats = store.get_stats()
        print(f"\n📊 통계:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # 히스토리
        history_files = store.get_history_files()
        print(f"\n📜 히스토리 파일: {len(history_files)}개")
        
        # 검증
        assert len(loaded) == 2
        assert loaded[0]["ticker"] == "AAPL"
        assert loaded[1]["can_trade"] == False
        
        print("\n✅ 모든 테스트 통과!")
