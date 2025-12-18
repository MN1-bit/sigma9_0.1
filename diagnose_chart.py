# ============================================================================
# 상세 차트 데이터 진단
# ============================================================================

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from backend.data.polygon_client import PolygonClient


async def detailed_diagnose(ticker: str = "SGBX"):
    api_key = os.getenv("MASSIVE_API_KEY", "")
    
    async with PolygonClient(api_key) as client:
        from datetime import datetime, timedelta
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        
        bars = await client.fetch_intraday_bars(
            ticker=ticker, multiplier=1,
            from_date=from_date, to_date=to_date, limit=5000
        )
    
    if not bars:
        print(f"No data for {ticker}")
        return
    
    print(f"Total bars: {len(bars)}")
    
    # High-Low 범위 분석
    hl_ranges = []
    non_doji_bars = []
    
    for i, bar in enumerate(bars):
        o, h, l, c = bar['open'], bar['high'], bar['low'], bar['close']
        hl_range = h - l
        hl_ranges.append(hl_range)
        
        # Non-Doji 캔들 (H != L)
        if h != l:
            non_doji_bars.append((i, o, h, l, c, hl_range))
    
    print(f"\nDoji bars (H=L): {len(bars) - len(non_doji_bars)}")
    print(f"Non-Doji bars (H!=L): {len(non_doji_bars)}")
    
    if non_doji_bars:
        # High-Low 범위 통계
        ranges = [b[5] for b in non_doji_bars]
        print(f"\nNon-Doji H-L Range Statistics:")
        print(f"  Min: {min(ranges):.4f}")
        print(f"  Max: {max(ranges):.4f}")
        print(f"  Avg: {sum(ranges)/len(ranges):.4f}")
        
        # 범위가 큰 상위 5개
        sorted_bars = sorted(non_doji_bars, key=lambda x: x[5], reverse=True)
        print(f"\nTop 5 Largest H-L Range Bars:")
        for idx, o, h, l, c, r in sorted_bars[:5]:
            print(f"  [{idx}] O:{o:.4f} H:{h:.4f} L:{l:.4f} C:{c:.4f} Range:{r:.4f}")
    
    # 가격의 전체 범위
    all_highs = [b['high'] for b in bars]
    all_lows = [b['low'] for b in bars]
    print(f"\nOverall Price Range:")
    print(f"  Global High: {max(all_highs):.4f}")
    print(f"  Global Low: {min(all_lows):.4f}")
    print(f"  Total Range: {max(all_highs) - min(all_lows):.4f}")


if __name__ == "__main__":
    asyncio.run(detailed_diagnose("SGBX"))
