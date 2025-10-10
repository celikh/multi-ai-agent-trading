#!/usr/bin/env python3
"""Simple test to check WebSocket"""

import asyncio
import ccxt.pro as ccxt

async def test():
    print("Connecting to Binance...")
    exchange = ccxt.binance()

    try:
        print("Watching BTC/USDT ticker...")
        ticker = await exchange.watch_ticker('BTC/USDT')
        print(f"✅ Ticker received: {ticker['last']}")

        print("Watching OHLCV...")
        ohlcv = await exchange.watch_ohlcv('BTC/USDT', '1m')
        print(f"✅ OHLCV received: {len(ohlcv)} candles")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(test())
