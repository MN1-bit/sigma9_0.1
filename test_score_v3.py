"""Quick test for score_v3 calculation"""
import asyncio
from backend.strategies.seismograph import SeismographStrategy
from backend.data.database import MarketDB

async def test():
    db = MarketDB("data/market_data.db")
    await db.initialize()
    bars = await db.get_daily_bars("AMCI", days=60)
    if bars:
        s = SeismographStrategy()
        data = [bar.to_dict() for bar in reversed(bars)]
        result = s.calculate_watchlist_score_detailed("AMCI", data)
        print(f"V1={result.get('score')}")
        print(f"V2={result.get('score_v2')}")
        print(f"V3={result.get('score_v3')}")
        print(f"V3_intensities={result.get('intensities_v3')}")
    else:
        print("No bars found for AMCI")
    await db.close()

if __name__ == "__main__":
    asyncio.run(test())
