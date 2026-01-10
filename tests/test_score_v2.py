"""Quick test for score_v2 calculation - output to file"""

import asyncio
import traceback
from backend.strategies.seismograph import SeismographStrategy
from backend.data.database import MarketDB


async def test():
    with open("test_output.txt", "w") as f:
        try:
            db = MarketDB("data/market_data.db")
            await db.initialize()

            bars = await db.get_daily_bars("AMCI", days=20)

            if bars:
                s = SeismographStrategy()
                data = [bar.to_dict() for bar in reversed(bars)]
                result = s.calculate_watchlist_score_detailed("AMCI", data)

                f.write(f"V1_SCORE={result.get('score', 'MISSING')}\n")
                f.write(f"V2_SCORE={result.get('score_v2', 'MISSING')}\n")
                f.write(f"KEYS={list(result.keys())}\n")
                f.write(f"INTENSITIES={result.get('intensities', 'MISSING')}\n")

            await db.close()
            f.write("TEST COMPLETED\n")
        except Exception as e:
            f.write(f"ERROR: {e}\n")
            traceback.print_exc(file=f)


if __name__ == "__main__":
    asyncio.run(test())
    print("Output written to test_output.txt")
