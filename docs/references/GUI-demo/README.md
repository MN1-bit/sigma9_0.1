# Acrylic Demo - 파일 구조 설명

Windows Acrylic/Glassmorphism 효과와 트레이딩 파티클 이펙트를 PyQt6에서 구현한 데모 프로젝트입니다.

## 파일 구조

```
acrylic-demo/
├── demo.py                  # 메인 앱 (실행 파일)
├── custom_window.py         # 커스텀 윈도우 클래스
├── window_effects.py        # Windows DWM API 래퍼
├── particle_effects.py      # 파티클 시스템 엔진
├── gold_coin-Photoroom.png  # 익절 이펙트용 코인 이미지
└── README.md                # 이 문서
```

---

## 📁 particle_effects.py

**역할**: 퀀트 트레이딩 봇을 위한 다양한 시각적 파티클 효과 구현

**주요 이펙트**:
1. **📝 주문 생성** (Order Created) - 파란색 펄스/리플 효과
2. **✅ 주문 체결** (Order Filled) - 금색/흰색 버스트 효과
3. **📈 수익중** (In Profit) - 화면 하단에서 위로 올라가는 녹색 파티클 (연속)
4. **📉 손실중** (In Loss) - 화면 상단에서 아래로 떨어지는 빨간색 파티클 (연속)
5. **💰 익절** (Take Profit) - 거대한 **금화(Gold Coin)**가 폭발하듯 쏟아지는 효과
6. **🛑 손절** (Stop Loss) - 빨간색 경고 플래시 및 하강 파티클

**특징**:
- **이미지 파티클**: `QPixmap`을 사용한 고해상도 코인 이미지 렌더링
- **물리 엔진**: 중력, 속도, 마찰력, 회전 등이 적용된 파티클 움직임
- **전역 투명도**: 모든 파티클의 투명도를 실시간으로 조절 가능

---

## 📁 window_effects.py

**역할**: Windows DWM (Desktop Window Manager) API를 ctypes로 호출하는 저수준 모듈

**주요 기능**:
- `add_acrylic_effect()` - Acrylic 블러 효과 적용 (Windows 10+)
- `add_mica_effect()` - Mica 효과 적용 (Windows 11 전용)
- `add_shadow_effect()` - 창 그림자 추가
- `add_blur_behind_window()` - 배경 블러 활성화
- `remove_background_effect()` - 효과 제거

**의존성**: `pywin32` (win32api, win32gui, win32con)

---

## 📁 custom_window.py

**역할**: Acrylic 효과가 적용된 Frameless 윈도우 + 커스텀 타이틀바

**주요 클래스**:
- `CustomBase` - 기본 프레임리스 윈도우 (타이틀바 없음)
- `CustomWindow` - 커스텀 타이틀바 포함 윈도우 (상속해서 사용)
- `TitleBar` - 최소화/최대화/닫기 버튼이 있는 타이틀바

**파라미터**:
```python
CustomWindow(
    use_mica='false',      # 'false', 'true', 'if available'
    theme='dark',          # 'auto', 'dark', 'light' 
    color="20202060"       # RRGGBBAA (Tint Color + Alpha)
)
```

**의존성**: `window_effects.py`, `PyQt6`

---

## 📁 demo.py

**역할**: 실제 실행되는 데모 앱

**기능**:
- **Trading Effects**: 6가지 트레이딩 이펙트 시연 버튼
- **Acrylic Settings**:
  - 투명도 슬라이더로 윈도우 Alpha 조절 (0~255)
  - 색상 피커로 윈도우 Tint Color 선택
- **Particle Settings**:
  - ✨ 파티클 Alpha 슬라이더로 이펙트 투명도 조절 (0~100%)

---

## 실행 방법

```powershell
# 가상환경 활성화 후
python demo.py
```

## 출처

코드 원본: [re7gog/CustomWindow](https://github.com/re7gog/CustomWindow)
