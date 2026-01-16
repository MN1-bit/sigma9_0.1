# 02-004: WatchlistStore 싱글톤 제거 Devlog

> **작성일**: 2026-01-08 15:35
> **관련 계획서**: [02-004_watchlist_store_singleton.md](../../Plan/refactor/02-004_watchlist_store_singleton.md)

## 진행 현황

| Step | 상태 | 완료 시간 |
|------|------|----------|
| Step 1 | ✅ 완료 | 15:37 |
| Step 2 | ✅ 완료 | 15:38 |
| Step 3 | ✅ 완료 | 15:39 |

---

## Step 1: Container에 WatchlistStore 등록

### 변경 사항
- `backend/container.py`:
  - `_create_watchlist_store()` 팩토리 함수 추가
  - `watchlist_store = providers.Singleton(...)` 등록

---

## Step 2: routes/scanner.py Container 마이그레이션

### 변경 사항
- `backend/api/routes/scanner.py`:
  - `get_watchlist_store()` → `container.watchlist_store()` 변경

---

## Step 3: get_watchlist_store() Deprecation Warning 추가

### 변경 사항
- `backend/data/watchlist_store.py`:
  - `get_watchlist_store()` 함수에 Deprecation Warning 추가

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
| `backend/api/routes/scanner.py` | 수정 | +2 |
| `backend/data/watchlist_store.py` | 수정 | +14 |
