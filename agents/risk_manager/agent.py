"""
Risk Manager Agent
Position sizing, risk assessment, and trade approval.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import json
import uuid

from agents.base.agent import BaseAgent
from agents.base.protocol import (
    MessageType,
    TradeIntent,
    Order,
    OrderType,
    RiskAssessment as RiskAssessmentMessage,
    deserialize_message,
)
from agents.risk_manager.position_sizing import PositionSizer
from agents.risk_manager.risk_assessment import (
    VaRCalculator,
    PortfolioRiskAnalyzer,
    TradeValidator,
)
from agents.risk_manager.stop_loss_placement import (
    StopLossManager,
    StopLossMethod,
)
from infrastructure.database.postgresql import get_db, PostgreSQLDatabase
from infrastructure.database.influxdb import get_influx, InfluxDBManager
from core.config.settings import settings


class RiskManagerAgent(BaseAgent):
    """
    Risk Manager Agent - Risk Assessment and Position Sizing

    Responsibilities:
    - Receive trade intents from Strategy Agent
    - Calculate optimal position sizes
    - Assess risk and validate trades
    - Set stop-loss and take-profit levels
    - Approve/reject trades based on risk rules
    - Monitor portfolio risk exposure

    Message Flow:
    Strategy Agent → [trade.intent] → Risk Manager → [trade.order] → Execution Agent
    """

    def __init__(
        self,
        name: str = "risk_manager",
        account_balance: float = 10000.0,  # Starting capital
        max_portfolio_risk: float = 0.20,  # Max 20% portfolio at risk
        max_position_risk: float = 0.05,  # Max 5% per position
        position_sizing_method: str = "hybrid",  # kelly, fixed, volatility, hybrid
        stop_loss_method: str = "atr",  # atr, percentage, volatility, support_resistance
        min_confidence: float = 0.6,  # Minimum signal confidence
        min_rr_ratio: float = 1.5,  # Minimum reward/risk ratio
    ):
        super().__init__(name, agent_type="risk_manager")

        # Configuration
        self.account_balance = account_balance
        self.max_portfolio_risk = max_portfolio_risk
        self.max_position_risk = max_position_risk
        self.position_sizing_method = position_sizing_method
        self.stop_loss_method = stop_loss_method
        self.min_confidence = min_confidence
        self.min_rr_ratio = min_rr_ratio

        # Risk modules
        # Adaptive max position size for small accounts
        # Small accounts (<$100) need higher position % to meet exchange minimums
        if account_balance < 100:
            max_position_pct = 0.80  # 80% for small accounts to meet $10 minimum
        elif account_balance < 1000:
            max_position_pct = 0.30  # 30% for medium accounts
        else:
            max_position_pct = 0.10  # 10% for larger accounts

        self.position_sizer = PositionSizer(
            account_balance=account_balance,
            max_position_pct=max_position_pct,
            max_total_risk=max_portfolio_risk,
            default_method=position_sizing_method,
        )

        self.stop_loss_manager = StopLossManager(
            default_method=StopLossMethod(stop_loss_method),
            default_rr_ratio=2.0,
        )

        self.trade_validator = TradeValidator(
            max_portfolio_risk=max_portfolio_risk,
            max_single_trade_risk=max_position_risk,
            min_reward_risk_ratio=min_rr_ratio,
            min_confidence=min_confidence,
        )

        self.var_calculator = VaRCalculator(confidence_level=0.95)
        self.portfolio_analyzer = PortfolioRiskAnalyzer(
            max_portfolio_var=0.10,
            max_position_risk=max_position_risk,
        )

        # Database clients
        self._db: Optional[PostgreSQLDatabase] = None
        self._influx: Optional[InfluxDBClient] = None

        # State tracking
        self.active_positions: List[Dict] = []
        self.current_portfolio_risk: float = 0.0
        self.returns_history: Dict[str, List[float]] = {}

    async def initialize(self) -> None:
        """Initialize agent resources"""
        await super().initialize()

        # Connect to PostgreSQL
        self._db = await get_db()

        # Connect to InfluxDB
        self._influx = get_influx()

        # Load active positions and portfolio state
        await self._load_portfolio_state()

        self.logger.info(
            "risk_manager_initialized",
            account_balance=self.account_balance,
            max_portfolio_risk=self.max_portfolio_risk,
            position_sizing_method=self.position_sizing_method,
            active_positions=len(self.active_positions),
            current_portfolio_risk=self.current_portfolio_risk,
        )

    async def setup(self) -> None:
        """Setup subscriptions"""
        # Subscribe to trade intents from Strategy Agent
        await self.subscribe_topic("trade.intent", self._handle_trade_intent)
        # Subscribe to position updates
        await self.subscribe_topic("position.update", self._handle_position_update)
        self.logger.info("risk_manager_setup_complete")

    async def run(self) -> None:
        """Main agent loop (event-driven, just wait)"""
        while self._running:
            await asyncio.sleep(1)

    async def cleanup(self) -> None:
        """Cleanup resources"""
        pass

    def get_subscribed_topics(self) -> List[str]:
        """Return subscribed topics"""
        return ["trade.intent", "position.update"]

    async def start(self) -> None:
        """Start the risk manager agent"""
        await super().start()
        self.logger.info("risk_manager_started")

    async def shutdown(self) -> None:
        """Shutdown agent gracefully"""
        if self._db:
            await self._db.close()

        if self._influx:
            await self._influx.close()

        await super().shutdown()

    async def _handle_trade_intent(self, message: TradeIntent) -> None:
        """Handle trade intent from Strategy Agent"""
        try:
            symbol = message.symbol
            side = message.side
            confidence = message.confidence

            # Generate intent_id from correlation_id or create new UUID
            intent_id = message.correlation_id or str(uuid.uuid4())

            # Extract stop/profit levels from metadata
            metadata = message.metadata or {}
            custom_stop = metadata.get('stop_loss')
            custom_tp = metadata.get('take_profit')

            self.logger.info(
                "trade_intent_received",
                symbol=symbol,
                side=side,
                confidence=confidence,
                intent_id=intent_id,
            )

            # Use expected_price from TradeIntent (more reliable than InfluxDB query)
            # InfluxDB query() method not working currently
            current_price = message.expected_price

            # Fallback prices if expected_price is 0 or None (temporary fix)
            if not current_price or current_price == 0.0:
                fallback_prices = {
                    "BTC/USDT": 50000.0,
                    "ETH/USDT": 2500.0,
                    "SOL/USDT": 150.0,
                }
                current_price = fallback_prices.get(symbol, 1000.0)
                self.logger.warning(
                    "using_fallback_price",
                    symbol=symbol,
                    fallback_price=current_price
                )

            # Get market data for ATR and std (best effort)
            market_data = await self._get_market_data(symbol)
            atr = market_data.get("atr")
            price_std = market_data.get("std")

            # Calculate stop-loss and take-profit
            stop_levels = self.stop_loss_manager.calculate_stops(
                symbol=symbol,
                current_price=current_price,
                side=side,
                method=StopLossMethod(self.stop_loss_method),
                atr=atr,
                price_std=price_std,
                custom_stop=custom_stop,
                custom_tp=custom_tp,
            )

            # Calculate position size
            position_size = self.position_sizer.calculate_position_size(
                symbol=symbol,
                current_price=current_price,
                confidence=confidence,
                stop_loss=stop_levels.stop_loss,
                take_profit=stop_levels.take_profit,
                atr=atr,
                method=self.position_sizing_method,
                current_portfolio_risk=self.current_portfolio_risk,
            )

            # Validate trade
            risk_assessment = self.trade_validator.validate_trade(
                symbol=symbol,
                confidence=confidence,
                position_size=position_size.size_usd,
                risk_amount=position_size.risk_amount,
                reward_risk_ratio=stop_levels.reward_risk_ratio,
                current_portfolio_risk=self.current_portfolio_risk,
                account_balance=self.account_balance,
                existing_positions=self.active_positions,
            )

            # Store risk assessment
            await self._store_risk_assessment(
                trade_intent=message,
                position_size=position_size,
                stop_levels=stop_levels,
                risk_assessment=risk_assessment,
            )

            # Log decision
            if risk_assessment.approved:
                # Additional balance and asset checks before order execution
                can_execute, execution_reason = await self._can_execute_order(
                    symbol=symbol,
                    side=side,
                    quantity=position_size.quantity,
                    size_usd=position_size.size_usd,
                )

                if not can_execute:
                    self.logger.warning(
                        "order_execution_blocked",
                        symbol=symbol,
                        side=side,
                        reason=execution_reason,
                        size_usd=position_size.size_usd,
                    )
                    return

                self.logger.info(
                    "trade_approved",
                    symbol=symbol,
                    side=side,
                    quantity=position_size.quantity,
                    size_usd=position_size.size_usd,
                    risk_amount=position_size.risk_amount,
                    stop_loss=stop_levels.stop_loss,
                    take_profit=stop_levels.take_profit,
                    risk_score=risk_assessment.risk_score,
                )

                # Create and publish order
                order = await self._create_order(
                    trade_intent=message,
                    position_size=position_size,
                    stop_levels=stop_levels,
                )

                self.logger.info(
                    "order_created",
                    symbol=symbol,
                    side=order.side.value,
                    quantity=order.quantity,
                    order_type=order.order_type.value,
                )

                await self.publish_message("trade.order", order, priority=9)

                self.logger.info(
                    "order_published",
                    symbol=symbol,
                    order_id=order.correlation_id or "none",
                )

                # Update portfolio risk
                self.current_portfolio_risk = (
                    risk_assessment.portfolio_risk_after
                )

            else:
                self.logger.warning(
                    "trade_rejected",
                    symbol=symbol,
                    side=side,
                    reason=risk_assessment.rejection_reason,
                    risk_score=risk_assessment.risk_score,
                )

                # Publish rejection notification
                rejection_msg = RiskAssessmentMessage(
                    symbol=symbol,
                    risk_score=risk_assessment.risk_score,
                    approved=False,
                    rejection_reason=risk_assessment.rejection_reason,
                    var_estimate=risk_assessment.var_contribution,
                    metadata={
                        "trade_intent_id": intent_id,
                        "confidence": confidence,
                    },
                )

                await self.publish_message(
                    "trade.rejection", rejection_msg, priority=7
                )

        except Exception as e:
            self.logger.error(
                "trade_intent_error",
                symbol=message.symbol,
                error=str(e),
                exc_info=True,
            )

    async def _handle_position_update(self, message: Any) -> None:
        """Handle position updates from Execution Agent"""
        # Update active positions and portfolio risk
        await self._load_portfolio_state()

        self.logger.debug(
            "position_updated",
            active_positions=len(self.active_positions),
            portfolio_risk=self.current_portfolio_risk,
        )

    async def _get_market_data(self, symbol: str) -> Dict[str, float]:
        """Get current market data and technical indicators"""
        try:
            # Get latest price
            price_query = f"""
                SELECT last(close) as price
                FROM ohlcv
                WHERE symbol = '{symbol}'
                AND time > now() - 1h
            """
            price_result = await self._influx.query(price_query)
            current_price = price_result[0]["price"] if price_result else 50000.0

            # Get ATR
            atr_query = f"""
                SELECT last(value) as atr
                FROM indicators
                WHERE symbol = '{symbol}'
                AND indicator = 'atr'
                AND time > now() - 1h
            """
            atr_result = await self._influx.query(atr_query)
            atr = atr_result[0]["atr"] if atr_result else None

            # Calculate recent price std
            std_query = f"""
                SELECT stddev(close) as std
                FROM ohlcv
                WHERE symbol = '{symbol}'
                AND time > now() - 24h
            """
            std_result = await self._influx.query(std_query)
            price_std = std_result[0]["std"] if std_result else None

            return {
                "price": current_price,
                "atr": atr,
                "std": price_std,
            }

        except Exception as e:
            self.logger.error(
                "market_data_error", symbol=symbol, error=str(e)
            )
            # Return default values
            return {"price": 50000.0, "atr": None, "std": None}

    async def _can_execute_order(
        self, symbol: str, side: str, quantity: float, size_usd: float
    ) -> tuple:
        """
        Check if order can be executed based on balance and holdings.

        Returns:
            (can_execute: bool, reason: str)
        """
        try:
            # Fetch current account balance from exchange
            import ccxt.async_support as ccxt

            exchange = ccxt.binance({
                'apiKey': settings.exchange.binance_api_key,
                'secret': settings.exchange.binance_secret,
                'enableRateLimit': True,
            })

            try:
                balance = await exchange.fetch_balance()

                # For BUY orders, check USDT balance
                if side.upper() == "BUY":
                    available_usdt = balance['free'].get('USDT', 0.0)

                    if available_usdt < size_usd:
                        return False, f"Insufficient USDT balance: have ${available_usdt:.2f}, need ${size_usd:.2f}"

                    self.logger.info(
                        "buy_order_balance_check",
                        symbol=symbol,
                        available_usdt=available_usdt,
                        required_usdt=size_usd,
                        approved=True
                    )
                    return True, "Sufficient USDT balance"

                # For SELL orders, check if we own the base asset
                elif side.upper() == "SELL":
                    # Extract base currency from symbol (e.g., BTC from BTC/USDT)
                    base_currency = symbol.split('/')[0]
                    available_base = balance['free'].get(base_currency, 0.0)

                    if available_base < quantity:
                        return False, f"Insufficient {base_currency} balance: have {available_base}, need {quantity}"

                    self.logger.info(
                        "sell_order_balance_check",
                        symbol=symbol,
                        base_currency=base_currency,
                        available=available_base,
                        required=quantity,
                        approved=True
                    )
                    return True, f"Sufficient {base_currency} balance"

                return True, "Unknown side, allowing order"

            finally:
                await exchange.close()

        except Exception as e:
            self.logger.error(
                "balance_check_error",
                symbol=symbol,
                side=side,
                error=str(e)
            )
            # On error, allow order to proceed (let exchange reject if needed)
            return True, f"Balance check failed: {str(e)}, allowing order"

    async def _load_portfolio_state(self) -> None:
        """Load current portfolio state from database"""
        try:
            # Get active positions
            query = """
                SELECT symbol, side, quantity, entry_price,
                       current_price, stop_loss, take_profit,
                       (quantity * entry_price) as size_usd
                FROM positions
                WHERE status = 'OPEN'
            """

            positions = await self._db.fetch_all(query)
            self.active_positions = [dict(p) for p in positions]

            # Calculate current portfolio risk
            total_risk = 0.0
            for pos in self.active_positions:
                if pos["stop_loss"]:
                    entry = pos["entry_price"]
                    stop = pos["stop_loss"]
                    risk_pct = abs(entry - stop) / entry
                    position_risk = pos["size_usd"] * risk_pct
                    total_risk += position_risk

            self.current_portfolio_risk = (
                total_risk / self.account_balance
                if self.account_balance > 0
                else 0.0
            )

        except Exception as e:
            self.logger.error("load_portfolio_error", error=str(e))
            self.active_positions = []
            self.current_portfolio_risk = 0.0

    async def _store_risk_assessment(
        self,
        trade_intent: TradeIntent,
        position_size: Any,
        stop_levels: Any,
        risk_assessment: Any,
    ) -> None:
        """Store risk assessment in database"""
        try:
            query = """
                INSERT INTO risk_assessments (
                    signal_id, symbol, risk_score, position_size,
                    var_estimate, max_loss, approved, rejection_reason,
                    metadata
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """

            await self._db.execute(
                query,
                None,  # signal_id (could link to signal table)
                trade_intent.symbol,
                risk_assessment.risk_score,
                position_size.size_usd,
                risk_assessment.var_contribution,
                position_size.risk_amount,
                risk_assessment.approved,
                risk_assessment.rejection_reason,
                json.dumps(
                    {
                        "trade_intent_id": trade_intent.correlation_id or str(uuid.uuid4()),
                        "confidence": trade_intent.confidence,
                        "kelly_fraction": position_size.kelly_fraction,
                        "sizing_method": position_size.method,
                        "stop_loss": stop_levels.stop_loss,
                        "take_profit": stop_levels.take_profit,
                        "rr_ratio": stop_levels.reward_risk_ratio,
                    }
                ),
            )

        except Exception as e:
            self.logger.error(
                "store_assessment_error",
                symbol=trade_intent.symbol,
                error=str(e),
            )

    async def _create_order(
        self, trade_intent: TradeIntent, position_size: Any, stop_levels: Any
    ) -> Order:
        """Create order from approved trade intent"""
        order = Order(
            source_agent=self.name,
            exchange="binance",  # Default to binance
            symbol=trade_intent.symbol,
            side=trade_intent.side,
            order_type=OrderType.MARKET,  # Default to market orders
            quantity=position_size.quantity,
            price=None,  # Market order
            stop_loss=stop_levels.stop_loss,
            take_profit=stop_levels.take_profit,
            risk_approved=True,  # Already approved if we're creating order
            risk_params={
                "position_size_usd": position_size.size_usd,
                "risk_amount": position_size.risk_amount,
                "kelly_fraction": position_size.kelly_fraction,
                "stop_method": stop_levels.method,
                "rr_ratio": stop_levels.reward_risk_ratio,
            },
            metadata={
                "trade_intent_id": trade_intent.correlation_id or str(uuid.uuid4()),
                "confidence": trade_intent.confidence,
                "sizing_method": position_size.method,
                "strategy_reasoning": trade_intent.metadata.get("reasoning", "") if trade_intent.metadata else "",
            },
        )

        return order


async def main():
    """Main entry point for Risk Manager Agent"""

    # Fetch real account balance from exchange
    import ccxt.async_support as ccxt

    exchange = ccxt.binance({
        'apiKey': settings.exchange.binance_api_key,
        'secret': settings.exchange.binance_secret,
        'enableRateLimit': True,
    })

    try:
        balance = await exchange.fetch_balance()
        # Get USDT balance (quote currency for all trading pairs)
        account_balance = balance['total'].get('USDT', 0.0)

        if account_balance <= 0:
            print(f"⚠️ Warning: USDT balance is {account_balance}. Using default 100.0")
            account_balance = 100.0

        print(f"✅ Real account balance: ${account_balance} USDT")

    except Exception as e:
        print(f"⚠️ Could not fetch balance: {e}. Using default 100.0")
        account_balance = 100.0
    finally:
        await exchange.close()

    agent = RiskManagerAgent(
        name="risk_manager_main",
        account_balance=account_balance,  # Use real balance
        max_portfolio_risk=0.20,
        max_position_risk=0.05,
        position_sizing_method="hybrid",
        stop_loss_method="atr",
        min_confidence=0.6,
        min_rr_ratio=1.5,
    )

    try:
        await agent.initialize()
        await agent.start()

        # Keep running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Shutting down Risk Manager Agent...")
    finally:
        await agent.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
