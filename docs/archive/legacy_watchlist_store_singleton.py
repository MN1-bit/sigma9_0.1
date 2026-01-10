# ============================================================================
# [ARCHIVED] Legacy Singleton Pattern Code
# ============================================================================
# 📌 아카이브 일자: 2026-01-10
# 📌 원본 파일: backend/data/watchlist_store.py
# 📌 관련 계획서: docs/Plan/refactor/02-006_singleton_cleanup.md
#
# 📖 제거 이유:
#   - DI Container(container.watchlist_store())로 마이그레이션 완료
#   - 레거시 싱글톤 패턴 금지 정책 (@PROJECT_DNA.md)
# ============================================================================

from typing import Optional, List, Dict, Any
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════
# [ARCHIVED] 싱글톤 인스턴스 - watchlist_store.py L384-410
# ═══════════════════════════════════════════════════════════════════════════

_store_instance: Optional["WatchlistStore"] = None


def get_watchlist_store() -> "WatchlistStore":
    """
    전역 WatchlistStore 인스턴스 반환

    ⚠️ Deprecated: Container 사용 권장
    >>> from backend.container import container
    >>> store = container.watchlist_store()
    """
    import warnings

    warnings.warn(
        "get_watchlist_store()는 deprecated입니다. "
        "container.watchlist_store() 사용을 권장합니다.",
        DeprecationWarning,
        stacklevel=2,
    )
    global _store_instance
    if _store_instance is None:
        from backend.data.watchlist_store import WatchlistStore
        _store_instance = WatchlistStore()
    return _store_instance


# ═══════════════════════════════════════════════════════════════════════════
# [ARCHIVED] 편의 함수 - watchlist_store.py L413-478
# ═══════════════════════════════════════════════════════════════════════════


def save_watchlist(watchlist: List[Dict[str, Any]]) -> Path:
    """편의 함수: Watchlist 저장"""
    return get_watchlist_store().save(watchlist)


def load_watchlist() -> List[Dict[str, Any]]:
    """편의 함수: Watchlist 로드"""
    return get_watchlist_store().load()


def merge_watchlist(
    new_items: List[Dict[str, Any]], update_existing: bool = True
) -> List[Dict[str, Any]]:
    """
    [Issue 6.2 Fix] 기존 Watchlist와 새 항목 병합

    새 항목을 기존 Watchlist에 추가하되, 중복은 건너뛰거나 업데이트합니다.
    덮어쓰기 대신 병합을 사용하여 깜빡임 문제를 해결합니다.

    Args:
        new_items: 추가할 새로운 Watchlist 항목들
        update_existing: True면 기존 항목을 새 데이터로 업데이트, False면 건너뛰기

    Returns:
        병합된 전체 Watchlist
    """
    from loguru import logger

    store = get_watchlist_store()
    current = store.load()

    # 기존 티커 맵 생성
    existing_map = {item.get("ticker"): i for i, item in enumerate(current)}

    added = 0
    updated = 0

    for new_item in new_items:
        ticker = new_item.get("ticker")
        if not ticker:
            continue

        if ticker in existing_map:
            # 기존 항목 존재 - 업데이트할지 결정
            if update_existing:
                idx = existing_map[ticker]
                # 기존 필드 유지하면서 새 필드로 업데이트
                current[idx].update(new_item)
                updated += 1
        else:
            # 새 항목 추가
            current.append(new_item)
            existing_map[ticker] = len(current) - 1
            added += 1

    # 변경이 있으면 저장
    if added > 0 or updated > 0:
        store.save(current, save_history=False)  # 히스토리는 저장 안함 (빈번한 병합)
        logger.info(
            f"📋 Watchlist 병합 완료: +{added} 추가, ~{updated} 업데이트 (총 {len(current)}개)"
        )

    return current
