#!/usr/bin/env python3
"""Quick script to check if data collection is working"""
import asyncio
from infrastructure.database.influxdb import get_influx

async def main():
    db = get_influx()

    # Check last 10 minutes of OHLCV data
    query = '''
    from(bucket: "market_data")
        |> range(start: -10m)
        |> filter(fn: (r) => r["_measurement"] == "ohlcv")
        |> filter(fn: (r) => r["symbol"] == "BTC/USDT")
        |> filter(fn: (r) => r["_field"] == "close")
        |> last()
    '''

    data = await db.query(query)

    if data:
        print(f"✅ Found {len(data)} data points")
        for item in data:
            print(f"   {item.get('_time')}: {item.get('_value')}")
    else:
        print("❌ No data found in last 10 minutes")

if __name__ == "__main__":
    asyncio.run(main())
