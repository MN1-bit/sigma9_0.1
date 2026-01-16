# IMP-planning.md

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `.agent/workflows/IMP-planning.md` |
| **역할** | 기능 구현 계획서 작성 워크플로우 |
| **라인 수** | 178 |

## 핵심 규칙

### 레이어 의존성
```
backend.api → backend.core → backend.strategies → backend.data → backend.broker
(상위 → 하위만 허용)
```

### DI 패턴
- 금지: `_instance`, `get_*_instance()`
- 필수: Container 등록 + 주입

### 크기 제한
| 대상 | 제한 |
|------|------|
| 파일 | ≤ 1000줄 |
| 클래스 | ≤ 30 메서드, ≤ 400줄 |

### 바퀴 재발명 금지
- PyPI/GitHub 검색 후 계획서에 결과 기록 필수

## 계획서 템플릿
- 경로: `docs/Plan/impl/{기능명}_plan.md`
- **사용자 승인 후 코드 작성**
