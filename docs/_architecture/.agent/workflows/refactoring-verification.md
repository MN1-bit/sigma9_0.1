# refactoring-verification.md

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `.agent/workflows/refactoring-verification.md` |
| **역할** | 리팩터링 검증 워크플로우 |
| **라인 수** | 103 |

## 검증 단계

### 1. 자동화 도구 검증
```bash
ruff format --check .
ruff check .
mypy backend frontend
lint-imports          # CRITICAL
pydeps backend --only backend --show-cycles --no-output
```

### 2. Architecture Tests
- 신규 파일 ≤ 500 라인
- 신규 클래스 ≤ 30 메서드
- Singleton 패턴 미사용

### 3. 기능 테스트
```bash
pytest tests/ -v
```

### 4. 수동 검증 (GUI 관련)
- `python -m backend` 시작
- `python -m frontend` 시작

### 5. 핵심 문서 업데이트
- `@PROJECT_DNA.md`
- `.agent/Ref/archt.md`
- `.agent/Ref/MPlan.md`

### 6. REFACTORING.md 상태 업데이트
- `📋 대기` → `🔄 진행 중` → `✅ 완료`

**다음**: `/refactoring-pr` 실행
