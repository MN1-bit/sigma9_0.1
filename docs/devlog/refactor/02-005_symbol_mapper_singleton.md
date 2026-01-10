# 02-005: SymbolMapper 싱글톤 제거 Devlog

> **작성일**: 2026-01-08 15:40
> **관련 계획서**: [02-005_symbol_mapper_singleton.md](../../Plan/refactor/02-005_symbol_mapper_singleton.md)

## 진행 현황

| Step | 상태 | 완료 시간 |
|------|------|----------|
| Step 1 | ✅ 완료 | 15:49 |
| Step 2 | ✅ 완료 | 15:50 |

---

## Step 1: Container에 SymbolMapper 등록

### 변경 사항
- `backend/container.py`:
  - `_create_symbol_mapper()` 팩토리 함수 추가
  - `symbol_mapper = providers.Singleton(...)` 등록

---

## Step 2: get_symbol_mapper() Deprecation Warning 추가

### 변경 사항
- `backend/data/symbol_mapper.py`:
  - `get_symbol_mapper()` 함수에 Deprecation Warning 추가

---

## 최종 검증 결과

| 검증 항목 | 결과 |
|----------|------|
| ruff check | ✅ |
| Container 테스트 | ✅ |

---

## 변경 파일 요약

| 파일 | 변경 유형 | 라인 변화 |
|------|----------|----------|
| `backend/container.py` | 추가 | +17 |
| `backend/data/symbol_mapper.py` | 수정 | +14 |
