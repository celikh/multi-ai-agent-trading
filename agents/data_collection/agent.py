"""
Data Collection Agent
Collects real-time market data from exchanges via REST and WebSocket.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from agents.base.agent import PeriodicAgent
from agents.base.protocol import MarketDataMessage, MessageType
from infrastructure.gateway.exchange import get_exchange, ExchangeGateway
from infrastructure.database.influxdb import get_influx, InfluxDBManager


class DataCollectionAgent(PeriodicAgent):
    """
    Collects and publishes market data from exchanges.

    Responsibilities:
    - Fetch OHLCV candles (REST)
    - Stream real-time ticks (WebSocket)
    - Monitor order book depth
    - Publish to message bus
    - Store in InfluxDB
    """

    def __init__(
        self,
        exchange_name: str = "binance",
        symbols: List[str] = None,
        timeframe: str = "1m",
    ):
        super().__init__(
            name="data_collector",
            agent_type="DATA_COLLECTION",
            interval_seconds=30,  # REST polling interval (optimized from 60s)
            description="Collects real-time market data from exchanges",
        )

        self.exchange_name = exchange_name
        self.symbols = symbols or ["BTC/USDT", "ETH/USDT"]
        self.timeframe = timeframe  # Changed from interval to timeframe
        self._exchange: Optional[ExchangeGateway] = None
        self._influx: Optional[InfluxDBManager] = None
        self._ws_tasks: List[asyncio.Task] = []

    async def setup(self) -> None:
        """Initialize exchange and database connections"""
        # Connect to exchange
        self._exchange = await get_exchange(self.exchange_name)

        # Connect to InfluxDB
        self._influx = get_influx()

        self.log_event(
            "data_collector_setup",
            exchange=self.exchange_name,
            symbols=self.symbols,
            timeframe=self.timeframe,
        )

    async def run(self) -> None:
        """Start REST-only mode (WebSocket disabled due to connection issues)"""
        # DISABLED: WebSocket streams (causing data pipeline failure)
        # TODO: Re-enable after implementing proper health monitoring (DEV-71 M2)
        # for symbol in self.symbols:
        #     task = self.create_task(self._stream_ticker(symbol))
        #     self._ws_tasks.append(task)
        #     task = self.create_task(self._stream_ohlcv(symbol))
        #     self._ws_tasks.append(task)
        # self.log_event("websocket_streams_started", symbols=self.symbols)

        self.log_event("rest_mode_enabled", symbols=self.symbols, interval=30)

        # Call parent's periodic run (REST polling every 30s)
        await super().run()

    async def execute(self) -> None:
        """Periodic REST fallback (runs every interval)"""
        self.log_event("execute_started", symbols=self.symbols)
        for symbol in self.symbols:
            try:
                await self._fetch_rest_data(symbol)
            except Exception as e:
                self.log_error(e, {"symbol": symbol, "source": "rest"})

    async def cleanup(self) -> None:
        """Cleanup resources"""
        # Cancel WebSocket tasks
        for task in self._ws_tasks:
            task.cancel()

        await asyncio.gather(*self._ws_tasks, return_exceptions=True)

        if self._exchange:
            await self._exchange.disconnect()

        if self._influx:
            self._influx.disconnect()

    def get_subscribed_topics(self) -> List[str]:
        """This agent doesn't subscribe to topics"""
        return []

    async def _stream_ticker(self, symbol: str) -> None:
        """Stream real-time ticker via WebSocket"""
        while self._running:
            try:
                ticker = await self._exchange.watch_ticker(symbol)

                # Store in InfluxDB
                await self._store_ticker(symbol, ticker)

                # Publish to message bus
                await self._publish_ticker(symbol, ticker)

                self.logger.debug(
                    "ticker_streamed",
                    symbol=symbol,
                    price=ticker.get("last"),
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log_error(e, {"symbol": symbol, "stream": "ticker"})
                await asyncio.sleep(5)  # Retry after delay

    async def _stream_ohlcv(self, symbol: str) -> None:
        """Stream OHLCV candles via WebSocket"""
        while self._running:
            try:
                candles = await self._exchange.watch_ohlcv(symbol, self.timeframe)

                if candles and len(candles) > 0:
                    latest = candles[-1]  # [timestamp, open, high, low, close, volume]

                    # Store in InfluxDB
                    await self._store_ohlcv(symbol, latest)

                    # Publish to message bus
                    await self._publish_ohlcv(symbol, latest)

                    self.logger.debug(
                        "ohlcv_streamed",
                        symbol=symbol,
                        close=latest[4],
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log_error(e, {"symbol": symbol, "stream": "ohlcv"})
                await asyncio.sleep(5)

    async def _fetch_rest_data(self, symbol: str) -> None:
        """Fetch data via REST (fallback)"""
        try:
            self.logger.info("fetching_rest_data", symbol=symbol)

            # Fetch OHLCV
            ohlcv = await self._exchange.fetch_ohlcv(
                symbol,
                timeframe=self.timeframe,
                limit=1,
            )

            self.logger.info("ohlcv_fetched", symbol=symbol, count=len(ohlcv) if ohlcv else 0)

            if ohlcv and len(ohlcv) > 0:
                latest = ohlcv[-1]
                self._store_ohlcv(symbol, latest)  # Removed await - sync method
                self.logger.info("ohlcv_stored", symbol=symbol)

            # Fetch ticker
            ticker = await self._exchange.fetch_ticker(symbol)
            self.logger.info("ticker_fetched", symbol=symbol, price=ticker.get("last"))
            self._store_ticker(symbol, ticker)  # Removed await - sync method
            self.logger.info("ticker_stored", symbol=symbol)

            # Fetch order book
            orderbook = await self._exchange.fetch_order_book(symbol, limit=10)
            self.logger.info("orderbook_fetched", symbol=symbol)
            self._store_orderbook(symbol, orderbook)  # Removed await - sync method
            self.logger.info("orderbook_stored", symbol=symbol)

            self.logger.info(
                "rest_data_fetched",
                symbol=symbol,
                exchange=self.exchange_name,
            )

        except Exception as e:
            self.log_error(e, {"symbol": symbol, "source": "rest_fetch"})

    async def _store_ohlcv(self, symbol: str, candle: List) -> None:
        """Store OHLCV in InfluxDB"""
        timestamp = datetime.fromtimestamp(candle[0] / 1000)

        self._influx.write_ohlcv(
            symbol=symbol,
            exchange=self.exchange_name,
            timestamp=timestamp,
            open_price=candle[1],
            high=candle[2],
            low=candle[3],
            close=candle[4],
            volume=candle[5],
            interval=self.timeframe,
        )

    async def _store_ticker(self, symbol: str, ticker: Dict[str, Any]) -> None:
        """Store ticker as latest OHLCV point"""
        price = ticker.get("last")
        if not price:
            return

        self._influx.write_ohlcv(
            symbol=symbol,
            exchange=self.exchange_name,
            timestamp=datetime.now(timezone.utc),
            open_price=price,
            high=price,
            low=price,
            close=price,
            volume=ticker.get("baseVolume", 0),
            interval=self.timeframe,  # Use configured timeframe instead of "tick"
        )

    async def _store_orderbook(self, symbol: str, orderbook: Dict[str, Any]) -> None:
        """Store order book snapshot"""
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])

        if not bids or not asks:
            return

        bid_price, bid_volume = bids[0][0], bids[0][1]
        ask_price, ask_volume = asks[0][0], asks[0][1]
        spread = ask_price - bid_price

        self._influx.write_orderbook(
            symbol=symbol,
            exchange=self.exchange_name,
            timestamp=datetime.now(timezone.utc),
            bid_price=bid_price,
            bid_volume=bid_volume,
            ask_price=ask_price,
            ask_volume=ask_volume,
            spread=spread,
        )

    async def _publish_ticker(self, symbol: str, ticker: Dict[str, Any]) -> None:
        """Publish ticker to message bus"""
        message = MarketDataMessage(
            source_agent=self.name,
            exchange=self.exchange_name,
            symbol=symbol,
            data={
                "type": "ticker",
                "last": ticker.get("last"),
                "bid": ticker.get("bid"),
                "ask": ticker.get("ask"),
                "volume": ticker.get("baseVolume"),
                "timestamp": ticker.get("timestamp"),
            },
        )

        await self.publish_message("ticks.raw", message, priority=6)

    async def _publish_ohlcv(self, symbol: str, candle: List) -> None:
        """Publish OHLCV to message bus"""
        message = MarketDataMessage(
            source_agent=self.name,
            exchange=self.exchange_name,
            symbol=symbol,
            data={
                "type": "ohlcv",
                "timestamp": candle[0],
                "open": candle[1],
                "high": candle[2],
                "low": candle[3],
                "close": candle[4],
                "volume": candle[5],
                "interval": self.timeframe,  # Fixed: was self.interval
            },
        )

        await self.publish_message("ticks.raw", message, priority=5)


# Main entry point
async def main():
    """Run the data collection agent"""
    agent = DataCollectionAgent(
        exchange_name="binance",
        symbols=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
        timeframe="1m",
    )

    try:
        await agent.initialize()
        await agent.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
