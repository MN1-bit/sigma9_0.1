---
description: 기능 구현 실행 (매 Step devlog 필수)
---

# IMP-execution

> **전제**: `/IMP-planning` 완료 및 승인

## 1. 실행 전 체크

// turbo
- 계획서 `docs/Plan/impl/` 존재 확인
- 사용자 승인 완료 확인

## 2. Step 단위 실행

### 코딩 규칙
- **ELI5 주석** 필수 (복잡한 로직)
- **Type hints** 필수
- **Docstring** 공개 API 필수

### 스파게티 방지 체크 (매 Step)
```
✓ 신규 파일 ≤ 500줄?
✓ 신규 클래스 ≤ 30 메서드?
✓ Singleton get_*_instance() 미사용?
✓ DI Container 사용?
```

## 3. Devlog 작성 (매 Step 필수)

경로: `docs/devlog/impl/{기능명}.md`

```markdown
# [기능명] Devlog

> **작성일**: YYYY-MM-DD
> **계획서**: [link](../../Plan/impl/{기능명}_plan.md)

## 진행 현황

| Step | 상태 | 시간 |
|------|------|------|
| Step 1 | ✅ | HH:MM |
| Step 2 | 🔄 | - |

---

## Step 1: [설명]

### 변경 사항
- `path/file.py`: 변경 내용

### 검증
- lint: ✅/❌
```

> **BLOCKED**: 다음 Step 전 devlog 작성 필수

## 4. 중간 검증

// turbo
매 Step 후:
```bash
ruff check .
lint-imports
```

## 5. 완료 후

`/IMP-verification` 실행

---

**다음**: `/IMP-verification`
