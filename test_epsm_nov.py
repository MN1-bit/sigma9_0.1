"""EPSM 11/12-15 데이터 확인"""
import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
from loguru import logger
logger.disable("backend.data.polygon_client")
load_dotenv()

async def main():
    from backend.data.polygon_client import PolygonClient
    api_key = os.getenv("MASSIVE_API_KEY")
    
    async with PolygonClient(api_key=api_key) as client:
        print("EPSM 5m bars for 2025-11-12 ~ 2025-11-15")
        print("="*50)
        
        bars = await client.fetch_intraday_bars(
            ticker="EPSM",
            multiplier=5,
            from_date="2025-11-12",
            to_date="2025-11-15",
            limit=5000
        )
        
        if bars:
            print(f"Total: {len(bars)} bars")
            print(f"First: {datetime.fromtimestamp(bars[0]['timestamp']/1000)}")
            print(f"Last: {datetime.fromtimestamp(bars[-1]['timestamp']/1000)}")
            
            # 날짜별 분포
            dates = {}
            for bar in bars:
                dt = datetime.fromtimestamp(bar['timestamp']/1000)
                d = dt.strftime("%Y-%m-%d")
                dates[d] = dates.get(d, 0) + 1
            print("\nPer-day breakdown:")
            for d, cnt in sorted(dates.items()):
                print(f"  {d}: {cnt} bars")
        else:
            print("NO DATA for this range!")

asyncio.run(main())
