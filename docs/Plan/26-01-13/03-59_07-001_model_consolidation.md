# 07-001: 데이터 모델 통합 리팩터링 계획서

> **작성일**: 2026-01-08 01:56  
> **수정일**: 2026-01-08 02:03  
> **우선순위**: 7 | **예상 소요**: 2-3h | **위험도**: 중간

## 1. 목표

현재 **14개 이상의 파일**에 분산된 `@dataclass` 모델들을 `backend/models/` 디렉터리로 중앙화
→ 모델 재사용성 향상, 중복 정의 제거, 임포트 경로 단순화

> [!IMPORTANT]
> **범위 제외 (확정)**:
> - `config_loader.py` - 설정 로딩 로직과 밀접하게 결합
> - `score_v3_config.py` - Seismograph 전략 전용 설정

### 기대 효과
- 모델 정의 위치 명확화 (단일 진입점)
- 순환 의존성 위험 감소
- 타입 힌트 일관성 확보
- 코드 재사용성 향상

---

## 2. 영향 분석

### 2.1 현재 모델 분포 (10+ 파일)

| 현재 위치 | 포함된 모델 | dataclass 수 |
|----------|-------------|-------------|
| `strategies/seismograph/models.py` | TickData, WatchlistItem | 2 |
| `strategies/score_v3_config.py` | ScoreV3Config 관련 8개 | 8 |
| `core/config_loader.py` | ServerConfig, 각종 설정 | 18 |
| `core/risk_manager.py` | Position | 1 |
| `core/risk_config.py` | RiskConfig | 1 |
| `core/order_manager.py` | OrderRequest, OrderResult | 2 |
| `core/backtest_engine.py` | BacktestConfig | 1 |
| `core/backtest_report.py` | TradeRecord, BacktestResult | 2 |
| `core/zscore_calculator.py` | ZScoreData, ZScoreResult | 2 |
| `core/technical_analysis.py` | OHLCData, TechnicalSignals | 2 |
| `core/trailing_stop.py` | TrailingStopState | 1 |
| `core/strategy_base.py` | StrategyBase 관련 | 1 |
| `core/double_tap.py` | DoubleTapConfig | 1 |
| `core/divergence_detector.py` | DivergenceResult | 1 |
| `core/mock_data.py` | MockCandle | 1 |
| **합계** | | **~44개** |

### 2.2 영향받는 모듈

- **직접 영향**: 모델을 import하는 모든 파일
- **주요 영향 파일**:
  - `realtime_scanner.py` (TickData, WatchlistItem)
  - `routes/*.py` (다양한 모델)
  - `seismograph/strategy.py` (TickData, WatchlistItem)
  - `backtest_*.py` (BacktestConfig, TradeRecord)

### 2.3 순환 의존성 위험

> [!WARNING]
> `config_loader.py`의 설정 모델을 분리할 경우 순환 import 위험 존재.
> **ServerConfig → 타 모델 참조 → ServerConfig** 형태의 순환 가능성 분석 필요.

### 2.4 위험도 평가: **중간**

- 모델 이동은 단순하나 임포트 경로 업데이트가 광범위함
- 하위 호환성 유지를 위한 re-export 필요
- 테스트 범위 확인 필수

---

## 3. 실행 계획

### 전략: 점진적 마이그레이션

> **Phase 1**: 공용 도메인 모델만 이동 (TickData, WatchlistItem, Position 등)
> **Phase 2**: 설정 모델은 `config_loader.py`에 유지 (안정성 우선)

---

### Step 1: backend/models/ 디렉터리 생성

```
backend/models/
├── __init__.py          # 공용 모델 re-export
├── tick.py              # TickData, TickBuffer
├── watchlist.py         # WatchlistItem, WatchlistState
├── order.py             # OrderRequest, OrderResult
├── risk.py              # Position, RiskConfig
├── backtest.py          # BacktestConfig, BacktestResult, TradeRecord
├── technical.py         # OHLCData, TechnicalSignals, ZScoreData
└── common.py            # 공용 타입 (Optional, List 등)
```

### Step 2: 도메인 모델 추출

#### 2a. `tick.py` 생성
- `seismograph/models.py` → `TickData` 이동

#### 2b. `watchlist.py` 생성
- `seismograph/models.py` → `WatchlistItem` 이동

#### 2c. `order.py` 생성
- `order_manager.py` → `OrderRequest`, `OrderResult` 이동

#### 2d. `risk.py` 생성
- `risk_config.py` → `RiskConfig` 이동
- `risk_manager.py` → `Position` 이동

#### 2e. `backtest.py` 생성
- `backtest_engine.py` → `BacktestConfig` 이동
- `backtest_report.py` → `TradeRecord`, `BacktestResult` 이동

#### 2f. `technical.py` 생성
- `technical_analysis.py` → `OHLCData`, `TechnicalSignals` 이동
- `zscore_calculator.py` → `ZScoreData`, `ZScoreResult` 이동

### Step 3: 기존 import문 직접 수정

> [!NOTE]
> re-export 없이 직접 import 경로를 새 위치로 변경합니다.

모든 import문을 아래와 같이 변경:
```python
# Before
from backend.strategies.seismograph.models import TickData, WatchlistItem

# After
from backend.models import TickData, WatchlistItem
```

### Step 4: backend/models/__init__.py 설정

```python
# 공용 모델 export
from .tick import TickData
from .watchlist import WatchlistItem
from .order import OrderRequest, OrderResult
from .risk import RiskConfig, Position
from .backtest import BacktestConfig, BacktestResult, TradeRecord
from .technical import OHLCData, TechnicalSignals, ZScoreData, ZScoreResult

__all__ = [
    "TickData", "WatchlistItem",
    "OrderRequest", "OrderResult",
    "RiskConfig", "Position",
    "BacktestConfig", "BacktestResult", "TradeRecord",
    "OHLCData", "TechnicalSignals", "ZScoreData", "ZScoreResult",
]
```

### Step 5: 원본 파일 정리

모델 이동 후 원본 파일에서 해당 dataclass 정의 삭제:
- `seismograph/models.py` → TickData, WatchlistItem 삭제
- `order_manager.py` → OrderRequest, OrderResult 삭제
- `risk_config.py` → 파일 삭제 (내용 전체 이동)
- `risk_manager.py` → Position 삭제
- 기타 파일들 동일하게 처리

### Step 6: 제외 항목 (변경 안 함)

> **확정 제외**: 
| 파일 | 이유 |
|------|------|
| `config_loader.py` (18개 모델) | 설정 로딩 로직과 밀접하게 결합, 순환 import 위험 |
| `score_v3_config.py` (8개 모델) | Seismograph 전략 전용 설정, 분리 불필요 |

---
## 4. 검증 계획

### 자동화 테스트

- [ ] `ruff check .` 통과
- [ ] `lint-imports` 통과
- [ ] `pydeps backend --show-cycles --no-output` 순환 없음
- [ ] `python -m backend` 서버 정상 시작
- [ ] 기존 import 문 호환성 검증:
  ```bash
  python -c "from backend.strategies.seismograph.models import TickData, WatchlistItem"
  python -c "from backend.models import TickData, WatchlistItem"
  ```

### 수동 검증

- [ ] Dashboard GUI 정상 동작
- [ ] API 엔드포인트 응답 정상

---

## 5. 롤백 계획

```bash
# 변경 취소
git checkout HEAD -- backend/models/
git checkout HEAD -- backend/strategies/seismograph/models.py
git checkout HEAD -- backend/core/order_manager.py
git checkout HEAD -- backend/core/risk_*.py
git checkout HEAD -- backend/core/backtest_*.py
git checkout HEAD -- backend/core/technical_analysis.py
git checkout HEAD -- backend/core/zscore_calculator.py

# 생성된 디렉터리 삭제
rm -rf backend/models/
```

---

## 6. 범위 제외 사항 (Out of Scope)

| 항목 | 이유 |
|------|------|
| `config_loader.py` 모델들 | 설정 로딩 로직과 결합도 높음 |
| `score_v3_config.py` 모델들 | Seismograph 전략 전용, 분리 불필요 |
| API routes 내 Pydantic 모델 | 이미 `routes/models.py`에 통합됨 |
| GUI dataclass (Tier2Item 등) | Frontend 전용 |

---

## 7. 예상 결과

### Before
```
backend/
├── core/
│   ├── order_manager.py      # OrderRequest, OrderResult 포함
│   ├── risk_config.py        # RiskConfig 포함
│   ├── risk_manager.py       # Position 포함
│   ├── backtest_engine.py    # BacktestConfig 포함
│   └── ...
└── strategies/
    └── seismograph/
        └── models.py         # TickData, WatchlistItem
```

### After
```
backend/
├── models/                    # 🆕 중앙 모델 저장소
│   ├── __init__.py
│   ├── tick.py
│   ├── watchlist.py
│   ├── order.py
│   ├── risk.py
│   ├── backtest.py
│   └── technical.py
├── core/
│   ├── order_manager.py      # → backend.models.order import
│   └── ...
└── strategies/
    └── seismograph/
        └── models.py         # re-export (하위 호환)
```

---

## 8. 다음 단계

- **07-001 완료 후**: `core/` 모듈 그룹화 (REFACTORING.md §2.5 참조)
  - `scanning/`, `tick/`, `backtest/`, `trading/`, `analysis/` 서브디렉터리

---

# Appendix A: 모델별 상세 정의

> 새 세션에서 배경지식 없이 구현 가능하도록 각 모델의 필드를 명시합니다.

## A.1 tick.py - TickData

```python
# backend/models/tick.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TickData:
    """실시간 틱 데이터 구조체"""
    price: float
    volume: int
    timestamp: datetime
    side: str = "B"  # "B" (buy) or "S" (sell)
```

## A.2 watchlist.py - WatchlistItem

```python
# backend/models/watchlist.py
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

@dataclass
class WatchlistItem:
    """Watchlist 항목 구조체"""
    ticker: str
    score: float
    stage: str
    stage_number: int  # 1~4 (Trading Restrictions용)
    signals: Dict[str, bool]  # 개별 신호 탐지 결과
    can_trade: bool  # Stage 3-4만 True
    last_close: float = 0.0
    avg_volume: float = 0.0
    scan_timestamp: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "score": self.score,
            "stage": self.stage,
            "stage_number": self.stage_number,
            "signals": self.signals,
            "can_trade": self.can_trade,
            "last_close": self.last_close,
            "avg_volume": self.avg_volume,
            "scan_timestamp": self.scan_timestamp.isoformat() if self.scan_timestamp else None,
        }
```

## A.3 order.py - OrderRecord, Position

```python
# backend/models/order.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum, auto

class OrderStatus(Enum):
    PENDING = auto()
    PARTIAL_FILL = auto()
    FILLED = auto()
    CANCELLED = auto()
    REJECTED = auto()
    ERROR = auto()

class OrderType(Enum):
    MARKET = "MKT"
    LIMIT = "LMT"
    STOP = "STP"
    STOP_LIMIT = "STP LMT"
    TRAILING_STOP = "TRAIL"

@dataclass
class OrderRecord:
    """주문 기록"""
    order_id: int
    symbol: str
    action: str  # "BUY" or "SELL"
    qty: int
    order_type: OrderType
    status: OrderStatus
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    fill_price: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    oca_group: Optional[str] = None
    signal_id: Optional[str] = None
    notes: str = ""

@dataclass
class Position:
    """포지션 정보"""
    symbol: str
    qty: int
    avg_price: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
```

## A.4 risk.py - RiskConfig

```python
# backend/models/risk.py
from dataclasses import dataclass

@dataclass
class RiskConfig:
    """리스크 관리 설정"""
    max_position_pct: float = 10.0
    max_positions: int = 3
    max_daily_trades: int = 50
    per_trade_stop_pct: float = -5.0
    daily_loss_limit_pct: float = -3.0
    weekly_loss_limit_pct: float = -10.0
    use_kelly: bool = False
    kelly_fraction: float = 0.25
    kelly_min_trades: int = 20
    auto_kill_on_daily_limit: bool = True
```

## A.5 backtest.py - BacktestConfig, Trade, BacktestReport

```python
# backend/models/backtest.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class BacktestConfig:
    """백테스트 설정"""
    initial_capital: float = 100_000.0
    position_size_pct: float = 10.0
    max_positions: int = 5
    stop_loss_pct: float = -5.0
    profit_target_pct: float = 8.0
    time_stop_days: int = 3
    entry_stage: int = 4
    min_score: float = 80.0

@dataclass
class Trade:
    """개별 거래 기록"""
    ticker: str
    entry_date: str
    entry_price: float
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl_pct: Optional[float] = None
    stage: int = 0
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class BacktestReport:
    """백테스트 결과 리포트"""
    start_date: str = ""
    end_date: str = ""
    initial_capital: float = 100_000.0
    strategy_name: str = ""
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
```

## A.6 technical.py - 지표 관련 모델

```python
# backend/models/technical.py
from dataclasses import dataclass

@dataclass
class IndicatorResult:
    """지표 계산 결과 구조체"""
    value: float
    is_valid: bool = True
    message: str = ""

@dataclass
class StopLossLevels:
    """Stop-Loss / Take-Profit 레벨 구조체"""
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    risk_amount: float

@dataclass
class ZScoreResult:
    """Z-Score 계산 결과"""
    zenV: float
    zenP: float

@dataclass
class DailyStats:
    """장중 Time-Projection 계산용 일별 통계 캐시"""
    avg_volume: float
    std_volume: float
    avg_change: float
    std_change: float
```

---

# Appendix B: Import 수정 대상 파일 목록

> 모델 이동 후 import 경로를 업데이트해야 하는 파일들입니다.

## B.1 TickData, WatchlistItem

| 파일 | 현재 import | 변경 후 |
|------|------------|--------|
| `seismograph/__init__.py` | `from .models import TickData, WatchlistItem` | `from backend.models import TickData, WatchlistItem` |
| `seismograph/strategy.py` | `from .models import TickData, WatchlistItem` | `from backend.models import TickData, WatchlistItem` |

## B.2 RiskConfig

| 파일 | 현재 import | 변경 후 |
|------|------------|--------|
| `core/risk_manager.py` | `from core.risk_config import RiskConfig` | `from backend.models import RiskConfig` |
| `tests/test_risk_manager.py` | `from core.risk_config import RiskConfig` | `from backend.models import RiskConfig` |

## B.3 Backtest 모델

| 파일 | 현재 import | 변경 후 |
|------|------------|--------|
| `core/backtest_engine.py` | (내부 정의) | `from backend.models import BacktestConfig, Trade` |
| (내부) | `from core.backtest_report import BacktestReport, Trade` | `from backend.models import BacktestReport, Trade` |

## B.4 ZScore 모델

| 파일 | 현재 import | 변경 후 |
|------|------------|--------|
| (사용처 조사 필요) | `from core.zscore_calculator import ZScoreResult` | `from backend.models import ZScoreResult` |

---

# Appendix C: 실행 스크립트

> 자동화를 위한 실행 순서입니다.

```bash
# Step 1: 디렉터리 생성
mkdir -p backend/models

# Step 2: 파일 생성 (수동 또는 AI 생성)
# - backend/models/__init__.py
# - backend/models/tick.py
# - backend/models/watchlist.py
# - backend/models/order.py
# - backend/models/risk.py
# - backend/models/backtest.py
# - backend/models/technical.py

# Step 3: import 수정 (IDE 리팩터링 또는 수동)

# Step 4: 원본에서 모델 정의 삭제
# - seismograph/models.py → 빈 파일 또는 삭제
# - risk_config.py → 삭제
# (나머지는 클래스만 삭제하고 로직은 유지)

# Step 5: 검증
python -c "from backend.models import TickData, WatchlistItem"
python -c "from backend.models import RiskConfig, Position"
python -c "from backend.models import BacktestConfig, Trade"
ruff check backend/models/
python -m backend  # 서버 시작 테스트
```
