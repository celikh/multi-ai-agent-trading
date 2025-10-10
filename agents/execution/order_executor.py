"""
Order Executor Module
Handles order placement, monitoring, and fill tracking via CCXT.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import asyncio
import ccxt.pro as ccxtpro
from decimal import Decimal


class OrderStatus(str, Enum):
    """Order status types"""

    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class OrderExecution:
    """Order execution result"""

    order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float]
    status: OrderStatus
    filled_quantity: float
    remaining_quantity: float
    average_fill_price: Optional[float]
    total_cost: float
    fees: float
    fee_currency: str
    timestamp: datetime
    exchange_info: Dict
    metadata: Dict


@dataclass
class Fill:
    """Individual fill/trade execution"""

    fill_id: str
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    cost: float
    fee: float
    fee_currency: str
    timestamp: datetime
    is_maker: bool


class OrderExecutor:
    """
    Order Executor - Place and monitor orders on exchange

    Responsibilities:
    - Create orders on exchange via CCXT
    - Monitor order status
    - Track fills and partial fills
    - Handle order modifications
    - Report execution results
    """

    def __init__(
        self,
        exchange_id: str = "binance",
        testnet: bool = True,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
    ):
        self.exchange_id = exchange_id
        self.testnet = testnet

        # Initialize exchange
        exchange_class = getattr(ccxtpro, exchange_id)
        self.exchange = exchange_class(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
                "options": {
                    "defaultType": "future" if testnet else "spot",
                    "test": testnet,
                },
            }
        )

        # Order tracking
        self.active_orders: Dict[str, OrderExecution] = {}
        self.fills: Dict[str, List[Fill]] = {}

    async def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        params: Optional[Dict] = None,
    ) -> OrderExecution:
        """
        Place market order

        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            side: "buy" or "sell"
            quantity: Order quantity
            params: Additional order parameters

        Returns:
            OrderExecution with order details
        """
        try:
            # Validate parameters
            await self.exchange.load_markets()

            # Create market order
            order = await self.exchange.create_order(
                symbol=symbol,
                type="market",
                side=side.lower(),
                amount=quantity,
                params=params or {},
            )

            # Parse order response
            execution = self._parse_order_response(order)

            # Track order
            self.active_orders[execution.order_id] = execution

            return execution

        except Exception as e:
            # Return rejected execution
            return OrderExecution(
                order_id=f"rejected_{datetime.utcnow().timestamp()}",
                symbol=symbol,
                side=side,
                order_type="market",
                quantity=quantity,
                price=None,
                status=OrderStatus.REJECTED,
                filled_quantity=0.0,
                remaining_quantity=quantity,
                average_fill_price=None,
                total_cost=0.0,
                fees=0.0,
                fee_currency="USDT",
                timestamp=datetime.utcnow(),
                exchange_info={},
                metadata={"error": str(e)},
            )

    async def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        params: Optional[Dict] = None,
    ) -> OrderExecution:
        """
        Place limit order

        Args:
            symbol: Trading pair
            side: "buy" or "sell"
            quantity: Order quantity
            price: Limit price
            params: Additional parameters

        Returns:
            OrderExecution
        """
        try:
            await self.exchange.load_markets()

            order = await self.exchange.create_order(
                symbol=symbol,
                type="limit",
                side=side.lower(),
                amount=quantity,
                price=price,
                params=params or {},
            )

            execution = self._parse_order_response(order)
            self.active_orders[execution.order_id] = execution

            return execution

        except Exception as e:
            return OrderExecution(
                order_id=f"rejected_{datetime.utcnow().timestamp()}",
                symbol=symbol,
                side=side,
                order_type="limit",
                quantity=quantity,
                price=price,
                status=OrderStatus.REJECTED,
                filled_quantity=0.0,
                remaining_quantity=quantity,
                average_fill_price=None,
                total_cost=0.0,
                fees=0.0,
                fee_currency="USDT",
                timestamp=datetime.utcnow(),
                exchange_info={},
                metadata={"error": str(e)},
            )

    async def place_stop_loss_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        params: Optional[Dict] = None,
    ) -> OrderExecution:
        """
        Place stop-loss order

        Args:
            symbol: Trading pair
            side: "buy" or "sell"
            quantity: Order quantity
            stop_price: Stop trigger price
            params: Additional parameters

        Returns:
            OrderExecution
        """
        try:
            await self.exchange.load_markets()

            # Different exchanges have different stop order types
            stop_params = params or {}
            stop_params["stopPrice"] = stop_price

            order = await self.exchange.create_order(
                symbol=symbol,
                type="stop_market",  # or "stop_loss" depending on exchange
                side=side.lower(),
                amount=quantity,
                params=stop_params,
            )

            execution = self._parse_order_response(order)
            self.active_orders[execution.order_id] = execution

            return execution

        except Exception as e:
            return OrderExecution(
                order_id=f"rejected_{datetime.utcnow().timestamp()}",
                symbol=symbol,
                side=side,
                order_type="stop_market",
                quantity=quantity,
                price=stop_price,
                status=OrderStatus.REJECTED,
                filled_quantity=0.0,
                remaining_quantity=quantity,
                average_fill_price=None,
                total_cost=0.0,
                fees=0.0,
                fee_currency="USDT",
                timestamp=datetime.utcnow(),
                exchange_info={},
                metadata={"error": str(e), "stop_price": stop_price},
            )

    async def place_take_profit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
        params: Optional[Dict] = None,
    ) -> OrderExecution:
        """
        Place take-profit order

        Args:
            symbol: Trading pair
            side: "buy" or "sell"
            quantity: Order quantity
            take_profit_price: Take profit trigger price
            params: Additional parameters

        Returns:
            OrderExecution
        """
        try:
            await self.exchange.load_markets()

            tp_params = params or {}
            tp_params["stopPrice"] = take_profit_price

            order = await self.exchange.create_order(
                symbol=symbol,
                type="take_profit_market",
                side=side.lower(),
                amount=quantity,
                params=tp_params,
            )

            execution = self._parse_order_response(order)
            self.active_orders[execution.order_id] = execution

            return execution

        except Exception as e:
            return OrderExecution(
                order_id=f"rejected_{datetime.utcnow().timestamp()}",
                symbol=symbol,
                side=side,
                order_type="take_profit_market",
                quantity=quantity,
                price=take_profit_price,
                status=OrderStatus.REJECTED,
                filled_quantity=0.0,
                remaining_quantity=quantity,
                average_fill_price=None,
                total_cost=0.0,
                fees=0.0,
                fee_currency="USDT",
                timestamp=datetime.utcnow(),
                exchange_info={},
                metadata={
                    "error": str(e),
                    "take_profit_price": take_profit_price,
                },
            )

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancel an order

        Args:
            order_id: Order ID to cancel
            symbol: Trading pair

        Returns:
            True if cancelled successfully
        """
        try:
            await self.exchange.cancel_order(order_id, symbol)

            # Update local tracking
            if order_id in self.active_orders:
                self.active_orders[order_id].status = OrderStatus.CANCELLED

            return True

        except Exception as e:
            return False

    async def get_order_status(
        self, order_id: str, symbol: str
    ) -> Optional[OrderExecution]:
        """
        Get current order status from exchange

        Args:
            order_id: Order ID
            symbol: Trading pair

        Returns:
            Updated OrderExecution or None
        """
        try:
            order = await self.exchange.fetch_order(order_id, symbol)
            execution = self._parse_order_response(order)

            # Update local tracking
            self.active_orders[order_id] = execution

            return execution

        except Exception as e:
            return None

    async def watch_order(
        self, order_id: str, symbol: str, callback: callable
    ) -> None:
        """
        Watch order updates via WebSocket

        Args:
            order_id: Order ID to watch
            symbol: Trading pair
            callback: Callback function for updates
        """
        try:
            while True:
                orders = await self.exchange.watch_orders(symbol)

                for order in orders:
                    if order["id"] == order_id:
                        execution = self._parse_order_response(order)
                        self.active_orders[order_id] = execution

                        # Call callback with updated execution
                        await callback(execution)

                        # Stop watching if order is final
                        if execution.status in [
                            OrderStatus.FILLED,
                            OrderStatus.CANCELLED,
                            OrderStatus.REJECTED,
                        ]:
                            return

        except Exception as e:
            pass

    async def get_fills(
        self, order_id: str, symbol: str
    ) -> List[Fill]:
        """
        Get all fills for an order

        Args:
            order_id: Order ID
            symbol: Trading pair

        Returns:
            List of Fill objects
        """
        try:
            trades = await self.exchange.fetch_order_trades(order_id, symbol)

            fills = []
            for trade in trades:
                fill = Fill(
                    fill_id=trade["id"],
                    order_id=order_id,
                    symbol=symbol,
                    side=trade["side"],
                    quantity=trade["amount"],
                    price=trade["price"],
                    cost=trade["cost"],
                    fee=trade["fee"]["cost"] if trade.get("fee") else 0.0,
                    fee_currency=trade["fee"]["currency"]
                    if trade.get("fee")
                    else "USDT",
                    timestamp=datetime.fromtimestamp(
                        trade["timestamp"] / 1000
                    ),
                    is_maker=trade.get("maker", False),
                )
                fills.append(fill)

            # Store fills
            self.fills[order_id] = fills

            return fills

        except Exception as e:
            return []

    def _parse_order_response(self, order: Dict) -> OrderExecution:
        """Parse exchange order response into OrderExecution"""
        # Map exchange status to OrderStatus
        status_map = {
            "open": OrderStatus.OPEN,
            "closed": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELLED,
            "cancelled": OrderStatus.CANCELLED,
            "expired": OrderStatus.EXPIRED,
            "rejected": OrderStatus.REJECTED,
        }

        status = status_map.get(order.get("status", "open"), OrderStatus.OPEN)

        # Check for partial fills
        filled = order.get("filled", 0.0)
        amount = order.get("amount", 0.0)

        if filled > 0 and filled < amount and status == OrderStatus.OPEN:
            status = OrderStatus.PARTIALLY_FILLED

        return OrderExecution(
            order_id=order["id"],
            symbol=order["symbol"],
            side=order["side"],
            order_type=order["type"],
            quantity=amount,
            price=order.get("price"),
            status=status,
            filled_quantity=filled,
            remaining_quantity=order.get("remaining", amount - filled),
            average_fill_price=order.get("average"),
            total_cost=order.get("cost", 0.0),
            fees=order.get("fee", {}).get("cost", 0.0),
            fee_currency=order.get("fee", {}).get("currency", "USDT"),
            timestamp=datetime.fromtimestamp(order["timestamp"] / 1000),
            exchange_info=order.get("info", {}),
            metadata={
                "exchange": self.exchange_id,
                "testnet": self.testnet,
            },
        )

    async def close(self):
        """Close exchange connection"""
        await self.exchange.close()
