# 02-003: IgnitionMonitor 싱글톤 제거 Devlog

> **작성일**: 2026-01-08 15:31
> **관련 계획서**: [02-003_ignition_monitor_singleton.md](../../Plan/refactor/02-003_ignition_monitor_singleton.md)

## 진행 현황

| Step | 상태 | 완료 시간 |
|------|------|----------|
| Step 1 | ✅ 완료 | 15:32 |
| Step 2 | ✅ 완료 | 15:33 |
| Step 3 | ✅ 완료 | 15:34 |

---

## Step 1: routes/ignition.py Container 마이그레이션

### 변경 사항
- `backend/api/routes/ignition.py`:
  - 3곳 `get_ignition_monitor()` → `container.ignition_monitor()` 변경
  - ELI5 주석 추가

### 검증 결과
- ruff check: ✅

---

## Step 2: startup/realtime.py 직접 클래스 생성으로 변경

### 변경 사항
- `backend/startup/realtime.py`:
  - `initialize_ignition_monitor as init_monitor` import 제거
  - 직접 `IgnitionMonitor` 클래스 import 및 인스턴스 생성

### 검증 결과
- ruff check: ✅

---

## Step 3: ignition_monitor.py 레거시 싱글톤 코드 삭제

### 변경 사항
- `backend/core/ignition_monitor.py`:
  - 라인 445-506 (62줄) 완전 삭제
  - 삭제된 항목:
    - `_monitor_instance` 전역 변수
    - `get_ignition_monitor()` 함수
    - `initialize_ignition_monitor()` 함수
    - 관련 헤더 주석, `import warnings`

### 검증 결과
- ruff check: ✅
- 파일 라인 수: 506줄 → 444줄 (-62줄)

---

## 최종 검증 결과

| 검증 항목 | 결과 |
|----------|------|
| ruff check | ✅ |
| import 테스트 | ✅ |
| 레거시 함수 참조 | ✅ (0개 - 완전 제거) |

---

## 변경 파일 요약

| 파일 | 변경 유형 | 라인 변화 |
|------|----------|----------|
| `backend/api/routes/ignition.py` | 수정 | +6 |
| `backend/core/ignition_monitor.py` | 삭제 | -62 |
| `backend/startup/realtime.py` | 수정 | +4 |
| **총계** | | **-52줄** |
