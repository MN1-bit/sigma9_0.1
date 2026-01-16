# [09-007] Volume Window Separation Devlog

> **작성일**: 2026-01-14
> **계획서**: [09-007_volume_window_separation.md](../../Plan/refactor/09-007_volume_window_separation.md)

## 진행 현황

| Step | 내용 | 상태 | 시간 |
|------|------|------|------|
| Step 1 | `_setup_ui()` - `create_plot(rows=2)` 변경 | ✅ | 기존 |
| Step 2 | ViewBox 제한 해제 로직 확인 | ✅ | 기존 |
| Step 3 | `clear()` 메서드 호환성 확인 | ✅ | 기존 |
| Step 4 | `set_volume_data()` → Dollar Volume 계산 | ✅ | 07:38 |
| Step 5 | 볼륨 차트 배경 투명화 | ✅ | 기존 |

---

## Step 4: Dollar Volume 계산 추가

### 변경 사항
- `frontend/gui/chart/finplot_chart.py`: 
  - `set_volume_data()`: `close` 값 있으면 `volume * close`로 Dollar Volume 계산
- `frontend/services/chart_data_service.py`: 
  - `_bars_to_volumes()`: close 필드 추가 (Daily 데이터)
  - Intraday 데이터는 기존에 close 포함됨

### 검증
- ruff check: ✅ All checks passed!
