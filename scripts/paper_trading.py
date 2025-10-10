#!/usr/bin/env python3
"""
Paper Trading Environment
Live market data with simulated execution for system validation
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OrderSide(Enum):
    """Order side"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order status"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"


@dataclass
class PaperPosition:
    """Paper trading position"""
    position_id: str
    symbol: str
    side: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    entry_time: str = ""


@dataclass
class PaperOrder:
    """Paper trading order"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: str
    quantity: float
    price: float
    status: OrderStatus
    filled_price: Optional[float] = None
    filled_quantity: float = 0.0
    timestamp: str = ""


class PaperTradingEngine:
    """
    Paper Trading Engine

    Simulates live trading with real market data but virtual execution
    - Connects to real exchange for market data
    - Simulates order execution with realistic slippage
    - Tracks P&L and performance metrics
    - No real money at risk
    """

    def __init__(
        self,
        initial_capital: float = 10000.0,
        exchange: str = "binance",
        testnet: bool = True
    ):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.exchange = exchange
        self.testnet = testnet

        self.positions: Dict[str, PaperPosition] = {}
        self.orders: Dict[str, PaperOrder] = {}
        self.trade_history: List[Dict] = []

        self.total_pnl = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0

        logger.info(f"🎯 Paper Trading Engine Initialized")
        logger.info(f"   Exchange: {exchange} ({'TESTNET' if testnet else 'LIVE'})")
        logger.info(f"   Capital: ${initial_capital:,.2f}")

    async def connect_exchange(self) -> bool:
        """Connect to exchange (simulated for now)"""
        logger.info(f"📡 Connecting to {self.exchange}...")
        await asyncio.sleep(0.5)  # Simulate connection
        logger.info(f"✅ Connected to {self.exchange} testnet")
        return True

    async def get_market_price(self, symbol: str) -> float:
        """Get current market price (simulated)"""
        # In production, this would use CCXT to get real price
        # For now, simulate realistic prices
        base_prices = {
            "BTC/USDT": 50000.0,
            "ETH/USDT": 3000.0,
            "SOL/USDT": 100.0
        }

        base = base_prices.get(symbol, 1000.0)
        # Add small random variation
        import random
        variation = random.uniform(-0.5, 0.5) / 100  # ±0.5%
        return base * (1 + variation)

    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: str,
        quantity: float,
        price: Optional[float] = None
    ) -> PaperOrder:
        """Place a paper trading order"""
        order_id = f"paper_{len(self.orders) + 1}_{datetime.utcnow().timestamp()}"

        if order_type == "market":
            # Market order - get current price
            market_price = await self.get_market_price(symbol)
            # Simulate slippage (0.05%)
            import random
            slippage = random.uniform(0.0001, 0.001)
            if side == OrderSide.BUY:
                fill_price = market_price * (1 + slippage)
            else:
                fill_price = market_price * (1 - slippage)

            order = PaperOrder(
                order_id=order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=market_price,
                status=OrderStatus.FILLED,
                filled_price=fill_price,
                filled_quantity=quantity,
                timestamp=datetime.utcnow().isoformat()
            )

            logger.info(f"📝 Market Order FILLED: {side.value.upper()} {quantity} {symbol} @ ${fill_price:,.2f}")

        else:  # limit order
            order = PaperOrder(
                order_id=order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price or 0.0,
                status=OrderStatus.PENDING,
                timestamp=datetime.utcnow().isoformat()
            )
            logger.info(f"📝 Limit Order PLACED: {side.value.upper()} {quantity} {symbol} @ ${price:,.2f}")

        self.orders[order_id] = order
        return order

    async def open_position(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> PaperPosition:
        """Open a paper trading position"""
        # Place market order
        order_side = OrderSide.BUY if side.upper() == "LONG" else OrderSide.SELL
        order = await self.place_order(symbol, order_side, "market", quantity)

        # Create position
        position_id = f"pos_{symbol}_{len(self.positions) + 1}"
        position = PaperPosition(
            position_id=position_id,
            symbol=symbol,
            side=side.upper(),
            quantity=quantity,
            entry_price=order.filled_price,
            current_price=order.filled_price,
            unrealized_pnl=0.0,
            unrealized_pnl_pct=0.0,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_time=datetime.utcnow().isoformat()
        )

        self.positions[position_id] = position

        # Deduct capital
        position_value = order.filled_price * quantity
        self.capital -= position_value

        logger.info(f"📈 Position OPENED: {side.upper()} {quantity} {symbol}")
        logger.info(f"   Entry: ${order.filled_price:,.2f}")
        logger.info(f"   SL: ${stop_loss:,.2f}, TP: ${take_profit:,.2f}" if stop_loss else "")
        logger.info(f"   Remaining Capital: ${self.capital:,.2f}")

        return position

    async def update_position(self, position_id: str) -> Optional[PaperPosition]:
        """Update position with current market price"""
        if position_id not in self.positions:
            return None

        position = self.positions[position_id]
        current_price = await self.get_market_price(position.symbol)

        position.current_price = current_price

        # Calculate unrealized P&L
        if position.side == "LONG":
            pnl_per_unit = current_price - position.entry_price
        else:  # SHORT
            pnl_per_unit = position.entry_price - current_price

        position.unrealized_pnl = pnl_per_unit * position.quantity
        position.unrealized_pnl_pct = (pnl_per_unit / position.entry_price) * 100

        # Check stop-loss/take-profit
        should_close = False
        close_reason = ""

        if position.stop_loss and position.side == "LONG" and current_price <= position.stop_loss:
            should_close = True
            close_reason = "Stop-Loss"
        elif position.take_profit and position.side == "LONG" and current_price >= position.take_profit:
            should_close = True
            close_reason = "Take-Profit"
        elif position.stop_loss and position.side == "SHORT" and current_price >= position.stop_loss:
            should_close = True
            close_reason = "Stop-Loss"
        elif position.take_profit and position.side == "SHORT" and current_price <= position.take_profit:
            should_close = True
            close_reason = "Take-Profit"

        if should_close:
            logger.info(f"🎯 {close_reason} triggered for {position_id}")
            await self.close_position(position_id)

        return position

    async def close_position(self, position_id: str) -> Optional[Dict]:
        """Close a paper trading position"""
        if position_id not in self.positions:
            return None

        position = self.positions[position_id]

        # Get current price
        current_price = await self.get_market_price(position.symbol)

        # Place closing order
        close_side = OrderSide.SELL if position.side == "LONG" else OrderSide.BUY
        order = await self.place_order(
            position.symbol,
            close_side,
            "market",
            position.quantity
        )

        # Calculate realized P&L
        if position.side == "LONG":
            realized_pnl = (order.filled_price - position.entry_price) * position.quantity
        else:
            realized_pnl = (position.entry_price - order.filled_price) * position.quantity

        realized_pnl_pct = (realized_pnl / (position.entry_price * position.quantity)) * 100

        # Update capital
        position_value = order.filled_price * position.quantity
        self.capital += position_value + realized_pnl

        # Update statistics
        self.total_trades += 1
        self.total_pnl += realized_pnl
        if realized_pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1

        # Record trade
        trade = {
            "position_id": position_id,
            "symbol": position.symbol,
            "side": position.side,
            "entry_price": position.entry_price,
            "exit_price": order.filled_price,
            "quantity": position.quantity,
            "pnl": realized_pnl,
            "pnl_pct": realized_pnl_pct,
            "entry_time": position.entry_time,
            "exit_time": datetime.utcnow().isoformat()
        }
        self.trade_history.append(trade)

        logger.info(f"📉 Position CLOSED: {position.side} {position.symbol}")
        logger.info(f"   Exit: ${order.filled_price:,.2f}")
        logger.info(f"   P&L: ${realized_pnl:,.2f} ({realized_pnl_pct:+.2f}%)")
        logger.info(f"   Total Capital: ${self.capital:,.2f}")

        # Remove position
        del self.positions[position_id]

        return trade

    async def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary"""
        total_unrealized_pnl = sum(p.unrealized_pnl for p in self.positions.values())
        portfolio_value = self.capital + total_unrealized_pnl

        summary = {
            "initial_capital": self.initial_capital,
            "current_capital": self.capital,
            "portfolio_value": portfolio_value,
            "total_pnl": self.total_pnl,
            "total_pnl_pct": ((portfolio_value - self.initial_capital) / self.initial_capital) * 100,
            "unrealized_pnl": total_unrealized_pnl,
            "open_positions": len(self.positions),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        }

        return summary

    async def print_portfolio_summary(self) -> None:
        """Print portfolio summary"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 Paper Trading Portfolio Summary")
        logger.info("=" * 60)

        summary = await self.get_portfolio_summary()

        logger.info(f"\n💰 Capital:")
        logger.info(f"   Initial: ${summary['initial_capital']:,.2f}")
        logger.info(f"   Current: ${summary['current_capital']:,.2f}")
        logger.info(f"   Portfolio Value: ${summary['portfolio_value']:,.2f}")
        logger.info(f"   Total P&L: ${summary['total_pnl']:,.2f} ({summary['total_pnl_pct']:+.2f}%)")

        logger.info(f"\n📈 Positions:")
        logger.info(f"   Open: {summary['open_positions']}")
        logger.info(f"   Unrealized P&L: ${summary['unrealized_pnl']:,.2f}")

        logger.info(f"\n📊 Trading Stats:")
        logger.info(f"   Total Trades: {summary['total_trades']}")
        logger.info(f"   Winning: {summary['winning_trades']}")
        logger.info(f"   Losing: {summary['losing_trades']}")
        logger.info(f"   Win Rate: {summary['win_rate']:.1f}%")

        if self.positions:
            logger.info(f"\n📍 Open Positions:")
            for pos in self.positions.values():
                logger.info(f"   {pos.side} {pos.symbol}: ${pos.current_price:,.2f} "
                          f"(P&L: ${pos.unrealized_pnl:,.2f} / {pos.unrealized_pnl_pct:+.2f}%)")

        logger.info("\n" + "=" * 60)


async def demo_paper_trading():
    """Demo paper trading session"""
    logger.info("🎯 Starting Paper Trading Demo")
    logger.info("=" * 60)

    # Initialize engine
    engine = PaperTradingEngine(initial_capital=10000.0)

    # Connect to exchange
    await engine.connect_exchange()

    # Simulate a trading session
    logger.info("\n📝 Opening positions...")

    # Open BTC long position
    btc_pos = await engine.open_position(
        symbol="BTC/USDT",
        side="LONG",
        quantity=0.1,
        stop_loss=48000.0,
        take_profit=54000.0
    )

    await asyncio.sleep(1)

    # Open ETH long position
    eth_pos = await engine.open_position(
        symbol="ETH/USDT",
        side="LONG",
        quantity=1.0,
        stop_loss=2800.0,
        take_profit=3200.0
    )

    # Simulate price updates
    logger.info("\n📊 Simulating market movements...")
    for i in range(5):
        await asyncio.sleep(1)
        for pos_id in list(engine.positions.keys()):
            await engine.update_position(pos_id)

    # Show portfolio
    await engine.print_portfolio_summary()

    # Close remaining positions
    logger.info("\n📉 Closing positions...")
    for pos_id in list(engine.positions.keys()):
        await engine.close_position(pos_id)

    # Final summary
    await engine.print_portfolio_summary()


if __name__ == "__main__":
    asyncio.run(demo_paper_trading())
