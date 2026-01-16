# ============================================================================
# Symbol Mapping Service - Massive ↔ IBKR 티커 매핑
# ============================================================================
# 📌 이 파일의 역할:
#   - Massive.com 티커 ↔ IBKR 티커 간 변환
#   - 일부 종목은 양 데이터 소스에서 다른 심볼을 사용
#   - 예: BRK.A (IBKR) ↔ BRK/A (Massive)
#
# 📖 사용 예시:
#   >>> mapper = SymbolMapper()
#   >>> ibkr_symbol = mapper.MASSIVE_TO_IBKR("BRK/A")
#   >>> print(ibkr_symbol)  # "BRK.A"
# ============================================================================

"""
Symbol Mapping Service

Massive.com와 IBKR 간 티커 심볼 차이를 처리합니다.

주요 차이점:
    - 클래스 주식: Massive는 "/" 사용 (BRK/A), IBKR은 "." 사용 (BRK.A)
    - 특수 문자: 일부 ETF/ETN은 표기가 다름
    - 워런트/유닛: 접미사 표기법 차이
"""

from typing import Optional, Dict
from loguru import logger
import re


# ═══════════════════════════════════════════════════════════════════════════
# 정적 매핑 테이블
# ═══════════════════════════════════════════════════════════════════════════

# Massive → IBKR 수동 매핑 (알려진 불일치 케이스)
# 키: Massive 심볼, 값: IBKR 심볼
MASSIVE_TO_IBKR_MANUAL: Dict[str, str] = {
    # 클래스 주식 예시 (슬래시 → 점)
    # 대부분은 자동 변환으로 처리됨, 예외만 여기에 추가
}

# IBKR → Massive 수동 매핑
IBKR_TO_MASSIVE_MANUAL: Dict[str, str] = {
    # 역방향 매핑
}

# 제외할 심볼 패턴 (거래 불가 또는 데이터 불일치)
EXCLUDED_PATTERNS = [
    r".*\.WS$",  # 워런트 (IBKR에서 별도 처리)
    r".*\.U$",  # 유닛
    r".*\.R$",  # 라이트
    r".*TEST.*",  # 테스트 심볼
]


# ═══════════════════════════════════════════════════════════════════════════
# SymbolMapper 클래스
# ═══════════════════════════════════════════════════════════════════════════


class SymbolMapper:
    """
    Massive.com ↔ IBKR 심볼 매퍼

    티커 심볼 형식 차이를 자동으로 처리합니다.

    주요 기능:
        - MASSIVE_TO_IBKR(): Massive 심볼 → IBKR 심볼
        - IBKR_TO_MASSIVE(): IBKR 심볼 → Massive 심볼
        - is_tradeable(): IBKR에서 거래 가능한 심볼인지 확인

    Example:
        >>> mapper = SymbolMapper()
        >>> mapper.MASSIVE_TO_IBKR("BRK/A")
        'BRK.A'
        >>> mapper.IBKR_TO_MASSIVE("BRK.A")
        'BRK/A'
    """

    def __init__(self):
        """매퍼 초기화"""
        # 제외 패턴 컴파일
        self._excluded_patterns = [re.compile(p) for p in EXCLUDED_PATTERNS]

        # 역방향 매핑 테이블 생성
        self._MASSIVE_TO_IBKR = MASSIVE_TO_IBKR_MANUAL.copy()
        self._IBKR_TO_MASSIVE = IBKR_TO_MASSIVE_MANUAL.copy()

        # MASSIVE_TO_IBKR_MANUAL의 역방향 자동 생성
        for massive_sym, ibkr_sym in MASSIVE_TO_IBKR_MANUAL.items():
            if ibkr_sym not in self._IBKR_TO_MASSIVE:
                self._IBKR_TO_MASSIVE[ibkr_sym] = massive_sym

        logger.debug(
            f"🔄 SymbolMapper 초기화 (수동 매핑: {len(self._MASSIVE_TO_IBKR)}개)"
        )

    # ═══════════════════════════════════════════════════════════════════════
    # 변환 메서드
    # ═══════════════════════════════════════════════════════════════════════

    def MASSIVE_TO_IBKR(self, massive_symbol: str) -> Optional[str]:
        """
        Massive 심볼 → IBKR 심볼 변환

        변환 규칙:
            1. 수동 매핑 테이블 확인
            2. "/" → "." 변환 (클래스 주식)
            3. 대문자 변환
            4. 제외 패턴 체크

        Args:
            massive_symbol: Massive.com 심볼 (예: "BRK/A", "AAPL")

        Returns:
            str: IBKR 심볼, 또는 None (거래 불가 심볼)

        Example:
            >>> mapper.MASSIVE_TO_IBKR("BRK/A")
            'BRK.A'
            >>> mapper.MASSIVE_TO_IBKR("AAPL")
            'AAPL'
        """
        if not massive_symbol:
            return None

        symbol = massive_symbol.upper().strip()

        # 1. 제외 패턴 체크
        if self._is_excluded(symbol):
            return None

        # 2. 수동 매핑 확인
        if symbol in self._MASSIVE_TO_IBKR:
            return self._MASSIVE_TO_IBKR[symbol]

        # 3. 자동 변환: "/" → "." (클래스 주식)
        # 예: BRK/A → BRK.A, GOOG/L → GOOG.L
        ibkr_symbol = symbol.replace("/", ".")

        return ibkr_symbol

    def IBKR_TO_MASSIVE(self, ibkr_symbol: str) -> Optional[str]:
        """
        IBKR 심볼 → Massive 심볼 변환

        Args:
            ibkr_symbol: IBKR 심볼 (예: "BRK.A", "AAPL")

        Returns:
            str: Massive.com 심볼, 또는 None (변환 불가)

        Example:
            >>> mapper.IBKR_TO_MASSIVE("BRK.A")
            'BRK/A'
        """
        if not ibkr_symbol:
            return None

        symbol = ibkr_symbol.upper().strip()

        # 1. 수동 매핑 확인
        if symbol in self._IBKR_TO_MASSIVE:
            return self._IBKR_TO_MASSIVE[symbol]

        # 2. 자동 변환: "." → "/" (클래스 주식)
        # 주의: 일부 "."은 클래스가 아닌 다른 의미일 수 있음
        # 단순 변환만 수행, 복잡한 케이스는 수동 매핑 필요
        massive_symbol = symbol.replace(".", "/")

        return massive_symbol

    def is_tradeable(self, massive_symbol: str) -> bool:
        """
        IBKR에서 거래 가능한 심볼인지 확인

        Args:
            massive_symbol: Massive.com 심볼

        Returns:
            bool: 거래 가능 여부
        """
        return self.MASSIVE_TO_IBKR(massive_symbol) is not None

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
        self, symbols: list[str], direction: str = "MASSIVE_TO_IBKR"
    ) -> Dict[str, Optional[str]]:
        """
        여러 심볼 일괄 변환

        Args:
            symbols: 변환할 심볼 리스트
            direction: "MASSIVE_TO_IBKR" 또는 "IBKR_TO_MASSIVE"

        Returns:
            dict: {원본 심볼: 변환된 심볼 또는 None}

        Example:
            >>> mapper.batch_convert(["AAPL", "BRK/A", "TSLA"])
            {'AAPL': 'AAPL', 'BRK/A': 'BRK.A', 'TSLA': 'TSLA'}
        """
        result = {}
        convert_fn = (
            self.MASSIVE_TO_IBKR
            if direction == "MASSIVE_TO_IBKR"
            else self.IBKR_TO_MASSIVE
        )

        for sym in symbols:
            result[sym] = convert_fn(sym)

        return result


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
        ("AAPL", "MASSIVE_TO_IBKR"),
        ("BRK/A", "MASSIVE_TO_IBKR"),
        ("GOOG", "MASSIVE_TO_IBKR"),
        ("SPY", "MASSIVE_TO_IBKR"),
        ("TEST.WS", "MASSIVE_TO_IBKR"),  # 제외 패턴
        ("BRK.A", "IBKR_TO_MASSIVE"),
    ]

    print("\n" + "=" * 60)
    print("📋 Symbol Mapping Test")
    print("=" * 60)

    for symbol, direction in test_cases:
        if direction == "MASSIVE_TO_IBKR":
            result = mapper.MASSIVE_TO_IBKR(symbol)
            print(f"  Massive→IBKR: {symbol:10} → {result}")
        else:
            result = mapper.IBKR_TO_MASSIVE(symbol)
            print(f"  IBKR→Massive: {symbol:10} → {result}")

    # 배치 변환 테스트
    print("\n" + "-" * 60)
    batch_result = mapper.batch_convert(["AAPL", "BRK/A", "TSLA"])
    print(f"  Batch: {batch_result}")
