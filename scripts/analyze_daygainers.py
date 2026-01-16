"""
Daygainer 분석 스크립트
- 일봉 데이터에서 임계값별 급등 종목 수 카운트
"""

import pandas as pd
from pathlib import Path

# 데이터 경로
DAILY_PARQUET = Path("d:/Codes/Sigma9-0.1/data/parquet/daily/all_daily.parquet")

def analyze_daygainers():
    print("=" * 60)
    print("Daygainer Analysis")
    print("=" * 60)
    
    # 데이터 로드
    print(f"\n[Loading] {DAILY_PARQUET}")
    df = pd.read_parquet(DAILY_PARQUET)
    
    print(f"\n[Data Overview]")
    print(f"   - Total rows: {len(df):,}")
    print(f"   - Columns: {list(df.columns)}")
    
    # 컬럼명 확인 (대소문자 다를 수 있음)
    print(f"\n   - Sample data:")
    print(df.head(3).to_string())
    
    # 컬럼명 정규화 (소문자로)
    df.columns = df.columns.str.lower()
    
    # 날짜 범위 확인
    if 'date' in df.columns:
        date_col = 'date'
    elif 'timestamp' in df.columns:
        date_col = 'timestamp'
    else:
        date_col = df.columns[0]  # 첫 번째 컬럼 시도
    
    try:
        df[date_col] = pd.to_datetime(df[date_col])
        print(f"\n[Period] {df[date_col].min()} ~ {df[date_col].max()}")
        print(f"   - Trading days: {df[date_col].nunique():,}")
    except:
        print(f"\n[Warning] Date parse failed: {date_col}")
    
    # 티커 수 확인
    if 'ticker' in df.columns:
        ticker_col = 'ticker'
    elif 'symbol' in df.columns:
        ticker_col = 'symbol'
    else:
        ticker_col = None
    
    if ticker_col:
        print(f"   - Tickers: {df[ticker_col].nunique():,}")
    
    # 등락률 계산 (시가 대비 종가)
    if 'open' in df.columns and 'close' in df.columns:
        df['change_pct'] = (df['close'] - df['open']) / df['open'] * 100
    else:
        print("\n[Error] 'open' or 'close' column not found")
        return
    
    # ========== 필터 적용 ==========
    MIN_DOLLAR_VOLUME = 500_000  # 최소 거래대금 $50만
    MIN_PRICE = 0.1              # 최소 가격 $0.1
    
    # 거래대금 계산
    df['dollar_volume'] = df['close'] * df['volume']
    
    print(f"\n[Filters Applied]")
    print(f"   - Min Dollar Volume: ${MIN_DOLLAR_VOLUME:,}")
    print(f"   - Min Price: ${MIN_PRICE}")
    
    before_filter = len(df)
    df = df[(df['dollar_volume'] >= MIN_DOLLAR_VOLUME) & (df['close'] >= MIN_PRICE)]
    after_filter = len(df)
    print(f"   - Rows: {before_filter:,} -> {after_filter:,} ({after_filter/before_filter*100:.1f}%)")
    
    # 임계값별 분석
    thresholds = [10, 20, 30, 50, 75, 100, 150]
    
    print("\n" + "=" * 60)
    print("Daygainer Count by Threshold")
    print("=" * 60)
    print(f"{'Threshold':>10} | {'Count':>10} | {'Ratio':>10} | {'Per Year':>12}")
    print("-" * 50)
    
    total_rows = len(df)
    
    # 날짜 범위로 연수 계산
    try:
        years = (df[date_col].max() - df[date_col].min()).days / 365
        if years < 0.1:
            years = 1  # 최소 1년
    except:
        years = 1
    
    for threshold in thresholds:
        count = len(df[df['change_pct'] >= threshold])
        pct = count / total_rows * 100
        per_year = count / years if years > 0 else count
        print(f"{threshold:>8}%+ | {count:>10,} | {pct:>9.4f}% | {per_year:>10.1f}/yr")
    
    # 상세 분석: 상위 20개
    print("\n" + "=" * 60)
    print("Top 20 All-Time Gainers (by change %)")
    print("=" * 60)
    
    top20 = df.nlargest(20, 'change_pct')
    
    if ticker_col and date_col:
        display_cols = [date_col, ticker_col, 'open', 'close', 'change_pct']
        if 'volume' in df.columns:
            display_cols.append('volume')
        
        top20_display = top20[display_cols].copy()
        top20_display['change_pct'] = top20_display['change_pct'].round(2).astype(str) + '%'
        print(top20_display.to_string(index=False))
    else:
        print(top20[['open', 'close', 'change_pct']].head(20).to_string())
    
    # 50%+ 전체 목록 저장
    print("\n" + "=" * 60)
    print("Saving 50%+ Gainers to CSV...")
    print("=" * 60)
    
    gainers_50 = df[df['change_pct'] >= 50].copy()
    if len(gainers_50) > 0:
        # 정렬: 날짜 내림차순
        if date_col in gainers_50.columns:
            gainers_50 = gainers_50.sort_values(date_col, ascending=False)
        
        # 저장할 컬럼 선택
        if ticker_col:
            save_cols = [date_col, ticker_col, 'open', 'close', 'change_pct']
            if 'volume' in df.columns:
                save_cols.append('volume')
            gainers_50_save = gainers_50[save_cols].copy()
        else:
            gainers_50_save = gainers_50
        
        # CSV 저장
        output_path = "scripts/daygainers_50plus.csv"
        gainers_50_save.to_csv(output_path, index=False)
        print(f"   Saved {len(gainers_50_save):,} records to {output_path}")
        
        # 콘솔에 일부 출력
        print(f"\n   Preview (first 30):")
        preview = gainers_50_save.head(30).copy()
        preview['change_pct'] = preview['change_pct'].round(2).astype(str) + '%'
        print(preview.to_string(index=False))
    else:
        print("No 50%+ gainers found")
    
    # 75%+ 목록도 저장
    gainers_75 = df[df['change_pct'] >= 75].copy()
    if len(gainers_75) > 0:
        if date_col in gainers_75.columns:
            gainers_75 = gainers_75.sort_values(date_col, ascending=False)
        if ticker_col:
            save_cols = [date_col, ticker_col, 'open', 'close', 'change_pct']
            if 'volume' in df.columns:
                save_cols.append('volume')
            gainers_75_save = gainers_75[save_cols]
        else:
            gainers_75_save = gainers_75
        output_path_75 = "scripts/daygainers_75plus.csv"
        gainers_75_save.to_csv(output_path_75, index=False)
        print(f"\n   Also saved {len(gainers_75_save):,} records (75%+) to {output_path_75}")
    
    # 100%+ 목록도 저장
    gainers_100 = df[df['change_pct'] >= 100].copy()
    if len(gainers_100) > 0:
        if date_col in gainers_100.columns:
            gainers_100 = gainers_100.sort_values(date_col, ascending=False)
        if ticker_col:
            save_cols = [date_col, ticker_col, 'open', 'close', 'change_pct']
            if 'volume' in df.columns:
                save_cols.append('volume')
            gainers_100_save = gainers_100[save_cols]
        else:
            gainers_100_save = gainers_100
        output_path_100 = "scripts/daygainers_100plus.csv"
        gainers_100_save.to_csv(output_path_100, index=False)
        print(f"   Also saved {len(gainers_100_save):,} records (100%+) to {output_path_100}")
    
    print("\n[Done]")

if __name__ == "__main__":
    analyze_daygainers()
