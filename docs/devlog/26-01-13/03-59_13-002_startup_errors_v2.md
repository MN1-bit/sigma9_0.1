# [13-002] Startup Errors v2 Fix - Devlog

> **작성일**: 2026-01-10 07:24
> **관련 계획서**: [13-002_startup_errors_v2_20260110.md](../../Plan/bugfix/13-002_startup_errors_v2_20260110.md)

## 진행 현황

| Step | 상태 | 완료 시간 |
|------|------|----------|
| Issue #1: StrategyLoader 폴더 지원 | ✅ 완료 | 07:24 |
| Issue #2: load_watchlist_context 삭제 | ✅ 완료 | 07:24 |
| Issue #3: RealtimeScanner data_repository | ✅ 완료 | 07:24 |
| 검증 | ✅ 완료 | 07:25 |

---

## Issue #1: StrategyLoader 폴더 구조 지원

### 변경 사항
- `backend/core/strategy_loader.py`:
  - `discover_strategies()`: 폴더 구조 전략 탐색 로직 추가 (L159-170)
  - `load_strategy()`: 파일/폴더 분기 처리 추가 (L215-227)
  - `spec_from_file_location`: `filepath` → `module_path` 수정 (L246-248)

### 검증 결과
```
[StrategyLoader] 발견된 전략: ['seismograph']
```

---

## Issue #2: load_watchlist_context 호출 삭제

### 변경 사항
- `backend/core/ignition_monitor.py`:
  - L111-112: `load_watchlist_context()` 호출 제거

### 원인
- Dead Code 분석 결과 `_watchlist_context`를 읽는 코드가 없음
- IgnitionMonitor가 자체 `watchlist_data`에서 직접 처리

---

## Issue #3: RealtimeScanner data_repository 수정

### 변경 사항
- `backend/startup/realtime.py`:
  - L285-292: DataRepository 인스턴스 생성
  - L297: `db=db` → `data_repository=repo`

---

## 최종 검증 결과

| 검증 항목 | 결과 |
|----------|------|
| StrategyLoader discover | ✅ seismograph 발견 |
| IgnitionMonitor import | ✅ |
| realtime import | ✅ |

## 수정 파일 요약

| 파일 | 수정 내용 |
|------|----------|
| `backend/core/strategy_loader.py` | 폴더 구조 전략 탐색/로드 지원 |
| `backend/core/ignition_monitor.py` | load_watchlist_context 호출 제거 |
| `backend/startup/realtime.py` | db → data_repository 수정 |
