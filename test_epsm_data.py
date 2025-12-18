"""
EPSM 9-11월 데이터 확인 스크립트
"""
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

async def main():
    # loguru 비활성화
    from loguru import logger
    logger.disable("backend.data.polygon_client")
    
    from backend.data.polygon_client import PolygonClient
    
    api_key = os.getenv("MASSIVE_API_KEY")
    if not api_key:
        print("ERROR: MASSIVE_API_KEY not set")
        return
    
    print(f"API Key: {api_key[:10]}...")
    
    async with PolygonClient(api_key=api_key) as client:
        print("\n" + "="*60)
        print("EPSM 15m data check (2025-09-01 ~ 2025-11-13)")
        print("="*60)
        
        bars = await client.fetch_intraday_bars(
            ticker="EPSM",
            multiplier=15,
            from_date="2025-09-01",
            to_date="2025-11-13",
            limit=5000
        )
        
        if bars:
            first_bar = bars[0]
            last_bar = bars[-1]
            
            first_time = datetime.fromtimestamp(first_bar["timestamp"] / 1000)
            last_time = datetime.fromtimestamp(last_bar["timestamp"] / 1000)
            
            print(f"Total: {len(bars)} bars")
            print(f"First: {first_time}")
            print(f"Last: {last_time}")
            
            # Monthly distribution
            months = {}
            for bar in bars:
                dt = datetime.fromtimestamp(bar["timestamp"] / 1000)
                month_key = dt.strftime("%Y-%m")
                months[month_key] = months.get(month_key, 0) + 1
            
            print(f"\nMonthly distribution:")
            for month, count in sorted(months.items()):
                print(f"  {month}: {count} bars")
        else:
            print("NO DATA")
        
        print("\n" + "="*60)
        print("Per-month query:")
        print("="*60)
        
        for month_range in [
            ("2025-09-01", "2025-09-30"),
            ("2025-10-01", "2025-10-31"),
            ("2025-11-01", "2025-11-13"),
        ]:
            from_d, to_d = month_range
            bars = await client.fetch_intraday_bars(
                ticker="EPSM",
                multiplier=15,
                from_date=from_d,
                to_date=to_d,
                limit=5000
            )
            print(f"  {from_d} ~ {to_d}: {len(bars)} bars")

if __name__ == "__main__":
    asyncio.run(main())
