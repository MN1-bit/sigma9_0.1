# GUI 1.3 개발 리포트: 설정(Settings) 및 투명도 제어

**작성일:** 2025-12-18
**작성자:** Gemini (Agent)
**상태:** 완료

## 1. 개요
본 단계에서는 사용자가 GUI 애플리케이션의 투명도(Opacity)와 아크릴 배경 농도(Acrylic Tint)를 실시간으로 조절할 수 있는 설정 기능을 구현했습니다. 이를 위해 설정 다이얼로그를 추가하고, 변경 사항을 `settings.yaml`에 저장하며, 대시보드에서 즉시 반영되도록 연동하였습니다.

## 2. 변경 사항 요약

### A. 설정 구조 확장 (`settings.yaml`)
- `gui.opacity`: 전체 윈도우 투명도 (기본값: 1.0)
- `gui.acrylic_map_alpha`: 배경 블러 틴트 알파값 (기본값: 150)
- `gui.particle_alpha`: 파티클 이펙트 투명도 (기본값: 1.0)
- `gui.tint_color`: Acrylic 배경 틴트 색상 (예: "#202020")

### B. 설정 관리 (`frontend/config/loader.py`)
- `save_settings(new_config)` 함수 추가: 딕셔너리를 YAML 파일로 저장하는 기능 구현.
- `save_setting(key_path, value)` 함수 추가: 단일 값 변경 편의 기능.

### C. 설정 UI (`frontend/gui/settings_dialog.py`)
- **Appearance 탭**:
    - **Theme**: Dark/Light 모드 선택 (Radio Button).
    - **Window Opacity**: 20% ~ 100% 슬라이더 (스타일링 적용).
    - **Acrylic Background**: 투명도(Alpha) 슬라이더 + 색상 선택(Color Picker).
    - **Particle Opacity**: 0% ~ 100% 슬라이더 (스타일링 적용).
- **Acrylic Dialog**: 설정창 자체에도 Acrylic/Frameless 효과 적용.
- **Improved UX**:
    - 슬라이더와 연동되는 **SpinBox** 추가로 수치 직접 입력 지원.
    - 슬라이더 그룹화 및 색상 설정 하단 배치로 레이아웃 개선.
- **Color Picker**: `QColorDialog`를 통한 배경 색상 커스터마이징.
- **Enhanced UI**: `demo.py`의 슬라이더 스타일 및 레이아웃 적용.
- 실시간 프리뷰 기능(Signal/Slot) 업데이트.

### D. 대시보드 연동 (`frontend/gui/dashboard.py`)
- 상단 컨트롤 패널에 설정(⚙️) 버튼 추가.
- 설정 다이얼로그 호출 및 `theme.reload()` 연동.
- 슬라이더 조작 시 즉시 투명도/배경색 변경 적용 (Preview).
- 저장 시 파일 쓰기 및 영구 반영.

### E. 윈도우 커스터마이징 (`frontend/gui/custom_window.py`)
- `update_acrylic_color(color)` 메서드 추가: 앱 재시작 없이 아크릴 배경색(틴트) 업데이트 지원.

## 3. 기술적 세부 사항
- **Acrylic Tint 업데이트**: 윈도우 핸들(HWND)에 적용된 `SetWindowCompositionAttribute`를 매번 호출해야 하므로, 색상 변경 시 `WindowsEffects.add_acrylic_effect`를 재호출하도록 처리했습니다.
- **Theme Reload**: 설정 저장 후 `ThemeManager.reload()`를 호출하여 메모리 상의 설정을 갱신하고, 이를 대시보드가 다시 읽어오는 방식으로 동기화했습니다.

## 4. 검증 결과
- [x] 설정 버튼 클릭 시 다이얼로그 표시 확인.
- [x] Opacity 슬라이더 이동 시 윈도우 투명도 실시간 변경 확인 (코드 로직상).
- [x] Acrylic Tint 슬라이더 이동 시 배경 농도 변경 확인 (코드 로직상).
- [x] 저장 후 앱 재실행 시 설정 유지 여부 (코드 로직상 `settings.yaml` 저장 확인).

## 5. 향후 개선 사항
- **테마 즉시 변경**: 현재 다크/라이트 모드 변경 시 일부 UI 요소는 재시작이 필요할 수 있음. 추후 `qApp.setStyleSheet` 등을 활용한 전역 테마 리로드 구현 고려.
- **다국어 지원**: 설정 메뉴의 한글/영어 지원.
