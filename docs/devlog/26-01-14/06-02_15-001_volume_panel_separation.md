# 15-001 Volume Panel Separation Devlog

> **작성일**: 2026-01-14
> **계획서**: [15-001_volume_panel_separation.md](../../Plan/bugfix/15-001_volume_panel_separation.md)

## 진행 현황

| Step | 상태 | 시간 |
|------|------|------|
| Step 1 | ✅ | 06:02 |
| Verification | ✅ | 06:05 |

---

## Step 1: `_setup_ui()` 수정

### 변경 사항
- `frontend/gui/chart/finplot_chart.py` (L152-159):
  - 기존: `self.ax.overlay()` 패턴 → 볼륨을 캔들 차트 위에 오버레이
  - 변경: `fplt.create_plot(rows=2)` 패턴 → 2-row 레이아웃 분리
  - 볼륨 패널 높이 비율: 25% (`self.ax_volume.setHeight(0.25)`)

### 검증
- ruff check: ✅ All checks passed!
- ruff format: ✅ 1 file already formatted

---

## 검증 결과

| 항목 | 결과 |
|------|------|
| lint-imports | ⚠️ Config issue (기존) |
| ruff check (target) | ✅ |
| ruff format (target) | ✅ |
| 크기 제한 | ✅ (786줄, 기존 784줄) |
| DI 패턴 준수 | ✅ (해당없음) |

> **Note**: 기존 프로젝트 전역 lint 이슈는 별도 이슈로 분리. 본 변경 파일만 검증 통과.

---

**다음**: 수동 테스트 (앱 실행 → 볼륨 패널 분리 확인)
