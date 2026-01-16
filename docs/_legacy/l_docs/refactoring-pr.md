---
description: 리팩터링 PR 제출 워크플로우 (체크리스트 및 커밋 컨벤션)
---

# 리팩터링 PR 제출

> **전제조건**: `/refactoring-verification` 워크플로우 완료

## 1. PR 체크리스트 (필수 확인)

### 기본 체크 (모두 통과 필수)
- [ ] `ruff format --check .` 통과
- [ ] `ruff check .` 통과
- [ ] `mypy backend frontend` 통과

### 리팩터링 체크
- [ ] `lint-imports` 통과 (순환 의존성 없음)
- [ ] Backend ↔ Frontend 분리 유지
- [ ] 신규 파일 ≤ 500 라인
- [ ] 신규 클래스 ≤ 30 메서드
- [ ] Singleton 대신 DI 사용

### 테스트 체크
- [ ] 관련 테스트 추가/수정
- [ ] `pytest tests/` 통과
- [ ] 커버리지 감소 없음

### 문서 체크
- [ ] 공개 API 변경 시 docstring 업데이트
- [ ] 관련 devlog 작성 완료 (`docs/devlog/refactor/`)
- [ ] REFACTORING.md 상태 업데이트

## 2. 커밋 컨벤션

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Type 목록
| Type | 설명 |
|------|------|
| `refactor` | 리팩터링 (기능 변경 없음) |
| `feat` | 새 기능 |
| `fix` | 버그 수정 |
| `test` | 테스트 추가/수정 |
| `docs` | 문서 수정 |

### Scope 목록 (리팩터링용)
| Scope | 대상 |
|-------|------|
| `seismograph` | Seismograph 전략 분리 |
| `dashboard` | Dashboard GUI 분리 |
| `routes` | routes.py 분할 |
| `models` | 데이터 모델 통합 |
| `core` | Core 모듈 그룹화 |
| `di` | DI Container 도입 |
| `interfaces` | 인터페이스 추출 |

### 예시
```
refactor(seismograph): extract score_v3 module

- Move scoring logic to backend/strategies/seismograph/scoring/
- Add ScoringStrategy interface

BREAKING CHANGE: calculate_score() signature changed
```

## 3. PR 제목 형식

```
[REFACTOR] {대상명}: {간단한 설명}
```

예시: `[REFACTOR] seismograph: Extract Score V3 to separate module`

## 4. PR 본문 템플릿

```markdown
## 변경 사항
- 

## 관련 문서
- 계획서: `docs/Plan/refactor/{계획서명}.md`
- Devlog: `docs/devlog/refactor/{보고서명}.md`

## 체크리스트
- [ ] lint-imports 통과
- [ ] pydeps 순환 없음
- [ ] 테스트 통과
- [ ] 문서 업데이트 완료
```

## 5. 최종 확인

PR 제출 전 마지막으로 확인:
1. 모든 체크리스트 항목 ✅
2. 커밋 메시지가 컨벤션 준수
3. 관련 문서(계획서, devlog) 링크 포함
4. REFACTORING.md 상태가 `✅ 완료`로 업데이트됨

---

**워크플로우 완료** 🎉
