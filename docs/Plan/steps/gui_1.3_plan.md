# GUI 1.3 개발 계획: 설정(Settings) 연동 및 투명도 제어

**문서 작성일:** 2025-12-18
**목표:** GUI 내에 설정 메뉴를 구현하고, `settings.yaml`과 연동하여 사용자가 애플리케이션의 투명도(Alpha) 및 기타 테마 설정을 실시간으로 조절할 수 있게 한다.

## 1. 개요 및 목표
현재 `settings.yaml`에 정의된 설정값(테마, Acrylic 활성화 여부 등)을 사용자가 직접 수정할 수 있는 UI가 부재함.
특히 사용자가 요청한 **배경 투명도(Alpha) 조절** 기능을 중심으로, 설정 변경 사항이 즉시 또는 저장 시 GUI에 반영되도록 구현한다.

## 2. 기존 코드 분석 및 변경 필요 사항

### A. 설정 파일 (`frontend/config/settings.yaml`)
현재 구조:
```yaml
gui:
  theme: "dark"
  acrylic_enabled: true
  font_family: "Pretendard"
  font_size: 12
```
**변경 계획:**
- `window_opacity` (전체 창 투명도) 및 `acrylic_tint_opacity` (배경 틴트 투명도) 항목 추가 필요.
```yaml
gui:
  ...
  opacity: 1.0           # 전체 창 투명도 (0.1 ~ 1.0)
  acrylic_map_alpha: 150 # Acrylic 배경 틴트 알파값 (0 ~ 255)
```

### B. 테마 매니저 (`frontend/gui/theme.py`)
- `reload()` 메서드는 이미 존재하나, 특정 설정값(Alpha 등)만 동적으로 업데이트하는 세분화된 메서드가 필요할 수 있음.
- `settings.yaml`에 저장하는 `save_settings()` 기능 구현 필요 (현재는 로드만 가능).

### C. 커스텀 윈도우 (`frontend/gui/custom_window.py`)
- `CustomBase` 클래스 내 `self.setWindowOpacity()`를 통해 전체 투명도 제어 가능.
- Acrylic 효과의 투명도는 `WindowsEffect.setAcrylicEffect` 호출 시 파라미터로 전달됨. 이를 동적으로 갱신할 수 있는 인터페이스(메서드)를 `CustomWindow`에 추가해야 함.

## 3. 구현 단계 (Step-by-Step)

### 1단계: 설정 로드/저장 기능 강화 (`backend/config/loader.py` or new `manager.py`)
- 단순 로드를 넘어, 변경된 설정을 `settings.yaml`에 다시 쓰는 `save_settings(new_config)` 함수 구현.
- 주석(Comments)을 보존하며 YAML을 저장하는 것이 좋으나, 초기에는 기능 구현에 집중 (`PyYAML` 사용 시 주석 날아감 주의, 필요시 `ruamel.yaml` 고려하거나 주석 무시).

### 2단계: 설정 UI (Settings Dialog) 구현
- **파일:** `frontend/gui/settings_dialog.py` (신규 생성)
- **구성:**
    - 모달 다이얼로그 (Modal Window).
    - **Appearance 탭**:
        - Theme (Radio: Dark/Light)
        - Window Opacity (Slider: 10% ~ 100%)
        - Acrylic Background Alpha (Slider: 0 ~ 255) - *Glassmorphism 강도 조절*
    - **Save / Cancel 버튼**.

### 3단계: 메인 대시보드 연동
- **파일:** `frontend/gui/dashboard.py`
- 상단 컨트롤 패널(Top Panel) 우측 또는 적절한 위치에 톱니바퀴(⚙️) 아이콘 버튼 추가.
- 버튼 클릭 시 `SettingsDialog` 오픈.

### 4단계: 실시간 반영 및 저장
- 다이얼로그의 슬라이더 조작 시 `sig_settings_changed` 시그널 등을 통해 메인 윈도우에 즉시 임시 반영(Preview).
- '저장' 버튼 클릭 시 `settings.yaml`에 확정 저장 및 `ThemeManager.reload()` 수행.

### 5단계: 결과 보고서 작성 (Documentation)
- **파일:** `docs/devlog/gui_1.3_report.md` (예상 파일명)
- **목표:** 작업 완료 후 구현 내용, 기술적 이슈, 해결 과정을 상세히 기록.
- **내용:**
    - `settings.yaml` 스키마 변경 내역.
    - 투명도/Alpha 제어 로직 설명.
    - 구현 결과 스크린샷 및 검증 결과.

## 4. 인수인계 노트 (Context for Developer)
- **현재 상태:** `ThemeManager`가 폰트와 색상을 중앙 관리 중이며, `loader.py`는 LRU 캐시를 사용해 설정을 읽기만 함.
- **핵심 과제:** Acrylic 효과는 `custom_window.py` -> `window_effects.py` (ctypes)를 통해 윈도우 핸들(HWND)에 직접 적용됨. 따라서 슬라이더 값 변경 시 `setAcrylicEffect`를 다시 호출해줘야 함.
- **주의:** 전체 창 투명도(`setWindowOpacity`)와 Acrylic 효과는 별개임. 사용자가 원하는 "배경 Alpha"가 창 자체의 투명도인지, 블러 효과의 틴트 농도인지 명확히 UI에서 구분해주는 것이 좋음 (보통 둘 다 제공).

## 5. 예상 결과물
- 사용자가 GUI 상에서 버튼을 눌러 설정창을 띄우고, 슬라이더를 드래그하여 배경의 유리 효과(Glassmorphism) 농도를 입맛대로 조절할 수 있게 됨.
