# Step 2.5 Report: Strategy Loader & Plugin System

> **작성일**: 2025-12-18  
> **소요 시간**: ~20분  
> **상태**: ✅ 완료

---

## 1. 작업 요약

`StrategyLoader` 플러그인 시스템을 구현하여 전략을 동적으로 로드/언로드/리로드할 수 있게 했습니다.
GUI에 전략 선택 드롭다운을 추가하여 런타임에 전략을 교체할 수 있습니다.

---

## 2. 새로 생성된 파일

| 파일 | 설명 |
|------|------|
| [strategy_loader.py](file:///d:/Codes/Sigma9-0.1/backend/core/strategy_loader.py) | 전략 플러그인 로더 |

---

## 3. 수정된 파일

| 파일 | 변경 내용 |
|------|----------|
| [dashboard.py](file:///d:/Codes/Sigma9-0.1/frontend/gui/dashboard.py) | 전략 드롭다운 + 리로드 버튼 추가 |
| [test_strategies.py](file:///d:/Codes/Sigma9-0.1/tests/test_strategies.py) | `TestStrategyLoader` 테스트 클래스 추가 |
| [development_steps.md](file:///d:/Codes/Sigma9-0.1/docs/Plan/steps/development_steps.md) | Step 2.5 완료 표시 |

---

## 4. 구현된 기능

### 4.1 StrategyLoader 클래스

| 메서드 | 설명 |
|--------|------|
| `discover_strategies()` | `strategies/` 폴더의 전략 파일 자동 탐지 (`_` 시작 제외) |
| `load_strategy(name)` | `importlib`로 동적 로드 + 인스턴스 캐싱 |
| `reload_strategy(name)` | 핫 리로드 (캐시 + `sys.modules` 제거 후 재로드) |
| `get_strategy(name)` | 캐시된 인스턴스 반환 |
| `list_loaded()` | 로드된 전략 메타정보 목록 |
| `unload_strategy(name)` | 전략 언로드 |

### 4.2 GUI 전략 선택

```
┌─ Top Panel ─────────────────────────────────────────────────┐
│ ⚡ Sigma9 | Connect | Start | Stop | Strategy: [▼] 🔄 | KILL │
└─────────────────────────────────────────────────────────────┘
```

- `QComboBox`: 사용 가능한 전략 목록 표시
- `🔄 Reload`: 선택된 전략 핫 리로드

---

## 5. 검증 결과

### 5.1 문법 검사 ✅

```powershell
python -m py_compile backend/core/strategy_loader.py
python -m py_compile frontend/gui/dashboard.py
# (에러 없음)
```

### 5.2 Self-Test ✅

```
============================================================
StrategyLoader 테스트
============================================================
[StrategyLoader] 초기화 완료: D:\Codes\Sigma9-0.1\backend\strategies

[Test 1] discover_strategies()
  발견된 전략: ['random_walker', 'seismograph']

[Test 2] load_strategy('random_walker')
  로드 성공: Random Walker v1.0.0

[Test 5] reload_strategy('random_walker')
  리로드 성공: Random Walker

[Test 6] load_strategy('nonexistent')
  예상된 에러 발생: FileNotFoundError

============================================================
모든 테스트 완료! ✓
============================================================
```

### 5.3 GUI 검증 ✅

```
[StrategyLoader] 초기화 완료
[StrategyLoader] 발견된 전략: ['random_walker', 'seismograph']
[StrategyLoader] 전략 클래스 발견: RandomWalkerStrategy
[StrategyLoader] 로드 완료: Random Walker v1.0.0
[DEBUG] Sigma9Dashboard window created
```

---

## 6. 다음 단계

- **Step 2.6**: Backtesting Framework (Basic)
  - `BacktestEngine` 구현
  - 히스토리 데이터 리플레이
  - 성과 리포트 생성
