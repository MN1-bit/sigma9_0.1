# 기술 노트: Acrylic 효과와 QWebEngineView 충돌 이슈

**날짜**: 2025-12-18
**컴포넌트**: Frontend / GUI / ChartWidget
**상태**: 제한 사항 확인됨 / 우회 해결책 적용됨

## 문제 설명
`Sigma9Dashboard`에 **Acrylic Effect** (블러 효과가 있는 투명 창)를 적용하려고 할 때, 크로미움(Chromium) 기반의 `QWebEngineView`를 사용하는 `ChartWidget`과 렌더링 충돌이 발생함.

### 증상
1. **전체 화면 암전**: `QWebEngineView`에 `WA_TranslucentBackground` 속성을 활성화하면, 애플리케이션 창 전체의 배경이 검은색으로 변하며 Windows DWM(데스크톱 창 관리자)이 제공하는 투명 및 블러 효과가 사라짐.
2. **투명도 잠금**: 차트의 `WA_TranslucentBackground`를 비활성화하면 차트는 정상적으로 렌더링되지만 불투명(단색)하게 표시됨. 이때 나머지 창 영역은 Acrylic 효과가 유지됨.

## 기술적 근본 원인 (Root Cause)
이 충돌은 `QWebEngineView`와 Windows Acrylic (DWM Blur)의 GPU 컴포지션 처리 방식 차이에서 기인함:

1. **OpenGL 컨텍스트 충돌**: `QWebEngineView`는 별도의 프로세스에서 하드웨어 가속(OpenGL/Direct3D)을 통해 렌더링됨. `WA_TranslucentBackground`가 설정되면, 알파 채널을 사용하여 부모 위젯과 블렌딩을 시도함.
2. **DWM 컴포지션**: Acrylic 효과는 `SetWindowCompositionAttribute` (비공개 Windows API) 또는 `DwmExtendFrameIntoClientArea`에 의존함. 이를 위해서는 창이 특정 투명 색상 키로 페인팅되어야 함.
3. **충돌 현상**: `QWebEngineView`가 하드웨어 가속 모드에서 알파 채널이 있는 프레임버퍼에 쓰기 작업을 할 때, DWM이 배경(데스크톱 바탕화면)을 샘플링하여 블러 효과를 만드는 과정을 방해하여 "검은 배경"으로 대체되는 현상이 발생함.

## 시도한 해결책 및 결과

| 시도 | 설정 | 결과 |
| :--- | :--- | :--- |
| **시도 1** | 차트 `background: transparent` + `WA_TranslucentBackground` | **실패**: 창 전체가 불투명한 검은색이 됨 (Acrylic 깨짐). |
| **시도 2** | 차트 컨테이너만 투명화 | **실패**: 차트가 기본 흰색 배경으로 불투명하게 렌더링됨. |
| **시도 3** | **단색 배경 사용 (Plan B)** | **성공 (부분적)**: 차트 영역은 불투명(다크 테마 색상)하지만, 나머지 UI(Watchlist 등)는 Acrylic 효과가 유지됨. |

## 최종 결정 (우회 방안)
**시도 3 (단색 배경 사용)**을 채택함.

- **차트 영역**: 테마의 다크 틴트 색상 (`#151520`)과 일치하는 불투명한 단색 배경으로 렌더링.
- **그 외 영역**: Acrylic Effect (투명 + 블러) 유지.
- **판단 근거**: 차트 배경의 투명화를 위해 전체 애플리케이션의 미적 감각(Acrylic)을 포기하는 것보다, 차트만 불투명하게 하고 나머지 UI의 퀄리티를 유지하는 것이 더 낫다고 판단함. (차트 가독성 면에서도 단색 배경이 유리함)

## 향후 계획 (Future Path)
만약 차트의 투명도가 반드시 필요하다면 다음 방안을 고려해볼 수 있음:
1. **소프트웨어 렌더링**: `QWebEngineView`를 소프트웨어 렌더링 모드(`Qt.AA_UseSoftwareOpenGL`)로 전환. (투명도 문제는 해결될 수 있으나 차트 성능이 심각하게 저하될 위험 있음)
2. **QGraphicsView 전환**: WebEngine을 버리고, Python 네이티브 플로팅 라이브러리(예: `PyQtGraph`)로 전환. 이는 DWM 충돌 없이 투명도를 기본적으로 지원함.
