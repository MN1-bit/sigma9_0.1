# 14-003: 검색창 자동완성/히스토리 및 시간 표시 버그

> **작성일**: 2026-01-13 | **예상**: 60분

---

## 1. 목표

14-001 구현 후 발견된 추가 버그 수정:
1. 자동완성 드롭다운 작동하지 않음
2. Backend time (US East) 표시되지 않음
3. 티커 검색창 히스토리 드롭다운 작동하지 않음

---

## 2. 레이어 체크

- [ ] 레이어 규칙 위반 없음
- [ ] 순환 의존성 없음
- [ ] DI Container 등록 필요: **TBD**

---

## 3. 분석 필요 항목

### 3.1 자동완성 미작동
- `_load_ticker_data_for_search()` 호출 시점 확인
- `DataRepository.get_all_tickers()` 반환값 확인
- `QCompleter` 모델 설정 확인

### 3.2 US East 시간 미표시
- `TimeDisplayWidget` 연결 상태 확인
- Backend heartbeat 수신 확인
- WebSocket 연결 상태 확인

### 3.3 히스토리 드롭다운 미작동
- `_update_combo_items()` 호출 확인
- `ComboBox.addItem()` 동작 확인

---

## 4. 변경 파일 (예상)

| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
| `frontend/gui/dashboard.py` | MODIFY | TBD |
| `frontend/gui/widgets/ticker_search_bar.py` | MODIFY | TBD |
| `frontend/gui/widgets/time_display_widget.py` | MODIFY | TBD |

---

## 5. 실행 단계

### Step 1: 문제 원인 분석
- 로그 확인 및 디버깅

### Step 2: 자동완성 수정

### Step 3: 시간 표시 수정

### Step 4: 히스토리 드롭다운 수정

---

## 6. 검증

### 수동 테스트
1. 앱 실행 → 검색창에 "A" 입력 → 자동완성 드롭다운 표시
2. US East 시간 표시 확인
3. 티커 선택 후 드롭다운 화살표 클릭 → 히스토리 표시

---

**다음**: `/IMP-execution`
