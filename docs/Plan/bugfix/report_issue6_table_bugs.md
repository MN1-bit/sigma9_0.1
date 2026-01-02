# Issue 6 수정 완료 리포트: 테이블 버그 3건 (컬럼 연동, Tier2, 정렬)

**완료일시**: 2026-01-03 07:11:30 (KST)

---

## 문제 설명

사용자가 보고한 세 가지 버그:

1. **컬럼 연동 문제**: 하나의 컬럼을 드래그하면 다른 컬럼 너비도 같이 변경됨
2. **Tier2 가변 너비 미적용**: Tier2 테이블에 가변 너비가 적용되지 않음
3. **정렬 오류**: 헤더 클릭 시 오름차순/내림차순 정렬이 제대로 되지 않고 랜덤하게 흩뿌려짐

---

## 원인 분석

### 버그 1, 2: 컬럼 연동 및 Tier2 가변 너비
- **원인**: Ticker 컬럼이 `QHeaderView.ResizeMode.Stretch` 모드로 설정됨
- **문제**: Stretch 컬럼은 테이블의 남은 공간을 채우도록 자동 조절되므로, 다른 컬럼 크기가 바뀌면 Stretch 컬럼도 자동으로 조절됨

### 버그 3: 정렬 오류
- **원인**: `QTableWidgetItem`은 기본적으로 **문자열 기준**으로 정렬함
- **문제**: 숫자 `"10"`, `"2"`, `"100"`을 문자열로 정렬하면 `"10" < "100" < "2"` 순서가 됨 (사전순)

---

## 해결 방안

### 1. NumericTableWidgetItem 클래스 추가

**파일**: `frontend/gui/dashboard.py` (Line 85-113)

```python
class NumericTableWidgetItem(QTableWidgetItem):
    """
    숫자 값으로 정렬되는 QTableWidgetItem
    
    일반 QTableWidgetItem은 문자열 기준으로 정렬하여 
    "10" < "2" 같은 잘못된 결과가 나옴.
    이 클래스는 내부 숫자 값으로 정렬함.
    """
    def __init__(self, display_text: str, sort_value: float = 0.0):
        super().__init__(display_text)
        self._sort_value = sort_value
        self.setData(Qt.ItemDataRole.UserRole, sort_value)
    
    def __lt__(self, other):
        """정렬 비교: 숫자 값으로 비교"""
        if isinstance(other, NumericTableWidgetItem):
            return self._sort_value < other._sort_value
        try:
            other_value = other.data(Qt.ItemDataRole.UserRole)
            if other_value is not None:
                return self._sort_value < float(other_value)
        except (TypeError, ValueError):
            pass
        return super().__lt__(other)
```

### 2. 테이블 헤더 모드 변경

**Tier 2 테이블** (Line 568-577):
```python
# 변경 전
t2_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
for i in range(1, 7):
    t2_header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

# 변경 후
t2_header.setStretchLastSection(False)
for i in range(7):  # 모든 컬럼 Interactive
    t2_header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
self.tier2_table.setColumnWidth(0, 60)  # Ticker 최소 너비
```

**Tier 1 테이블** (Line 648-656):
```python
# 변경 전
header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
for i in range(1, 5):
    header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

# 변경 후
header.setStretchLastSection(False)
for i in range(5):  # 모든 컬럼 Interactive
    header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
self.watchlist_table.setColumnWidth(0, 60)  # Ticker 최소 너비
```

### 3. 숫자 컬럼에 NumericTableWidgetItem 적용

**Tier 2 `_set_tier2_row` 메서드** (Line 1545-1600):
```python
# 변경 전
price_item = QTableWidgetItem(price_text)
price_item.setData(Qt.ItemDataRole.UserRole, item.price)

# 변경 후
price_item = NumericTableWidgetItem(price_text, item.price)
```

**Tier 1 `_update_watchlist_panel` 메서드** (Line 1325-1380):
```python
# 변경 전  
change_item = QTableWidgetItem(f"{sign}{change_pct:.1f}%")
change_item.setData(Qt.ItemDataRole.UserRole, change_pct)

# 변경 후
change_item = NumericTableWidgetItem(f"{sign}{change_pct:.1f}%", change_pct)
```

---

## 수정 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| `frontend/gui/dashboard.py` | NumericTableWidgetItem 클래스 추가, 헤더 모드 변경, 숫자 컬럼에 적용 |

---

## 적용된 컬럼

### Tier 1 Watchlist
| 컬럼 | 타입 | 정렬 방식 |
|------|------|----------|
| Ticker | 텍스트 | 문자열 (QTableWidgetItem) |
| Chg% | 숫자 | 숫자 (NumericTableWidgetItem) |
| DolVol | 숫자 | 숫자 |
| Score | 숫자 | 숫자 |
| Ign | 숫자 | 숫자 |

### Tier 2 Hot Zone
| 컬럼 | 타입 | 정렬 방식 |
|------|------|----------|
| Ticker | 텍스트 | 문자열 (QTableWidgetItem) |
| Price | 숫자 | 숫자 (NumericTableWidgetItem) |
| Chg% | 숫자 | 숫자 |
| zenV | 숫자 | 숫자 |
| zenP | 숫자 | 숫자 |
| Ign | 숫자 | 숫자 |
| Sig | 텍스트 | 문자열 (QTableWidgetItem) |

---

## 동작 확인

1. ✅ 컬럼 하나를 드래그해도 다른 컬럼이 변경되지 않음
2. ✅ Tier2 테이블 컬럼 너비 조절 가능
3. ✅ 헤더 클릭 시 올바른 오름차순/내림차순 정렬
4. ✅ 컬럼 너비가 `settings.yaml`에 저장됨

---

## 상태

✅ **완료**
