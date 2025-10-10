#!/usr/bin/env python3
"""Test data collection agent"""

import asyncio
from agents.data_collection.agent import DataCollectionAgent

async def main():
    print("Starting data collection test...")

    agent = DataCollectionAgent(
        exchange_name="binance",
        symbols=["BTC/USDT"],
        interval="1m",
    )

    try:
        print("Initializing agent...")
        await agent.initialize()
        print("Agent initialized successfully!")

        print("Starting agent...")
        # Run for 30 seconds
        async def run_for_duration():
            await agent.start()

        task = asyncio.create_task(run_for_duration())
        await asyncio.sleep(30)

        print("\nStopping agent...")
        await agent.shutdown()
        task.cancel()

        print("Test completed!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
