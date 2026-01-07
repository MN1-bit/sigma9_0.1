---
description: 리팩터링 검증 워크플로우 (PR 제출 전 품질 검증)
---

# 리팩터링 검증

> **전제조건**: `/refactoring-execution` 워크플로우 완료

## 1. 자동화 도구 검증

// turbo
다음 명령어를 **순차적으로** 실행합니다:

```bash
# 1. 코드 포맷 검사
ruff format --check .

# 2. 린트 검사
ruff check .

# 3. 타입 검사
mypy backend frontend --ignore-missing-imports

# 4. Import 경계 검증 (필수 통과)
lint-imports

# 5. 순환 의존성 검출
pydeps backend --only backend --show-cycles --no-output
```

> **⚠️ CRITICAL**: `lint-imports` 또는 `pydeps --show-cycles` 실패 시 PR 제출 불가

## 2. Architecture Tests

// turbo
```bash
pytest tests/architecture/ -v
```

### 검증 항목
- [ ] 신규 파일 ≤ 500 라인
- [ ] 신규 클래스 ≤ 30 메서드, ≤ 400 라인
- [ ] Singleton 패턴 미사용 (`_instance`, `get_*_instance()` 금지)

## 3. 기능 테스트

```bash
pytest tests/ -v
```

실패 테스트가 있으면 수정 후 재실행합니다.

## 4. 수동 검증 (해당되는 경우)

GUI 관련 리팩터링 시:
- [ ] 백엔드 시작: `python -m backend`
- [ ] 프론트엔드 시작: `python -m frontend`
- [ ] 주요 기능 동작 확인

## 5. Devlog 최종 업데이트

`docs/devlog/refactor/{대상명}.md` 에 검증 결과를 추가합니다:

```markdown
## 최종 검증 결과

| 검증 항목 | 결과 |
|----------|------|
| ruff format | ✅ |
| ruff check | ✅ |
| mypy | ✅ |
| lint-imports | ✅ |
| pydeps cycles | ✅ (순환 없음) |
| pytest | ✅ (N passed) |
| 수동 테스트 | ✅ |
```

## 6. REFACTORING.md 상태 업데이트

`docs/context/REFACTORING.md` 섹션 2 우선순위 테이블에서 해당 항목 상태를 업데이트합니다:
- `📋 대기` → `🔄 진행 중` → `✅ 완료`

---

**다음 단계**: `/refactoring-pr` 워크플로우 실행
