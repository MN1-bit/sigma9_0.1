# refactoring-pr.md

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `.agent/workflows/refactoring-pr.md` |
| **역할** | 리팩터링 PR 제출 워크플로우 |
| **라인 수** | 109 |

## PR 체크리스트

### 기본 체크
- `ruff format --check .` 통과
- `ruff check .` 통과
- `mypy backend frontend` 통과

### 리팩터링 체크
- `lint-imports` 통과
- 신규 파일 ≤ 500 라인
- 신규 클래스 ≤ 30 메서드
- DI 사용 (Singleton 금지)

## 커밋 컨벤션
```
<type>(<scope>): <description>
```

### Type
| Type | 설명 |
|------|------|
| `refactor` | 리팩터링 |
| `feat` | 새 기능 |
| `fix` | 버그 수정 |

## PR 제목 형식
```
[REFACTOR] {대상명}: {간단한 설명}
```
