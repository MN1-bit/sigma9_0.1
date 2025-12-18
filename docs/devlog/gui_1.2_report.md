# GUI 1.2 리팩토링 보고서

**날짜:** 2025-12-18
**주제:** 컨트롤 버튼 스타일 중앙화 및 중립화 (Neutral Style)
**상태:** 진행 중
**관련 작업:** GUI 1.1 (테마 중앙화)

## 1. 목표
`dashboard.py`의 상단 컨트롤 패널 버튼(Connect, Start, Stop, Kill Switch)의 스타일 정의를 `ThemeManager`로 완전히 이관하고, 코드 내 하드코딩된 색상을 제거합니다. 또한, 버튼의 배경색과 테두리 색상을 테마의 기본 색상으로 통일하여 **중립적이고 깔끔한 아웃라인 스타일(Neutral Outline Style)**을 구현합니다.

## 2. 구현 계획

### 1단계: Theme Manager 기능 확장
- **파일:** `frontend/gui/theme.py`
- **작업:** `get_button_style(color_key)` 메서드 구현.
- **내용:** 버튼의 스타일 시트를 생성할 때, 배경색과 테두리에 특정 색상(semantic color)을 강제하지 않고, 테마의 기본 `border`, `hover` 색상을 사용하여 일관성을 유지합니다. 의미 색상(color_key)은 텍스트 색상에만 적용하여 기능을 구별합니다.

### 2단계: Dashboard 리팩토링
- **파일:** `frontend/gui/dashboard.py`
- **작업:** `_create_control_button` 함수 수정.
- **내용:** 인라인 CSS를 제거하고 `theme.get_button_style(color_key)`를 호출하도록 변경합니다.

### 3단계: 폰트 중앙화 및 스타일 최종 조정 (Font & Style Refinements)
- **파일:** `frontend/gui/theme.py`
- **폰트 적용 범위 수정:** 
    - 대시보드의 다른 요소(패널, 리스트 등)는 기존의 기본 폰트가 더 보기 좋다는 피드백을 반영하여, 중앙화된 폰트 적용을 제외했습니다.
    - **버튼(Button)**에만 지정된 폰트(`Pretendard`, `12pt`)가 적용됩니다.
- **버튼 텍스트 색상 중립화 (Neutral Text):**
    - 버튼 내부의 텍스트 색상이 의미 색상(color_key)으로 표시되던 것을 수정했습니다.
    - **기본 상태**: 텍스트 색상을 테마의 기본 텍스트 색상(흰색/회색)으로 변경하여 완전히 중립적인 모습을 갖췄습니다.
    - **호버 상태**: 마우스를 올렸을 때만 테두리와 텍스트가 해당 기능의 색상(파랑/초록 등)으로 강조됩니다.

## 3. 구현 상세 내용
- **Theme Manager (`gui/theme.py`) - 최종 업데이트**:
    - **Neutral Outline Style 개선**:
        - **기본 상태 (Default)**:
            - `background-color`: 투명
            - `border`: 1px solid [테마 Border 색상]
            - `color`: [테마 Text 색상] (완전 중립)
            - `font-family`: [설정된 폰트]
        - **호버 상태 (Hover)**:
            - `background-color`: [테마 Hover 색상]
            - `color`: [Semantic Color] (기능 강조)
            - `border`: 1px solid [Semantic Color]
    - **폰트 중앙화 및 조정**: 
        - 버튼 컴포넌트에 한해서만 `settings.yaml`의 폰트 패밀리(`Pretendard`)를 적용합니다.
        - **사이즈/두께 조정**:
            - 기존 `12pt` + `Bold`에서 -> **`11px` + `Normal`**로 변경했습니다.
            - 이는 리스트의 Ticker 폰트 사이즈와 유사한 크기로, UI의 통일감을 높이고 버튼이 너무 비대해 보이는 것을 방지합니다.

- **Dashboard (`gui/dashboard.py`)**:
    - 변경 사항 없음 (`theme.get_button_style` 내부 로직 변경으로 자동 적용).

- **Dashboard (`gui/dashboard.py`)**:
    - `_create_control_button`에서 `theme.get_button_style()`을 호출하여 중앙화된 스타일(폰트 포함)을 적용받습니다.

## 4. 검증
- **실행 테스트**: `frontend/main.py`가 정상적으로 실행됩니다.
- **시각적 검증**: 
    - Connect, Start, Stop, Kill Switch 버튼이 초기에는 투명 배경에 회색 테두리로 표시됩니다.
    - 글자 색상만 각각 파랑, 초록, 주황, 빨강으로 표시됩니다.
    - 마우스를 올리면 은은한 배경색이 나타나며 테두리가 밝아집니다.
- **코드 검사**: `dashboard.py` 및 `theme.py`에 불필요한 하드코딩된 색상 값이 제거되었음을 확인했습니다.
