# GUI Development Report: v1.4 (Chart Overhaul)
**Date:** 2025-12-18
**Author:** Assistant

## 1. 개요
본 리포트는 GUI 차트 컴포넌트(`PyQtGraphChartWidget`)의 주요 개선 사항 및 버그 수정 내역을 기술합니다. 특히 차트의 가시성과 사용자 경험(UX)을 향상시키기 위해 축(Axis) 위치 재조정, 자동 스케일링 로직 강화, 그리고 주말 데이터 공백(Gap) 제거 작업을 중점적으로 수행했습니다.

## 2. 주요 변경 사항

### 2.1 차트 축(Axis) 레이아웃 재구성
사용자 피드백을 반영하여 TradingView 등 전문 차트 툴과 유사한 레이아웃으로 변경했습니다.
- **Price Chart Y-Axis:** 좌측 → **우측** 이동 (캔들 차트 시인성 확보)
- **Volume Chart Y-Axis:** 우측 → **좌측** 이동 (가격 축과 분리하여 혼동 방지)
- **Volume Y-Axis Format:** 과학적 표기법(예: `1.2e6`) 대신 자연수 약어(예: `1.2M`, `500K`) 적용

### 2.2 강력한 Y축 자동 스케일링 (Robust Auto-Scaling)
기존의 단순 `autoRange()`는 전체 데이터를 기준으로 하거나, 줌/팬 동작 시 반응이 늦는 문제가 있었습니다.
- **ViewBox 연동:** X축의 가시 범위(`viewRange`)가 변경될 때마다(`sigXRangeChanged`) 트리거되는 커스텀 스케일러 구현.
- **동적 계산:** 현재 화면에 보이는 캔들의 고가(High)와 저가(Low)를 실시간으로 스캔하여 Y축 범위를 동적으로 맞춤.
- **결과:** 사용자가 차트를 좌우로 이동(Pan)하더라도 캔들이 항상 화면 중앙에 꽉 차게 표시됨.

### 2.3 툴팁 시스템 (Interactive Tooltips)
마우스 호버 시 상세 정보를 표시하는 인터랙티브 툴팁을 구현했습니다.
- **Candlestick Tooltip:** 날짜, 시가(O), 고가(H), 저가(L), 종가(C) 표시
- **Volume Tooltip:** 날짜, 거래량(Volume) 표시
- **데이터 캐싱:** 마우스 이동 시 성능 저하를 방지하기 위해 렌더링용 데이터와 별도로 `_candle_data`, `_volume_data` 캐시 리스트를 운용하여 빠른 조회(O(1) Access) 실현.

### 2.4 주말/공휴일 공백(Gap) 제거
주식 시장은 주말이나 공휴일에 데이터가 없습니다. 기존 타임스탬프 기반 X축은 이 기간을 빈 공간으로 표시하여 차트의 연속성을 해쳤습니다.
- **Index-Based X-Axis:** X축 좌표를 시간(Time)이 아닌 **인덱스(0, 1, 2...)**로 변경.
- **IndexDateAxis:** 인덱스를 다시 날짜 문자열(`MM-DD`)로 매핑해주는 커스텀 축 클래스 구현.
- **Indicator Mapping:** 이동평균선(MA), VWAP, ATR 등 모든 보조지표와 마커도 인덱스 좌표계에 맞춰 렌더링되도록 리팩토링.
- **결과:** 금요일 장 마감 봉 바로 옆에 월요일 시가 봉이 붙어서 표시됨 (연속성 확보).

### 2.5 초기화 버그 수정
- **증상:** 종목 변경 시(`clear()` 호출 후) Y축 오토 스케일링이 풀리거나 툴팁이 사라지는 현상.
- **원인:** `plot.clear()`가 플롯의 모든 아이템과 설정까지 초기화하기 때문.
- **해결:** `clear()` 대신 `removeItem()`으로 데이터 아이템만 선별적으로 제거하여 축 설정과 툴팁 객체를 유지함.

## 3. 기술적 세부 사항
- **File:** `frontend/gui/chart/pyqtgraph_chart.py`
- **Class:** `PyQtGraphChartWidget`, `IndexDateAxis`
- **Key Methods:**
  - `_update_y_range()`: 가시 영역 기반 Y축 동적 계산
  - `set_candlestick_data()`: 인덱스 매핑 및 데이터 캐싱
  - `_timestamp_map`: {Timestamp: Index} 매핑 테이블

## 4. 향후 계획
- **Multi-Timeframe Support (Step 2.7):** 인트라데이 데이터 연동 및 타임프레임 선택 기능 개발 예정.
- **Note:** 공휴일/비규칙적 폐장일 처리는 본 업데이트의 Index-based X-axis 도입으로 자연스럽게 해결되어 추가 개발 계획에서 제외됨.
