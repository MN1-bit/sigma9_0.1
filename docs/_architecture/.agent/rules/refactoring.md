# refactoring.md (rules)

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `.agent/rules/refactoring.md` |
| **역할** | 리팩터링 규칙 간소화 버전 |
| **라인 수** | 11 |

## 필수 규칙
1. **Doc-First**: `docs/Plan/refactor/`에 계획 먼저
2. **Devlog**: `docs/devlog/refactor/`에 Step별 보고
3. **QA**: `lint-imports` + `pydeps --show-cycles` 필수
4. **No Singleton**: `_instance`, `get_*_instance()` 금지

## 워크플로우 순서
```
/refactoring-planning → /refactoring-execution → /refactoring-verification → /refactoring-pr
```
