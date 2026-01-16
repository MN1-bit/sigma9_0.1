# DataRepository 통합 및 Parquet 전면 전환 계획서

> **작성일**: 2026-01-10 04:11
> **우선순위**: 11 (Data Layer) | **예상 소요**: 6-8h | **위험도**: 중간
> **상태**: ✅ 설계 확정, 실행 대기

---

## 0. 배경 컨텍스트 (Zero-Context Session용)

### 0.1 현재 시스템 상태

```
Sigma9: 미국 마이크로캡 자동 트레이딩 시스템
├── Backend: FastAPI + SQLite + Parquet (듀얼)
├── Frontend: PyQt6 + pyqtgraph
└── 데이터: Massive.com API + 로컬 캐시
```

### 0.2 문제점

1. **데이터 접근 분산**: 8+곳에서 SQLite 직접 호출
2. **레거시 의존성**: SQLite ORM (`DailyBar`, `IntradayBar`) 아직 사용
3. **이중 관리**: SQLite + Parquet 듀얼 라이트 상태

### 0.3 목표

- **통합 DataRepository 레이어**: 모든 데이터 접근을 단일 인터페이스로
- **Parquet 전용**: SQLite 완전 제거
- **확장성**: 보조지표/스코어 캐싱, On-Demand Gap Fill 지원

### 0.4 선행 작업 (완료)

| 작업 | 상태 | 문서 |
|------|------|------|
| ParquetManager 구현 | ✅ 완료 | `backend/data/parquet_manager.py` |
| SQLite → Parquet 마이그레이션 스크립트 | ✅ 완료 | `backend/scripts/migrate_to_parquet.py` |
| MassiveLoader 듀얼 라이트 | ✅ 완료 | 계속 운영 (예외) |

---

## 1. 설계 개요

### 1.1 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           DataRepository                                 │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │ Public API                                                         │  │
│  │ ┌─────────────────┐ ┌─────────────────┐ ┌────────────────────────┐│  │
│  │ │get_daily_bars() │ │get_intraday()   │ │get_all_tickers()       ││  │
│  │ └─────────────────┘ └─────────────────┘ └────────────────────────┘│  │
│  │ ┌─────────────────┐ ┌─────────────────┐ ┌────────────────────────┐│  │
│  │ │get_indicator()  │ │update_score()   │ │flush_scores()          ││  │
│  │ └─────────────────┘ └─────────────────┘ └────────────────────────┘│  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                    │                                     │
│  ┌─────────────────────────────────┼─────────────────────────────────┐  │
│  │ Internal Components             ▼                                  │  │
│  │ ┌───────────────┐  ┌───────────────┐  ┌─────────────────────────┐ │  │
│  │ │ParquetManager │  │FlushPolicy    │  │ScoreCache (in-memory)   │ │  │
│  │ │(Raw I/O)      │  │(configurable) │  │(fast access)            │ │  │
│  │ └───────────────┘  └───────────────┘  └─────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 파일 구조

```
backend/data/
├── data_repository.py       # 🆕 통합 데이터 접근 레이어
├── flush_policy.py          # 🆕 캐시 Flush 정책 (Strategy Pattern)
├── parquet_manager.py       # 기존 유지 (Low-Level I/O)
├── massive_loader.py        # 기존 유지 (예외: SQLite→Parquet 변환)
└── database.py              # SQLite 코드 정리 (Ticker만 유지)

data/parquet/
├── daily/
│   └── all_daily.parquet
├── intraday/
│   └── {TICKER}_{timeframe}.parquet
├── indicators/              # 🆕
│   └── {indicator}_{ticker}.parquet
└── scores/                  # 🆕
    └── current_v3.parquet
```

---

## 2. 핵심 컴포넌트 설계

### 2.1 FlushPolicy (캐시 Flush 전략)

**목적**: 스코어 갱신 주기가 아직 미정 (1초~1분)이므로, 설정 기반으로 유연하게 대응

```python
# backend/data/flush_policy.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
import time

@dataclass
class FlushPolicy(ABC):
    """캐시 Flush 정책 인터페이스 (Strategy Pattern)"""
    
    @abstractmethod
    def should_flush(self, last_flush_time: float, update_count: int) -> bool:
        """Flush 여부 판단"""
        ...


@dataclass
class ImmediateFlush(FlushPolicy):
    """즉시 저장 (매 업데이트마다 Parquet 쓰기)"""
    def should_flush(self, last_flush_time: float, update_count: int) -> bool:
        return True  # 항상 flush


@dataclass  
class IntervalFlush(FlushPolicy):
    """시간 기반 Flush (권장)"""
    interval_seconds: float = 30.0  # 기본 30초
    
    def should_flush(self, last_flush_time: float, update_count: int) -> bool:
        return (time.time() - last_flush_time) >= self.interval_seconds


@dataclass
class CountFlush(FlushPolicy):
    """업데이트 횟수 기반 Flush"""
    threshold: int = 100
    
    def should_flush(self, last_flush_time: float, update_count: int) -> bool:
        return update_count >= self.threshold


@dataclass
class HybridFlush(FlushPolicy):
    """시간 + 횟수 복합 (둘 중 하나 충족 시 Flush)"""
    interval_seconds: float = 30.0
    count_threshold: int = 50
    
    def should_flush(self, last_flush_time: float, update_count: int) -> bool:
        time_trigger = (time.time() - last_flush_time) >= self.interval_seconds
        count_trigger = update_count >= self.count_threshold
        return time_trigger or count_trigger
```

### 2.2 DataRepository 인터페이스

```python
# backend/data/data_repository.py

class DataRepository:
    """
    통합 데이터 접근 레이어
    
    모든 시장 데이터 접근은 이 클래스를 통해 이루어집니다.
    Parquet을 Primary Storage로 사용하며, On-Demand Gap Fill을 지원합니다.
    
    ELI5: 데이터가 필요하면 이 클래스한테 물어보세요.
          로컬에 없으면 알아서 API 호출해서 가져와 줍니다.
    """
    
    def __init__(
        self,
        parquet_manager: ParquetManager,
        massive_client: MassiveClient | None = None,
        flush_policy: FlushPolicy = IntervalFlush(30),  # 기본 30초
    ):
        self._pm = parquet_manager
        self._client = massive_client
        self._flush_policy = flush_policy
        
        # 스코어 캐시 (메모리)
        self._score_cache: dict[str, dict] = {}
        self._last_flush = time.time()
        self._update_count = 0
    
    # ═══════════════════════════════════════════════════════════════════
    # Daily/Intraday Data (auto_fill=True 기본값)
    # ═══════════════════════════════════════════════════════════════════
    
    async def get_daily_bars(
        self,
        ticker: str,
        days: int = 60,
        *,
        auto_fill: bool = True,
    ) -> pd.DataFrame:
        """
        일봉 데이터 조회 (누락 시 API 자동 호출)
        
        Args:
            ticker: 종목 심볼
            days: 조회할 일수
            auto_fill: True면 누락 데이터 API 호출 후 저장 (기본값: True)
        """
        df = self._pm.read_daily(ticker, days)
        
        if auto_fill and self._has_gaps(df, days):
            await self._fill_gaps(ticker, days)
            df = self._pm.read_daily(ticker, days)
        
        return df
    
    async def get_intraday_bars(
        self,
        ticker: str,
        timeframe: str,
        days: int = 2,
        *,
        auto_fill: bool = True,
    ) -> pd.DataFrame:
        """분봉/시봉 데이터 조회 (누락 시 API 자동 호출)"""
        ...
    
    def get_all_tickers(self) -> list[str]:
        """저장된 일봉 데이터의 티커 목록"""
        return self._pm.get_available_tickers()
    
    # ═══════════════════════════════════════════════════════════════════
    # Indicators (On-Demand 생산 + 저장)
    # ═══════════════════════════════════════════════════════════════════
    
    def get_indicator(
        self,
        ticker: str,
        indicator: str,
        days: int = 60,
    ) -> pd.Series:
        """
        보조지표 조회 (캐시 우선, 없으면 계산 후 저장)
        
        ELI5: "SMA 20일 줘" → 이미 계산했으면 바로 반환,
              없으면 계산해서 저장 후 반환
        """
        cached = self._load_indicator_cache(ticker, indicator)
        if cached is not None:
            return cached
        
        # 계산
        result = self._calculate_indicator(ticker, indicator, days)
        
        # 저장 (On-Demand 생산 시 항상 저장)
        self._save_indicator_cache(ticker, indicator, result)
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════
    # Scores (메모리 캐시 + 설정 기반 Flush)
    # ═══════════════════════════════════════════════════════════════════
    
    def update_score(
        self,
        ticker: str,
        version: str,
        score_data: dict,
    ) -> None:
        """
        스코어 업데이트 (갱신 주기에 따라 호출)
        
        메모리 캐시에 저장하고, FlushPolicy에 따라 Parquet 저장
        """
        self._score_cache[ticker] = score_data
        self._update_count += 1
        
        # FlushPolicy에 따라 저장 여부 결정
        if self._flush_policy.should_flush(self._last_flush, self._update_count):
            self._flush_scores(version)
    
    def _flush_scores(self, version: str = "v3") -> None:
        """스코어 Parquet 저장"""
        if self._score_cache:
            df = pd.DataFrame(self._score_cache.values())
            self._pm.write(f"scores/current_{version}.parquet", df)
            self._last_flush = time.time()
            self._update_count = 0
    
    def get_score(self, ticker: str) -> dict:
        """스코어 조회 (메모리 캐시 우선)"""
        return self._score_cache.get(ticker, {})
    
    def force_flush(self) -> None:
        """강제 Flush (장 마감, 서버 종료 시 호출)"""
        self._flush_scores()
```

### 2.3 설정 통합

```yaml
# settings.yaml

data_repository:
  # Gap Fill 설정
  auto_fill: true
  
  # FlushPolicy 설정
  flush_policy: interval  # immediate | interval | count | hybrid
  flush_interval_seconds: 30
  flush_count_threshold: 100
```

---

## 3. 변경 대상 파일

### 3.1 신규 파일

| 파일 | 설명 |
|------|------|
| `backend/data/data_repository.py` | 통합 데이터 접근 레이어 |
| `backend/data/flush_policy.py` | 캐시 Flush 정책 (Strategy Pattern) |

### 3.2 수정 파일

| 파일 | 변경 내용 | 호출 패턴 변경 |
|------|----------|---------------|
| `backend/core/scanner.py` | `db.get_daily_bars()` → `repo.get_daily_bars()` | 3곳 |
| `backend/core/realtime_scanner.py` | 동일 | 3곳 |
| `backend/core/backtest_engine.py` | 동일 | 1곳 |
| `backend/api/routes/zscore.py` | 동일 | 1곳 |
| `backend/api/routes/chart.py` | `db.get_intraday_bars()` → `repo.get_intraday_bars()` | 1곳 |
| `frontend/services/chart_data_service.py` | `ParquetManager` 직접 사용 → `DataRepository` | 다수 |
| `backend/container.py` | `DataRepository` DI 등록 | 1곳 |
| `backend/data/database.py` | `DailyBar`, `IntradayBar` 코드 정리 (Ticker 유지) | - |

### 3.3 예외 (변경 제외)

| 파일 | 이유 |
|------|------|
| `backend/data/massive_loader.py` | 현재 SQLite → Parquet 변환 담당. DataRepository와 독립 운영 |

---

## 4. 실행 계획

### Step 1: FlushPolicy 구현 (0.5h)

- [ ] `backend/data/flush_policy.py` 생성
- [ ] `FlushPolicy` ABC 및 4개 구현체

### Step 2: DataRepository 기반 구현 (2-3h)

- [ ] `backend/data/data_repository.py` 생성
- [ ] `get_daily_bars()`, `get_intraday_bars()` (auto_fill=True)
- [ ] `get_all_tickers()`
- [ ] `get_indicator()`, `_save_indicator_cache()`
- [ ] `update_score()`, `get_score()`, `_flush_scores()`
- [ ] DI Container 등록 (`container.py`)

### Step 3: Gap Fill 기능 (1-2h)

- [ ] `_has_gaps()` 구현 (누락 날짜 감지)
- [ ] `_fill_gaps()` 구현 (Massive API 호출)
- [ ] Rate Limit 고려 (5 req/min)
- [ ] 에러 핸들링

### Step 4: Core 모듈 마이그레이션 (2-3h)

- [ ] `scanner.py` → `repo.get_daily_bars()` (3곳)
- [ ] `realtime_scanner.py` → `repo.get_daily_bars()` (3곳)
- [ ] `backtest_engine.py` → `repo.get_daily_bars()` (1곳)
- [ ] `zscore.py` → `repo.get_daily_bars()` (1곳)
- [ ] `chart.py` → `repo.get_intraday_bars()` (1곳)
- [ ] `chart_data_service.py` → `DataRepository` 의존

### Step 5: SQLite 레거시 코드 정리 (1h)

> **⚠️ 예외**: `massive_loader.py`는 변경하지 않음

- [ ] `database.py` - `DailyBar`, `IntradayBar` 관련 코드 제거 (Ticker 유지)
- [ ] `chart_data_service.py` - SQLite fallback 로직 제거

### Step 6: 아키텍처 문서 반영 (0.5h)

| 파일 | 반영 내용 |
|------|----------|
| `@PROJECT_DNA.md` | Tech Stack에 Parquet 추가, 디렉터리 구조에 `data_repository.py` |
| `.agent/Ref/archt.md` | 모듈 구조, 데이터 파이프라인 다이어그램 |
| `.agent/Ref/MPlan.md` | Tech Stack, 완료 마일스톤 |

---

## 5. 검증 계획

### 5.1 자동화 테스트

```bash
# 기존 테스트
pytest tests/test_parquet_manager.py -v

# 전체 회귀 테스트
pytest tests/ -v

# 코드 품질
ruff check . && lint-imports

# 순환 의존성
pydeps backend --only backend --show-cycles --no-output
```

### 5.2 신규 테스트 (`tests/test_data_repository.py`)

- [ ] `get_daily_bars()` 라운드트립
- [ ] `get_intraday_bars()` 라운드트립
- [ ] `get_all_tickers()` 반환값 검증
- [ ] `get_indicator()` 캐시 hit/miss
- [ ] `update_score()` + FlushPolicy 동작 검증
- [ ] `gap_fill_daily()` Mock API 테스트
- [ ] FlushPolicy 각 정책별 단위 테스트

### 5.3 수동 검증

1. **GUI 테스트**: `python -m frontend` → 일봉/분봉 차트 정상 표시
2. **백테스트**: `python -m backend.scripts.run_backtest --ticker AAPL --days 30`
3. **Gap Fill**: 누락 티커 조회 시 자동 API 호출 확인

---

## 6. 롤백 계획

1. **Git revert**: 해당 커밋들 리버트
2. **SQLite fallback**: `chart_data_service.py`의 기존 SQLite 로직 활성화
3. **Dual Write 복원**: `massive_loader.py` 롤백

---

## 7. 확정된 설계 결정

| 항목 | 결정 |
|------|------|
| **Gap Fill** | `auto_fill=True` 기본값 (항상 누락 데이터 자동 보충) |
| **보조지표** | On-Demand 생산 + 생산 시 모두 저장 |
| **스코어 저장** | FlushPolicy 패턴 (설정 기반 유연화) |
| **SQLite 제거** | 이번 PR에서 제거 |
| **MassiveLoader** | 예외 (현재 역할 유지) |

---

## 8. 관련 문서

- [11-001_parquet_migration.md](file:///d:/Codes/Sigma9-0.1/docs/Plan/refactor/11-001_parquet_migration.md) - Phase 1 (완료)
- [REFACTORING.md](file:///d:/Codes/Sigma9-0.1/docs/Plan/refactor/REFACTORING.md) - 리팩터링 가이드
- [parquet_manager.py](file:///d:/Codes/Sigma9-0.1/backend/data/parquet_manager.py) - 기존 Parquet I/O

---

## 9. 실행 시작 전 체크리스트

새 세션에서 이 계획서를 사용할 때:

- [ ] `@PROJECT_DNA.md` 읽기 (프로젝트 구조 이해)
- [ ] `backend/data/parquet_manager.py` 확인 (기존 I/O 인터페이스)
- [ ] `backend/container.py` 확인 (DI 패턴)
- [ ] `/refactoring-execution` 워크플로우 따라 실행
