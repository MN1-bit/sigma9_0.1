---
description: 일반 개발 워크플로우
---

# Development Workflow

> **Mandatory**: Plan  Execute  Devlog (incremental)

## 1. Pre-Step

// turbo
Read: `@PROJECT_DNA.md`, `docs/Plan/MASTERPLAN.md`, `docs/context/ARCHITECTURE.md`

## 2. Planning

Create: `docs/Plan/steps/step_X.Y_plan.md`

## 3. Execution + Incremental Devlog

### Devlog 정책
| 단위 | 액션 |
|------|------|
| 큰 과정 시작 | `docs/devlog/step_X.Y_report.md` 생성 |
| 작은 과정 완료 | 동일 문서에 행 추가 |
| 큰 과정 완료 | 요약 추가 후 다음 문서 생성 |

### Devlog 최소 형식
```markdown
# Step X.Y Report
| Time | Task | Status | Note |
|------|------|--------|------|
| HH:MM | [작은과정1] |  | 파일명 |
| HH:MM | [작은과정2] |  | 에러내용 |
```

> **BLOCKED**: 다음 Step 진행 전 devlog 필수

## 4. Reference Sync

Update if needed (user confirm):
- `@PROJECT_DNA.md`, `ARCHITECTURE.md`, `MASTERPLAN.md`, `REFACTORING.md`

## 5. Git Checkpoint

// turbo
Major updates or every 2-3h:
```bash
git add -A && git commit -m "checkpoint: [step_X.Y] - [desc]"
```

## 6. QA

// turbo
```bash
ruff format && ruff check . && lint-imports
```
