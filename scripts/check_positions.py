#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.database.postgresql import get_db

async def check():
    db = await get_db()

    positions = await db.fetch_all("""
        SELECT symbol, side, status, quantity, entry_price, current_price, realized_pnl, closed_at
        FROM positions
        ORDER BY opened_at DESC
        LIMIT 5
    """)

    print(f"\n=== POSITIONS ===")
    for p in positions:
        print(f"\n{p['symbol']} {p['side']} - {p['status']}")
        if p['status'] == 'OPEN':
            print(f"  Quantity: {p['quantity']}")
            print(f"  Entry: ${p['entry_price']:.2f}")
            print(f"  Current: ${p['current_price']:.2f}")
        else:
            print(f"  Closed at: ${p['current_price']:.2f}")
            print(f"  Realized PnL: ${p['realized_pnl']:.2f}")
            print(f"  Closed time: {p['closed_at']}")

    await db.disconnect()

asyncio.run(check())
