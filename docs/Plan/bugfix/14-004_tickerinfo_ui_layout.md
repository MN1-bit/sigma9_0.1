# 14-004: TickerInfo UI 레이아웃 통합 개선

> **작성일**: 2026-01-13 | **예상 소요**: 3-4h | **위험도**: 낮음

## 1. 목표

TickerInfoWindow의 레이아웃 및 크기 관련 이슈 통합 해결:
1. Related Tickers를 뉴스 아래로 이동, 4열 Grid 표시
2. 창 크기 조절 및 스크롤 추가
3. Profile 카드 동적 높이 적용
4. 미표시 데이터 (Splits, IPO, Ticker Events) UI 추가

---

## 2. 레이어 체크

- [x] 레이어 규칙 위반 없음 (Frontend GUI 내부 변경)
- [x] 순환 의존성 없음 (GUI 단일 파일 내 변경)
- [ ] DI Container 등록 필요: **아니오** (기존 TickerInfoService 사용)

> **Frontend 단독 변경**: `frontend/gui/ticker_info_window.py` 레이아웃 및 위젯 수정만 해당.
> Backend나 Core 레이어와의 의존성 변경 없음.

---

## 3. 기존 솔루션 검색 결과

| 솔루션 | 출처 | 채택 여부 | 사유 |
|--------|------|----------|------|
| `QScrollArea` | Qt 공식 문서 | ✅ 채택 | 콘텐츠 스크롤을 위한 표준 Qt 위젯 |
| `QGridLayout` | Qt 공식 문서 | ✅ 채택 | Related Tickers 4열 그리드 표시에 최적 |
| `QFormLayout` | Qt 공식 문서 | ⚠️ 검토 | Profile 동적 높이에 대안으로 고려 가능 |
| Frameless Resize | `QSizeGrip` | ✅ 채택 | Frameless 창 리사이즈를 위한 표준 방법 |

> ✅ 검색 완료. 모든 필요 기능은 Qt 표준 위젯으로 구현 가능.

---

## 4. 영향 분석

### 변경 파일 목록

| 파일 | 유형 | 예상 라인 | 변경 내용 |
|------|------|----------|----------|
| `frontend/gui/ticker_info_window.py` | MODIFY | +80~100 | 레이아웃 구조 변경 |

### 영향받는 모듈

- **직접 영향**: `TickerInfoWindow` 클래스
- **간접 영향**: 없음 (독립적인 팝업 창)

### 순환 의존성 체크

- `pydeps --show-cycles`: Frontend 단독 변경으로 불필요

---

## 5. 실행 계획

### Step 1: Related Tickers 레이아웃 개선

**현재 상태**:
- Related Tickers가 Column 3 상단에 위치
- 쉼표로 구분된 단일 문자열로 표시

**변경 작업**:
1. `_create_column3_news()` 순서 변경 (News → Related 순서로)
2. Related 표시를 `QGridLayout` 기반 4열 그리드로 변경

```python
# Grid 레이아웃으로 Related 표시
grid = QGridLayout()
grid.setSpacing(4)
for i, ticker in enumerate(related_tickers):
    col = i % 4
    row = i // 4
    label = QLabel(ticker)
    label.setAlignment(Qt.AlignCenter)
    grid.addWidget(label, row, col)
```

---

### Step 2: 창 크기 조절 및 스크롤 추가

**현재 상태**:
- Frameless 윈도우로 리사이즈 불가
- 콘텐츠가 창 크기를 초과해도 스크롤 없음

**변경 작업**:
1. `QSizeGrip` 추가로 창 가장자리 리사이즈 지원
2. 본문 영역을 `QScrollArea`로 래핑

```python
# 3-Column body를 QScrollArea로 감싸기
scroll_area = QScrollArea()
scroll_area.setWidgetResizable(True)
scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

body_widget = QWidget()
body_layout = QHBoxLayout(body_widget)
# ... Column 1, 2, 3 추가
scroll_area.setWidget(body_widget)
```

---

### Step 3: Profile 카드 동적 크기 적용

**현재 상태**:
- DetailTable의 val_label에 WordWrap 적용됨
- 부모 위젯 높이가 고정되어 텍스트가 잘림

**변경 작업**:
1. Grid 행 높이 자동 조절 설정
2. val_label SizePolicy 개선

```python
# 각 행의 높이가 콘텐츠에 맞게 자동 조절되도록
self._grid.setRowStretch(row, 0)  # stretch 비활성화

# val_label 설정 개선
val_label.setWordWrap(True)
val_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
val_label.setMinimumHeight(0)  # 최소 높이 제한 해제
```

---

### Step 4: 미표시 데이터 UI 추가

**현재 상태**: API에서 가져오지만 UI에 표시되지 않는 3가지 데이터:

| 카테고리 | 데이터 | 용도 |
|----------|--------|------|
| **Splits** | split_from, split_to, execution_date | 주식 분할 이력 |
| **IPO** | offer_price, listing_date | 상장가 및 상장일 |
| **Ticker Events** | name_change, delisting | 이름 변경, 상장폐지 이력 |

**변경 작업**:

#### 4-1. Column 2 (재무 섹션)에 Splits 추가
```python
# Dividends 아래에 Splits 테이블 추가
self._splits_table = DetailTable("📊 Stock Splits")
layout.addWidget(self._splits_table)

# 데이터 바인딩
splits_data = [(s.get("execution_date"), f"{s.get('split_from')}:{s.get('split_to')}") 
               for s in info.splits]
self._splits_table.set_data(splits_data if splits_data else [("No splits", "--")])
```

#### 4-2. Column 1 (Profile)에 IPO 정보 추가
```python
# Profile 테이블에 추가
profile_data.extend([
    ("상장일", info.ipo.get("listing_date", profile.get("list_date", "--"))),
    ("공모가", f"${info.ipo.get('offer_price', '--')}" if info.ipo.get('offer_price') else "--"),
])
```

#### 4-3. Column 1에 Ticker Events 알림 표시
```python
# 이벤트 있으면 경고 라벨 표시
if info.ticker_events:
    event = info.ticker_events[0]
    event_label = QLabel(f"⚠️ {event.get('type', '')}: {event.get('description', '')}")
    event_label.setStyleSheet("color: orange; font-size: 10px;")
    layout.addWidget(event_label)
```

---

## 6. 검증 계획

### 자동화 테스트

- [ ] `lint-imports` 통과
- [ ] `ruff check frontend/gui/ticker_info_window.py` 통과

### 수동 테스트

| 항목 | 테스트 방법 | 예상 결과 |
|------|------------|----------|
| Related 레이아웃 | AAPL (5개+ 관련 종목) 로드 | News 아래 4열 그리드 표시 |
| 창 리사이즈 | 창 가장자리 드래그 | 창 크기 조절 가능 |
| 스크롤 동작 | 많은 데이터 티커 로드 | 세로 스크롤바 표시 |
| 긴 회사명 | 중국 ADR 티커 검색 | 전체 이름 표시 (줄바꿈) |
| 긴 SIC 설명 | "Pharmaceutical Preparations" 등 | 잘림 없이 표시 |
| Splits 표시 | AAPL, TSLA 로드 | 분할 이력 테이블 표시 |
| IPO 정보 | 최근 상장 티커 로드 | 상장일/공모가 표시 |
| Ticker Events | 이름 변경 이력 티커 로드 | 이벤트 경고 표시 |

---

## 7. 롤백 계획

변경 범위가 단일 파일(`ticker_info_window.py`) 내 레이아웃 수정이므로:

```bash
# 문제 발생 시 롤백
git checkout HEAD~1 -- frontend/gui/ticker_info_window.py
```

또는 Git stash를 활용하여 변경 전 상태로 즉시 복원 가능.

---

## 8. 수정 대상 파일

### [MODIFY] [ticker_info_window.py](file:///d:/Codes/Sigma9-0.1/frontend/gui/ticker_info_window.py)

- Related Tickers 레이아웃 변경 (Grid 4열)
- QScrollArea 래핑
- Profile 동적 높이
- Splits, IPO, Ticker Events UI 추가
