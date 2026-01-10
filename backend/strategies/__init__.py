# ============================================================================
# Backend Strategies Package
# ============================================================================
# 이 패키지는 Sigma9의 트레이딩 전략 플러그인들을 저장합니다.
#
# 📌 전략 추가 방법:
#   1. _template.py를 복사하여 새 파일 생성 (예: my_strategy.py)
#   2. StrategyBase를 상속받아 필수 메서드 구현
#   3. GUI에서 전략 선택 → 자동 로드
#
# 📦 포함 전략:
#   - _template.py: 새 전략 개발 템플릿 (복사용)
#   - seismograph/: 메인 전략 패키지 (Step 2.x에서 구현)
#
# 📖 [03-001] 순환 import 방지:
#   - 직접 export 대신 서브모듈에서 명시적으로 import
#   - from backend.strategies.seismograph import SeismographStrategy
# ============================================================================

"""
Sigma9 Strategies Package

트레이딩 전략 플러그인 폴더입니다.
StrategyBase를 상속받은 전략 클래스들이 이 폴더에 위치합니다.

사용법::

    from backend.strategies.seismograph import SeismographStrategy
"""

# [03-001] 순환 import 방지: 직접 import 제거
# 전략은 필요한 곳에서 명시적으로 import하세요:
#   from backend.strategies.seismograph import SeismographStrategy

__all__ = [
    "seismograph",  # 서브패키지
]
