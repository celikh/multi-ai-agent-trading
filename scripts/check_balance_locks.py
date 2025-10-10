#!/usr/bin/env python3
"""Check balance locks in database"""
import asyncio
from infrastructure.database.postgres import PostgresManager

async def main():
    pg = PostgresManager()
    await pg.connect()

    # Check balance_locks table
    result = await pg.execute_query("""
        SELECT symbol, order_id, amount, created_at
        FROM balance_locks
        ORDER BY created_at DESC
        LIMIT 10
    """)

    if result:
        print("Recent balance locks:")
        for row in result:
            symbol, order_id, amount, created_at = row
            print(f"  - {symbol}: ${amount:.2f} (order: {order_id[:8]}...) at {created_at}")
    else:
        print("No balance locks found")

    # Check total locked amount
    total_result = await pg.execute_query("""
        SELECT COALESCE(SUM(amount), 0) as total_locked
        FROM balance_locks
    """)

    if total_result:
        print(f"\nTotal locked: ${total_result[0][0]:.2f}")

    await pg.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
