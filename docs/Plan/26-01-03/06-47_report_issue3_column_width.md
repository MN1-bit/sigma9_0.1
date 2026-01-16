# Issue 3 수정 완료 리포트: 테이블 컬럼 너비 가변 조절 및 저장

**완료일시**: 2026-01-03 06:41:00 (KST)

---

## 문제 설명

Tier 1 Watchlist와 Tier 2 Hot Zone 테이블의 컬럼 너비가 고정되어 있어 사용자가 드래그로 조절할 수 없었습니다. 또한 조절하더라도 GUI 재시작 시 초기화되는 문제가 있었습니다.

---

## 수정 내용

### 1. settings.yaml에 컬럼 너비 설정 추가

**파일**: `frontend/config/settings.yaml`

#### 추가된 내용
```yaml
tables:
  tier1_column_widths: [0, 55, 60, 45, 55]    # 0 = Stretch (Ticker)
  tier2_column_widths: [0, 60, 50, 45, 45, 40, 30]  # 0 = Stretch (Ticker)
```

---

### 2. Tier 2 테이블 헤더 설정 수정

**파일**: `frontend/gui/dashboard.py` (Line 537-551)

#### 변경 전
```python
# 헤더 크기 설정
t2_header = self.tier2_table.horizontalHeader()
t2_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Ticker
t2_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)    # Price
t2_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)    # Chg%
t2_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)    # zenV
t2_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)    # zenP
t2_header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)    # Ign
t2_header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)    # Sig
self.tier2_table.setColumnWidth(1, 60)
self.tier2_table.setColumnWidth(2, 50)
self.tier2_table.setColumnWidth(3, 45)
self.tier2_table.setColumnWidth(4, 45)
self.tier2_table.setColumnWidth(5, 40)
self.tier2_table.setColumnWidth(6, 30)
```

#### 변경 후
```python
# 헤더 크기 설정 (Interactive 모드 - 드래그로 크기 조절 가능)
t2_header = self.tier2_table.horizontalHeader()
t2_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Ticker (항상 Stretch)
for i in range(1, 7):
    t2_header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

# 저장된 컨럼 너비 로드
saved_widths = load_settings().get("tables", {}).get("tier2_column_widths", [0, 60, 50, 45, 45, 40, 30])
default_widths = [0, 60, 50, 45, 45, 40, 30]
for i in range(1, min(7, len(saved_widths))):
    width = saved_widths[i] if saved_widths[i] > 0 else default_widths[i]
    self.tier2_table.setColumnWidth(i, width)

# 컨럼 너비 변경 시 저장
t2_header.sectionResized.connect(lambda idx, old, new: self._save_column_widths("tier2", idx, new))
```

---

### 3. Tier 1 테이블 헤더 설정 수정

**파일**: `frontend/gui/dashboard.py` (Line 614-628)

#### 변경 전
```python
# 헤더 스타일 및 크기
header = self.watchlist_table.horizontalHeader()
header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Ticker
header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)    # Chg%
header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)    # DolVol
header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)    # Score
header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)    # Ign
self.watchlist_table.setColumnWidth(1, 55)
self.watchlist_table.setColumnWidth(2, 60)
self.watchlist_table.setColumnWidth(3, 45)
self.watchlist_table.setColumnWidth(4, 55)
```

#### 변경 후
```python
# 헤더 스타일 및 크기 (Interactive 모드 - 드래그로 크기 조절 가능)
header = self.watchlist_table.horizontalHeader()
header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Ticker (항상 Stretch)
for i in range(1, 5):
    header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

# 저장된 컨럼 너비 로드
saved_widths = load_settings().get("tables", {}).get("tier1_column_widths", [0, 55, 60, 45, 55])
default_widths = [0, 55, 60, 45, 55]
for i in range(1, min(5, len(saved_widths))):
    width = saved_widths[i] if saved_widths[i] > 0 else default_widths[i]
    self.watchlist_table.setColumnWidth(i, width)

# 컨럼 너비 변경 시 저장
header.sectionResized.connect(lambda idx, old, new: self._save_column_widths("tier1", idx, new))
```

---

### 4. 컬럼 너비 저장 메서드 추가

**파일**: `frontend/gui/dashboard.py` (Line 736-759)

#### 추가된 메서드
```python
def _save_column_widths(self, table_name: str, column: int, width: int):
    """
    컬럼 너비 변경 시 settings.yaml에 저장
    
    Args:
        table_name: "tier1" 또는 "tier2"
        column: 변경된 컬럼 인덱스
        width: 새 너비 (픽셀)
    """
    from frontend.config.loader import load_settings, save_setting
    
    # 0번 컬럼(Ticker)은 Stretch 모드이므로 저장하지 않음
    if column == 0:
        return
    
    key = f"tables.{table_name}_column_widths"
    current = load_settings().get("tables", {}).get(f"{table_name}_column_widths", [])
    
    # 리스트 확장 필요 시
    while len(current) <= column:
        current.append(0)
    
    current[column] = width
    save_setting(key, current)
```

---

## 수정 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| `frontend/config/settings.yaml` | `tables` 섹션 추가 (컬럼 너비 기본값) |
| `frontend/gui/dashboard.py` | Tier 1/2 테이블 `Interactive` 모드 전환, 저장/로드 로직 추가 |

---

## 동작 방식

### 초기 로드 시
1. `settings.yaml`에서 저장된 컬럼 너비 배열 로드
2. 각 컬럼에 저장된 너비 적용 (0이면 기본값 사용)
3. Ticker 컬럼(0번)은 항상 `Stretch` 모드로 남은 공간 채움

### 사용자 조절 시
1. 사용자가 컬럼 헤더 경계를 드래그하여 크기 조절
2. `sectionResized` 시그널 발생 → `_save_column_widths()` 호출
3. 현재 너비를 `settings.yaml`에 저장

### GUI 재시작 시
1. 저장된 너비가 자동으로 로드되어 이전 상태 복원

---

## 상태

✅ **완료**
