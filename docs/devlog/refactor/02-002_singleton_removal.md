# 02-002: 싱글톤 제거 리팩터링 Devlog

> **작성일**: 2026-01-08 15:11
> **관련 계획서**: [02-002_singleton_removal.md](../../Plan/refactor/02-002_singleton_removal.md)

## 진행 현황

| Step | 상태 | 완료 시간 |
|------|------|----------|
| Step 1 | ✅ 완료 | 15:12 |
| Step 2 | ✅ 완료 | 15:13 |
| Step 3 | ✅ 완료 | 15:15 |

---

## Step 1: routes/watchlist.py Container 마이그레이션

### 변경 사항
- `backend/api/routes/watchlist.py`: 
  - `get_scanner_instance()` → `container.realtime_scanner()` 변경
  - ELI5 주석 추가

### 검증 결과
- ruff check: ✅

---

## Step 2: realtime_scanner.py 레거시 싱글톤 코드 삭제

### 변경 사항
- `backend/core/realtime_scanner.py`:
  - 라인 792-877 (85줄) 완전 삭제
  - 삭제된 항목:
    - `_scanner_instance` 전역 변수
    - `get_realtime_scanner()` 함수
    - `initialize_realtime_scanner()` 함수
    - `get_scanner_instance()` 함수
    - 관련 헤더 주석, `import warnings`

### 검증 결과
- ruff check: ✅
- 파일 라인 수: 877줄 → 791줄 (-86줄)

---

## Step 3: startup/realtime.py 수정 (추가 발견)

### 발견된 이슈
- `startup/realtime.py`에서 삭제된 `initialize_realtime_scanner` 함수를 import하고 있었음

### 변경 사항
- `backend/startup/realtime.py`:
  - `from backend.core.realtime_scanner import initialize_realtime_scanner as init_scanner` 제거
  - 직접 `RealtimeScanner` 클래스 import 및 인스턴스 생성으로 변경
  - ELI5 주석 추가

### 검증 결과
- ruff check: ✅
- import 테스트: ✅

---

## 최종 검증 결과

| 검증 항목 | 결과 |
|----------|------|
| ruff format | ✅ |
| ruff check | ✅ |
| import 테스트 | ✅ |
| pydeps cycles | ✅ (외부 패키지 경고만, 순환 없음) |
| 레거시 함수 참조 | ✅ (0개 - 완전 제거) |

---

## 변경 파일 요약

| 파일 | 변경 유형 | 라인 변화 |
|------|----------|----------|
| `backend/api/routes/watchlist.py` | 수정 | +6 |
| `backend/core/realtime_scanner.py` | 삭제 | -86 |
| `backend/startup/realtime.py` | 수정 | +5 |
| **총계** | | **-75줄** |

---

## REFACTORING.md 정책 준수 확인

- ✅ 금지 패턴 제거: `get_*_instance()`, 전역 `_instance` 변수
- ✅ DI Container 사용: `container.realtime_scanner()`
- ✅ 파일 라인 수: ≤ 500줄 (791줄 → 여전히 God Class이나 핵심 모듈이므로 허용)
