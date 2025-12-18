# ============================================================================
# Symbol Mapping Service - Polygon ↔ IBKR 티커 매핑
# ============================================================================
# 📌 이 파일의 역할:
#   - Polygon.io 티커 ↔ IBKR 티커 간 변환
#   - 일부 종목은 양 데이터 소스에서 다른 심볼을 사용
#   - 예: BRK.A (IBKR) ↔ BRK/A (Polygon)
#
# 📖 사용 예시:
#   >>> mapper = SymbolMapper()
#   >>> ibkr_symbol = mapper.polygon_to_ibkr("BRK/A")
#   >>> print(ibkr_symbol)  # "BRK.A"
# ============================================================================

"""
Symbol Mapping Service

Polygon.io와 IBKR 간 티커 심볼 차이를 처리합니다.

주요 차이점:
    - 클래스 주식: Polygon은 "/" 사용 (BRK/A), IBKR은 "." 사용 (BRK.A)
    - 특수 문자: 일부 ETF/ETN은 표기가 다름
    - 워런트/유닛: 접미사 표기법 차이
"""

from typing import Optional, Dict
from loguru import logger
import re


# ═══════════════════════════════════════════════════════════════════════════
# 정적 매핑 테이블
# ═══════════════════════════════════════════════════════════════════════════

# Polygon → IBKR 수동 매핑 (알려진 불일치 케이스)
# 키: Polygon 심볼, 값: IBKR 심볼
POLYGON_TO_IBKR_MANUAL: Dict[str, str] = {
    # 클래스 주식 예시 (슬래시 → 점)
    # 대부분은 자동 변환으로 처리됨, 예외만 여기에 추가
}

# IBKR → Polygon 수동 매핑
IBKR_TO_POLYGON_MANUAL: Dict[str, str] = {
    # 역방향 매핑
}

# 제외할 심볼 패턴 (거래 불가 또는 데이터 불일치)
EXCLUDED_PATTERNS = [
    r".*\.WS$",   # 워런트 (IBKR에서 별도 처리)
    r".*\.U$",    # 유닛
    r".*\.R$",    # 라이트
    r".*TEST.*",  # 테스트 심볼
]


# ═══════════════════════════════════════════════════════════════════════════
# SymbolMapper 클래스
# ═══════════════════════════════════════════════════════════════════════════

class SymbolMapper:
    """
    Polygon.io ↔ IBKR 심볼 매퍼
    
    티커 심볼 형식 차이를 자동으로 처리합니다.
    
    주요 기능:
        - polygon_to_ibkr(): Polygon 심볼 → IBKR 심볼
        - ibkr_to_polygon(): IBKR 심볼 → Polygon 심볼
        - is_tradeable(): IBKR에서 거래 가능한 심볼인지 확인
    
    Example:
        >>> mapper = SymbolMapper()
        >>> mapper.polygon_to_ibkr("BRK/A")
        'BRK.A'
        >>> mapper.ibkr_to_polygon("BRK.A")
        'BRK/A'
    """
    
    def __init__(self):
        """매퍼 초기화"""
        # 제외 패턴 컴파일
        self._excluded_patterns = [re.compile(p) for p in EXCLUDED_PATTERNS]
        
        # 역방향 매핑 테이블 생성
        self._polygon_to_ibkr = POLYGON_TO_IBKR_MANUAL.copy()
        self._ibkr_to_polygon = IBKR_TO_POLYGON_MANUAL.copy()
        
        # POLYGON_TO_IBKR_MANUAL의 역방향 자동 생성
        for polygon_sym, ibkr_sym in POLYGON_TO_IBKR_MANUAL.items():
            if ibkr_sym not in self._ibkr_to_polygon:
                self._ibkr_to_polygon[ibkr_sym] = polygon_sym
        
        logger.debug(f"🔄 SymbolMapper 초기화 (수동 매핑: {len(self._polygon_to_ibkr)}개)")
    
    # ═══════════════════════════════════════════════════════════════════════
    # 변환 메서드
    # ═══════════════════════════════════════════════════════════════════════
    
    def polygon_to_ibkr(self, polygon_symbol: str) -> Optional[str]:
        """
        Polygon 심볼 → IBKR 심볼 변환
        
        변환 규칙:
            1. 수동 매핑 테이블 확인
            2. "/" → "." 변환 (클래스 주식)
            3. 대문자 변환
            4. 제외 패턴 체크
        
        Args:
            polygon_symbol: Polygon.io 심볼 (예: "BRK/A", "AAPL")
        
        Returns:
            str: IBKR 심볼, 또는 None (거래 불가 심볼)
        
        Example:
            >>> mapper.polygon_to_ibkr("BRK/A")
            'BRK.A'
            >>> mapper.polygon_to_ibkr("AAPL")
            'AAPL'
        """
        if not polygon_symbol:
            return None
        
        symbol = polygon_symbol.upper().strip()
        
        # 1. 제외 패턴 체크
        if self._is_excluded(symbol):
            return None
        
        # 2. 수동 매핑 확인
        if symbol in self._polygon_to_ibkr:
            return self._polygon_to_ibkr[symbol]
        
        # 3. 자동 변환: "/" → "." (클래스 주식)
        # 예: BRK/A → BRK.A, GOOG/L → GOOG.L
        ibkr_symbol = symbol.replace("/", ".")
        
        return ibkr_symbol
    
    def ibkr_to_polygon(self, ibkr_symbol: str) -> Optional[str]:
        """
        IBKR 심볼 → Polygon 심볼 변환
        
        Args:
            ibkr_symbol: IBKR 심볼 (예: "BRK.A", "AAPL")
        
        Returns:
            str: Polygon.io 심볼, 또는 None (변환 불가)
        
        Example:
            >>> mapper.ibkr_to_polygon("BRK.A")
            'BRK/A'
        """
        if not ibkr_symbol:
            return None
        
        symbol = ibkr_symbol.upper().strip()
        
        # 1. 수동 매핑 확인
        if symbol in self._ibkr_to_polygon:
            return self._ibkr_to_polygon[symbol]
        
        # 2. 자동 변환: "." → "/" (클래스 주식)
        # 주의: 일부 "."은 클래스가 아닌 다른 의미일 수 있음
        # 단순 변환만 수행, 복잡한 케이스는 수동 매핑 필요
        polygon_symbol = symbol.replace(".", "/")
        
        return polygon_symbol
    
    def is_tradeable(self, polygon_symbol: str) -> bool:
        """
        IBKR에서 거래 가능한 심볼인지 확인
        
        Args:
            polygon_symbol: Polygon.io 심볼
        
        Returns:
            bool: 거래 가능 여부
        """
        return self.polygon_to_ibkr(polygon_symbol) is not None
    
    # ═══════════════════════════════════════════════════════════════════════
    # 유틸리티
    # ═══════════════════════════════════════════════════════════════════════
    
    def _is_excluded(self, symbol: str) -> bool:
        """제외 패턴에 해당하는지 확인"""
        for pattern in self._excluded_patterns:
            if pattern.match(symbol):
                return True
        return False
    
    def batch_convert(
        self, 
        symbols: list[str], 
        direction: str = "polygon_to_ibkr"
    ) -> Dict[str, Optional[str]]:
        """
        여러 심볼 일괄 변환
        
        Args:
            symbols: 변환할 심볼 리스트
            direction: "polygon_to_ibkr" 또는 "ibkr_to_polygon"
        
        Returns:
            dict: {원본 심볼: 변환된 심볼 또는 None}
        
        Example:
            >>> mapper.batch_convert(["AAPL", "BRK/A", "TSLA"])
            {'AAPL': 'AAPL', 'BRK/A': 'BRK.A', 'TSLA': 'TSLA'}
        """
        result = {}
        convert_fn = (
            self.polygon_to_ibkr if direction == "polygon_to_ibkr" 
            else self.ibkr_to_polygon
        )
        
        for sym in symbols:
            result[sym] = convert_fn(sym)
        
        return result


# ═══════════════════════════════════════════════════════════════════════════
# 싱글톤 인스턴스 (편의 함수용)
# ═══════════════════════════════════════════════════════════════════════════

_mapper_instance: Optional[SymbolMapper] = None


def get_symbol_mapper() -> SymbolMapper:
    """전역 SymbolMapper 인스턴스 반환"""
    global _mapper_instance
    if _mapper_instance is None:
        _mapper_instance = SymbolMapper()
    return _mapper_instance


def polygon_to_ibkr(symbol: str) -> Optional[str]:
    """편의 함수: Polygon → IBKR 변환"""
    return get_symbol_mapper().polygon_to_ibkr(symbol)


def ibkr_to_polygon(symbol: str) -> Optional[str]:
    """편의 함수: IBKR → Polygon 변환"""
    return get_symbol_mapper().ibkr_to_polygon(symbol)


# ═══════════════════════════════════════════════════════════════════════════
# 테스트
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """독립 실행 테스트"""
    import sys
    
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")
    
    mapper = SymbolMapper()
    
    # 테스트 케이스
    test_cases = [
        ("AAPL", "polygon_to_ibkr"),
        ("BRK/A", "polygon_to_ibkr"),
        ("GOOG", "polygon_to_ibkr"),
        ("SPY", "polygon_to_ibkr"),
        ("TEST.WS", "polygon_to_ibkr"),  # 제외 패턴
        ("BRK.A", "ibkr_to_polygon"),
    ]
    
    print("\n" + "=" * 60)
    print("📋 Symbol Mapping Test")
    print("=" * 60)
    
    for symbol, direction in test_cases:
        if direction == "polygon_to_ibkr":
            result = mapper.polygon_to_ibkr(symbol)
            print(f"  Polygon→IBKR: {symbol:10} → {result}")
        else:
            result = mapper.ibkr_to_polygon(symbol)
            print(f"  IBKR→Polygon: {symbol:10} → {result}")
    
    # 배치 변환 테스트
    print("\n" + "-" * 60)
    batch_result = mapper.batch_convert(["AAPL", "BRK/A", "TSLA"])
    print(f"  Batch: {batch_result}")
