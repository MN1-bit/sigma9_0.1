---
description: 구현 검증 (PR/커밋 전 필수)
---

# IMP-verification

> **원칙**: REFACTORING.md 규칙 100% 준수 검증

## 1. 레이어 의존성 검증 (CRITICAL)

// turbo
```bash
# 경계 위반 검출 (필수 통과)
lint-imports

# 순환 의존성 검출 (필수 통과)
pydeps backend --only backend --show-cycles --no-output
```

> **⚠️ 실패 시 머지 불가**

### 레이어 규칙 리마인더
```
backend.api → backend.core → backend.strategies → backend.data → backend.broker
(상위 → 하위만 허용, 역방향 금지)
```

---

## 2. DI 패턴 검증

수동 체크:
- [ ] `get_*_instance()` 패턴 미사용
- [ ] 전역 `_instance` 변수 미사용
- [ ] 신규 서비스 → `container.py`에 등록됨

```bash
# 금지 패턴 검색
grep -r "get_.*_instance\|_instance\s*=" backend/ --include="*.py"
```

---


## 3. 코드 품질 검증

// turbo
```bash
ruff format --check .
ruff check .
mypy backend frontend --ignore-missing-imports
```

---

## 4. 테스트

```bash
pytest tests/ -v
```

---

## 5. 수동 검증 (해당 시)

- [ ] `python -m backend` 시작
- [ ] `python -m frontend` 시작
- [ ] 주요 기능 동작 확인

---

## 6. Devlog 최종 업데이트

```markdown
## 검증 결과

| 항목 | 결과 |
|------|------|
| lint-imports | ✅ |
| pydeps cycles | ✅ |
| DI 패턴 준수 | ✅ |
| 크기 제한 | ✅ |
| ruff | ✅ |
| pytest | ✅ |
```

---

## 7. 아키텍처 문서 대조 (필수)

// turbo
참조 문서:
```
docs/_architecture/_index.md       ← 전체 파일 구조
docs/_architecture/Full_DataFlow.md ← 데이터 흐름 다이어그램
```

대조 체크리스트:
- [ ] 신규/수정 모듈이 `_index.md` 레이어 구조 준수?
- [ ] 데이터 흐름이 `Full_DataFlow.md` 다이어그램과 일치?

---

## 8. 핵심 문서 업데이트 (필수)

> **원칙**: 아키텍처 변경 시 문서 동기화 필수

신규 모듈/API/데이터 명세 변경 시 다음 문서를 반드시 업데이트:

| 문서 | 업데이트 대상 |
|------|-------------|
| `docs/_architecture/_index.md` | 파일 추가/삭제/이동 |
| `docs/_architecture/Full_DataFlow.md` | 데이터 흐름 변경 |
| `docs/_architecture/{레이어}/{파일명}.md` | 코드 변경 시 해당 문서 |

체크리스트:
- [ ] `docs/_architecture/_index.md` - 구조 반영
- [ ] `docs/_architecture/Full_DataFlow.md` - 흐름 동기화 (해당 시)
- [ ] 관련 `docs/_architecture/` 개별 문서 업데이트

---

## 9. 문서 동기화 워크플로우 (필수)

> **원칙**: 모든 작업 완료 시 문서 동기화 필수

### Step 1: Devlog 작성

작업 완료 후 개별 devlog 작성:
```
docs/devlog/{yy-mm-dd}/{hh-mm}_{작업명}.md
```

### Step 2: Full Log History 업데이트

`docs/devlog/full_log_history.md`에 한 줄 추가:

```markdown
| {YYYY-MM-DD HH:MM} | {작업 내용 요약} | `{yy-mm-dd}/{hh-mm}_{작업명}.md` |
```

예시:
```markdown
| 2026-01-16 15:40 | DI Container 리팩터링 | `26-01-16/15-40_di_refactor.md` |
```

### Step 3: Architecture 문서 업데이트

코드 변경 시 해당 파일의 아키텍처 문서 업데이트:

| 변경 유형 | 업데이트 대상 |
|-----------|--------------|
| 신규 파일 생성 | `docs/_architecture/{레이어}/{파일명}.md` 생성 |
| 기존 파일 수정 | 해당 `.md` 문서의 관련 섹션 업데이트 |
| 파일 삭제 | 해당 `.md` 문서를 `_legacy/`로 이동 |

### Step 4: 인덱스 및 데이터플로우 반영

| 문서 | 업데이트 조건 |
|------|-------------|
| `docs/_architecture/_index.md` | 파일 추가/삭제/이동 시 |
| `docs/_architecture/Full_DataFlow.md` | 데이터 흐름 변경 시 |
| `docs/_architecture/Full_DataFlow_Diagram.md` | 의존성/다이어그램 변경 시 |

### 체크리스트

- [ ] Devlog 작성 (`docs/devlog/{yy-mm-dd}/`)
- [ ] `full_log_history.md` 업데이트
- [ ] 관련 `docs/_architecture/` 문서 업데이트
- [ ] `_index.md` 파일 수/구조 반영
- [ ] `Full_DataFlow.md` 데이터 흐름 동기화 (해당 시)

---

**다음**: 커밋/PR 또는 완료
