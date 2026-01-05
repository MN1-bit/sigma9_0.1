# Devlog 01-003: Watchlist Data Refresh Fix (Phase 2)

**작성일**: 2026-01-06  
**작업자**: AI Assistant  
**이슈**: `docs/Plan/bugfix/01-003_watchlist_data_refresh.md`

---

## Phase 2: Frontend 경고 표시

### 변경 사항

#### `frontend/gui/dashboard.py`

`_update_watchlist_panel()` 메서드에 **Transparency Protocol** 적용:

1. **Dollar Volume 경고 표시**
   - `dollar_volume <= 0` 인 경우 ⚠️ 아이콘 표시
   - ToolTip: "Dollar Volume 데이터 없음"
   - 주황색 (255, 165, 0) 텍스트

2. **Score 경고 표시**
   - `score <= 0` 인 경우 ⚠️ 아이콘 표시
   - ToolTip: "Score 데이터 없음"
   - 주황색 텍스트

3. **Ignition 경고 표시**
   - Ignition 모니터링 활성화 상태에서 데이터 없을 경우 ⚠️ 표시
   - ToolTip: "Ignition 데이터 수신 대기 중"
   - 모니터링 비활성화 상태에서는 기존처럼 "-" 표시

### 설계 철학

> **"Transparency Over Fallback"** - 데이터 누락 시 캐시된 값으로 대체하지 않고, 
> 사용자에게 명시적으로 경고하여 데이터 품질 문제를 인지할 수 있도록 함.

### 코드 변경

```python
# [Issue 01-003] Dollar Volume (경고 표시 추가)
if dollar_volume > 0:
    dolvol_item = NumericTableWidgetItem(self._format_dollar_volume(dollar_volume), dollar_volume)
else:
    dolvol_item = QTableWidgetItem("⚠️")
    dolvol_item.setToolTip("Dollar Volume 데이터 없음")
    dolvol_item.setForeground(QColor(255, 165, 0))  # 주황색
```

### 예상 UI

| Ticker | Change | DolVol | Score | Ign |
|--------|--------|--------|-------|-----|
| SMXT   | +15.3% | 1.8M   | 50    | 🔥73|
| ABCD   | +8.4%  | ⚠️     | ⚠️    | ⚠️  |

⚠️ 아이콘에 마우스를 올리면 ToolTip으로 누락 원인 표시

---

## 완료된 작업

1. ✅ Phase 1: Backend 주기적 브로드캐스트 (`realtime_scanner.py`)
2. ✅ Phase 2: Frontend 경고 표시 (`dashboard.py`)

---

## 다음 단계

- 검증: GUI 시작 후 Watchlist 데이터 유지 확인
- 이슈 문서 상태 업데이트
