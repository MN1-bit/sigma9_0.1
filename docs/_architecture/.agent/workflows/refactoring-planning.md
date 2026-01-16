# refactoring-planning.md

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `.agent/workflows/refactoring-planning.md` |
| **역할** | 리팩터링 계획서 작성 워크플로우 |
| **라인 수** | 101 |

## 사전 컨텍스트 확인
- `@PROJECT_DNA.md`
- `docs/context/REFACTORING.md`
- `docs/Plan/refactor/` 기존 계획서

## 바퀴 재발명 금지
- PyPI/GitHub/Stack Overflow 검색 (최소 3곳)
- 결과 → 계획서에 기록 필수
- **검색 없이 직접 구현 = 계획서 반려**

## 영향 분석
- 변경 대상 파일 목록
- 영향받는 모듈
- 순환 의존성 체크 (`pydeps --show-cycles`)
- 위험도 평가

## 계획서 경로
```
docs/Plan/refactor/{RR}-{NNN}_{대상명}.md
```

## 사용자 승인
**승인 전까지 코드 수정 금지**
