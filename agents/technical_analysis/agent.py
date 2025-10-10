"""
Technical Analysis Agent
Analyzes market data and generates trading signals using technical indicators.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from agents.base.agent import PeriodicAgent
from agents.base.protocol import (
    MarketDataMessage,
    TradingSignal,
    SignalType,
    MessageType,
)
from agents.technical_analysis.indicators import (
    TechnicalIndicators,
    SignalGenerator,
)
from infrastructure.database.influxdb import get_influx, InfluxDBManager
from infrastructure.database.postgresql import get_db, PostgreSQLDatabase


class TechnicalAnalysisAgent(PeriodicAgent):
    """
    Analyzes market data using technical indicators and generates trading signals.

    Responsibilities:
    - Subscribe to market data from Data Collection Agent
    - Calculate technical indicators (RSI, MACD, BB, MA)
    - Generate BUY/SELL/HOLD signals with confidence scores
    - Publish signals to message bus
    - Store signals in PostgreSQL
    """

    def __init__(
        self,
        symbols: List[str] = None,
        lookback_periods: int = 100,
        interval: int = 60,
    ):
        super().__init__(
            name="technical_analyzer",
            agent_type="TECHNICAL",
            interval_seconds=interval,
            description="Analyzes market data using technical indicators",
        )

        self.symbols = symbols or ["BTC/USDT", "ETH/USDT"]
        self.lookback_periods = lookback_periods
        self._influx: Optional[InfluxDBManager] = None
        self._db: Optional[PostgreSQLDatabase] = None
        self._indicators = TechnicalIndicators()
        self._signal_gen = SignalGenerator()

    async def setup(self) -> None:
        """Initialize connections and subscriptions"""
        # Connect to databases
        self._influx = get_influx()
        self._db = await get_db()

        # Subscribe to market data
        await self.subscribe_topic("ticks.raw", self.handle_market_data)

        self.log_event(
            "technical_analyzer_setup",
            symbols=self.symbols,
            lookback=self.lookback_periods,
        )

    async def execute(self) -> None:
        """Periodic execution - analyze each symbol"""
        for symbol in self.symbols:
            try:
                await self._analyze_symbol(symbol)
            except Exception as e:
                self.log_error(e, {"symbol": symbol, "phase": "analysis"})

    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self._influx:
            self._influx.disconnect()

    def get_subscribed_topics(self) -> List[str]:
        """Topics this agent subscribes to"""
        return ["ticks.raw"]

    async def handle_market_data(self, message: MarketDataMessage) -> None:
        """
        Handle incoming market data messages

        This is called in real-time when new data arrives
        """
        # For now, we rely on periodic analysis
        # Could add real-time incremental analysis here
        pass

    async def _analyze_symbol(self, symbol: str) -> None:
        """
        Analyze a symbol and generate trading signals

        Steps:
        1. Fetch historical OHLCV data
        2. Calculate technical indicators
        3. Generate signals from indicators
        4. Combine signals with confidence score
        5. Publish signal to message bus
        6. Store signal in database
        """
        try:
            # 1. Fetch historical data
            df = await self._fetch_ohlcv_data(symbol)

            if df is None or len(df) < self.lookback_periods:
                self.logger.warning(
                    "insufficient_data",
                    symbol=symbol,
                    rows=len(df) if df is not None else 0,
                    required=self.lookback_periods,
                )
                return

            # 2. Calculate indicators
            indicators = self._indicators.calculate_all_indicators(df)
            latest_indicators = self._indicators.get_latest_values(indicators)

            # 3. Generate individual signals
            signals = self._generate_individual_signals(
                latest_indicators,
                df["close"].iloc[-1],
            )

            # 4. Combine signals
            final_signal = self._signal_gen.combine_signals(signals)

            # 5. Create signal message
            signal_message = await self._create_signal_message(
                symbol,
                final_signal,
                latest_indicators,
            )

            # 6. Publish signal
            await self.publish_message(
                "signals.tech",
                signal_message,
                priority=7,
            )

            # 7. Store in database
            await self._store_signal(signal_message, latest_indicators)

            self.log_signal(
                agent=self.name,
                symbol=symbol,
                signal=final_signal["signal"],
                confidence=final_signal["confidence"],
                indicators=latest_indicators,
            )

        except Exception as e:
            self.log_error(e, {"symbol": symbol, "phase": "symbol_analysis"})

    async def _fetch_ohlcv_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from InfluxDB"""
        try:
            start_time = datetime.utcnow() - timedelta(hours=24)

            data = self._influx.query_ohlcv(
                symbol=symbol,
                exchange="binance",
                start_time=start_time,
                interval="1m",
            )

            if not data:
                return None

            # Convert to DataFrame
            df = pd.DataFrame(data)

            # Ensure we have required columns
            required_cols = ["timestamp", "open", "high", "low", "close", "volume"]
            if not all(col in df.columns for col in required_cols):
                self.logger.error(
                    "missing_columns",
                    symbol=symbol,
                    available=list(df.columns),
                    required=required_cols,
                )
                return None

            # Sort by timestamp
            df = df.sort_values("timestamp").reset_index(drop=True)

            # Convert to numeric
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            # Remove NaN rows
            df = df.dropna()

            self.logger.debug(
                "ohlcv_fetched",
                symbol=symbol,
                rows=len(df),
                start=df["timestamp"].iloc[0] if len(df) > 0 else None,
                end=df["timestamp"].iloc[-1] if len(df) > 0 else None,
            )

            return df

        except Exception as e:
            self.log_error(e, {"symbol": symbol, "operation": "fetch_ohlcv"})
            return None

    def _generate_individual_signals(
        self,
        indicators: Dict[str, float],
        current_price: float,
    ) -> List[Dict[str, Any]]:
        """Generate signals from each indicator"""
        signals = []

        # RSI Signal
        if indicators.get("rsi") is not None:
            rsi_signal = self._signal_gen.analyze_rsi(indicators["rsi"])
            signals.append(rsi_signal)

        # MACD Signal
        if all(indicators.get(k) is not None for k in ["macd", "macd_signal", "macd_hist"]):
            macd_signal = self._signal_gen.analyze_macd(
                indicators["macd"],
                indicators["macd_signal"],
                indicators["macd_hist"],
            )
            signals.append(macd_signal)

        # Bollinger Bands Signal
        if all(indicators.get(k) is not None for k in ["bb_upper", "bb_lower", "bb_middle"]):
            bb_signal = self._signal_gen.analyze_bollinger_bands(
                current_price,
                indicators["bb_upper"],
                indicators["bb_lower"],
                indicators["bb_middle"],
            )
            signals.append(bb_signal)

        # Moving Averages Signal
        if all(indicators.get(k) is not None for k in ["sma_20", "sma_50", "ema_20"]):
            ma_signal = self._signal_gen.analyze_moving_averages(
                current_price,
                indicators["sma_20"],
                indicators["sma_50"],
                indicators["ema_20"],
            )
            signals.append(ma_signal)

        return signals

    async def _create_signal_message(
        self,
        symbol: str,
        final_signal: Dict[str, Any],
        indicators: Dict[str, float],
    ) -> TradingSignal:
        """Create a TradingSignal message"""
        # Map signal string to SignalType enum
        signal_type_map = {
            "BUY": SignalType.BUY,
            "SELL": SignalType.SELL,
            "HOLD": SignalType.HOLD,
        }

        signal_type = signal_type_map.get(
            final_signal["signal"],
            SignalType.HOLD,
        )

        # Build reasoning text
        reasoning_parts = final_signal.get("reasoning", [])
        reasoning = " | ".join(reasoning_parts) if reasoning_parts else "No clear signals"

        # Create message
        message = TradingSignal(
            source_agent=self.name,
            agent_type=self.agent_type,
            symbol=symbol,
            signal=signal_type,
            confidence=final_signal.get("confidence", 0.0),
            reasoning=reasoning,
            indicators={
                k: float(v) if v is not None else None
                for k, v in indicators.items()
            },
        )

        return message

    async def _store_signal(
        self,
        signal: TradingSignal,
        indicators: Dict[str, float],
    ) -> None:
        """Store signal in PostgreSQL"""
        try:
            await self._db.insert_signal(
                agent_type=self.agent_type,
                agent_name=self.name,
                symbol=signal.symbol,
                signal_type=signal.signal.value,
                confidence=signal.confidence,
                reasoning=signal.reasoning,
                indicators=indicators,
            )

            self.logger.debug(
                "signal_stored",
                symbol=signal.symbol,
                signal=signal.signal.value,
                confidence=signal.confidence,
            )

        except Exception as e:
            self.log_error(e, {"symbol": signal.symbol, "operation": "store_signal"})


# Main entry point
async def main():
    """Run the technical analysis agent"""
    agent = TechnicalAnalysisAgent(
        symbols=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
        lookback_periods=100,
        interval=60,  # Analyze every 60 seconds
    )

    try:
        await agent.initialize()
        await agent.start()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down Technical Analysis Agent...")
    finally:
        await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
