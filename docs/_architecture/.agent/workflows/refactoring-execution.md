# refactoring-execution.md

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `.agent/workflows/refactoring-execution.md` |
| **역할** | 리팩터링 실행 워크플로우 |
| **라인 수** | 90 |

## 전제조건
`/refactoring-planning` 완료 및 사용자 승인

## 워크플로우 단계

### 1. 실행 전 체크
- 계획서 `docs/Plan/refactor/` 존재
- Git 브랜치 생성 (권장: `refactor/{대상명}`)

### 2. Step 단위 실행
- ELI5 수준 상세 주석 필수
- 각 Step 완료 후 즉시 devlog 작성

### 3. Devlog 작성 (매 Step 필수)
- 경로: `docs/devlog/refactor/{RR}-{NNN}_{대상명}.md`
- **다음 Step 전 devlog 작성 필수**

### 4. 중간 검증
```bash
lint-imports
pydeps backend --show-cycles --no-output
```

### 5. 완료 후
→ `/refactoring-verification` 실행
