#!/usr/bin/env python3
"""
Backtesting Engine
Historical data backtesting for strategy validation and performance metrics
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import random
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PositionSide(Enum):
    """Position side"""
    LONG = "long"
    SHORT = "short"


@dataclass
class BacktestPosition:
    """Backtest position"""
    symbol: str
    side: PositionSide
    entry_price: float
    entry_time: datetime
    quantity: float
    stop_loss: float
    take_profit: float
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    status: str = "open"  # open, closed


@dataclass
class BacktestMetrics:
    """Backtest performance metrics"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0

    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0

    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0

    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0

    avg_trade_duration_hours: float = 0.0

    positions: List[BacktestPosition] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)


class BacktestingEngine:
    """
    Historical Backtesting Engine

    Tests trading strategies on historical data to validate performance
    """

    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission_pct: float = 0.1,  # 0.1% per trade
        slippage_pct: float = 0.05    # 0.05% slippage
    ):
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct

        self.capital = initial_capital
        self.positions: List[BacktestPosition] = []
        self.closed_positions: List[BacktestPosition] = []

        self.equity_curve: List[float] = [initial_capital]

    def generate_sample_data(
        self,
        symbol: str = "BTC/USDT",
        start_date: datetime = None,
        days: int = 30
    ) -> pd.DataFrame:
        """
        Generate sample OHLCV data for testing

        In production, this would load from InfluxDB or CSV
        """
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=days)

        dates = pd.date_range(start=start_date, periods=days*24, freq='H')

        # Generate realistic price data with trend + noise
        base_price = 50000.0
        trend = np.linspace(0, 5000, len(dates))  # Upward trend
        noise = np.random.normal(0, 500, len(dates))

        close_prices = base_price + trend + noise

        data = {
            'timestamp': dates,
            'open': close_prices - np.random.uniform(0, 200, len(dates)),
            'high': close_prices + np.random.uniform(100, 500, len(dates)),
            'low': close_prices - np.random.uniform(100, 500, len(dates)),
            'close': close_prices,
            'volume': np.random.uniform(1000, 5000, len(dates))
        }

        df = pd.DataFrame(data)
        df['symbol'] = symbol

        return df

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators"""
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()

        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)

        # ATR for stop-loss
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        df['atr'] = ranges.max(axis=1).rolling(14).mean()

        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate trading signals based on strategy"""
        df['signal'] = 0  # 0: no signal, 1: buy, -1: sell

        # Multi-indicator strategy (similar to our Strategy Agent)

        # BUY conditions
        buy_conditions = (
            (df['rsi'] < 40) &  # Oversold
            (df['macd'] > df['macd_signal']) &  # MACD crossover
            (df['close'] < df['bb_lower'])  # Below lower Bollinger
        )

        # SELL conditions
        sell_conditions = (
            (df['rsi'] > 60) &  # Overbought
            (df['macd'] < df['macd_signal']) &  # MACD cross down
            (df['close'] > df['bb_upper'])  # Above upper Bollinger
        )

        df.loc[buy_conditions, 'signal'] = 1
        df.loc[sell_conditions, 'signal'] = -1

        return df

    def open_position(
        self,
        symbol: str,
        side: PositionSide,
        entry_price: float,
        entry_time: datetime,
        atr: float
    ) -> Optional[BacktestPosition]:
        """Open a new position"""
        # Position sizing: 2% risk per trade
        risk_per_trade = self.capital * 0.02

        # ATR-based stop-loss
        if side == PositionSide.LONG:
            stop_loss = entry_price - (atr * 2)
            take_profit = entry_price + (atr * 4)  # 2:1 R/R
        else:
            stop_loss = entry_price + (atr * 2)
            take_profit = entry_price - (atr * 4)

        # Calculate position size
        stop_distance = abs(entry_price - stop_loss)
        if stop_distance == 0:
            return None

        quantity = risk_per_trade / stop_distance

        # Apply slippage
        actual_entry = entry_price * (1 + self.slippage_pct/100 if side == PositionSide.LONG
                                     else 1 - self.slippage_pct/100)

        # Apply commission
        commission = (actual_entry * quantity) * (self.commission_pct / 100)
        self.capital -= commission

        position = BacktestPosition(
            symbol=symbol,
            side=side,
            entry_price=actual_entry,
            entry_time=entry_time,
            quantity=quantity,
            stop_loss=stop_loss,
            take_profit=take_profit
        )

        self.positions.append(position)
        logger.info(f"📈 Opened {side.value.upper()} @ {actual_entry:.2f}, SL: {stop_loss:.2f}, TP: {take_profit:.2f}")

        return position

    def close_position(
        self,
        position: BacktestPosition,
        exit_price: float,
        exit_time: datetime
    ) -> None:
        """Close a position"""
        # Apply slippage
        actual_exit = exit_price * (1 - self.slippage_pct/100 if position.side == PositionSide.LONG
                                    else 1 + self.slippage_pct/100)

        # Calculate P&L
        if position.side == PositionSide.LONG:
            pnl = (actual_exit - position.entry_price) * position.quantity
        else:
            pnl = (position.entry_price - actual_exit) * position.quantity

        # Apply commission
        commission = (actual_exit * position.quantity) * (self.commission_pct / 100)
        pnl -= commission

        pnl_pct = (pnl / (position.entry_price * position.quantity)) * 100

        position.exit_price = actual_exit
        position.exit_time = exit_time
        position.pnl = pnl
        position.pnl_pct = pnl_pct
        position.status = "closed"

        self.capital += pnl
        self.equity_curve.append(self.capital)

        self.positions.remove(position)
        self.closed_positions.append(position)

        logger.info(f"📉 Closed {position.side.value.upper()} @ {actual_exit:.2f}, P&L: ${pnl:.2f} ({pnl_pct:.2f}%)")

    def update_positions(self, current_price: float, current_time: datetime) -> None:
        """Update open positions and check stop-loss/take-profit"""
        positions_to_close = []

        for position in self.positions:
            # Check stop-loss
            if position.side == PositionSide.LONG:
                if current_price <= position.stop_loss:
                    positions_to_close.append((position, position.stop_loss, "Stop-Loss"))
                elif current_price >= position.take_profit:
                    positions_to_close.append((position, position.take_profit, "Take-Profit"))
            else:  # SHORT
                if current_price >= position.stop_loss:
                    positions_to_close.append((position, position.stop_loss, "Stop-Loss"))
                elif current_price <= position.take_profit:
                    positions_to_close.append((position, position.take_profit, "Take-Profit"))

        for position, exit_price, reason in positions_to_close:
            logger.info(f"🎯 {reason} hit!")
            self.close_position(position, exit_price, current_time)

    def calculate_metrics(self) -> BacktestMetrics:
        """Calculate backtest performance metrics"""
        if not self.closed_positions:
            return BacktestMetrics()

        winning_trades = [p for p in self.closed_positions if p.pnl > 0]
        losing_trades = [p for p in self.closed_positions if p.pnl <= 0]

        total_wins = sum(p.pnl for p in winning_trades)
        total_losses = abs(sum(p.pnl for p in losing_trades))

        # Win rate
        win_rate = (len(winning_trades) / len(self.closed_positions)) * 100 if self.closed_positions else 0

        # Average win/loss
        avg_win = total_wins / len(winning_trades) if winning_trades else 0
        avg_loss = total_losses / len(losing_trades) if losing_trades else 0

        # Profit factor
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        # Sharpe ratio (simplified)
        returns = [p.pnl_pct for p in self.closed_positions]
        sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0

        # Max drawdown
        peak = self.initial_capital
        max_dd = 0
        for equity in self.equity_curve:
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd

        max_dd_pct = (max_dd / peak) * 100 if peak > 0 else 0

        # Trade duration
        durations = [(p.exit_time - p.entry_time).total_seconds() / 3600
                    for p in self.closed_positions if p.exit_time]
        avg_duration = np.mean(durations) if durations else 0

        metrics = BacktestMetrics(
            total_trades=len(self.closed_positions),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=win_rate,
            total_pnl=sum(p.pnl for p in self.closed_positions),
            total_pnl_pct=((self.capital - self.initial_capital) / self.initial_capital) * 100,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=max(p.pnl for p in self.closed_positions),
            largest_loss=min(p.pnl for p in self.closed_positions),
            profit_factor=profit_factor,
            sharpe_ratio=sharpe,
            max_drawdown=max_dd,
            max_drawdown_pct=max_dd_pct,
            avg_trade_duration_hours=avg_duration,
            positions=self.closed_positions,
            equity_curve=self.equity_curve
        )

        return metrics

    async def run_backtest(
        self,
        symbol: str = "BTC/USDT",
        start_date: datetime = None,
        days: int = 30
    ) -> BacktestMetrics:
        """Run backtest simulation"""
        logger.info("=" * 60)
        logger.info("🚀 Starting Backtest")
        logger.info(f"Symbol: {symbol}")
        logger.info(f"Period: {days} days")
        logger.info(f"Initial Capital: ${self.initial_capital:,.2f}")
        logger.info("=" * 60)

        # Generate/load data
        df = self.generate_sample_data(symbol, start_date, days)

        # Calculate indicators
        df = self.calculate_indicators(df)

        # Generate signals
        df = self.generate_signals(df)

        # Simulate trading
        for idx, row in df.iterrows():
            if idx < 30:  # Skip initial rows for indicator warmup
                continue

            current_price = row['close']
            current_time = row['timestamp']
            signal = row['signal']
            atr = row['atr']

            # Update existing positions
            self.update_positions(current_price, current_time)

            # Open new positions on signals
            if signal == 1 and len(self.positions) == 0:  # BUY signal, no open position
                self.open_position(symbol, PositionSide.LONG, current_price, current_time, atr)
            elif signal == -1 and len(self.positions) > 0:  # SELL signal, close long
                for position in list(self.positions):
                    if position.side == PositionSide.LONG:
                        self.close_position(position, current_price, current_time)

        # Close any remaining positions
        final_price = df.iloc[-1]['close']
        final_time = df.iloc[-1]['timestamp']
        for position in list(self.positions):
            logger.info("📌 Closing remaining position at backtest end")
            self.close_position(position, final_price, final_time)

        # Calculate metrics
        metrics = self.calculate_metrics()

        # Print results
        self._print_results(metrics)

        return metrics

    def _print_results(self, metrics: BacktestMetrics) -> None:
        """Print backtest results"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 Backtest Results")
        logger.info("=" * 60)

        logger.info(f"\n💰 Capital:")
        logger.info(f"  Initial: ${self.initial_capital:,.2f}")
        logger.info(f"  Final: ${self.capital:,.2f}")
        logger.info(f"  P&L: ${metrics.total_pnl:,.2f} ({metrics.total_pnl_pct:.2f}%)")

        logger.info(f"\n📈 Trading Statistics:")
        logger.info(f"  Total Trades: {metrics.total_trades}")
        logger.info(f"  Winning: {metrics.winning_trades}")
        logger.info(f"  Losing: {metrics.losing_trades}")
        logger.info(f"  Win Rate: {metrics.win_rate:.2f}%")

        logger.info(f"\n💵 P&L Analysis:")
        logger.info(f"  Avg Win: ${metrics.avg_win:.2f}")
        logger.info(f"  Avg Loss: ${metrics.avg_loss:.2f}")
        logger.info(f"  Largest Win: ${metrics.largest_win:.2f}")
        logger.info(f"  Largest Loss: ${metrics.largest_loss:.2f}")
        logger.info(f"  Profit Factor: {metrics.profit_factor:.2f}")

        logger.info(f"\n📊 Risk Metrics:")
        logger.info(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
        logger.info(f"  Max Drawdown: ${metrics.max_drawdown:.2f} ({metrics.max_drawdown_pct:.2f}%)")
        logger.info(f"  Avg Trade Duration: {metrics.avg_trade_duration_hours:.1f} hours")

        logger.info("\n" + "=" * 60)

        # Performance assessment
        if metrics.total_pnl_pct > 10 and metrics.win_rate > 50 and metrics.sharpe_ratio > 1:
            logger.info("🎉 EXCELLENT PERFORMANCE!")
        elif metrics.total_pnl_pct > 5 and metrics.win_rate > 45:
            logger.info("✅ GOOD PERFORMANCE")
        elif metrics.total_pnl_pct > 0:
            logger.info("⚠️  MODERATE PERFORMANCE - Needs Optimization")
        else:
            logger.info("❌ POOR PERFORMANCE - Strategy Needs Revision")

        logger.info("=" * 60)


async def main():
    """Main backtest runner"""
    engine = BacktestingEngine(
        initial_capital=10000.0,
        commission_pct=0.1,
        slippage_pct=0.05
    )

    await engine.run_backtest(
        symbol="BTC/USDT",
        days=30
    )


if __name__ == "__main__":
    asyncio.run(main())
