# __main__.py

## 기본 정보

| 항목 | 값 |
|------|---|
| **경로** | `frontend/__main__.py` |
| **역할** | `python -m frontend` 실행 시 진입점 |
| **라인 수** | 8 |
| **바이트** | 130 |

## 내용

```python
from .main import main

if __name__ == "__main__":
    main()
```

> 📌 `main.py`의 `main()` 함수를 호출하는 단순 래퍼

## 🔗 외부 연결 (Connections)

### Imports From (이 파일이 가져오는 것)
| 파일 | 가져오는 항목 |
|------|--------------|
| `frontend/main.py` | `main()` |

### Imported By (이 파일을 가져가는 것)
| 파일 | 사용 목적 |
|------|----------|
| (없음) | CLI 진입점으로 직접 실행됨 |

### Data Flow
```mermaid
graph LR
    A["python -m frontend"] --> B["__main__.py"]
    B --> C["main.py::main()"]
```

## 실행 방법

```bash
python -m frontend
```

## 외부 의존성
- (없음 - main.py에 위임)
