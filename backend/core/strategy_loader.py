# ============================================================================
# Strategy Loader - 전략 플러그인 시스템
# ============================================================================
# 📌 이 파일의 역할:
#   전략 파일을 동적으로 검색, 로드, 리로드하는 플러그인 시스템입니다.
#   서버 재시작 없이 전략을 교체할 수 있습니다 (Hot Reload).
#
# 📌 사용법:
#   loader = StrategyLoader("backend/strategies")
#   strategies = loader.discover_strategies()  # ['seismograph', 'random_walker']
#   strategy = loader.load_strategy("seismograph")
#   strategy.on_tick(...)
#
# 📌 masterplan.md 13.5절 기준 구현
# ============================================================================

"""
Strategy Loader Module

전략 파일을 동적으로 로드하는 플러그인 시스템입니다.
strategies/ 폴더의 .py 파일을 자동으로 탐지하고 로드합니다.

Example:
    >>> from backend.core.strategy_loader import StrategyLoader
    >>> loader = StrategyLoader()
    >>> print(loader.discover_strategies())
    ['seismograph', 'random_walker']
    >>> strategy = loader.load_strategy('seismograph')
    >>> print(strategy.name)
    'Seismograph'
"""

import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════
# StrategyLoader 클래스
# ═══════════════════════════════════════════════════════════════════════════

class StrategyLoader:
    """
    전략 파일을 동적으로 로드하는 플러그인 시스템
    
    ═══════════════════════════════════════════════════════════════════════
    쉬운 설명 (ELI5):
    ═══════════════════════════════════════════════════════════════════════
    게임에서 캐릭터를 바꾸는 것처럼, 트레이딩 전략도 바꿀 수 있어요.
    StrategyLoader는 "전략 캐릭터 선택 화면"과 같습니다.
    
    - discover_strategies(): 선택 가능한 전략 목록 보기
    - load_strategy("seismograph"): 특정 전략 선택
    - reload_strategy("seismograph"): 전략 다시 로드 (코드 수정 후)
    
    ═══════════════════════════════════════════════════════════════════════
    핵심 기능:
    ═══════════════════════════════════════════════════════════════════════
    
    1. **Auto Discovery**: strategies/ 폴더의 모든 전략 파일 자동 탐지
    2. **Dynamic Loading**: importlib로 런타임에 전략 로드
    3. **Hot Reload**: 코드 수정 후 서버 재시작 없이 리로드
    4. **Caching**: 로드된 전략 인스턴스 캐싱
    
    Attributes:
        strategy_dir (Path): 전략 파일이 있는 디렉토리 경로
        strategies (Dict[str, StrategyBase]): 로드된 전략 인스턴스 캐시
    
    Example:
        >>> loader = StrategyLoader("backend/strategies")
        >>> available = loader.discover_strategies()
        >>> print(available)
        ['seismograph', 'random_walker']
        
        >>> strategy = loader.load_strategy("seismograph")
        >>> print(strategy.name)
        'Seismograph'
        
        >>> # 코드 수정 후 핫 리로드
        >>> strategy = loader.reload_strategy("seismograph")
    """
    
    def __init__(self, strategy_dir: Optional[str] = None):
        """
        StrategyLoader 초기화
        
        Args:
            strategy_dir (str, optional): 전략 파일이 있는 디렉토리 경로.
                기본값은 backend/strategies 폴더입니다.
        
        Example:
            >>> loader = StrategyLoader()  # 기본 경로 사용
            >>> loader = StrategyLoader("custom/strategies")  # 커스텀 경로
        """
        # 전략 디렉토리 경로 설정
        # 기본값: 이 파일의 상위 폴더의 strategies 폴더
        if strategy_dir is None:
            # backend/core/strategy_loader.py → backend/strategies
            self.strategy_dir = Path(__file__).parent.parent / "strategies"
        else:
            self.strategy_dir = Path(strategy_dir)
        
        # 로드된 전략 인스턴스 캐시
        # {"seismograph": SeismographStrategy(), "random_walker": RandomWalkerStrategy()}
        self.strategies: Dict = {}
        
        # StrategyBase import를 위해 backend 경로 추가
        backend_path = Path(__file__).parent.parent
        if str(backend_path) not in sys.path:
            sys.path.insert(0, str(backend_path))
        
        print(f"[StrategyLoader] 초기화 완료: {self.strategy_dir}")
    
    def discover_strategies(self) -> List[str]:
        """
        strategies/ 폴더의 모든 전략 파일 탐색
        
        '_'로 시작하는 파일(예: _template.py, __init__.py)은 제외합니다.
        
        ═══════════════════════════════════════════════════════════════
        쉬운 설명:
        ═══════════════════════════════════════════════════════════════
        폴더 안에 어떤 전략 파일들이 있는지 목록을 만드는 거예요.
        "_"로 시작하는 파일은 "숨김 파일"처럼 취급해서 무시합니다.
        
        Returns:
            List[str]: 사용 가능한 전략 이름 목록 (파일명에서 .py 제외)
            
        Example:
            >>> loader = StrategyLoader()
            >>> loader.discover_strategies()
            ['seismograph', 'random_walker']
        """
        # 폴더가 존재하는지 확인
        if not self.strategy_dir.exists():
            print(f"[StrategyLoader] 경고: 디렉토리 없음 - {self.strategy_dir}")
            return []
        
        found = []
        
        # 제외할 파일 패턴
        excluded_suffixes = ("_config.py",)  # 설정 파일 제외
        
        # strategies/ 폴더의 모든 .py 파일 탐색
        for file in self.strategy_dir.glob("*.py"):
            # '_'로 시작하는 파일 제외 (_template.py, __init__.py 등)
            if file.name.startswith("_"):
                continue
            
            # 설정 파일 제외 (*_config.py)
            if file.name.endswith(excluded_suffixes):
                continue
            
            # 파일명에서 확장자 제거
            # 예: "seismograph.py" → "seismograph"
            strategy_name = file.stem
            found.append(strategy_name)
        
        # 알파벳 순으로 정렬
        found.sort()
        
        print(f"[StrategyLoader] 발견된 전략: {found}")
        return found
    
    def load_strategy(self, strategy_name: str):
        """
        특정 전략을 동적으로 로드
        
        ═══════════════════════════════════════════════════════════════
        쉬운 설명:
        ═══════════════════════════════════════════════════════════════
        "seismograph"라고 말하면, seismograph.py 파일을 읽어서
        그 안에 있는 SeismographStrategy 클래스를 찾아서 사용할 수 있게 만들어요.
        
        동작 순서:
        1. 파일 경로 확인 (seismograph.py)
        2. Python이 파일을 읽도록 함 (importlib)
        3. StrategyBase를 상속한 클래스 찾기
        4. 인스턴스 생성 및 초기화
        5. 캐시에 저장
        
        Args:
            strategy_name (str): 로드할 전략 이름 (파일명에서 .py 제외)
        
        Returns:
            StrategyBase: 로드된 전략 인스턴스
        
        Raises:
            FileNotFoundError: 전략 파일이 없을 때
            ValueError: StrategyBase 서브클래스를 찾을 수 없을 때
        
        Example:
            >>> strategy = loader.load_strategy("seismograph")
            >>> print(strategy.name)
            'Seismograph'
        """
        # 이미 로드된 전략이 있으면 캐시에서 반환
        if strategy_name in self.strategies:
            print(f"[StrategyLoader] 캐시에서 로드: {strategy_name}")
            return self.strategies[strategy_name]
        
        # 파일 경로 구성
        filepath = self.strategy_dir / f"{strategy_name}.py"
        
        # 파일 존재 여부 확인
        if not filepath.exists():
            raise FileNotFoundError(
                f"전략 파일을 찾을 수 없습니다: {filepath}\n"
                f"사용 가능한 전략: {self.discover_strategies()}"
            )
        
        print(f"[StrategyLoader] 로드 중: {filepath}")
        
        # ─────────────────────────────────────────────────────────────
        # 동적 모듈 로드 (importlib 사용)
        # ─────────────────────────────────────────────────────────────
        # 
        # 일반적인 import 문 대신 importlib을 사용하는 이유:
        # - 런타임에 파일 경로로 모듈을 로드할 수 있음
        # - 핫 리로드를 위해 모듈을 언로드/재로드할 수 있음
        #
        # spec = 모듈의 "설계도" (어디서 로드할지, 이름이 뭔지 등)
        # module = spec을 기반으로 실제로 만들어진 모듈 객체
        
        spec = importlib.util.spec_from_file_location(strategy_name, filepath)
        if spec is None or spec.loader is None:
            raise ValueError(f"모듈 스펙을 생성할 수 없습니다: {filepath}")
        
        module = importlib.util.module_from_spec(spec)
        
        # sys.modules에 등록 (다른 곳에서 import 가능하게)
        sys.modules[strategy_name] = module
        
        # 모듈 코드 실행 (클래스 정의 등이 실행됨)
        spec.loader.exec_module(module)
        
        # ─────────────────────────────────────────────────────────────
        # StrategyBase 서브클래스 찾기
        # ─────────────────────────────────────────────────────────────
        # 
        # 모듈 안의 모든 이름(클래스, 함수, 변수)을 순회하며
        # StrategyBase를 상속한 클래스를 찾습니다.
        
        from core.strategy_base import StrategyBase
        
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            
            # 클래스인지 확인
            if not isinstance(attr, type):
                continue
            
            # StrategyBase의 서브클래스인지 확인
            # (StrategyBase 자체는 제외)
            if issubclass(attr, StrategyBase) and attr is not StrategyBase:
                print(f"[StrategyLoader] 전략 클래스 발견: {attr_name}")
                
                # 인스턴스 생성
                instance = attr()
                
                # 초기화 메서드 호출
                instance.initialize()
                
                # 캐시에 저장
                self.strategies[strategy_name] = instance
                
                print(f"[StrategyLoader] 로드 완료: {instance.name} v{instance.version}")
                return instance
        
        # StrategyBase 서브클래스를 찾지 못한 경우
        raise ValueError(
            f"StrategyBase 서브클래스를 찾을 수 없습니다: {filepath}\n"
            f"전략 클래스가 StrategyBase를 상속하는지 확인하세요."
        )
    
    def reload_strategy(self, strategy_name: str):
        """
        전략 파일 수정 후 핫 리로드
        
        ═══════════════════════════════════════════════════════════════
        쉬운 설명:
        ═══════════════════════════════════════════════════════════════
        전략 코드를 수정한 후, 서버를 재시작하지 않고
        새 코드를 적용하고 싶을 때 사용합니다.
        
        "게임 패치"처럼, 실행 중에 새 버전을 적용하는 것입니다.
        
        동작 순서:
        1. 기존 인스턴스 삭제 (캐시에서 제거)
        2. sys.modules에서 모듈 제거 (Python 캐시 초기화)
        3. 파일 다시 로드
        
        Args:
            strategy_name (str): 리로드할 전략 이름
        
        Returns:
            StrategyBase: 새로 로드된 전략 인스턴스
        
        Example:
            >>> # seismograph.py 파일 수정 후...
            >>> strategy = loader.reload_strategy("seismograph")
            >>> # 새 코드가 적용됨!
        """
        print(f"[StrategyLoader] 리로드 중: {strategy_name}")
        
        # 1. 캐시에서 기존 인스턴스 제거
        if strategy_name in self.strategies:
            del self.strategies[strategy_name]
            print(f"[StrategyLoader] 기존 인스턴스 제거: {strategy_name}")
        
        # 2. sys.modules에서 모듈 제거
        # 이렇게 해야 Python이 파일을 다시 읽습니다.
        if strategy_name in sys.modules:
            del sys.modules[strategy_name]
            print(f"[StrategyLoader] 모듈 캐시 제거: {strategy_name}")
        
        # 3. 다시 로드
        return self.load_strategy(strategy_name)
    
    def get_strategy(self, strategy_name: str):
        """
        이미 로드된 전략 인스턴스 반환
        
        load_strategy()와 달리, 캐시에 없으면 None을 반환합니다.
        (자동으로 로드하지 않음)
        
        Args:
            strategy_name (str): 전략 이름
        
        Returns:
            Optional[StrategyBase]: 로드된 전략 인스턴스 또는 None
        
        Example:
            >>> strategy = loader.get_strategy("seismograph")
            >>> if strategy is None:
            ...     print("아직 로드되지 않았습니다")
        """
        return self.strategies.get(strategy_name)
    
    def list_loaded(self) -> List[dict]:
        """
        현재 로드된 전략들의 메타정보 목록 반환
        
        Returns:
            List[dict]: 로드된 전략들의 정보 목록
                - name: 전략 이름
                - version: 버전
                - description: 설명
        
        Example:
            >>> loader.load_strategy("seismograph")
            >>> loader.list_loaded()
            [{'name': 'Seismograph', 'version': '2.0.0', 'description': '...'}]
        """
        result = []
        
        for strategy_name, instance in self.strategies.items():
            result.append({
                "strategy_id": strategy_name,  # 파일명 기반 ID
                "name": instance.name,          # 전략 표시 이름
                "version": instance.version,
                "description": instance.description,
            })
        
        return result
    
    def unload_strategy(self, strategy_name: str) -> bool:
        """
        전략 언로드 (메모리에서 제거)
        
        Args:
            strategy_name (str): 언로드할 전략 이름
        
        Returns:
            bool: 언로드 성공 여부
        
        Example:
            >>> loader.unload_strategy("seismograph")
            True
        """
        if strategy_name in self.strategies:
            del self.strategies[strategy_name]
            if strategy_name in sys.modules:
                del sys.modules[strategy_name]
            print(f"[StrategyLoader] 언로드 완료: {strategy_name}")
            return True
        return False
    
    def unload_all(self) -> None:
        """
        모든 전략 언로드
        
        Example:
            >>> loader.unload_all()
        """
        strategy_names = list(self.strategies.keys())
        for name in strategy_names:
            self.unload_strategy(name)
        print("[StrategyLoader] 모든 전략 언로드 완료")


# ═══════════════════════════════════════════════════════════════════════════
# 모듈 레벨 테스트 코드
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("StrategyLoader 테스트")
    print("=" * 60)
    
    # StrategyLoader 인스턴스 생성
    loader = StrategyLoader()
    
    # 1. 사용 가능한 전략 탐색
    print("\n[Test 1] discover_strategies()")
    available = loader.discover_strategies()
    print(f"  발견된 전략: {available}")
    
    # 2. 전략 로드
    if available:
        print(f"\n[Test 2] load_strategy('{available[0]}')")
        try:
            strategy = loader.load_strategy(available[0])
            print(f"  로드 성공: {strategy.name} v{strategy.version}")
            print(f"  설명: {strategy.description}")
        except Exception as e:
            print(f"  로드 실패: {e}")
    
    # 3. 로드된 전략 목록
    print("\n[Test 3] list_loaded()")
    loaded = loader.list_loaded()
    for info in loaded:
        print(f"  - {info['name']} v{info['version']}")
    
    # 4. 캐시에서 가져오기
    if available:
        print(f"\n[Test 4] get_strategy('{available[0]}')")
        cached = loader.get_strategy(available[0])
        print(f"  캐시 히트: {cached is not None}")
    
    # 5. 리로드 테스트
    if available:
        print(f"\n[Test 5] reload_strategy('{available[0]}')")
        try:
            reloaded = loader.reload_strategy(available[0])
            print(f"  리로드 성공: {reloaded.name}")
        except Exception as e:
            print(f"  리로드 실패: {e}")
    
    # 6. 없는 전략 로드 시도
    print("\n[Test 6] load_strategy('nonexistent')")
    try:
        loader.load_strategy("nonexistent")
    except FileNotFoundError as e:
        print(f"  예상된 에러 발생: FileNotFoundError")
    
    print("\n" + "=" * 60)
    print("모든 테스트 완료! ✓")
    print("=" * 60)
