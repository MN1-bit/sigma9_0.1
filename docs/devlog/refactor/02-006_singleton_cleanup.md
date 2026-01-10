# 02-006 싱글톤 정리 Devlog

> **작성일**: 2026-01-10 05:42  
> **관련 계획서**: [02-006_singleton_cleanup.md](../Plan/refactor/02-006_singleton_cleanup.md)

## 진행 현황

| Step | 상태 | 완료 시간 |
|------|------|----------|
| Step 1: watchlist_store.py 레거시 제거 | ✅ 완료 | 05:38 |
| Step 2: symbol_mapper.py 레거시 제거 | ✅ 완료 | 05:40 |
| 검증 | ✅ 완료 | 05:42 |

---

## Step 1: watchlist_store.py 레거시 제거

### 변경 사항
- `backend/data/watchlist_store.py`: 97줄 삭제
  - `_store_instance` 전역 변수 제거
  - `get_watchlist_store()` 함수 제거
  - `save_watchlist()`, `load_watchlist()`, `merge_watchlist()` 편의 함수 제거

### 아카이브
- `docs/archive/legacy_watchlist_store_singleton.py`: 레거시 코드 보관

---

## Step 2: symbol_mapper.py 레거시 제거

### 변경 사항
- `backend/data/symbol_mapper.py`: 39줄 삭제
  - `_mapper_instance` 전역 변수 제거
  - `get_symbol_mapper()` 함수 제거
  - `MASSIVE_TO_IBKR()`, `IBKR_TO_MASSIVE()` 편의 함수 제거

### 아카이브
- `docs/archive/legacy_symbol_mapper_singleton.py`: 레거시 코드 보관

---

## 검증 결과

| 검증 항목 | 결과 |
|----------|------|
| lint-imports | ✅ |
| WatchlistStore 모듈 로드 | ✅ |
| SymbolMapper 모듈 로드 | ✅ |
| Container 주입 테스트 | ✅ |

---

## 요약

- **삭제 라인**: 136줄 (watchlist_store 97줄 + symbol_mapper 39줄)
- **아카이브 파일**: 2개 생성
- **외부 사용처**: 없음 (사전 검색으로 확인)
