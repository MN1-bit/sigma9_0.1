# 📅 Step 1.2: Mock Data & Strategy Interface - 개발 계획서

> **작성일**: 2024-12-18  
> **목표**: 전략 인터페이스(ABC)를 정의하고, 로컬 테스트용 Mock 데이터를 생성한다.

---

## 1. 개요 (Overview)

이 스텝은 Sigma9 전략 시스템의 **추상 인터페이스**와 **테스트용 Mock 데이터**를 구축하는 단계이다.

**왜 필요한가?**
- `StrategyBase` ABC가 정의되어야 모든 전략이 일관된 인터페이스를 따름
- Mock 데이터가 있어야 IBKR 연결 없이 로컬에서 전략 로직 테스트 가능
- `Signal` 데이터 클래스로 전략 ↔ 엔진 간 통신 표준화

**의존성**: Step 1.1 (프로젝트 구조 완료) ✅

---

## 2. 상세 구현 계획 (Implementation Details)

### Backend Core

---

#### [NEW] [strategy_base.py](file:///d:/Codes/Sigma9-0.1/backend/core/strategy_base.py)

`masterplan.md` 13.3절 기준 구현:

**Signal 데이터 클래스**:
```python
@dataclass
class Signal:
    action: str        # "BUY" | "SELL" | "HOLD"
    ticker: str        # 종목 코드
    confidence: float  # 신뢰도 (0.0 ~ 1.0)
    reason: str        # 사람이 읽을 수 있는 이유 설명
    metadata: dict     # 추가 정보 (가격, 거래량 등)
```

**StrategyBase ABC**:
| Layer | Method | Return Type |
|-------|--------|-------------|
| Scanning | `get_universe_filter()` | `dict` |
| Scanning | `calculate_watchlist_score(ticker, daily_data)` | `float` (0~100) |
| Scanning | `calculate_trigger_score(ticker, tick_data, bar_data)` | `float` (0~100) |
| Scanning | `get_anti_trap_filter()` | `dict` |
| Trading | `initialize()` | `None` |
| Trading | `on_tick(ticker, price, volume, timestamp)` | `Optional[Signal]` |
| Trading | `on_bar(ticker, ohlcv)` | `Optional[Signal]` |
| Trading | `on_order_filled(order)` | `None` |
| Config | `get_config()` | `dict` |
| Config | `set_config(config)` | `None` |

**클래스 속성**: `name`, `version`, `description` (필수)

---

#### [NEW] [mock_data.py](file:///d:/Codes/Sigma9-0.1/backend/core/mock_data.py)

IBKR 없이 로컬 테스트를 위한 Mock 가격 데이터 생성기:

**MockPriceFeed 클래스**:
```python
class MockPriceFeed:
    def __init__(self, mode: str = "random_walk"):
        """mode: 'random_walk' | 'sine_wave' | 'spike'"""
        
    def generate_tick(self) -> dict:
        """단일 틱 데이터 생성"""
        
    def generate_ohlcv(self, periods: int = 100) -> list[dict]:
        """OHLCV 분봉 데이터 생성"""
        
    def subscribe(self, callback: Callable, interval_ms: int = 100):
        """실시간 스트리밍 시뮬레이션 (asyncio)"""
```

**지원 모드**:
| Mode | 설명 | 용도 |
|------|------|------|
| `random_walk` | 랜덤 워크 (브라운 운동) | 일반 시장 시뮬레이션 |
| `sine_wave` | 사인파 | 예측 가능한 패턴 테스트 |
| `spike` | 갑작스런 급등 | Ignition 감지 테스트 |

---

### Backend Strategies

---

#### [NEW] [random_walker.py](file:///d:/Codes/Sigma9-0.1/backend/strategies/random_walker.py)

`StrategyBase` 인터페이스 테스트용 더미 전략:

```python
class RandomWalkerStrategy(StrategyBase):
    """
    RandomWalker - 테스트용 더미 전략
    
    무작위로 BUY/SELL 신호 생성.
    실제 거래용 아님, 인터페이스 테스트 전용.
    """
    name = "Random Walker"
    version = "1.0.0"
    description = "테스트용 무작위 신호 생성 전략"
```

- `on_tick()`: 5% 확률로 랜덤 BUY/SELL 신호 반환
- 모든 `abstractmethod` 구현 (기본값 반환)

---

#### [MODIFY] [_template.py](file:///d:/Codes/Sigma9-0.1/backend/strategies/_template.py)

- 주석 해제하여 실제 작동하는 템플릿으로 변환
- `StrategyBase` import 경로 수정

---

### Tests

---

#### [NEW] [test_strategies.py](file:///d:/Codes/Sigma9-0.1/tests/test_strategies.py)

전략 인터페이스 검증 테스트:

```python
class TestStrategyBase:
    """StrategyBase ABC 테스트"""
    
    def test_signal_dataclass(self):
        """Signal 데이터 클래스 생성 테스트"""
        
    def test_strategy_must_implement_abstract_methods(self):
        """ABC 미구현 시 에러 발생 확인"""

class TestRandomWalker:
    """RandomWalker 전략 테스트"""
    
    def test_inherits_strategy_base(self):
        """StrategyBase 상속 확인"""
        
    def test_on_tick_returns_signal_or_none(self):
        """on_tick() 반환값 타입 검증"""
        
    def test_config_get_set(self):
        """설정값 조회/변경 테스트"""

class TestMockPriceFeed:
    """Mock 데이터 생성기 테스트"""
    
    def test_generate_tick(self):
        """틱 데이터 생성 테스트"""
        
    def test_generate_ohlcv(self):
        """OHLCV 데이터 생성 테스트"""
```

---

### Package Updates

---

#### [MODIFY] [backend/core/__init__.py](file:///d:/Codes/Sigma9-0.1/backend/core/__init__.py)

```diff
- # Step 1.2에서 추가 예정
- # "StrategyBase",
- # "Signal",
+ from .strategy_base import StrategyBase, Signal
+ from .mock_data import MockPriceFeed

__all__ = [
+   "StrategyBase",
+   "Signal",
+   "MockPriceFeed",
]
```

---

## 3. 검증 계획 (Verification Plan)

### Automated Tests

**실행 환경**: 프로젝트 루트 디렉토리 (`d:\Codes\Sigma9-0.1`)

```powershell
# 1. Python 문법 검사 - 모든 새 파일
python -m py_compile backend/core/strategy_base.py
python -m py_compile backend/core/mock_data.py
python -m py_compile backend/strategies/random_walker.py

# 2. 단위 테스트 실행
python -m pytest tests/test_strategies.py -v

# 3. Import 검증 (에러 없이 import 가능해야 함)
python -c "from backend.core import StrategyBase, Signal, MockPriceFeed"
python -c "from backend.strategies.random_walker import RandomWalkerStrategy"
```

### Manual Verification

1. **ABC 강제 확인**: `StrategyBase`를 상속하고 `abstractmethod`를 구현하지 않은 클래스 인스턴스화 시도 → `TypeError` 발생 확인
2. **Mock 데이터 시각 확인**: `MockPriceFeed.generate_ohlcv()` 결과 출력하여 OHLCV 형식 확인

---

## 4. 예상 난관 (Risks)

| 난관 | 대비책 |
|------|--------|
| ABC 메서드 시그니처 불일치 | `masterplan.md` 13.3절 정확히 따르기 |
| Type Hint 호환성 | Python 3.10+ 문법 사용 (`list[dict]` 등) |
| Circular Import | `TYPE_CHECKING` 블록 활용 |

---

## 5. 실행 순서 (Execution Order)

1. `backend/core/strategy_base.py` 생성 (Signal + StrategyBase)
2. `backend/core/mock_data.py` 생성 (MockPriceFeed)
3. `backend/core/__init__.py` 수정 (export 추가)
4. `backend/strategies/random_walker.py` 생성
5. `backend/strategies/_template.py` 주석 해제
6. `tests/test_strategies.py` 생성
7. 검증 테스트 실행
8. devlog 작성 (`docs/devlog/step_1.2_report.md`)

---

## 6. 참조 문서

- [masterplan.md 13절](file:///d:/Codes/Sigma9-0.1/docs/Plan/masterplan.md) - Modular Strategy Architecture
- [@PROJECT_DNA.md](file:///d:/Codes/Sigma9-0.1/@PROJECT_DNA.md) - 코딩 표준 (한글 주석 ELI5)
