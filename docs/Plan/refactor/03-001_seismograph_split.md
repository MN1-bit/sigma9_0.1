# seismograph.py 분리 리팩터링 계획서

> **작성일**: 2026-01-08 00:29
> **우선순위**: 3 | **예상 소요**: 6-8h | **위험도**: 중간
> **선행 조건**: 01-001, 02-001 완료

## 1. 목표

- God Class 해소: 2,259줄 → 각 모듈 ≤500줄
- 단일 책임 원칙(SRP) 적용
- 개별 컴포넌트 테스트 용이성 확보

### 현재 문제점

| 책임 | 라인 수 (추정) | 분리 대상 |
|------|---------------|----------|
| 데이터 모델 (TickData, WatchlistItem) | ~150 | `models.py` |
| Score V1 계산 | ~200 | `scoring/v1.py` |
| Score V2 계산 | ~250 | `scoring/v2.py` |
| Score V3 계산 | ~400 | `scoring/v3.py` |
| Tight Range 시그널 | ~150 | `signals/tight_range.py` |
| OBV Divergence 시그널 | ~200 | `signals/obv_divergence.py` |
| Accumulation Bar 시그널 | ~150 | `signals/accumulation_bar.py` |
| Volume Dryout 시그널 | ~150 | `signals/volume_dryout.py` |
| SeismographStrategy 코어 | ~600 | `__init__.py` |

## 2. 영향 분석

### 목표 디렉터리 구조

```
backend/strategies/seismograph/
├── __init__.py              # SeismographStrategy (진입점, ~300줄)
├── models.py                # TickData, WatchlistItem (~150줄)
├── scoring/                 
│   ├── __init__.py          # 점수 계산 통합
│   ├── base.py              # 공통 유틸리티
│   ├── v1.py                # Stage-based scoring
│   ├── v2.py                # Weighted intensity
│   └── v3.py                # Pinpoint algorithm
└── signals/                 
    ├── __init__.py          # 시그널 탐지 통합
    ├── tight_range.py
    ├── obv_divergence.py
    ├── accumulation_bar.py
    └── volume_dryout.py
```

### 변경 파일 목록

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `backend/strategies/seismograph.py` | 🗑️ 삭제 | 분리 후 삭제 |
| `backend/strategies/seismograph/__init__.py` | 🆕 신규 | 메인 진입점 |
| `backend/strategies/seismograph/models.py` | 🆕 신규 | 데이터 모델 |
| `backend/strategies/seismograph/scoring/*.py` | 🆕 신규 | 점수 계산 모듈 |
| `backend/strategies/seismograph/signals/*.py` | 🆕 신규 | 시그널 탐지 모듈 |
| `backend/container.py` | 📝 수정 | import 경로 변경 |

### 영향받는 모듈

- `backend/core/realtime_scanner.py` - import 경로 변경
- `backend/api/routes.py` - 간접 영향
- `tests/` - 테스트 import 경로 변경

## 3. 실행 계획

### Step 1: 디렉터리 구조 생성

```bash
mkdir -p backend/strategies/seismograph/scoring
mkdir -p backend/strategies/seismograph/signals
touch backend/strategies/seismograph/__init__.py
touch backend/strategies/seismograph/models.py
touch backend/strategies/seismograph/scoring/__init__.py
touch backend/strategies/seismograph/signals/__init__.py
```

### Step 2: 데이터 모델 분리 (models.py)

`TickData`, `WatchlistItem` 등 `@dataclass` 정의 이동

```python
# backend/strategies/seismograph/models.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class TickData:
    symbol: str
    price: float
    volume: int
    timestamp: float
    # ... 기존 필드

@dataclass
class WatchlistItem:
    symbol: str
    score_v1: float
    score_v2: float
    score_v3: Dict[str, float]
    # ... 기존 필드
```

### Step 3: Scoring 모듈 분리

각 버전의 점수 계산 로직을 별도 파일로 분리:

```python
# backend/strategies/seismograph/scoring/v3.py
from typing import Dict, Any
from ..models import TickData, WatchlistItem

def calculate_score_v3(
    tick_data: TickData,
    watchlist_item: WatchlistItem,
    config: Dict[str, Any]
) -> Dict[str, float]:
    """Pinpoint Algorithm - Score V3 계산"""
    # ... 기존 로직 이동
```

### Step 4: Signals 모듈 분리

```python
# backend/strategies/seismograph/signals/obv_divergence.py
from typing import List
import pandas as pd

def detect_obv_divergence(
    prices: List[float],
    volumes: List[int],
    window: int = 20
) -> float:
    """OBV Divergence 감지"""
    # ... 기존 로직 이동
```

### Step 5: 메인 클래스 리팩터링

```python
# backend/strategies/seismograph/__init__.py
from backend.core.interfaces.scoring import ScoringStrategy
from .models import TickData, WatchlistItem
from .scoring import v1, v2, v3
from .signals import tight_range, obv_divergence, accumulation_bar, volume_dryout

class SeismographStrategy(ScoringStrategy):
    """Seismograph 전략 - 리팩터링된 진입점"""
    
    def calculate_score(self, tick_data, watchlist_item) -> float:
        return v3.calculate_score_v3(tick_data, watchlist_item, self.config)
    
    def detect_signals(self, data) -> Dict[str, float]:
        return {
            "tight_range": tight_range.detect(data),
            "obv_divergence": obv_divergence.detect(data),
            "accumulation_bar": accumulation_bar.detect(data),
            "volume_dryout": volume_dryout.detect(data),
        }
```

### Step 6: Import 경로 업데이트

```python
# Before
from backend.strategies.seismograph import SeismographStrategy, TickData

# After
from backend.strategies.seismograph import SeismographStrategy
from backend.strategies.seismograph.models import TickData
```

### Step 7: 기존 파일 삭제

```bash
rm backend/strategies/seismograph.py
```

## 4. 검증 계획

### 자동화 테스트

```bash
# 1. Import 경계 검증
lint-imports

# 2. 순환 의존성 검사
pydeps backend --only backend --show-cycles --no-output

# 3. 기존 테스트 실행
pytest tests/ -v

# 4. Architecture 테스트 (파일 크기)
pytest tests/architecture/test_file_size.py -v

# 5. mypy 타입 체크
mypy backend/strategies/seismograph/
```

### 수동 테스트

- [ ] Backend 서버 정상 시작: `python -m backend`
- [ ] Watchlist 스코어 계산 정상 작동 확인
- [ ] Score V1, V2, V3 모두 정상 계산 확인
- [ ] 시그널 감지 기능 정상 작동 확인
- [ ] Frontend에서 실시간 데이터 표시 확인

## 5. 롤백 계획

```bash
# 문제 발생 시 롤백
git checkout HEAD -- backend/strategies/seismograph.py
rm -rf backend/strategies/seismograph/
```

---

## 6. 위험 요소 및 대응

| 위험 | 확률 | 영향 | 대응 |
|------|-----|-----|------|
| Import 경로 누락 | 중간 | 높음 | grep으로 모든 import 검색 후 업데이트 |
| 순환 의존성 재발 | 낮음 | 높음 | models.py를 최하위 계층으로 유지 |
| 런타임 에러 | 중간 | 중간 | 단계별 테스트 실행 |

---

**참조 문서**:
- [REFACTORING.md](./REFACTORING.md) - 섹션 3.1 seismograph.py 분리 제안
- [@PROJECT_DNA.md](../../@PROJECT_DNA.md) - 코드 품질 기준 (≤500 라인)
