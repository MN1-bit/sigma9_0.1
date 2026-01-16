# [02-005] WatchlistStore DI 마이그레이션 (통합)

> **작성일**: 2026-01-17 05:04 | **예상**: 30min | **위험도**: 낮음

---

## 1. 목표 (PRD 구조)

### 1.1 배경 (Problem)
- `watchlist_store.py`에 레거시 Singleton 패턴 존재:
  - `WatchlistWriter._instance` (L67-75)
  - `_default_store` + `_get_default_store()` (L461-469)
- DI Container에 `WatchlistStore` 이미 등록되어 있으나, 레거시 코드 잔존
- `/IMP-verification` DI 패턴 검증에서 위반으로 감지됨

### 1.2 목표 (Goal)
- `_instance` 패턴 제거하고 DI Container 일관성 확보
- `WatchlistWriter`도 Container에 등록하여 수명 주기 통합 관리
- **레거시 편의 함수 완전 삭제** (~80줄 dead code 제거)

### 1.3 User Stories
- 개발자로서, `_instance` 검색 시 0건이 되어 DI 규칙 준수를 확인하고 싶다

### 1.4 Functional Requirements
1. `WatchlistWriter`를 Container에 Singleton으로 등록
2. `_writer` 전역 변수 제거
3. `_default_store`, `_get_default_store()` 삭제
4. `load_watchlist()`, `save_watchlist()`, `merge_watchlist()` 완전 삭제

### 1.5 Non-Goals (범위 제외)

#### 🚫 Out of Scope
- ❌ `WatchlistStore` 기능 변경 — 순수 DI 마이그레이션만

---

## 2. 레이어 체크

- [x] 레이어 규칙 위반 없음 (backend.data 내부 변경)
- [x] 순환 의존성 없음
- [x] DI Container 등록 필요: **예** (WatchlistWriter)

---

## 3. 기존 솔루션 검색 결과

| 솔루션 | 출처 | 채택 | 사유 |
|--------|------|------|------|
| WatchlistStore in container.py | 기존 코드 | ✅ | 이미 등록됨 (L334-346) |

### 레거시 함수 사용 현황
```bash
grep -r "load_watchlist\|save_watchlist\|merge_watchlist" --include="*.py" .
# 결과: 0건 (정의 파일 제외) → 안전하게 삭제 가능
```

---

## 4. 변경 파일

| 파일 | 유형 | 변경 내용 |
|------|-----|----------|
| `backend/container.py` | 수정 | WatchlistWriter 등록 |
| `backend/data/watchlist_store.py` | 수정 | `_instance` 제거, L454-534 삭제 (~80줄) |

---

## 5. Tasks (2레벨 분해)

- [ ] 1.0 WatchlistWriter Container 등록
  - [ ] 1.1 `container.py`에 `watchlist_writer` Singleton 추가
  - [ ] 1.2 `WatchlistWriter.__new__` → 일반 `__init__`으로 변경
  - [ ] 1.3 `_instance`, `_lock` 클래스 변수 제거

- [ ] 2.0 WatchlistStore 정리
  - [ ] 2.1 `_writer` 전역 변수 제거
  - [ ] 2.2 `WatchlistStore.__init__`에 writer 주입 파라미터 추가
  - [ ] 2.3 `container.py`의 `watchlist_store` 팩토리가 writer 주입하도록 수정

- [ ] 3.0 레거시 코드 삭제
  - [ ] 3.1 L454-534 전체 삭제 (`_default_store`, 편의 함수 등)

- [ ] 4.0 검증
  - [ ] 4.1 `grep _instance backend/data/` 0건 확인
  - [ ] 4.2 `ruff check backend/data/watchlist_store.py` 0 에러

---

## 6. 검증

- [ ] `grep -r "_instance" backend/data/` 0건
- [ ] `ruff check backend/data/watchlist_store.py` 0 에러
- [ ] `python -c "from backend.container import container; print(container.watchlist_writer())"` 성공

---

## 7. 롤백 계획

Git revert로 원상복구 가능 (단순 리팩터링)

---

## ✅ 승인 대기

> **다음**: 승인 후 `/IMP-execution`
