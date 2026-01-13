# 테마 투명화 중앙화 리팩터링 계획서

> **작성일**: 2026-01-13 02:10
> **우선순위**: P2 (코드 품질) | **예상 소요**: 2h | **위험도**: 중간

---

## 1. 목표

`TickerInfoWindow` 및 기타 Frameless 창에서 발생하는 **Navy Background 문제** 해결.
테마 투명화 패턴을 중앙화하여 재발 방지.

### 해결 대상 이슈
- [15-001 이슈 3](file:///d:/Codes/Sigma9-0.1/docs/devlog/impl/15-001_ticker_info_viewer.md#L123-L181): 배경 투명 설정 안됨

### 근본 원인
1. `theme.py`에 Git conflict markers 잔존 (lines 100-189)
2. `background-color` 직접 설정 → `WA_TranslucentBackground` 무효화
3. Frameless Dialog 패턴 미적용 (0.01 Alpha 레이어 누락)

---

## 2. 영향 분석

### 변경 대상 파일
| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `frontend/gui/theme.py` | **MODIFY** | Git conflict 해결 + `theme_changed` 시그널 추가 |
| `frontend/gui/ticker_info_window.py` | **MODIFY** | 0.01 Alpha 컨테이너 + 드래그 로직 정비 |

### 영향받는 모듈
- `dashboard.py`: `TickerInfoWindow` 호출부 (변경 없음, 동작 검증 필요)
- `settings_dialog.py`: 동일 패턴 참조용 (변경 없음)

### 위험도 평가
- **중간**: 시각적 버그 수정이나 기능 로직 변경 없음. 회귀 가능성 낮음.

---

## 3. 기존 솔루션 검색 결과

| 솔루션 | 출처 | 채택 여부 | 사유 |
|--------|------|----------|------|
| KI `frameless_dialog_pattern.md` | 내부 KI | ✅ 채택 | 검증된 0.01 Alpha + QDialog 패턴 |
| `settings_dialog.py` | 프로젝트 내부 | ✅ 참조 | 동일 패턴 작동 확인 |

---

## 4. 실행 계획

### Step 1: Git Conflict 해결 (theme.py)
- [ ] `<<<<<<< Updated upstream` ~ `>>>>>>> Stashed changes` (lines 100-189) 병합
- [ ] `theme_changed` 시그널 추가 (`pyqtSignal` from QtCore)
- [ ] `reload()` 에서 `self.theme_changed.emit()` 호출

**예상 diff:**
```python
# theme.py 수정 후 구조
class ThemeManager:
    theme_changed = pyqtSignal()  # 추가
    
    def reload(self):
        load_settings.cache_clear()
        self._init_theme()
        self.theme_changed.emit()  # 추가
        
    def apply_to_widget(self, widget, include_opacity=True, include_background=True):
        # ... (기존 코드 유지)
```

### Step 2: TickerInfoWindow 리팩터링
- [ ] `_setup_ui()`에 0.01 Alpha 컨테이너 추가
- [ ] `_apply_theme()`에서 `include_background=False` 사용
- [ ] 드래그 로직 정비 (interactive widget guard)

**0.01 Alpha 컨테이너 패턴:**
```python
def _setup_ui(self):
    outer_layout = QVBoxLayout(self)
    outer_layout.setContentsMargins(0, 0, 0, 0)
    
    # 마우스 이벤트 캡처용 컨테이너
    self._container = QFrame()
    self._container.setObjectName("mainContainer")
    self._container.setStyleSheet("""
        #mainContainer {
            background-color: rgba(0, 0, 0, 0.01);
            border-radius: 12px;
        }
    """)
    outer_layout.addWidget(self._container)
    
    # 이후 레이아웃은 self._container에 추가
```

---

## 5. 검증 계획

### 자동화 테스트
```powershell
# Lint 검증
cd d:\Codes\Sigma9-0.1
ruff check frontend/gui/theme.py frontend/gui/ticker_info_window.py

# Import 순환 의존성 검사
lint-imports
```

### 수동 테스트
1. **GUI 실행**: `python -m frontend.main`
2. **Dashboard 로드 확인**: 메인 창 정상 표시
3. **TickerInfoWindow 열기**: Dashboard에서 티커 선택 → 정보 창 열기
4. **투명화 확인**:
   - Navy Background 없음
   - Acrylic 블러 효과 표시
   - 배경 드래그로 창 이동 가능
5. **테마 핫리로드**: Settings → Theme 변경 → 즉시 반영 확인

---

## 6. 롤백 계획

문제 발생 시:
```powershell
git checkout HEAD -- frontend/gui/theme.py
git checkout HEAD -- frontend/gui/ticker_info_window.py
```

---

## 7. 참고 자료

- [KI: Frameless Dialog Pattern](file:///C:/Users/USER/.gemini/antigravity/knowledge/frontend_ui_architecture/artifacts/architecture/frameless_dialog_pattern.md)
- [Devlog: 15-001 Ticker Info Viewer](file:///d:/Codes/Sigma9-0.1/docs/devlog/impl/15-001_ticker_info_viewer.md)
- [settings_dialog.py](file:///d:/Codes/Sigma9-0.1/frontend/gui/settings_dialog.py) — 참조 구현
