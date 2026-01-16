# ============================================================================
# [ARCHIVED] Legacy Singleton Pattern Code
# ============================================================================
# 📌 아카이브 일자: 2026-01-10
# 📌 원본 파일: backend/data/symbol_mapper.py
# 📌 관련 계획서: docs/Plan/refactor/02-006_singleton_cleanup.md
#
# 📖 제거 이유:
#   - DI Container(container.symbol_mapper())로 마이그레이션 완료
#   - 레거시 싱글톤 패턴 금지 정책 (@PROJECT_DNA.md)
# ============================================================================

from typing import Optional


# ═══════════════════════════════════════════════════════════════════════════
# [ARCHIVED] 싱글톤 인스턴스 - symbol_mapper.py L226-262
# ═══════════════════════════════════════════════════════════════════════════

_mapper_instance: Optional["SymbolMapper"] = None


def get_symbol_mapper() -> "SymbolMapper":
    """
    전역 SymbolMapper 인스턴스 반환

    ⚠️ Deprecated: Container 사용 권장
    >>> from backend.container import container
    >>> mapper = container.symbol_mapper()
    """
    import warnings

    warnings.warn(
        "get_symbol_mapper()는 deprecated입니다. "
        "container.symbol_mapper() 사용을 권장합니다.",
        DeprecationWarning,
        stacklevel=2,
    )
    global _mapper_instance
    if _mapper_instance is None:
        from backend.data.symbol_mapper import SymbolMapper
        _mapper_instance = SymbolMapper()
    return _mapper_instance


def MASSIVE_TO_IBKR(symbol: str) -> Optional[str]:
    """편의 함수: Massive → IBKR 변환"""
    return get_symbol_mapper().MASSIVE_TO_IBKR(symbol)


def IBKR_TO_MASSIVE(symbol: str) -> Optional[str]:
    """편의 함수: IBKR → Massive 변환"""
    return get_symbol_mapper().IBKR_TO_MASSIVE(symbol)
