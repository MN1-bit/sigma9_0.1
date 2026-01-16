# [09-007] 볼륨 차트 윈도우 분리 + Dollar Volume 변환 및 Zoom/Scroll 싱크 구현 계획서

> **작성일**: 2026-01-10 | **예상**: 2h
> **상태**: 📋 계획 검토 대기
> **선행 작업**: 09-001 (finplot 마이그레이션 완료)

---

## 1. 목표

1. **윈도우 분리**: 현재 **볼륨 차트가 캔들스틱 차트와 동일 윈도우에 오버레이**되어 있는 구조를 **분리된 윈도우**로 변경
2. **Zoom/Scroll 동기화**: 두 차트 간의 **Zoom/Scroll이 자동으로 동기화**되도록 수정
3. **Dollar Volume (dolvol) 변환**: 단순 Volume 대신 **Dollar Volume (= Close × Volume)** 표시

> [!NOTE]
> 현재 구현: `self.ax_volume = self.ax.overlay()` (오버레이 방식, 단순 Volume)
> 목표 구현: `fplt.create_plot(rows=2)` 방식으로 별도 행에 **Dollar Volume** 차트 배치

---

## 2. 현재 상태 분석

### 2.1 현재 구조 (문제점)

```
┌─────────────────────────────────────────────┐
│  Candlestick + Volume (같은 ax 위에 overlay) │
│  ┌─────────────────────────────────────────┐│
│  │ 🕯️ 캔들스틱 (ax)                         ││
│  │ 📊 볼륨 바 (ax_volume = ax.overlay())   ││ ← 문제: 겹침
│  └─────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```

**문제점**:
1. **시각적 간섭**: 볼륨 바가 캔들스틱과 겹쳐 가독성 저하
2. **Zoom/Scroll 비동기**: 볼륨 차트의 ViewBox가 별도로 관리되어 캔들과 싱크 안 됨
3. **Y축 스케일 충돌**: 가격 Y축과 볼륨 Y축이 다른 범위임에도 같은 공간 사용

### 2.2 목표 구조 (개선)

```
┌─────────────────────────────────────────────┐
│  Candlestick Window (ax)                    │
│  ┌─────────────────────────────────────────┐│
│  │ 🕯️ 캔들스틱                              ││
│  └─────────────────────────────────────────┘│
├─────────────────────────────────────────────┤
│  Dollar Volume Window (ax_volume) - X축 동기화 │
│  ┌─────────────────────────────────────────┐│
│  │ 💵 Dollar Volume 바 (= Close × Volume)  ││
│  └─────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
          ↑ X축 Zoom/Scroll 자동 싱크
```

---

## 3. 기존 솔루션 검색 결과

| 솔루션 | 출처 | 채택 여부 | 사유 |
|--------|------|----------|------|
| `fplt.create_plot(rows=N)` | finplot 공식 | ✅ 채택 | 다중 행 지원, X축 자동 싱크 |
| `ax.overlay()` | 현재 구현 | ❌ 폐기 | 오버레이 방식으로 분리 불가 |
| 별도 QWidget 분리 | - | ❌ 미채택 | 수동 싱크 구현 복잡도 증가 |

> **결론**: finplot 공식 `create_plot(rows=2)` 방식 사용으로 X축 자동 동기화 확보

---

## 4. 레이어 체크

- [x] 레이어 규칙 위반 없음 (Frontend GUI 내부 수정)
- [x] 순환 의존성 없음
- [x] DI Container 등록 필요: **아니오**

---

## 5. 변경 파일

| 파일 | 유형 | 예상 라인 | 변경 내용 |
|------|-----|----------|-----------|
| [finplot_chart.py](file:///d:/Codes/Sigma9-0.1/frontend/gui/chart/finplot_chart.py) | MODIFY | +40 / -15 | `_setup_ui()` 변경 + `set_volume_data()` → Dollar Volume 계산 추가 |

---

## 6. 실행 단계

### Step 1: `_setup_ui()` 수정 - 차트 생성 방식 변경

**현재 코드** (L152-L162):
```python
# 메인 차트 (캔들스틱)
self.ax = fplt.create_plot(init_zoom_periods=100)

# 볼륨 차트 (오버레이)
self.ax_volume = self.ax.overlay()

# finplot 요구사항: 위젯에 axs 속성 설정
self.axs = [self.ax, self.ax_volume]

# ax.vb.win (ViewBox의 윈도우)을 레이아웃에 추가
layout.addWidget(self.ax.vb.win, stretch=1)
```

**변경 후 코드**:
```python
# 다중 행 차트 생성 (캔들스틱 + 볼륨)
# rows=2 사용시 finplot이 자동으로 X축 싱크 처리
self.ax, self.ax_volume = fplt.create_plot(
    title='',
    rows=2,
    init_zoom_periods=100
)

# finplot 요구사항: 위젯에 axs 속성 설정
self.axs = [self.ax, self.ax_volume]

# 볼륨 차트 높이 비율 조정 (캔들 3 : 볼륨 1)
self.ax_volume.setFixedHeight(80)  # 픽셀 단위 또는 비율 조정

# ax.vb.win (ViewBox의 윈도우)을 레이아웃에 추가
layout.addWidget(self.ax.vb.win, stretch=1)
```

### Step 2: ViewBox 제한 해제 로직 업데이트

**현재 코드** (`_disable_viewport_limits()` L496-L511):
```python
# Volume 차트도 동일하게 적용
if hasattr(self, "ax_volume") and self.ax_volume:
    self.ax_volume.vb.disableAutoRange()
    self.ax_volume.vb.setLimits(xMin=None, xMax=None, yMin=None, yMax=None)
```

> [!TIP]
> `rows=2` 방식에서도 동일 로직 유지 가능. finplot이 자동으로 X축을 링크하므로
> 메인 ax만 제한 해제해도 볼륨 차트도 함께 스크롤되지만, 명시적으로 둘 다 해제 권장.

### Step 3: `clear()` 메서드 호환성 확인

**현재 코드** (L477-L485):
```python
def clear(self) -> None:
    """차트 초기화"""
    self.ax.reset()
    self.ax_volume.reset()
    # ...
```

> rows=2 방식에서도 `ax.reset()` 동일하게 동작. 변경 불필요.

### Step 4: `set_volume_data()` → Dollar Volume 계산 추가

**현재 코드** (L274-L309):
```python
def set_volume_data(self, volume_data: List[Dict]) -> None:
    """
    Volume 바 차트 설정

    Args:
        volume_data: [{"time": timestamp, "volume": int, "is_up": bool}, ...]
    """
    # ... 단순 volume 표시
    df = df.rename(columns={"volume": "Volume"})
```

**변경 후 코드**:
```python
def set_volume_data(self, volume_data: List[Dict]) -> None:
    """
    Dollar Volume 바 차트 설정

    Args:
        volume_data: [{"time": timestamp, "volume": int, "close": float, "is_up": bool}, ...]
        
    ELI5:
        Dollar Volume = 거래량 × 종가
        실제 거래된 금액을 보여줘서 단순 거래량보다 의미 있음
    """
    if not volume_data:
        return

    self._volume_data = volume_data

    # DataFrame 변환
    df = pd.DataFrame(volume_data)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df = df.set_index("time")
    
    # Dollar Volume 계산 (close × volume)
    # close가 없으면 기존 volume 사용 (하위호환)
    if "close" in df.columns:
        df["Volume"] = df["volume"] * df["close"]
    else:
        df["Volume"] = df["volume"]

    # finplot volume_ocv는 Open, Close, Volume 3개 컬럼 필요
    if "is_up" in df.columns:
        df["Open"] = 0
        df["Close"] = df["is_up"].apply(lambda x: 1 if x else -1)
    else:
        df["Open"] = 0
        df["Close"] = 1

    # 기존 볼륨 플롯 제거
    self.ax_volume.reset()

    # Dollar Volume 플롯
    self._volume_plot = fplt.volume_ocv(
        df[["Open", "Close", "Volume"]], ax=self.ax_volume
    )

    fplt.refresh()
```

> [!IMPORTANT]
> **호출부 수정 필요**: `set_volume_data()` 호출 시 `close` 값을 함께 전달해야 함.
> 현재 캔들 데이터와 볼륨 데이터가 별도로 전달되므로, 캔들 데이터에서 close 값을 추출하여 병합 필요.

### Step 5: 볼륨 차트 배경 투명화

**문제**: `rows=2` 방식 사용 시 볼륨 차트 배경이 **흰색**으로 표시됨

**해결 코드** (`_setup_ui()` 내):
```python
# [15-001] Volume 패널 배경 투명화 (ViewBox만 지원)
self.ax_volume.vb.setBackgroundColor(None)

# 메인 캔들스틱 패널도 배경 투명화
self.ax.vb.setBackgroundColor(None)

# [15-001] Row 비율 설정 (3:1 = 캔들:볼륨)
self.ax.vb.win.ci.layout.setRowStretchFactor(0, 3)  # 캔들스틱 row
self.ax.vb.win.ci.layout.setRowStretchFactor(1, 1)  # 볼륨 row
```

> [!NOTE]
> `PlotItem`에는 `setBackground()` 메서드가 없음. `vb.setBackgroundColor(None)`만 사용해야 함.

---

## 7. 검증 계획

### 7.1 수동 테스트 (필수)

1. **Frontend 실행**:
   ```bash
   cd D:\Codes\Sigma9-0.1
   python -m frontend.main
   ```

2. **시각적 확인 항목**:
   | 항목 | 예상 결과 |
   |------|----------|
   | 캔들스틱 차트 | 상단 영역에 단독 표시 |
   | Dollar Volume 차트 | 하단 별도 영역에 표시 (캔들과 분리) |
   | 차트 간 간격 | 적절한 여백으로 시각적 분리 |
   | Dollar Volume 값 | 단순 Volume이 아닌 Close × Volume 값 반영 |

3. **Zoom/Scroll 싱크 테스트**:
   | 조작 | 예상 결과 |
   |------|----------|
   | 캔들스틱 영역에서 마우스 휠 Zoom | 볼륨 차트도 동일하게 Zoom |
   | 캔들스틱 영역에서 드래그 Scroll | 볼륨 차트도 동일하게 Scroll |
   | 볼륨 영역에서 마우스 휠 Zoom | 캔들스틱 차트도 동일하게 Zoom |
   | 좌측 끝까지 스크롤 | 두 차트가 동일한 시간 범위 표시 |

4. **타임프레임 변경 테스트**:
   - 1m, 5m, 1h, 1D 각각 선택 후 차트 데이터 정상 표시 확인
   - 타임프레임 변경 시 두 차트 모두 갱신 확인

### 7.2 자동화 테스트

| 테스트 | 명령어 | 기대 결과 |
|--------|--------|----------|
| lint-imports | `lint-imports` | 레이어 위반 없음 |
| ruff check | `ruff check frontend/gui/chart/finplot_chart.py` | All checks passed |
| ruff format | `ruff format --check frontend/gui/chart/finplot_chart.py` | Already formatted |

---

## 8. 사전 체크리스트

- [x] 레이어 규칙 위반 없는가?
- [x] 신규 서비스 → Container 등록 계획 있는가? → 불필요
- [x] 순환 의존성 위험 → 인터페이스 추출 계획 있는가? → 해당 없음
- [x] 기존 1000줄+ 파일 수정 → 분할 선행 필요? → 아니오 (finplot_chart.py 801줄)

---

## 9. 아키텍처 대조

- [x] 신규 모듈이 `archt.md` 레이어 규칙 준수 (Frontend GUI 내부)
- [x] 변경이 기존 인터페이스 호환성 유지 (`set_volume_data()` 동일)
- [x] Tech Stack 변경 없음

---

## 10. 관련 문서

- [09-001_finplot_chart_migration.md](file:///d:/Codes/Sigma9-0.1/docs/Plan/refactor/09-001_finplot_chart_migration.md) - finplot 마이그레이션 계획서
- [09-002_finplot_chart_enhancements.md](file:///d:/Codes/Sigma9-0.1/docs/Plan/refactor/09-002_finplot_chart_enhancements.md) - finplot 기능 개선 계획서
- [archt.md](file:///d:/Codes/Sigma9-0.1/.agent/Ref/archt.md) - 시스템 아키텍처

---

## 11. 예상 리스크 및 대응

| 리스크 | 영향도 | 대응 방안 |
|--------|--------|----------|
| `rows=2` 방식에서 임베딩 패턴 변경 필요 | 중 | finplot embed.py 예제 참조하여 `ax.vb.win` 대신 `fplt.win` 사용 검토 |
| 볼륨 차트 높이 하드코딩 이슈 | 하 | 테마 설정으로 분리 (추후 개선) |
| Y축 스케일 독립성 확인 필요 | 하 | `rows=2` 방식은 Y축 독립 기본 지원 |
