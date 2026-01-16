---
description: 리팩터링 실행 워크플로우 (매 스텝마다 devlog 보고서 작성 강제)
---

# 리팩터링 실행

> **전제조건**: `/refactoring-planning` 워크플로우 완료 및 사용자 승인

## 1. 실행 전 체크

// turbo
다음을 확인합니다:
- 계획서가 `docs/Plan/refactor/` 에 존재하는지
- 계획서가 사용자 승인을 받았는지
- Git 브랜치가 적절히 생성되었는지 (권장: `refactor/{대상명}`)

## 2. Step 단위 실행

계획서의 각 Step을 **순차적으로** 실행합니다.

### 각 Step 실행 규칙

1. **Step 시작 전**: 해당 Step 내용을 계획서에서 확인
2. **코드 수정**: ELI5 수준의 상세한 주석 포함 필수
3. **Step 완료 후**: 즉시 devlog 작성 (아래 형식)

## 3. Task Progress Tracking (필수)

> **원칙**: 매 Sub-task 완료 시 계획서의 체크박스 업데이트

### 마킹 절차
1. Sub-task 완료
2. 계획서 파일에서 `- [ ] X.X` → `- [x] X.X` 변경
3. Devlog에 완료 기록
4. 다음 Sub-task 진행

### 예시
```diff
- - [ ] 1.1 모듈 분석
+ - [x] 1.1 모듈 분석
  - [ ] 1.2 의존성 정리
```

> ⚠️ **마킹 없이 다음 Task 진행 금지**

## 4. Devlog 작성 (매 Step 필수)

경로: `docs/devlog/{yy-mm-dd}/{hh-mm}_{phase}-{step}_{subtitle}.md`
- `yy-mm-dd`: 오늘 날짜
- `hh-mm`: 작성 시각
- `phase-step`: 예) `RR-NNN` (리팩터링 우선순위-순차번호)
- `subtitle`: 간략한 작업 내용

예시: `docs/devlog/26-01-16/16-30_02-001_di_container_cleanup.md`

> **⚠️ 중요**: 다음 Step 진행 전 반드시 devlog를 작성해야 합니다.

### Devlog 형식

```markdown
# [{phase}-{step}] {subtitle} Devlog

> **작성일**: YYYY-MM-DD HH:MM
> **관련 계획서**: [link](../../Plan/{yy-mm-dd}/{hh-mm}_{phase}-{step}_{subtitle}.md)

## 진행 현황

| Step | 상태 | 완료 시간 |
|------|------|----------|
| Step 1 | ✅ 완료 | HH:MM |
| Step 2 | 🔄 진행중 | - |
| Step 3 | 📋 대기 | - |

---

## Step 1: [설명]

### 변경 사항
- `path/to/file.py`: [변경 내용 요약]

### 발생한 이슈
- (있는 경우) 발생한 문제와 해결 방법

### 검증 결과
- lint-imports: ✅/❌
- 테스트: ✅/❌

---

## Step 2: [설명]
(동일 형식으로 계속...)
```

## 5. 중간 검증 (매 Step 후)

// turbo
각 Step 완료 후 다음을 실행합니다:
```bash
lint-imports
pydeps backend --show-cycles --no-output
```

실패 시 해당 Step에서 수정 완료 후 다음으로 진행합니다.

## 6. Context Checkpoint (Long Task Management)

> **Purpose**: Prevent context window overflow and maintain quality during extended tasks.

### Trigger Conditions
Perform checkpoint when ANY of the following occurs:
- [ ] **200+ lines** of code changes accumulated
- [ ] **3+ files** modified
- [ ] **30 minutes** elapsed since last checkpoint
- [ ] Current Step completed

### Checkpoint Procedure
1. **Update Plan**: Mark current progress with `[x]` in plan document
2. **Write Devlog**: Record changes made so far
3. **Proceed to next step**

> **Effect**: Context compression + external memory → sustained quality in long tasks

## 7. 전체 완료 후

모든 Step 완료 시 `/refactoring-verification` 워크플로우를 실행합니다.

---

**다음 단계**: `/refactoring-verification` 워크플로우 실행
