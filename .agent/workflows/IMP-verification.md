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

## 3. 크기 제한 검증

- [ ] 신규/수정 파일 ≤ **500줄**
- [ ] 신규/수정 클래스 ≤ **30 메서드**
- [ ] 신규/수정 클래스 ≤ **400줄**

```bash
# 라인 수 확인
wc -l backend/**/*.py | sort -n | tail -20
```

---

## 4. 코드 품질 검증

// turbo
```bash
ruff format --check .
ruff check .
mypy backend frontend --ignore-missing-imports
```

---

## 5. 테스트

```bash
pytest tests/ -v
```

---

## 6. 수동 검증 (해당 시)

- [ ] `python -m backend` 시작
- [ ] `python -m frontend` 시작
- [ ] 주요 기능 동작 확인

---

## 7. Devlog 최종 업데이트

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

## 8. 아키텍처/마스터플랜 대조 (필수)

// turbo
참조 문서:
```
.agent\Ref\archt.md   ← 모듈 구조, 데이터 파이프라인
.agent\Ref\MPlan.md   ← 마일스톤, Tech Stack
```

대조 체크리스트:
- [ ] 신규/수정 모듈이 `archt.md` 레이어 규칙 준수?
- [ ] 데이터 흐름이 `archt.md` 다이어그램과 일치?
- [ ] 구현이 `MPlan.md` 마일스톤 범위 내?
- [ ] Tech Stack 변경 시 `MPlan.md` 동기화 필요?

---

## 9. 핵심 문서 업데이트 (필수)

> **원칙**: 아키텍처 변경 시 문서 동기화 필수

신규 모듈/API/데이터 명세 변경 시 다음 문서를 반드시 업데이트:

| 문서 | 업데이트 대상 |
|------|-------------|
| `@PROJECT_DNA.md` | 디렉터리 구조, Tech Stack |
| `.agent/Ref/archt.md` | 모듈 구조, 데이터 파이프라인 다이어그램 |
| `.agent/Ref/MPlan.md` | Tech Stack, 완료 마일스톤 |

체크리스트:
- [ ] `@PROJECT_DNA.md` - 해당 섹션 업데이트
- [ ] `.agent/Ref/archt.md` - 해당 섹션 업데이트
- [ ] `.agent/Ref/MPlan.md` - 해당 섹션 업데이트

---

**다음**: 커밋/PR 또는 완료
