# 14-002: Info Panel 레이아웃 재설계

> **작성일**: 2026-01-13 | **예상**: 2시간

---

## 1. 목표

- TickerInfoWindow를 3-컬럼 구조로 재설계
- 정보 밀도와 가독성 향상
- 모든 TickerInfo 데이터 필드 매핑

---

## 2. 레이어 체크

- [x] 레이어 규칙 위반 없음 (frontend 내부 변경)
- [x] 순환 의존성 없음
- [ ] DI Container 등록 필요: **아니오**

---

## 3. 기존 솔루션 검색 결과

| 솔루션 | 출처 | 채택 여부 | 사유 |
|--------|------|----------|------|
| QTabWidget | Qt 내장 | ✅ 채택 | 탭 기반 UI |
| QGridLayout | Qt 내장 | ✅ 채택 | 3-컬럼 레이아웃 |

---

## 4. 변경 파일

| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
| `frontend/gui/ticker_info_window.py` | MAJOR REFACTOR | +300 |

---

## 5. 신규 레이아웃

```
+-----------------------------------------------------------------------+
|  Ticker | Apple Inc. | $259.37 (+0.12%) | 시총 $3.8T | Last updated: |
+-----------------------+-------------------------------+---------------+
| [Col 1: 프로필/메타]  | [Col 2: 핵심 데이터 (Tabs)]   | [Col 3: 뉴스] |
|                       |                               |               |
| 회사 설명 (3줄 요약)  | [ 재무 | 배당 | 공시 | 유동성 ]| 관련 종목     |
| [더보기 v]            |                               | [MSFT][NVDA]..|
|                       | ----------------------------- |               |
| --------------------- | | 기간 | 매출 | 순이익 |    | ---------------- |
| 업종: Computers       | | TTM  | $416B| $112B  |    |               |
| 직원: 166,000         | | Q4   | $102B| $27B   |    | 최신 뉴스     |
| 상장일: 1980-12-12    | | ...  | ...  | ...    |    |               |
|                       | ----------------------------- | - Semico...   |
| --------------------- |                               | - Should..    |
| 주소/웹사이트         | (하단: Split 정보 병기)       | - Predict...  |
| CIK / FIGI (작게)     |                               |               |
+-----------------------+-------------------------------+---------------+
```

---

## 6. 데이터 매핑 (TickerInfo 기반)

### Header Row
| 요소 | 데이터 소스 |
|------|-------------|
| Ticker | `ticker` |
| 거래소 | `profile["primary_exchange"]` |
| 회사명 | `profile["name"]` |
| 현재가 | `snapshot["ticker"]["lastTrade"]["p"]` |
| 등락 | `snapshot["ticker"]["todaysChangePerc"]` |
| 시가총액 | `profile["market_cap"]` |
| Last updated | `snapshot["ticker"]["updated"]` |

### Column 1: 프로필/메타
| 요소 | 데이터 소스 |
|------|-------------|
| 회사 설명 | `profile["description"]` |
| 업종 | `profile["sic_description"]` |
| 직원 수 | `profile["total_employees"]` |
| 발행주식 | `profile["share_class_shares_outstanding"]` |
| 상장일 | `profile["list_date"]` |
| 웹사이트 | `profile["homepage_url"]` |
| CIK | `profile["cik"]` |

### Column 2: Tabs
- **재무**: `financials[n]` (revenues, net_income_loss, EPS)
- **배당**: `dividends[n]` (cash_amount, pay_date)
- **공시**: `filings[n]` (type → SEC_FILING_TYPES 변환)
- **유동성**: `float_data`, `short_interest`

### Column 3: 뉴스/관련
- **관련 종목**: `related_companies[n]["ticker"]`
- **뉴스**: `news[n]["title"]`, `news[n]["article_url"]`

---

## 7. 실행 단계

### Step 1: Header 리팩토링 (30분)
- 기존 헤더 → 새 데이터 매핑 (거래소, 시총 추가)

### Step 2: 3-Column 레이아웃 (30분)
- `QHBoxLayout` + 3개 `QVBoxLayout`
- Col1: 200px, Col2: stretch, Col3: 250px

### Step 3: Column 1 구현 (20분)
- Profile DetailTable 재사용

### Step 4: Column 2 QTabWidget (30분)
- 4개 탭: 재무/배당/공시/유동성

### Step 5: Column 3 뉴스 (20분)
- 관련 종목 버튼 + 뉴스 리스트

---

## 8. 검증

### 자동 테스트
```bash
ruff check frontend/gui/ticker_info_window.py
```

### 수동 테스트
1. 앱 실행 → Info 창 열기
2. 3-컬럼 레이아웃 렌더링 확인
3. 탭 전환 동작 확인
4. 관련 종목 클릭 → 티커 전환
5. 뉴스 클릭 → 브라우저 열기
6. 창 리사이즈 시 반응형 동작

---

**다음**: `/IMP-execution`
