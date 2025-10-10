"""
Exchange gateway using CCXT for unified exchange access.
Supports REST and WebSocket connections with retry logic.
"""

from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime
import ccxt.pro as ccxt
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from core.config.settings import settings
from core.security.secrets import get_exchange_credentials
from core.logging.logger import get_logger, LoggerMixin

logger = get_logger(__name__)


class ExchangeGateway(LoggerMixin):
    """Unified gateway for cryptocurrency exchange access"""

    SUPPORTED_EXCHANGES = ["binance", "coinbase", "kraken"]

    def __init__(self, exchange_name: str):
        if exchange_name.lower() not in self.SUPPORTED_EXCHANGES:
            raise ValueError(f"Unsupported exchange: {exchange_name}")

        self.name = exchange_name.lower()
        self._exchange: Optional[ccxt.Exchange] = None
        self._is_connected = False

    async def connect(self) -> None:
        """Initialize exchange connection"""
        try:
            credentials = get_exchange_credentials(self.name)

            # Get exchange class
            exchange_class = getattr(ccxt, self.name)

            # Initialize exchange
            self._exchange = exchange_class({
                "apiKey": credentials.get("apiKey"),
                "secret": credentials.get("secret"),
                "enableRateLimit": True,
                "options": {
                    "defaultType": "spot",  # spot or future
                    "adjustForTimeDifference": True,
                },
            })

            # Test connection
            await self._exchange.load_markets()
            self._is_connected = True

            self.log_event(
                "exchange_connected",
                exchange=self.name,
                markets=len(self._exchange.markets),
            )

        except Exception as e:
            self.log_error(e, {"exchange": self.name})
            raise

    async def disconnect(self) -> None:
        """Close exchange connection"""
        if self._exchange:
            await self._exchange.close()
            self._is_connected = False
            self.log_event("exchange_disconnected", exchange=self.name)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ccxt.NetworkError, ccxt.ExchangeNotAvailable)),
    )
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1m",
        limit: int = 100,
    ) -> List[List]:
        """Fetch OHLCV candles"""
        if not self._exchange:
            raise RuntimeError("Exchange not connected")

        try:
            ohlcv = await self._exchange.fetch_ohlcv(
                symbol,
                timeframe=timeframe,
                limit=limit,
            )

            self.logger.debug(
                "ohlcv_fetched",
                exchange=self.name,
                symbol=symbol,
                timeframe=timeframe,
                candles=len(ohlcv),
            )

            return ohlcv

        except Exception as e:
            self.log_error(e, {
                "operation": "fetch_ohlcv",
                "symbol": symbol,
                "timeframe": timeframe,
            })
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch ticker data"""
        if not self._exchange:
            raise RuntimeError("Exchange not connected")

        ticker = await self._exchange.fetch_ticker(symbol)

        self.logger.debug(
            "ticker_fetched",
            exchange=self.name,
            symbol=symbol,
            price=ticker.get("last"),
        )

        return ticker

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def fetch_order_book(
        self,
        symbol: str,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Fetch order book"""
        if not self._exchange:
            raise RuntimeError("Exchange not connected")

        orderbook = await self._exchange.fetch_order_book(symbol, limit=limit)

        self.logger.debug(
            "orderbook_fetched",
            exchange=self.name,
            symbol=symbol,
            bids=len(orderbook["bids"]),
            asks=len(orderbook["asks"]),
        )

        return orderbook

    async def watch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Watch ticker via WebSocket"""
        if not self._exchange:
            raise RuntimeError("Exchange not connected")

        ticker = await self._exchange.watch_ticker(symbol)
        return ticker

    async def watch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1m",
    ) -> List[List]:
        """Watch OHLCV via WebSocket"""
        if not self._exchange:
            raise RuntimeError("Exchange not connected")

        ohlcv = await self._exchange.watch_ohlcv(symbol, timeframe)
        return ohlcv

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
    )
    async def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create an order"""
        if not self._exchange:
            raise RuntimeError("Exchange not connected")

        # Paper trading mode check
        if settings.trading.mode == "paper":
            self.logger.warning(
                "paper_trading_order",
                symbol=symbol,
                side=side,
                amount=amount,
                price=price,
            )
            return {
                "id": f"PAPER_{datetime.utcnow().timestamp()}",
                "symbol": symbol,
                "type": order_type,
                "side": side,
                "amount": amount,
                "price": price,
                "status": "closed",
                "filled": amount,
                "remaining": 0,
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Live trading
        try:
            order = await self._exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
                params=params or {},
            )

            self.log_trade(
                action="order_created",
                symbol=symbol,
                side=side,
                quantity=amount,
                price=price or 0,
                order_id=order.get("id"),
            )

            return order

        except Exception as e:
            self.log_error(e, {
                "operation": "create_order",
                "symbol": symbol,
                "side": side,
                "amount": amount,
            })
            raise

    async def cancel_order(
        self,
        order_id: str,
        symbol: str,
    ) -> Dict[str, Any]:
        """Cancel an order"""
        if not self._exchange:
            raise RuntimeError("Exchange not connected")

        if settings.trading.mode == "paper":
            return {"id": order_id, "status": "canceled"}

        result = await self._exchange.cancel_order(order_id, symbol)

        self.logger.info(
            "order_canceled",
            exchange=self.name,
            order_id=order_id,
            symbol=symbol,
        )

        return result

    async def fetch_balance(self) -> Dict[str, Any]:
        """Fetch account balance"""
        if not self._exchange:
            raise RuntimeError("Exchange not connected")

        if settings.trading.mode == "paper":
            return {
                "USDT": {"free": 10000, "used": 0, "total": 10000},
                "BTC": {"free": 0, "used": 0, "total": 0},
            }

        balance = await self._exchange.fetch_balance()
        return balance

    async def fetch_positions(self) -> List[Dict[str, Any]]:
        """Fetch open positions (for futures)"""
        if not self._exchange:
            raise RuntimeError("Exchange not connected")

        if settings.trading.mode == "paper":
            return []

        if hasattr(self._exchange, "fetch_positions"):
            positions = await self._exchange.fetch_positions()
            return positions

        return []


# Exchange pool manager
class ExchangePool:
    """Manage multiple exchange connections"""

    def __init__(self):
        self._exchanges: Dict[str, ExchangeGateway] = {}

    async def get_exchange(self, name: str) -> ExchangeGateway:
        """Get or create exchange connection"""
        if name not in self._exchanges:
            exchange = ExchangeGateway(name)
            await exchange.connect()
            self._exchanges[name] = exchange

        return self._exchanges[name]

    async def close_all(self) -> None:
        """Close all exchange connections"""
        for exchange in self._exchanges.values():
            await exchange.disconnect()

        self._exchanges.clear()


# Global exchange pool
exchange_pool = ExchangePool()


async def get_exchange(name: str = "binance") -> ExchangeGateway:
    """Get exchange instance"""
    return await exchange_pool.get_exchange(name)
