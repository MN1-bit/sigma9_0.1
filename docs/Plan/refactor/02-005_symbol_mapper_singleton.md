# 02-005: SymbolMapper 싱글톤 제거 계획서

> **작성일**: 2026-01-08 15:28  
> **우선순위**: 2 (DI Container 후속) | **예상 소요**: 30m | **위험도**: 낮음

---

## 1. 목표

`symbol_mapper.py`의 레거시 싱글톤 패턴 제거 및 Container 등록.

1. 내부 편의 함수에 Deprecation Warning 추가
2. Container에 SymbolMapper 등록
3. 외부 사용처 마이그레이션 (현재 없음 - 내부 사용만)

---

## 2. 영향 분석

### 2.1 변경 대상 파일

| 파일 | 변경 유형 | 변경 내용 |
|------|----------|----------|
| [container.py](file:///d:/Codes/Sigma9-0.1/backend/container.py) | 추가 | SymbolMapper provider 등록 |
| [symbol_mapper.py](file:///d:/Codes/Sigma9-0.1/backend/data/symbol_mapper.py) | 수정 | Deprecation Warning 추가 |

### 2.2 레거시 함수 사용처

```
symbol_mapper.py:243,248 → 내부 편의함수 (massive_to_ibkr, ibkr_to_massive)
```

> **참고**: 외부에서 `get_symbol_mapper()` 직접 호출하는 곳 없음

---

## 3. 실행 계획

### Step 1: Container에 SymbolMapper 등록

**파일**: `backend/container.py`

```python
# 추가
symbol_mapper = providers.Singleton(SymbolMapper)
```

### Step 2: `get_symbol_mapper()` Deprecation Warning 추가

```python
import warnings

def get_symbol_mapper() -> SymbolMapper:
    warnings.warn(
        "get_symbol_mapper()는 deprecated입니다. "
        "container.symbol_mapper() 사용을 권장합니다.",
        DeprecationWarning,
        stacklevel=2,
    )
    global _mapper_instance
    if _mapper_instance is None:
        _mapper_instance = SymbolMapper()
    return _mapper_instance
```

---

## 4. 검증 계획

```bash
ruff check backend/container.py backend/data/symbol_mapper.py
python -c "from backend.data.symbol_mapper import SymbolMapper; print('✅ OK')"
python -c "from backend.container import container; print(container.symbol_mapper())"
```

---

## 5. 롤백 계획

```bash
git checkout -- backend/container.py backend/data/symbol_mapper.py
```
