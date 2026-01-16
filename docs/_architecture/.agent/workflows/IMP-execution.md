# IMP-execution.md

## 기본 정보
| 항목 | 값 |
|------|---|
| **경로** | `.agent/workflows/IMP-execution.md` |
| **역할** | 기능 구현 실행 워크플로우 |
| **라인 수** | 106 |

## 워크플로우 단계

### 1. 실행 전 체크
- 계획서 `docs/Plan/impl/` 존재 확인
- 사용자 승인 완료 확인

### 2. Step 단위 실행
- ELI5 주석 필수
- Type hints 필수
- 스파게티 방지 체크 (≤1000줄, ≤30 메서드)

### 3. Devlog 작성 (매 Step 필수)
- 경로: `docs/devlog/impl/{기능명}.md`
- 다음 Step 전 devlog 작성 **필수**

### 4. 중간 검증
```bash
ruff check .
lint-imports
```

### 5. 완료 후
→ `/IMP-verification` 실행
