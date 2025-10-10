"""
Execution Agent
Order execution, position management, and execution reporting.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import json
import uuid

from agents.base.agent import PeriodicAgent
from agents.base.protocol import (
    MessageType,
    Order,
    OrderType,
    ExecutionReport as ExecReportMessage,
    PositionUpdate as PositionUpdateMessage,
    deserialize_message,
)
from agents.execution.order_executor import OrderExecutor, OrderStatus
from agents.execution.execution_quality import (
    ExecutionReporter,
    ExecutionBenchmark,
)
from agents.execution.position_manager import (
    PositionManager,
    PositionSide,
)
from infrastructure.database.postgresql import get_db, PostgreSQLDatabase
from core.config.settings import settings


class ExecutionAgent(PeriodicAgent):
    """
    Execution Agent - Order Execution and Position Management

    Responsibilities:
    - Receive approved orders from Risk Manager
    - Execute orders on exchange via CCXT
    - Monitor order fills and partial fills
    - Calculate slippage and execution costs
    - Manage positions and P&L tracking
    - Report execution results
    - Monitor positions periodically (every 10 seconds)
    - Check SL/TP order triggers

    Message Flow:
    Risk Manager → [trade.order] → Execution Agent → Exchange
                                           ↓
                                   [execution.report]
                                   [position.update]

    Periodic Tasks (every 10 seconds):
    - Update position prices and PnL
    - Check SL/TP order status
    """

    def __init__(
        self,
        name: str = "execution_agent",
        exchange_id: str = "binance",
        testnet: bool = True,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        max_slippage_pct: float = 1.0,  # Max 1% slippage
        monitoring_interval: int = 10,  # Position monitoring interval in seconds
    ):
        super().__init__(
            name=name,
            agent_type="execution",
            interval_seconds=monitoring_interval,
            description="Order execution and position monitoring"
        )

        # Configuration
        self.exchange_id = exchange_id
        self.testnet = testnet
        self.max_slippage_pct = max_slippage_pct

        # Execution modules
        self.order_executor = OrderExecutor(
            exchange_id=exchange_id,
            testnet=testnet,
            api_key=api_key,
            api_secret=api_secret,
        )

        self.execution_reporter = ExecutionReporter()
        self.execution_benchmark = ExecutionBenchmark()
        self.position_manager = PositionManager()

        # Database
        self._db: Optional[PostgreSQLDatabase] = None

        # State
        self.pending_orders: Dict[str, Order] = {}

    async def initialize(self) -> None:
        """Initialize agent resources"""
        await super().initialize()

        # Connect to PostgreSQL
        self._db = await get_db()

        self.logger.info(
            "execution_agent_initialized",
            exchange=self.exchange_id,
            testnet=self.testnet,
            max_slippage_pct=self.max_slippage_pct,
        )

    async def setup(self) -> None:
        """Setup subscriptions"""
        # Subscribe to approved orders from Risk Manager
        await self.subscribe_topic("trade.order", self._handle_order)
        self.logger.info("execution_agent_setup_complete")

    # Note: run() method inherited from PeriodicAgent
    # Periodic execution handled by execute() method

    async def cleanup(self) -> None:
        """Cleanup resources"""
        pass

    def get_subscribed_topics(self) -> List[str]:
        """Return subscribed topics"""
        return ["trade.order"]

    async def start(self) -> None:
        """Start the execution agent"""
        await super().start()
        self.logger.info("execution_agent_started")

    async def shutdown(self) -> None:
        """Shutdown agent gracefully"""
        # Close exchange connection
        await self.order_executor.close()

        if self._db:
            await self._db.close()

        await super().shutdown()

    async def _handle_order(self, message: Order) -> None:
        """Handle approved order from Risk Manager"""
        try:
            symbol = message.symbol
            side = message.side
            order_type = message.order_type
            quantity = message.quantity

            # Generate order_id from correlation_id or create new UUID
            order_id = message.correlation_id or str(uuid.uuid4())

            self.logger.info(
                "order_received",
                symbol=symbol,
                side=side,
                order_type=order_type.value,
                quantity=quantity,
                order_id=order_id,
            )

            # Store as pending
            self.pending_orders[order_id] = message

            # Execute order based on type
            execution_start = datetime.utcnow()

            if order_type == OrderType.MARKET:
                execution = await self.order_executor.place_market_order(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                )
            elif order_type == OrderType.LIMIT:
                execution = await self.order_executor.place_limit_order(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=message.price,
                )
            else:
                self.logger.error(
                    "unsupported_order_type", order_type=order_type.value
                )
                return

            execution_end = datetime.utcnow()

            # Check if order was filled
            if execution.status == OrderStatus.FILLED:
                await self._process_filled_order(
                    message, execution, execution_start, execution_end
                )

            elif execution.status == OrderStatus.REJECTED:
                await self._process_rejected_order(message, execution)

            else:
                # Order is open, monitor it
                await self._monitor_order(
                    message, execution, execution_start
                )

        except Exception as e:
            self.logger.error(
                "order_execution_error",
                symbol=message.symbol,
                error=str(e),
                exc_info=True,
            )

    async def _process_filled_order(
        self,
        order: Order,
        execution: Any,
        execution_start: datetime,
        execution_end: datetime,
    ):
        """Process fully filled order"""
        # Get fills
        fills = await self.order_executor.get_fills(
            execution.order_id, execution.symbol
        )

        # Generate execution report
        expected_price = order.price or execution.average_fill_price
        report = self.execution_reporter.generate_report(
            order_id=execution.order_id,
            symbol=execution.symbol,
            side=execution.side,
            quantity=execution.filled_quantity,
            expected_price=expected_price,
            average_fill_price=execution.average_fill_price,
            fills=[f.__dict__ for f in fills],
            exchange_fees=execution.fees,
            execution_start=execution_start,
            execution_end=execution_end,
        )

        # Check slippage limits
        if abs(report.slippage.slippage_percentage) > self.max_slippage_pct:
            self.logger.warning(
                "high_slippage",
                symbol=execution.symbol,
                slippage_pct=report.slippage.slippage_percentage,
                max_allowed=self.max_slippage_pct,
            )

        # Add to benchmark
        self.execution_benchmark.add_execution(report)

        # Update position
        await self._update_position(order, execution, report)

        # Store execution in database
        await self._store_execution(execution, report)

        # Publish execution report
        exec_report_msg = ExecReportMessage(
            source_agent=self.name,
            order_id=execution.order_id,
            exchange=order.exchange,
            symbol=execution.symbol,
            side=execution.side.upper() if isinstance(execution.side, str) else execution.side,
            status=execution.status,
            filled_quantity=execution.filled_quantity,
            average_price=execution.average_fill_price,
            total_value=execution.total_cost,
            fee=execution.fees,
            fee_currency="USDT",  # TODO: Get from exchange
            execution_time=execution_end,
        )

        await self.publish_message(
            "execution.report", exec_report_msg, priority=8
        )

        # Place stop-loss and take-profit orders if specified
        if order.stop_loss:
            await self._place_stop_loss(
                execution.symbol,
                "sell" if execution.side == "buy" else "buy",
                execution.filled_quantity,
                order.stop_loss,
            )

        if order.take_profit:
            await self._place_take_profit(
                execution.symbol,
                "sell" if execution.side == "buy" else "buy",
                execution.filled_quantity,
                order.take_profit,
            )

        self.logger.info(
            "order_filled",
            order_id=execution.order_id,
            symbol=execution.symbol,
            quantity=execution.filled_quantity,
            avg_price=execution.average_fill_price,
            slippage_pct=report.slippage.slippage_percentage,
            quality_score=report.quality_score,
        )

        # Remove from pending
        order_id = order.correlation_id or str(uuid.uuid4())
        if order_id in self.pending_orders:
            del self.pending_orders[order_id]

    async def _process_rejected_order(self, order: Order, execution: Any):
        """Process rejected order"""
        self.logger.error(
            "order_rejected",
            order_id=execution.order_id,
            symbol=execution.symbol,
            error=execution.metadata.get("error"),
        )

        # Publish execution report for rejected order to release reserved balance
        try:
            exec_report_msg = ExecReportMessage(
                source_agent=self.name,
                order_id=execution.order_id,
                exchange=order.exchange,
                symbol=execution.symbol,
                side=execution.side.upper() if isinstance(execution.side, str) else execution.side,
                status="REJECTED",
                filled_quantity=0.0,
                average_price=0.0,
                total_value=0.0,
                fee=0.0,
                fee_currency="USDT",
                execution_time=datetime.utcnow(),
            )

            await self.publish_message(
                "execution.report", exec_report_msg, priority=8
            )

            self.logger.info(
                "execution_report_published",
                order_id=execution.order_id,
                status="REJECTED",
            )
        except Exception as e:
            self.logger.error(
                "failed_to_publish_rejection_report",
                order_id=execution.order_id,
                error=str(e),
            )

        # Remove from pending
        order_id = order.correlation_id or str(uuid.uuid4())
        if order_id in self.pending_orders:
            del self.pending_orders[order_id]

    async def _monitor_order(
        self, order: Order, execution: Any, execution_start: datetime
    ):
        """Monitor open order until filled"""

        async def order_callback(updated_execution):
            if updated_execution.status == OrderStatus.FILLED:
                await self._process_filled_order(
                    order,
                    updated_execution,
                    execution_start,
                    datetime.utcnow(),
                )

        # Watch order updates
        await self.order_executor.watch_order(
            execution.order_id, execution.symbol, order_callback
        )

    async def _update_position(
        self, order: Order, execution: Any, report: Any
    ):
        """Update or create position"""
        symbol = execution.symbol
        side = execution.side
        quantity = execution.filled_quantity
        price = execution.average_fill_price

        # Get existing positions for symbol
        existing_positions = self.position_manager.get_positions_by_symbol(
            symbol
        )

        if not existing_positions:
            # Open new position
            position = self.position_manager.open_position(
                symbol=symbol,
                side="long" if side == "buy" else "short",
                quantity=quantity,
                entry_price=price,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
                metadata={
                    "order_id": execution.order_id,
                    "execution_quality": report.quality_score,
                },
            )

            # Store in database
            await self._store_position_to_db(position)

            self.logger.info(
                "position_opened",
                position_id=position.position_id,
                symbol=symbol,
                side=position.side.value,
                quantity=quantity,
                entry_price=price,
            )

        else:
            # Update existing position
            position = existing_positions[0]

            if (side == "buy" and position.side == PositionSide.LONG) or (
                side == "sell" and position.side == PositionSide.SHORT
            ):
                # Increase position
                self.position_manager.increase_position(
                    position.position_id, quantity, price
                )
                await self._update_position_in_db(position)
                self.logger.info(
                    "position_increased",
                    position_id=position.position_id,
                    additional_quantity=quantity,
                )
            else:
                # Decrease/close position
                self.position_manager.decrease_position(
                    position.position_id, quantity, price
                )
                await self._update_position_in_db(position)
                self.logger.info(
                    "position_decreased",
                    position_id=position.position_id,
                    reduced_quantity=quantity,
                )

        # Publish position update
        position_msg = PositionUpdateMessage(
            source_agent=self.name,
            symbol=symbol,
            side=position.side.value,
            quantity=position.quantity,
            entry_price=position.entry_price,
            current_price=price,
            unrealized_pnl=position.unrealized_pnl,
            realized_pnl=position.realized_pnl,
            metadata={"position_id": position.position_id},
        )

        await self.publish_message(
            "position.update", position_msg, priority=7
        )

    async def _place_stop_loss(
        self, symbol: str, side: str, quantity: float, stop_price: float
    ):
        """Place stop-loss order"""
        try:
            execution = await self.order_executor.place_stop_loss_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                stop_price=stop_price,
            )

            self.logger.info(
                "stop_loss_placed",
                symbol=symbol,
                stop_price=stop_price,
                order_id=execution.order_id,
            )
        except Exception as e:
            self.logger.error(
                "stop_loss_error", symbol=symbol, error=str(e)
            )

    async def _place_take_profit(
        self, symbol: str, side: str, quantity: float, tp_price: float
    ):
        """Place take-profit order"""
        try:
            execution = await self.order_executor.place_take_profit_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                take_profit_price=tp_price,
            )

            self.logger.info(
                "take_profit_placed",
                symbol=symbol,
                tp_price=tp_price,
                order_id=execution.order_id,
            )
        except Exception as e:
            self.logger.error(
                "take_profit_error", symbol=symbol, error=str(e)
            )

    async def _store_execution(self, execution: Any, report: Any):
        """Store execution in database"""
        try:
            query = """
                INSERT INTO trades (
                    exchange, symbol, side, order_type, quantity,
                    price, fee, fee_currency, status, order_id,
                    execution_time, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """

            await self._db.execute(
                query,
                self.exchange_id,
                execution.symbol,
                execution.side.upper(),
                execution.order_type.upper(),
                execution.filled_quantity,
                execution.average_fill_price,
                execution.fees,
                execution.fee_currency,
                "FILLED",
                execution.order_id,
                datetime.utcnow(),
                json.dumps(
                    {
                        "slippage_pct": report.slippage.slippage_percentage,
                        "quality_score": report.quality_score,
                        "execution_time_ms": report.execution_time_ms,
                        "total_cost": report.costs.total_cost,
                    }
                ),
            )

        except Exception as e:
            self.logger.error("store_execution_error", error=str(e))

    async def _store_position_to_db(self, position: Any):
        """Store position in database"""
        try:
            import json
            from uuid import uuid4

            query = """
                INSERT INTO positions (
                    id, exchange, symbol, side, quantity,
                    entry_price, current_price, unrealized_pnl, realized_pnl,
                    stop_loss, take_profit, leverage, margin, status,
                    opened_at, metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            """

            await self._db.execute(
                query,
                uuid4(),
                self.exchange_id,
                position.symbol,
                position.side.value.upper(),
                position.quantity,
                position.entry_price,
                position.entry_price,  # current_price = entry_price initially
                0.0,  # unrealized_pnl = 0 initially
                position.realized_pnl,
                position.stop_loss,
                position.take_profit,
                1.0,  # leverage default to 1.0
                0.0,  # margin calculation TBD
                position.status.value.upper(),
                position.entry_time,
                json.dumps(position.metadata if hasattr(position, 'metadata') else {}),
            )

            self.logger.debug("position_stored_to_db", position_id=position.position_id)

        except Exception as e:
            self.logger.error("store_position_error", error=str(e), position_id=getattr(position, 'position_id', 'unknown'))

    async def _update_position_in_db(self, position: Any):
        """Update position in database"""
        try:
            import json

            # Determine if position should be closed
            if position.quantity <= 0 or (hasattr(position, 'status') and position.status.value == 'closed'):
                query = """
                    UPDATE positions
                    SET quantity = $1, current_price = $2, unrealized_pnl = $3, realized_pnl = $4,
                        status = 'CLOSED', closed_at = NOW(), metadata = $5
                    WHERE symbol = $6 AND exchange = $7 AND status = 'OPEN'
                """
                await self._db.execute(
                    query,
                    position.quantity,
                    position.entry_price,
                    position.unrealized_pnl,
                    position.realized_pnl,
                    json.dumps(position.metadata if hasattr(position, 'metadata') else {}),
                    position.symbol,
                    self.exchange_id,
                )
                self.logger.debug("position_closed_in_db", position_id=position.position_id)
            else:
                query = """
                    UPDATE positions
                    SET quantity = $1, current_price = $2, unrealized_pnl = $3, realized_pnl = $4,
                        stop_loss = $5, take_profit = $6, metadata = $7
                    WHERE symbol = $8 AND exchange = $9 AND status = 'OPEN'
                """
                await self._db.execute(
                    query,
                    position.quantity,
                    position.entry_price,
                    position.unrealized_pnl,
                    position.realized_pnl,
                    position.stop_loss,
                    position.take_profit,
                    json.dumps(position.metadata if hasattr(position, 'metadata') else {}),
                    position.symbol,
                    self.exchange_id,
                )
                self.logger.debug("position_updated_in_db", position_id=position.position_id)

        except Exception as e:
            self.logger.error("update_position_error", error=str(e), position_id=getattr(position, 'position_id', 'unknown'))

    async def execute(self) -> None:
        """
        Periodic position monitoring task (runs every interval_seconds)

        Tasks:
        1. Update all open position prices
        2. Calculate unrealized PnL
        3. Update database
        4. Check SL/TP order triggers (DEV-76)
        """
        try:
            # Get all open positions
            open_positions = self.position_manager.get_all_positions()

            if not open_positions:
                self.logger.info("no_open_positions_to_monitor")
                return

            self.logger.info(
                "monitoring_positions",
                count=len(open_positions),
                symbols=[p.symbol for p in open_positions]
            )

            # Update each position
            for position in open_positions:
                try:
                    # Fetch current market price
                    current_price = await self._fetch_current_price(position.symbol)

                    if current_price is None:
                        self.logger.warning(
                            "failed_to_fetch_price",
                            symbol=position.symbol,
                            position_id=position.position_id
                        )
                        continue

                    # Update position price in memory
                    self.position_manager.update_position_price(
                        position.position_id,
                        current_price
                    )

                    # Update database
                    await self._update_position_in_db(position)

                    self.logger.debug(
                        "position_updated",
                        position_id=position.position_id,
                        symbol=position.symbol,
                        current_price=current_price,
                        unrealized_pnl=position.unrealized_pnl
                    )

                    # Publish position update
                    position_msg = PositionUpdateMessage(
                        source_agent=self.name,
                        symbol=position.symbol,
                        side=position.side.value,
                        quantity=position.quantity,
                        entry_price=position.entry_price,
                        current_price=current_price,
                        unrealized_pnl=position.unrealized_pnl,
                        realized_pnl=position.realized_pnl,
                        metadata={"position_id": position.position_id},
                    )

                    await self.publish_message(
                        "position.update", position_msg, priority=7
                    )

                except Exception as e:
                    self.log_error(
                        e,
                        {
                            "position_id": position.position_id,
                            "symbol": position.symbol,
                            "operation": "position_monitoring"
                        }
                    )

        except Exception as e:
            self.log_error(e, {"operation": "execute_periodic_monitoring"})

    async def _fetch_current_price(self, symbol: str) -> Optional[float]:
        """Fetch current market price for symbol"""
        try:
            ticker = await self.order_executor.exchange.fetch_ticker(symbol)
            return ticker.get('last') or ticker.get('close')
        except Exception as e:
            self.log_error(e, {"symbol": symbol, "operation": "fetch_current_price"})
            return None


async def main():
    """Main entry point for Execution Agent"""
    agent = ExecutionAgent(
        name="execution_agent_main",
        exchange_id="binance",
        testnet=False,  # Use live trading with real API keys
        api_key=settings.exchange.binance_api_key,
        api_secret=settings.exchange.binance_secret,
        max_slippage_pct=1.0,
    )

    try:
        await agent.initialize()
        await agent.start()

        # Keep running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Shutting down Execution Agent...")
    finally:
        await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
