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
✓ 신규 파일 ≤ 1000줄?
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

### 4.1 기존 에러 분석 (Sub-Phase)

> ⚠️ **기존 에러를 무시하고 넘어가지 않는다**

수정 대상 파일에 기존 lint 에러가 발견될 경우:

1. **에러 분석**
   - 에러 목록 전체 출력
   - 각 에러의 수정 가능 여부 판단

2. **계획서 업데이트**
   - 발견된 기존 에러를 계획서에 추가
   - 수정 범위: 현재 작업과 관련된 에러 + 자동 수정 가능 에러

3. **수정 실행**
   | 에러 유형 | 조치 |
   |----------|------|
   | F401 (unused import) | 즉시 제거 |
   | E722 (bare except) | `Exception`으로 변경 |
   | E501 (line too long) | 가능시 분할 |
   | 복잡한 리팩터링 | 별도 이슈로 분리 |

4. **검증**
   ```bash
   ruff check {파일} --fix  # 자동 수정 가능 항목
   ruff check {파일}        # 최종 확인 (All checks passed!)
   ```

> **BLOCKED**: lint 에러 0건 확인 후 다음 Step 진행

## 5. 완료 후

`/IMP-verification` 실행

---

**다음**: `/IMP-verification`
