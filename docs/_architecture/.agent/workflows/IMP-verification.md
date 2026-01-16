# IMP-verification.md

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `.agent/workflows/IMP-verification.md` |
| **역할** | 구현 검증 워크플로우 (PR 전 필수) |
| **라인 수** | 138 |

## 검증 단계

### 1. 레이어 의존성 검증 (CRITICAL)
```bash
lint-imports
pydeps backend --only backend --show-cycles --no-output
```

### 2. DI 패턴 검증
- `get_*_instance()` 미사용
- 전역 `_instance` 미사용

### 3. 크기 제한 검증
- 신규/수정 파일 ≤ 500줄
- 신규/수정 클래스 ≤ 30 메서드

### 4. 코드 품질 검증
```bash
ruff format --check .
ruff check .
mypy backend frontend
```

### 5. 테스트
```bash
pytest tests/ -v
```

### 6. 핵심 문서 업데이트
- `@PROJECT_DNA.md`
- `.agent/Ref/archt.md`
- `.agent/Ref/MPlan.md`
