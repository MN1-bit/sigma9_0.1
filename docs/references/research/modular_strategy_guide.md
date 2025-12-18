# 🔌 Modular Strategy Architecture Guide

> **목적**: 프레임워크 없이 전략 모듈화 및 런타임 교체 가능한 설계  
> **패턴**: Strategy Pattern + Plugin Architecture

---

## 1. 설계 목표

| 목표 | 설명 |
|------|------|
| **모듈화** | 전략마다 독립된 파일, 수정 시 다른 코드 영향 없음 |
| **Hot Reload** | 서버 재시작 없이 전략 파일 교체 가능 |
| **GUI 연동** | 드롭다운에서 전략 선택 → 즉시 적용 |
| **타입 안전** | ABC 인터페이스로 필수 메서드 강제 |
| **테스트 용이** | 각 전략 독립적으로 단위 테스트 가능 |

---

## 2. 디렉토리 구조

```
backend/
├── core/
│   ├── strategy_base.py      # 추상 인터페이스 (모든 전략의 부모)
│   ├── strategy_loader.py    # 플러그인 로더 (동적 로딩)
│   └── engine.py             # 전략 실행 엔진
│
├── strategies/               # ← 전략 플러그인 폴더
│   ├── __init__.py
│   ├── seismograph.py        # Sigma9 메인 전략
│   ├── momentum.py           # 모멘텀 전략 (예시)
│   └── mean_reversion.py     # 평균회귀 전략 (예시)
│
└── config/
    └── active_strategy.yaml  # 현재 활성 전략 설정
```

---

## 3. 핵심 컴포넌트

### 3.1 Strategy Base (추상 인터페이스)

```python
# backend/core/strategy_base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class Signal:
    """전략이 생성하는 매매 신호"""
    action: str      # "BUY", "SELL", "HOLD"
    ticker: str      # 종목 심볼
    confidence: float  # 신뢰도 0.0 ~ 1.0
    reason: str      # 신호 발생 이유
    metadata: Dict[str, Any] = None  # 추가 정보

class StrategyBase(ABC):
    """
    모든 전략이 구현해야 하는 인터페이스
    
    새 전략 개발 시:
    1. 이 클래스를 상속
    2. 모든 @abstractmethod 구현
    3. strategies/ 폴더에 .py 파일로 저장
    """
    
    # 전략 메타데이터 (서브클래스에서 오버라이드)
    name: str = "BaseStrategy"
    version: str = "1.0"
    description: str = "Base strategy interface"
    
    @abstractmethod
    def initialize(self) -> None:
        """전략 초기화 (로드 시 1회 호출)"""
        pass
    
    @abstractmethod
    def on_tick(self, ticker: str, price: float, volume: int, timestamp: float) -> Optional[Signal]:
        """
        실시간 틱 데이터 처리
        
        Args:
            ticker: 종목 심볼
            price: 현재가
            volume: 체결량
            timestamp: 체결 시각 (Unix timestamp)
        
        Returns:
            Signal 또는 None (신호 없음)
        """
        pass
    
    @abstractmethod
    def on_bar(self, ticker: str, ohlcv: dict) -> Optional[Signal]:
        """
        분봉/일봉 데이터 처리
        
        Args:
            ticker: 종목 심볼
            ohlcv: {"open": float, "high": float, "low": float, 
                    "close": float, "volume": int, "timestamp": float}
        
        Returns:
            Signal 또는 None
        """
        pass
    
    @abstractmethod
    def on_order_filled(self, order: dict) -> None:
        """주문 체결 시 콜백 (포지션 추적용)"""
        pass
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """
        전략 설정값 반환 (GUI에서 표시/수정용)
        
        Returns:
            {"param_name": {"value": X, "min": Y, "max": Z, "description": "..."}}
        """
        pass
    
    @abstractmethod
    def set_config(self, config: Dict[str, Any]) -> None:
        """전략 설정값 변경 (런타임)"""
        pass
    
    def get_info(self) -> dict:
        """전략 메타정보 반환"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
        }
```

### 3.2 전략 구현 예시

```python
# backend/strategies/seismograph.py

from typing import Optional, Dict, Any
from core.strategy_base import StrategyBase, Signal

class SeismographStrategy(StrategyBase):
    """
    Sigma9 메인 전략: 매집 탐지 → 급등 포착
    
    Phase 1: Accumulation Detection (일봉)
    Phase 2: Ignition Detection (실시간 틱)
    """
    
    name = "Seismograph"
    version = "2.0"
    description = "Detect accumulation, strike ignition, harvest surge"
    
    def __init__(self):
        self.config = {
            "accumulation_threshold": {
                "value": 60, "min": 40, "max": 80,
                "description": "매집 점수 진입 기준"
            },
            "ignition_threshold": {
                "value": 70, "min": 50, "max": 90,
                "description": "급등 점수 진입 기준"
            },
            "tick_velocity_multiplier": {
                "value": 8, "min": 4, "max": 15,
                "description": "틱 속도 배수 기준"
            },
            "volume_burst_multiplier": {
                "value": 6, "min": 3, "max": 12,
                "description": "거래량 폭발 배수 기준"
            },
        }
        self._tick_buffer = {}
        self._positions = {}
    
    def initialize(self) -> None:
        """전략 초기화"""
        self._tick_buffer.clear()
        self._positions.clear()
    
    def on_tick(self, ticker: str, price: float, volume: int, timestamp: float) -> Optional[Signal]:
        """실시간 Ignition Detection"""
        # 틱 버퍼에 저장
        if ticker not in self._tick_buffer:
            self._tick_buffer[ticker] = []
        self._tick_buffer[ticker].append((price, volume, timestamp))
        
        # 최근 10초 데이터만 유지
        cutoff = timestamp - 10
        self._tick_buffer[ticker] = [
            t for t in self._tick_buffer[ticker] if t[2] > cutoff
        ]
        
        # Ignition Score 계산
        score = self._calculate_ignition_score(ticker)
        threshold = self.config["ignition_threshold"]["value"]
        
        if score >= threshold:
            return Signal(
                action="BUY",
                ticker=ticker,
                confidence=score / 100,
                reason=f"Ignition detected (score: {score})",
                metadata={"ignition_score": score}
            )
        return None
    
    def on_bar(self, ticker: str, ohlcv: dict) -> Optional[Signal]:
        """일봉 기반 Accumulation Detection"""
        score = self._calculate_accumulation_score(ticker, ohlcv)
        # Watchlist 관리용, 직접 신호 생성하지 않음
        return None
    
    def on_order_filled(self, order: dict) -> None:
        """주문 체결 시 포지션 추적"""
        ticker = order["ticker"]
        if order["action"] == "BUY":
            self._positions[ticker] = order
        elif order["action"] == "SELL":
            self._positions.pop(ticker, None)
    
    def get_config(self) -> Dict[str, Any]:
        return self.config
    
    def set_config(self, config: Dict[str, Any]) -> None:
        for key, value in config.items():
            if key in self.config:
                self.config[key]["value"] = value
    
    # ─── Private Methods ─────────────────────────────────
    
    def _calculate_ignition_score(self, ticker: str) -> float:
        """Ignition Score 계산 로직"""
        # TODO: 구현
        return 0.0
    
    def _calculate_accumulation_score(self, ticker: str, ohlcv: dict) -> float:
        """Accumulation Score 계산 로직"""
        # TODO: 구현
        return 0.0
```

### 3.3 Strategy Loader (플러그인 시스템)

```python
# backend/core/strategy_loader.py

import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Optional
from core.strategy_base import StrategyBase

class StrategyLoader:
    """
    전략 파일을 동적으로 로드하는 플러그인 시스템
    
    사용법:
        loader = StrategyLoader("strategies")
        strategies = loader.discover_strategies()  # ['seismograph', 'momentum']
        strategy = loader.load_strategy("seismograph")
        strategy.on_tick(...)
    """
    
    def __init__(self, strategy_dir: str = "strategies"):
        self.strategy_dir = Path(strategy_dir)
        self.strategies: Dict[str, StrategyBase] = {}
    
    def discover_strategies(self) -> List[str]:
        """strategies/ 폴더의 모든 전략 파일 탐색"""
        found = []
        for file in self.strategy_dir.glob("*.py"):
            if file.name.startswith("_"):
                continue
            found.append(file.stem)
        return found
    
    def load_strategy(self, strategy_name: str) -> StrategyBase:
        """
        특정 전략을 동적으로 로드
        
        Args:
            strategy_name: 파일명 (확장자 제외)
        
        Returns:
            StrategyBase 인스턴스
        """
        filepath = self.strategy_dir / f"{strategy_name}.py"
        if not filepath.exists():
            raise FileNotFoundError(f"Strategy file not found: {filepath}")
        
        # 모듈 동적 로드
        spec = importlib.util.spec_from_file_location(strategy_name, filepath)
        module = importlib.util.module_from_spec(spec)
        sys.modules[strategy_name] = module
        spec.loader.exec_module(module)
        
        # StrategyBase를 상속한 클래스 찾기
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, StrategyBase) and 
                attr is not StrategyBase):
                instance = attr()
                instance.initialize()
                self.strategies[strategy_name] = instance
                return instance
        
        raise ValueError(f"No StrategyBase subclass found in {filepath}")
    
    def reload_strategy(self, strategy_name: str) -> StrategyBase:
        """
        전략 파일 수정 후 핫 리로드
        
        Returns:
            새로 로드된 StrategyBase 인스턴스
        """
        # 기존 인스턴스 제거
        if strategy_name in self.strategies:
            del self.strategies[strategy_name]
        
        # 캐시된 모듈 제거
        if strategy_name in sys.modules:
            del sys.modules[strategy_name]
        
        return self.load_strategy(strategy_name)
    
    def get_strategy(self, strategy_name: str) -> Optional[StrategyBase]:
        """이미 로드된 전략 반환"""
        return self.strategies.get(strategy_name)
    
    def list_loaded(self) -> List[dict]:
        """현재 로드된 전략 목록"""
        return [s.get_info() for s in self.strategies.values()]
```

---

## 4. API 엔드포인트

```python
# backend/api/routes.py

from fastapi import APIRouter, HTTPException
from core.strategy_loader import StrategyLoader

router = APIRouter(prefix="/api/strategies", tags=["strategies"])
loader = StrategyLoader("strategies")

@router.get("/")
async def list_available_strategies():
    """사용 가능한 전략 파일 목록"""
    return {"strategies": loader.discover_strategies()}

@router.get("/loaded")
async def list_loaded_strategies():
    """현재 로드된 전략 목록"""
    return {"strategies": loader.list_loaded()}

@router.post("/{name}/load")
async def load_strategy(name: str):
    """전략 로드"""
    try:
        strategy = loader.load_strategy(name)
        return {"status": "loaded", "info": strategy.get_info()}
    except Exception as e:
        raise HTTPException(400, str(e))

@router.post("/{name}/reload")
async def reload_strategy(name: str):
    """전략 핫 리로드 (파일 수정 후)"""
    try:
        strategy = loader.reload_strategy(name)
        return {"status": "reloaded", "info": strategy.get_info()}
    except Exception as e:
        raise HTTPException(400, str(e))

@router.get("/{name}/config")
async def get_strategy_config(name: str):
    """전략 설정값 조회"""
    strategy = loader.get_strategy(name)
    if not strategy:
        raise HTTPException(404, "Strategy not loaded")
    return strategy.get_config()

@router.post("/{name}/config")
async def update_strategy_config(name: str, config: dict):
    """전략 설정값 수정 (런타임)"""
    strategy = loader.get_strategy(name)
    if not strategy:
        raise HTTPException(404, "Strategy not loaded")
    strategy.set_config(config)
    return {"status": "updated", "config": strategy.get_config()}
```

---

## 5. GUI 연동

### 5.1 전략 선택 위젯

```python
# frontend/gui/strategy_selector.py

from PyQt6.QtWidgets import QWidget, QComboBox, QPushButton, QVBoxLayout
from client.api_client import BackendClient

class StrategySelector(QWidget):
    def __init__(self, client: BackendClient):
        super().__init__()
        self.client = client
        
        self.combo = QComboBox()
        self.reload_btn = QPushButton("🔄 Reload")
        
        layout = QVBoxLayout()
        layout.addWidget(self.combo)
        layout.addWidget(self.reload_btn)
        self.setLayout(layout)
        
        self.reload_btn.clicked.connect(self._on_reload)
        self.combo.currentTextChanged.connect(self._on_strategy_changed)
        
        self._refresh_list()
    
    async def _refresh_list(self):
        strategies = await self.client.get("/api/strategies/")
        self.combo.clear()
        self.combo.addItems(strategies["strategies"])
    
    async def _on_strategy_changed(self, name: str):
        await self.client.post(f"/api/strategies/{name}/load")
    
    async def _on_reload(self):
        name = self.combo.currentText()
        await self.client.post(f"/api/strategies/{name}/reload")
```

### 5.2 전략 교체 워크플로우

```
┌─────────────────────────────────────────────────────────────────┐
│  전략 교체 워크플로우                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 새 전략 파일 작성 (예: new_strategy.py)                     │
│     └─ StrategyBase 상속, 필수 메서드 구현                      │
│                                                                 │
│  2. backend/strategies/ 폴더에 복사                             │
│                                                                 │
│  3. GUI에서:                                                    │
│     ┌─────────────────────────────────────────┐                 │
│     │  Strategy: [▼ new_strategy ]  [🔄 Reload] │                 │
│     └─────────────────────────────────────────┘                 │
│                                                                 │
│  4. 드롭다운에 자동 표시 → 선택 → 즉시 적용!                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. 새 전략 개발 템플릿

```python
# backend/strategies/_template.py (복사해서 사용)

"""
전략명: [전략 이름]
작성자: [이름]
버전: 1.0
설명: [전략 설명]
"""

from typing import Optional, Dict, Any
from core.strategy_base import StrategyBase, Signal

class MyNewStrategy(StrategyBase):
    
    name = "MyNewStrategy"
    version = "1.0"
    description = "전략 설명"
    
    def __init__(self):
        self.config = {
            "param1": {"value": 10, "min": 1, "max": 100, "description": "파라미터 1"},
            "param2": {"value": 0.5, "min": 0.0, "max": 1.0, "description": "파라미터 2"},
        }
    
    def initialize(self) -> None:
        # 초기화 로직
        pass
    
    def on_tick(self, ticker: str, price: float, volume: int, timestamp: float) -> Optional[Signal]:
        # 틱 처리 로직
        return None
    
    def on_bar(self, ticker: str, ohlcv: dict) -> Optional[Signal]:
        # 바 처리 로직
        return None
    
    def on_order_filled(self, order: dict) -> None:
        # 체결 처리 로직
        pass
    
    def get_config(self) -> Dict[str, Any]:
        return self.config
    
    def set_config(self, config: Dict[str, Any]) -> None:
        for key, value in config.items():
            if key in self.config:
                self.config[key]["value"] = value
```

---

## 7. 장점 요약

| 장점 | 설명 |
|------|------|
| ✅ **프레임워크 독립** | 외부 의존성 없음, 순수 Python |
| ✅ **Hot Reload** | 서버 중단 없이 전략 교체 |
| ✅ **타입 안전** | ABC로 필수 메서드 강제 |
| ✅ **GUI 친화적** | API로 전략 목록/설정 제공 |
| ✅ **테스트 용이** | 각 전략 독립적으로 테스트 |
| ✅ **확장 용이** | 새 전략 = 새 파일 추가 |

---

> **"Simple is better than complex. But a good interface makes complex things simple."**
