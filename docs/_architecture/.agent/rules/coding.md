# coding.md

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `.agent/rules/coding.md` |
| **역할** | 코딩 규칙 간소화 버전 |
| **라인 수** | 28 |

## 핵심 규칙

### 파일 제한
- Max lines: **500** (예외: seismograph.py, dashboard.py)
- Max class methods: **30**

### 금지 패턴
- `_instance` 전역 변수
- `get_*_instance()` 함수
- 전역 싱글톤

### 필수 사항
- DI: 신규 서비스 → Container 등록
- Type Hints: 모든 함수
- Comments: ELI5 수준 (한국어)
- Docstrings: Google style

### 품질 게이트
```bash
ruff format && ruff check .
mypy backend frontend
lint-imports
```
