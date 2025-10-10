#!/usr/bin/env python3
"""
Populate SL/TP orders for existing positions
This is a one-time script to add SL/TP orders to orders table for positions opened before this feature.
"""
import asyncio
import uuid
import json
from datetime import datetime
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.database.postgresql import get_db


async def populate_sl_tp_orders():
    db = await get_db()

    # Get all open positions with SL/TP
    positions = await db.fetch_all("""
        SELECT id, symbol, side, quantity, stop_loss, take_profit, opened_at
        FROM positions
        WHERE status = 'OPEN' AND (stop_loss IS NOT NULL OR take_profit IS NOT NULL)
    """)

    print(f"\n=== Found {len(positions)} positions with SL/TP ===")

    for pos in positions:
        print(f"\n{pos['symbol']} {pos['side']}")

        # Generate position_id (same format as in code)
        position_id = f"{pos['symbol']}_{pos['side']}_{pos['opened_at'].timestamp()}"

        # Create SL order if exists
        if pos['stop_loss']:
            sl_order_id = f"SL_{str(uuid.uuid4())[:8]}"
            close_side = "SELL" if pos['side'] == "LONG" else "BUY"

            await db.execute("""
                INSERT INTO orders (
                    order_id, symbol, side, order_type, quantity, price, status,
                    created_at, exchange_order_id, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                sl_order_id,
                pos['symbol'],
                close_side,
                "STOP_LOSS",
                pos['quantity'],
                pos['stop_loss'],
                "PENDING",
                datetime.utcnow(),
                f"MANUAL_{sl_order_id}",
                json.dumps({"position_id": position_id})
            )
            print(f"  ✅ Created SL order: ${pos['stop_loss']:.2f}")

        # Create TP order if exists
        if pos['take_profit']:
            tp_order_id = f"TP_{str(uuid.uuid4())[:8]}"
            close_side = "SELL" if pos['side'] == "LONG" else "BUY"

            await db.execute("""
                INSERT INTO orders (
                    order_id, symbol, side, order_type, quantity, price, status,
                    created_at, exchange_order_id, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                tp_order_id,
                pos['symbol'],
                close_side,
                "TAKE_PROFIT",
                pos['quantity'],
                pos['take_profit'],
                "PENDING",
                datetime.utcnow(),
                f"MANUAL_{tp_order_id}",
                json.dumps({"position_id": position_id})
            )
            print(f"  ✅ Created TP order: ${pos['take_profit']:.2f}")

    # Verify
    orders = await db.fetch_all("""
        SELECT order_type, symbol, price, status
        FROM orders
        ORDER BY created_at DESC
    """)

    print(f"\n=== Total orders in table: {len(orders)} ===")
    for o in orders:
        print(f"  {o['order_type']}: {o['symbol']} @ ${o['price']:.2f} ({o['status']})")

    await db.disconnect()
    print("\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(populate_sl_tp_orders())
