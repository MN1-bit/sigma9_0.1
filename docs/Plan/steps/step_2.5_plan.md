# Step 2.5: Strategy Loader & Plugin System 구현 계획

> **작성일**: 2025-12-18  
> **Phase**: 2 (Core Engine)  
> **목표**: 전략 파일을 동적으로 로드/언로드/리로드하는 플러그인 시스템 구현

---

## 1. 배경 및 목적

`masterplan.md` Section 13에 정의된 **Modular Strategy Architecture**를 구현합니다.

- **Hot Reload**: 서버 재시작 없이 전략 파일 교체 가능
- **GUI 연동**: 드롭다운에서 전략 선택 → 즉시 적용
- **타입 안전**: ABC 인터페이스로 필수 메서드 강제

---

## 2. 현재 상태 분석

| 파일 | 상태 | 비고 |
|------|------|------|
| `strategy_base.py` | ✅ 완료 | Signal + StrategyBase ABC 구현됨 |
| `_template.py` | ✅ 완료 | 새 전략 개발 템플릿 존재 |
| `seismograph.py` | ✅ 완료 | 메인 전략 구현됨 |
| `random_walker.py` | ✅ 완료 | 테스트용 전략 존재 |
| `strategy_loader.py` | ❌ 미구현 | **이번 단계에서 구현** |

---

## 3. Proposed Changes

### 3.1 Core Module

#### [NEW] [strategy_loader.py](file:///d:/Codes/Sigma9-0.1/backend/core/strategy_loader.py)

전략 플러그인 로더 클래스 구현:

```
StrategyLoader
├── __init__(strategy_dir: str = "strategies")
│   └── strategies: Dict[str, StrategyBase]  # 로드된 전략 캐시
│
├── discover_strategies() → List[str]
│   └── strategies/ 폴더의 모든 .py 파일 탐색 ('_'로 시작하는 파일 제외)
│
├── load_strategy(name: str) → StrategyBase
│   └── importlib.util로 동적 로드 → StrategyBase 서브클래스 탐색 → 인스턴스화
│
├── reload_strategy(name: str) → StrategyBase
│   └── 기존 인스턴스 삭제 → sys.modules 캐시 삭제 → 재로드
│
├── get_strategy(name: str) → Optional[StrategyBase]
│   └── 캐시에서 로드된 전략 반환
│
└── list_loaded() → List[dict]
    └── 로드된 전략들의 메타정보 (name, version, description) 반환
```

**핵심 구현 포인트**:
- `importlib.util.spec_from_file_location()` 사용
- `StrategyBase` 서브클래스 자동 탐지
- `initialize()` 자동 호출

---

### 3.2 Frontend (GUI)

#### [MODIFY] [dashboard.py](file:///d:/Codes/Sigma9-0.1/frontend/gui/dashboard.py)

Control Panel에 전략 선택 드롭다운 추가:

```python
# Top Panel에 추가
self.strategy_combo = QComboBox()
self.reload_btn = QPushButton("🔄 Reload")
```

| 위젯 | 기능 |
|------|------|
| `QComboBox` | 사용 가능한 전략 목록 표시 |
| `QPushButton` | 선택된 전략 핫 리로드 |

---

### 3.3 Tests

#### [MODIFY] [test_strategies.py](file:///d:/Codes/Sigma9-0.1/tests/test_strategies.py)

`TestStrategyLoader` 클래스 추가:

| 테스트 | 검증 내용 |
|--------|----------|
| `test_discover_strategies` | `seismograph`, `random_walker` 발견 확인 |
| `test_discover_excludes_underscore` | `_template.py` 제외 확인 |
| `test_load_strategy_success` | 정상 로드 + `StrategyBase` 인스턴스 확인 |
| `test_load_strategy_not_found` | 없는 파일 시 `FileNotFoundError` |
| `test_reload_strategy` | 리로드 후 새 인스턴스 확인 |
| `test_get_strategy_cached` | 캐시된 인스턴스 반환 확인 |

---

## 4. Verification Plan

### 4.1 Syntax Check

```powershell
cd d:\Codes\Sigma9-0.1
python -m py_compile backend/core/strategy_loader.py
```

### 4.2 Unit Tests

```powershell
cd d:\Codes\Sigma9-0.1
pytest tests/test_strategies.py -v -k "StrategyLoader"
```

### 4.3 Integration Test (Manual)

1. GUI 실행:
   ```powershell
   cd d:\Codes\Sigma9-0.1
   .venv\Scripts\python -m frontend.main
   ```

2. Top Panel에서 전략 드롭다운 확인
3. `seismograph` 선택 → 로드 확인
4. `🔄 Reload` 버튼 클릭 → 리로드 확인

---

## 5. 의존성

추가 설치 필요 없음 (Python 표준 라이브러리 `importlib` 사용)

---

## 6. 다음 단계

- **Step 2.6**: Backtesting Framework (Basic)
