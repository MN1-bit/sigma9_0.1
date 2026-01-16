# R-3 대조군 매칭 로직 구현 계획서

> **작성일**: 2026-01-15 | **예상**: 4h  
> **선행**: R-2 완료 (daygainers_75plus.csv 추출)

---

## 1. 목표

Daygainer(75%+ 급등주)에 대응하는 **대조군(Control Group)** 자동 매칭 로직 개발.
- 같은 날, 비슷한 조건에서 급등하지 않은 종목 추출
- "Failed Pump" 패턴(RVOL 스파이크 후 하락) 별도 라벨링
- ML 학습용 데이터셋 생성

---

## 2. 대조군 설계 (v4 확정)

| 조건 | 값 | 근거 |
|------|-----|------|
| 동일 날짜 | 필수 | 시장 환경 통제 |
| 종가 등락률 | -50% ~ +10% | 급등 실패 ~ 평범 |
| 가격 | ≥ $0.1 | 초저가 제외 |
| RVOL 스파이크 | 분봉 RVOL ≥ 2x 존재 | 관심 받았던 종목 필터 |
| 가격 구간 매칭 | Tier 기반 (Phase 1) | 가격 프록시 |
| 비율 | 1:5 | Daygainer당 5개 대조군 |

### 가격 구간 (Price Tier)
```python
PRICE_TIERS = {
    'penny': (0.1, 1.0),     # $0.1 ~ $1
    'low': (1.0, 5.0),       # $1 ~ $5
    'mid': (5.0, 20.0),      # $5 ~ $20
    'high': (20.0, float('inf'))  # $20+
}
```

### Failed Pump 라벨
```python
is_failed_pump = (
    has_rvol_spike and           # 분봉 RVOL ≥ 2x 존재
    high_to_close_drop >= 0.30   # 장중 고점 대비 30% 하락
)
```

### RVOL 피처화
```python
# RVOL 자체를 피처로 저장 (연속값)
rvol_max = max(bar_rvol for bar in intraday_bars)  # 당일 최대 RVOL
# → ML 학습 시 급등 예측 피처로 활용
```

---

## 3. 레이어 체크

- [x] 레이어 규칙 위반 없음 (독립 스크립트)
- [x] 순환 의존성 없음
- [x] DI Container 등록 필요: **아니오**

> 이 작업은 `scripts/` 폴더의 독립 스크립트로 구현.  
> 기존 backend/frontend 아키텍처와 무관.

---

## 4. 변경/생성 파일

| 파일 | 유형 | 예상 라인 |
|------|-----|----------|
| `scripts/build_control_group.py` | [NEW] | ~200 |
| `scripts/control_groups.csv` | [NEW] 출력 | - |
| `docs/Plan/backtest/_detection.md` | [MODIFY] | +10 (R-3 완료 표시) |

---

## 5. 기존 솔루션 검색 결과

| 솔루션 | 출처 | 채택 여부 | 사유 |
|--------|------|----------|------|
| Propensity Score Matching (statsmodels) | PyPI | ❌ | 시총/섹터 데이터 없음, 과도 |
| Random Stratified Sampling (sklearn) | PyPI | ⚠️ 참고 | 부분 활용 가능 |
| 직접 구현 | - | ✅ 채택 | 조건 맞춤형 필요 |

---

## 6. 실행 단계

### Step 1: 일봉 기반 1차 후보군 추출
```
1. 각 Daygainer의 날짜별로 조건 충족 종목 필터링
   - change_pct: -50% ~ +10%
   - price >= $0.1
   - 동일 가격 티어
2. 결과: {date: [candidate_tickers]} 딕셔너리
```

### Step 2: RVOL 스파이크 검사 (분봉 기반)
```
1. 후보군 중 분봉 데이터 로드
   - 로컬에 없으면 → Massive API로 수집
2. 각 분봉의 RVOL 계산: bar_volume / avg_volume_20d
3. RVOL >= 2x 분봉 존재 여부 체크
4. rvol_max 값 저장 (피처용)
5. 필터: has_rvol_spike == True만 남김
```

### Step 2-1: Massive API Fallback
```python
# 분봉 데이터 없는 종목 처리
def fetch_intraday_from_massive(ticker: str, date: str) -> pd.DataFrame:
    """Massive API로 분봉 데이터 수집"""
    # mcp_massive 활용
    # 수집 후 로컬 parquet에 캐싱
    pass
```

### Step 3: Failed Pump 라벨링
```
1. 장중 고점 (intraday_high) 계산
2. high_to_close_drop = (high - close) / high
3. drop >= 30% → failed_pump = True
```

### Step 4: 1:5 샘플링 및 CSV 출력
```
1. 각 Daygainer당 조건 충족 종목 중 최대 5개 랜덤 샘플
   - 가능하면 failed_pump 1~2개 포함
   - 나머지는 일반 종목
2. 출력 형식 (rvol_max 피처 포함):
   daygainer_date,daygainer_ticker,control_ticker,control_type,rvol_max
   2026-01-12,LVLU,ABCD,normal,3.5
   2026-01-12,LVLU,EFGH,failed_pump,8.2
```

---

## 7. 검증

### 7.1 스크립트 실행 테스트
```bash
cd d:\Codes\Sigma9-0.1
python scripts/build_control_group.py
```

**예상 출력**:
- `scripts/control_groups.csv` 생성
- 레코드 수: ~6,000건 (1,284 Daygainers × 5)
- 컬럼: daygainer_date, daygainer_ticker, control_ticker, control_type

### 7.2 데이터 품질 검증
```python
# scripts/build_control_group.py 내 검증 코드 포함
def validate_output():
    df = pd.read_csv('scripts/control_groups.csv')
    
    # 1. 날짜 일치 확인
    assert (df['daygainer_date'] == df['control_date']).all()
    
    # 2. 등락률 범위 확인
    assert df['control_change_pct'].between(-50, 10).all()
    
    # 3. 비율 확인 (평균 4~5개)
    ratio = len(df) / df['daygainer_ticker'].nunique()
    assert 3 <= ratio <= 5
    
    # 4. failed_pump 비율 (10~30%)
    fp_ratio = (df['control_type'] == 'failed_pump').mean()
    assert 0.05 <= fp_ratio <= 0.40
```

### 7.3 수동 검증 (사용자)
1. `control_groups.csv` 열어서 샘플 10개 확인
2. 날짜/가격구간 매칭 여부 육안 검증
3. Failed Pump 라벨 합리성 확인

---

## 8. 리스크 및 대안

| 리스크 | 영향 | 대안 |
|--------|------|------|
| 분봉 데이터 없는 종목 | 일부 후보군 제외 | 일봉만으로 fallback |
| RVOL 조건 너무 엄격 | 후보군 부족 | 임계값 2x로 완화 |
| 특정 날짜 대조군 부족 | 불균형 데이터 | 인접 날짜 허용 검토 |

---

## 9. 다음 단계 (R-4 선행조건)

- R-3 완료 후: `control_groups.csv` + `daygainers_75plus.csv` 결합
- R-4: D-1 시점 지표 계산 파이프라인 구축
