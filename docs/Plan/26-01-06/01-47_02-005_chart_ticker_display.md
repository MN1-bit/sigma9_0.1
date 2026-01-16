# 02-005: 차트 위젯에 티커명 표시

## 문제 설명
차트 위젯에 현재 표시 중인 종목의 티커명이 표시되지 않음.

## 근본 원인
`pyqtgraph_chart.py`의 `PyQtGraphChartWidget`에 종목명 표시 기능이 구현되지 않음.
`_current_chart_ticker`는 `dashboard.py`에서만 추적됨.

---

## 제안된 해결책

### 차트 위젯 상단에 티커 라벨 추가
- 툴바 영역(타임프레임 버튼 옆)에 티커명 라벨 추가
- `set_ticker()` 메서드로 외부에서 설정 가능

---

## 수정 파일

### [MODIFY] [pyqtgraph_chart.py](file:///d:/Codes/Sigma9-0.1/frontend/gui/chart/pyqtgraph_chart.py)

**수정 1**: `_setup_ui()` (라인 142~)
- 툴바에 티커 라벨 추가

```diff
         # 타임프레임 버튼 그룹
         self._tf_buttons = {}
         self._current_timeframe = '1D'  # 일봉 기본
         
+        # [Issue 01-005] 티커 라벨 추가
+        self._ticker_label = QLabel("")
+        self._ticker_label.setStyleSheet(f"""
+            QLabel {{
+                color: {theme.get_color('text')};
+                font-size: 14px;
+                font-weight: bold;
+                padding: 0 8px;
+                background: transparent;
+            }}
+        """)
+        toolbar.addWidget(self._ticker_label)
+        
         for tf in self.TIMEFRAMES:
             btn = QPushButton(tf)
```

**수정 2**: 새 메서드 추가

```python
def set_ticker(self, ticker: str):
    """
    현재 차트 종목 설정 및 라벨 업데이트
    
    Args:
        ticker: 종목 코드 (예: "AAPL", "NVDA")
    """
    self._current_ticker = ticker
    self._ticker_label.setText(ticker)
```

---

### [MODIFY] [dashboard.py](file:///d:/Codes/Sigma9-0.1/frontend/gui/dashboard.py)

**수정**: `_apply_pending_chart_data()` 또는 차트 로드 완료 시점

```diff
     def _apply_pending_chart_data(self):
         """비동기 차트 데이터 로드 완료 후 적용"""
         if not self._pending_chart_data:
             return
         
         ticker, data = self._pending_chart_data
         self._pending_chart_data = None
         
+        # [Issue 01-005] 차트 위젯에 티커명 설정
+        self.chart_widget.set_ticker(ticker)
+        
         # 차트 업데이트...
```

---

## 검증 계획

### 수동 테스트
1. 애플리케이션 실행: `python -m frontend.main`
2. Watchlist에서 종목 클릭
3. 차트 로드 완료 후:
   - ✅ 차트 상단 툴바 왼쪽에 티커명(예: "AAPL")이 표시됨
   - ✅ 다른 종목 선택 시 티커명이 변경됨
4. 타임프레임 버튼과 티커 라벨이 시각적으로 구분되는지 확인

> [!TIP]
> 추후 가격이나 change%도 함께 표시하도록 확장 가능합니다.
