"""
Strategy Agent
Combines signals from multiple analysis agents and generates trading decisions.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import asyncio
from collections import defaultdict
import json

from agents.base.agent import BaseAgent
from agents.base.protocol import (
    MessageType,
    TradingSignal,
    TradeIntent,
    SignalType,
    deserialize_message,
)
from agents.strategy.signal_fusion import (
    BayesianFusion,
    ConsensusStrategy,
    TimeDecayFusion,
    HybridFusion,
    Signal as FusionSignal,
)
from infrastructure.database.postgresql import get_db, PostgreSQLDatabase
from core.config.settings import settings


@dataclass
class SignalBuffer:
    """Buffer for collecting signals by symbol"""

    signals: List[TradingSignal] = field(default_factory=list)
    last_decision: Optional[datetime] = None
    pending_count: int = 0


class StrategyAgent(BaseAgent):
    """
    Strategy Agent - Signal Fusion and Decision Making

    Responsibilities:
    - Collect signals from multiple analysis agents
    - Apply fusion strategies to combine signals
    - Generate trade intents based on fused signals
    - Track decision history and performance

    Signal Flow:
    1. Subscribe to signals.* topics
    2. Buffer signals by symbol
    3. Apply fusion when sufficient signals received
    4. Generate TradeIntent if confidence threshold met
    5. Publish to trade.intent for Risk Manager
    """

    def __init__(
        self,
        name: str = "strategy_agent",
        fusion_strategy: str = "hybrid",
        min_signals: int = 2,
        signal_timeout_seconds: int = 300,
        min_confidence: float = 0.6,
        decision_interval_seconds: int = 30,
    ):
        super().__init__(name, agent_type="strategy")

        # Fusion configuration
        self.fusion_strategy = fusion_strategy
        self.min_signals = min_signals
        self.signal_timeout = timedelta(seconds=signal_timeout_seconds)
        self.min_confidence = min_confidence
        self.decision_interval = decision_interval_seconds

        # Signal buffers by symbol
        self.signal_buffers: Dict[str, SignalBuffer] = defaultdict(SignalBuffer)

        # Fusion engines
        self.bayesian_fusion = BayesianFusion(history_window=100)
        self.consensus_fusion = ConsensusStrategy(
            min_confidence=min_confidence,
            min_agreement=0.6
        )
        self.time_decay_fusion = TimeDecayFusion(half_life_minutes=30)
        self.hybrid_fusion = HybridFusion()

        # Database
        self._db: Optional[PostgreSQLDatabase] = None

        # State
        self._decision_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize agent resources"""
        await super().initialize()

        # Connect to database
        self._db = await get_db()

        self.logger.info(
            "strategy_agent_initialized",
            fusion_strategy=self.fusion_strategy,
            min_signals=self.min_signals,
            min_confidence=self.min_confidence,
        )

    async def setup(self) -> None:
        """Setup subscriptions"""
        # Subscribe to all signal topics
        await self.subscribe_topic("signals.tech", self._handle_technical_signal)
        await self.subscribe_topic("signals.fundamental", self._handle_fundamental_signal)
        await self.subscribe_topic("signals.sentiment", self._handle_sentiment_signal)
        self.logger.info("strategy_agent_setup_complete")

    async def run(self) -> None:
        """Main agent loop"""
        # Start periodic decision making
        self._decision_task = asyncio.create_task(self._decision_loop())
        while self._running:
            await asyncio.sleep(1)

    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self._decision_task:
            self._decision_task.cancel()
            try:
                await self._decision_task
            except asyncio.CancelledError:
                pass

    def get_subscribed_topics(self) -> List[str]:
        """Return subscribed topics"""
        return ["signals.tech", "signals.fundamental", "signals.sentiment"]

    async def start(self) -> None:
        """Start the strategy agent"""
        await super().start()
        self.logger.info("strategy_agent_started")

    async def shutdown(self) -> None:
        """Shutdown agent gracefully"""
        if self._decision_task:
            self._decision_task.cancel()
            try:
                await self._decision_task
            except asyncio.CancelledError:
                pass

        if self._db:
            await self._db.close()

        await super().shutdown()

    async def _handle_technical_signal(self, message: TradingSignal) -> None:
        """Handle technical analysis signals"""
        await self._add_signal_to_buffer(message)

    async def _handle_fundamental_signal(self, message: TradingSignal) -> None:
        """Handle fundamental analysis signals"""
        await self._add_signal_to_buffer(message)

    async def _handle_sentiment_signal(self, message: TradingSignal) -> None:
        """Handle sentiment analysis signals"""
        await self._add_signal_to_buffer(message)

    async def _add_signal_to_buffer(self, signal: TradingSignal) -> None:
        """Add signal to appropriate buffer"""
        symbol = signal.symbol
        buffer = self.signal_buffers[symbol]

        # Add signal
        buffer.signals.append(signal)
        buffer.pending_count += 1

        self.logger.debug(
            "signal_buffered",
            symbol=symbol,
            agent_type=signal.agent_type,
            signal_type=signal.signal.value,
            confidence=signal.confidence,
            buffer_size=len(buffer.signals),
        )

    async def _decision_loop(self) -> None:
        """Periodic decision making loop"""
        while self._running:
            try:
                await asyncio.sleep(self.decision_interval)

                # Process all symbols with pending signals
                for symbol, buffer in list(self.signal_buffers.items()):
                    if buffer.pending_count >= self.min_signals:
                        await self._make_decision(symbol, buffer)
                        buffer.pending_count = 0

                # Cleanup old signals
                await self._cleanup_old_signals()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("decision_loop_error", error=str(e), exc_info=True)

    async def _make_decision(self, symbol: str, buffer: SignalBuffer) -> None:
        """Make trading decision for a symbol"""
        # Filter recent signals
        now = datetime.utcnow()
        recent_signals = [
            s for s in buffer.signals
            if now - s.timestamp < self.signal_timeout
        ]

        if len(recent_signals) < self.min_signals:
            self.logger.debug(
                "insufficient_signals",
                symbol=symbol,
                required=self.min_signals,
                available=len(recent_signals),
            )
            return

        # Convert to fusion signal format
        fusion_signals = [
            FusionSignal(
                agent_type=s.agent_type,
                symbol=s.symbol,
                signal=s.signal,
                confidence=s.confidence,
                timestamp=s.timestamp,
                reasoning=s.reasoning or "",
                metadata=s.indicators,
            )
            for s in recent_signals
        ]

        # Apply fusion strategy
        fusion_result = await self._apply_fusion_strategy(fusion_signals)

        # Check confidence threshold
        if fusion_result["confidence"] < self.min_confidence:
            self.logger.info(
                "low_confidence_decision",
                symbol=symbol,
                signal=fusion_result["signal"].value,
                confidence=fusion_result["confidence"],
                threshold=self.min_confidence,
            )
            return

        # Don't create trade intent for HOLD signals
        if fusion_result["signal"].value == "HOLD":
            self.logger.info(
                "hold_signal_decision",
                symbol=symbol,
                confidence=fusion_result["confidence"],
                reasoning=fusion_result.get("reasoning", ""),
            )
            return

        # Generate trade intent
        trade_intent = await self._generate_trade_intent(
            symbol, recent_signals, fusion_result
        )

        # Publish trade intent
        await self.publish_message("trade.intent", trade_intent, priority=8)

        # Store decision
        await self._store_decision(symbol, fusion_result, trade_intent)

        # Update buffer
        buffer.last_decision = now

        self.logger.info(
            "decision_made",
            symbol=symbol,
            signal=fusion_result["signal"].value,
            confidence=fusion_result["confidence"],
            num_signals=len(recent_signals),
            fusion_strategy=self.fusion_strategy,
        )

    async def _apply_fusion_strategy(
        self, signals: List[FusionSignal]
    ) -> Dict[str, Any]:
        """Apply selected fusion strategy"""
        if self.fusion_strategy == "bayesian":
            return self.bayesian_fusion.fuse_signals(signals)
        elif self.fusion_strategy == "consensus":
            return self.consensus_fusion.fuse_signals(signals)
        elif self.fusion_strategy == "time_decay":
            return self.time_decay_fusion.fuse_signals(signals)
        elif self.fusion_strategy == "hybrid":
            return self.hybrid_fusion.fuse_signals(signals)
        else:
            raise ValueError(f"Unknown fusion strategy: {self.fusion_strategy}")

    async def _generate_trade_intent(
        self,
        symbol: str,
        signals: List[TradingSignal],
        fusion_result: Dict[str, Any],
    ) -> TradeIntent:
        """Generate trade intent from fused signals"""
        # Calculate price targets from signals
        price_targets = [s.price_target for s in signals if s.price_target]
        stop_losses = [s.stop_loss for s in signals if s.stop_loss]
        take_profits = [s.take_profit for s in signals if s.take_profit]

        # Average targets if available
        avg_price_target = sum(price_targets) / len(price_targets) if price_targets else None
        avg_stop_loss = sum(stop_losses) / len(stop_losses) if stop_losses else None
        avg_take_profit = sum(take_profits) / len(take_profits) if take_profits else None

        # Create reasoning
        reasoning_parts = fusion_result.get("reasoning", [])
        if isinstance(reasoning_parts, list):
            reasoning = "; ".join(reasoning_parts)
        else:
            reasoning = str(reasoning_parts)

        # Normalize confidence to [0.0, 1.0] range
        normalized_confidence = min(fusion_result["confidence"], 1.0)

        # Get current market price from latest signal
        latest_signal = signals[-1]
        expected_price = latest_signal.price_target or 0.0

        # Create trade intent with all required fields
        trade_intent = TradeIntent(
            source_agent=self.name,
            symbol=symbol,
            side=fusion_result["signal"].value,
            quantity=0.0,  # To be determined by Risk Manager
            expected_price=expected_price,
            signals=signals,
            strategy_name=self.fusion_strategy,
            confidence=normalized_confidence,
            reasoning=reasoning,
            metadata={
                "fusion_strategy": self.fusion_strategy,
                "num_signals": len(signals),
                "signal_agents": [s.agent_type for s in signals],
                "raw_confidence": fusion_result["confidence"],
                "stop_loss": avg_stop_loss,
                "take_profit": avg_take_profit,
                "fusion_details": {
                    k: v for k, v in fusion_result.items()
                    if k not in ["signal", "confidence", "reasoning"]
                },
            },
        )

        return trade_intent

    async def _store_decision(
        self,
        symbol: str,
        fusion_result: Dict[str, Any],
        trade_intent: TradeIntent,
    ) -> None:
        """Store decision in database"""
        try:
            query = """
                INSERT INTO strategy_decisions (
                    symbol, signal_type, confidence, fusion_strategy,
                    num_signals, reasoning, fusion_details,
                    price_target, stop_loss, take_profit, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """

            # Extract price targets from metadata
            metadata = trade_intent.metadata or {}
            price_target = metadata.get("price_target")
            stop_loss = metadata.get("stop_loss")
            take_profit = metadata.get("take_profit")

            await self._db.execute(
                query,
                symbol,
                fusion_result["signal"].value,
                fusion_result["confidence"],
                self.fusion_strategy,
                fusion_result.get("num_signals", 0),
                fusion_result.get("reasoning", ""),
                json.dumps({
                    k: v for k, v in fusion_result.items()
                    if k not in ["signal", "confidence", "reasoning"]
                }),
                price_target,
                stop_loss,
                take_profit,
                json.dumps(metadata),
            )

        except Exception as e:
            self.logger.error(
                "store_decision_error",
                symbol=symbol,
                error=str(e),
                exc_info=True,
            )

    async def _cleanup_old_signals(self) -> None:
        """Remove signals older than timeout"""
        now = datetime.utcnow()

        for symbol, buffer in list(self.signal_buffers.items()):
            # Filter recent signals
            buffer.signals = [
                s for s in buffer.signals
                if now - s.timestamp < self.signal_timeout
            ]

            # Remove empty buffers
            if not buffer.signals and buffer.pending_count == 0:
                del self.signal_buffers[symbol]

    async def update_agent_performance(
        self, agent_type: str, accuracy: float
    ) -> None:
        """Update agent performance for Bayesian fusion"""
        self.bayesian_fusion.update_performance(agent_type, accuracy)

        self.logger.info(
            "agent_performance_updated",
            agent_type=agent_type,
            accuracy=accuracy,
        )


async def main():
    """Main entry point for Strategy Agent"""
    agent = StrategyAgent(
        name="strategy_agent_main",
        fusion_strategy="hybrid",  # or "bayesian", "consensus", "time_decay"
        min_signals=2,
        signal_timeout_seconds=300,
        min_confidence=0.6,
        decision_interval_seconds=30,
    )

    try:
        await agent.initialize()
        await agent.start()

        # Keep running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Shutting down Strategy Agent...")
    finally:
        await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
