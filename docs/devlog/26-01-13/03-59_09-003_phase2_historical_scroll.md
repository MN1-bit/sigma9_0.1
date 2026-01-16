# 09-003 Phase 2: Historical Data Scrolling Devlog

> **일자**: 2026-01-10
> **상태**: 🚧 진행 중 (트리거 동작 확인, 데이터 로드 추가 디버깅 필요)

---

## 구현 요약

### 목표
차트에서 **첫 번째 캔들이 뷰포트에 보일 때** 더 많은 과거 데이터를 자동으로 로드하여 prepend.

> [!NOTE]
> finplot은 의도적으로 데이터 범위 밖 스크롤을 제한합니다 ([GitHub #106](https://github.com/highfestiva/finplot/issues/106)).
> 우회책: Edge Trigger 방식 채택.

---

## 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| [finplot_chart.py](file:///d:/Codes/Sigma9-0.1/frontend/gui/chart/finplot_chart.py) | Edge trigger, 로드 정책, 헬퍼 메서드 추가 |
| [dashboard.py](file:///d:/Codes/Sigma9-0.1/frontend/gui/dashboard.py) | `set_ticker()` 호출 추가 |

---

## 주요 구현 내용

### 1. Edge Trigger 구현 (L504-531)

```python
def _on_viewport_changed(self, vb, range_) -> None:
    # range_ = [x_min, x_max] (캔들 인덱스 기반)
    TRIGGER_THRESHOLD = 5
    if x_min <= TRIGGER_THRESHOLD:
        # 첫 5개 캔들이 보이면 트리거
        self._viewport_debounce.start()
```

**발견사항**: `sigXRangeChanged`의 `range_`는 epoch seconds가 아닌 **캔들 인덱스** 기반.

### 2. 로드 정책 (80/50/30 bars)

| 단위 | 바 수 | 근거 |
|------|------|------|
| m (1m/3m/5m/15m) | 80 bars | 분봉은 밀도 높음 |
| h (1h/4h) | 50 bars | 중간 밀도 |
| D (1D/1W) | 30 bars | 일봉은 저밀도 |

### 3. Daily vs Intraday 분기 (L590-598)

```python
if source_tf in ("1D", "1W"):
    df = pm.read_daily(ticker=ticker, days=365)
    ts_col = "date"
else:
    df = pm.get_intraday_bars(ticker=ticker, tf=source_tf, days=60)
    ts_col = "timestamp"
```

### 4. 새 메서드 추가

| 메서드 | 역할 |
|--------|------|
| `set_ticker(ticker)` | 티커 설정 (historical loading에 필요) |
| `_disable_viewport_limits()` | ViewBox 제한 해제 |
| `_get_load_bars_for_timeframe(tf)` | 타임프레임별 로드량 반환 |
| `_get_source_request(target_tf, target_bars)` | 소스 TF와 배수 계산 |
| `_resample_df(df, target_tf)` | DataFrame 리샘플링 |

---

## 테스트 결과

| 테스트 항목 | 결과 | 비고 |
|------------|------|------|
| Edge Trigger 발동 | ✅ | `x_min <= 5` 조건 작동 |
| `_is_loading_historical` 플래그 | ✅ | 중복 방지 작동 |
| 1D 데이터 로드 (read_daily) | ⚠️ | SMX 365일 데이터 있으나 필터링 후 0개 |
| Intraday 데이터 로드 | 🔄 | 테스트 필요 |

### SMX 1D 데이터 확인
```
Rows: 365
Date range: 2025-XX-XX - 2026-01-07
```

**이슈**: 차트에 표시된 첫 번째 캔들이 이미 데이터의 시작점이면 더 이상 로드할 데이터 없음 → 정상 동작.

---

## 남은 작업

1. [ ] 5m 등 intraday 타임프레임 테스트
2. [ ] API fallback 구현 (Parquet에 없으면 Massive API 호출)
3. [ ] prepend 후 차트 업데이트 확인

---

## 검증 결과

| 항목 | 결과 |
|------|------|
| lint-imports | 🔄 확인 필요 |
| pydeps cycles | 🔄 확인 필요 |
| DI 패턴 준수 | ✅ 신규 서비스 없음 |
| 크기 제한 | ✅ finplot_chart.py ~750줄 |
| ruff | ⚠️ E501 (줄 길이) |
