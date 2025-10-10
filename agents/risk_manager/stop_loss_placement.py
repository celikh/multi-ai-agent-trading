"""
Stop-Loss and Take-Profit Placement Module
Dynamic stop-loss and take-profit calculation based on market conditions.
"""

from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np


class StopLossMethod(str, Enum):
    """Stop-loss placement methods"""

    ATR = "atr"  # Based on Average True Range
    PERCENTAGE = "percentage"  # Fixed percentage
    SUPPORT_RESISTANCE = "support_resistance"  # Technical levels
    VOLATILITY = "volatility"  # Standard deviation based
    TRAILING = "trailing"  # Trailing stop


@dataclass
class StopLossLevels:
    """Stop-loss and take-profit levels"""

    stop_loss: float
    take_profit: float
    stop_loss_pct: float
    take_profit_pct: float
    reward_risk_ratio: float
    method: str
    reasoning: str
    metadata: Dict


class ATRStopLoss:
    """
    ATR-based stop-loss placement
    Uses Average True Range for volatility-adjusted stops
    """

    def __init__(
        self,
        atr_multiplier: float = 2.0,  # 2x ATR for stop
        rr_ratio: float = 2.0,  # 2:1 reward/risk for take profit
    ):
        self.atr_multiplier = atr_multiplier
        self.rr_ratio = rr_ratio

    def calculate(
        self, current_price: float, atr: float, side: str
    ) -> Tuple[float, float]:
        """
        Calculate stop-loss and take-profit based on ATR

        Args:
            current_price: Current market price
            atr: Average True Range value
            side: 'BUY' or 'SELL'

        Returns:
            (stop_loss, take_profit)
        """
        stop_distance = atr * self.atr_multiplier

        if side == "BUY":
            stop_loss = current_price - stop_distance
            take_profit = current_price + (stop_distance * self.rr_ratio)
        else:  # SELL
            stop_loss = current_price + stop_distance
            take_profit = current_price - (stop_distance * self.rr_ratio)

        return stop_loss, take_profit


class PercentageStopLoss:
    """
    Fixed percentage stop-loss
    Simple but effective for consistent risk management
    """

    def __init__(
        self,
        stop_pct: float = 0.05,  # 5% stop loss
        rr_ratio: float = 2.0,  # 2:1 reward/risk
    ):
        self.stop_pct = stop_pct
        self.rr_ratio = rr_ratio

    def calculate(
        self, current_price: float, side: str
    ) -> Tuple[float, float]:
        """
        Calculate fixed percentage stops

        Args:
            current_price: Current market price
            side: 'BUY' or 'SELL'

        Returns:
            (stop_loss, take_profit)
        """
        if side == "BUY":
            stop_loss = current_price * (1 - self.stop_pct)
            take_profit = current_price * (
                1 + (self.stop_pct * self.rr_ratio)
            )
        else:  # SELL
            stop_loss = current_price * (1 + self.stop_pct)
            take_profit = current_price * (
                1 - (self.stop_pct * self.rr_ratio)
            )

        return stop_loss, take_profit


class VolatilityStopLoss:
    """
    Volatility-based stop-loss using standard deviation
    """

    def __init__(
        self,
        std_multiplier: float = 2.0,  # 2 standard deviations
        rr_ratio: float = 2.0,
    ):
        self.std_multiplier = std_multiplier
        self.rr_ratio = rr_ratio

    def calculate(
        self, current_price: float, price_std: float, side: str
    ) -> Tuple[float, float]:
        """
        Calculate volatility-based stops

        Args:
            current_price: Current market price
            price_std: Standard deviation of recent prices
            side: 'BUY' or 'SELL'

        Returns:
            (stop_loss, take_profit)
        """
        stop_distance = price_std * self.std_multiplier

        if side == "BUY":
            stop_loss = current_price - stop_distance
            take_profit = current_price + (stop_distance * self.rr_ratio)
        else:  # SELL
            stop_loss = current_price + stop_distance
            take_profit = current_price - (stop_distance * self.rr_ratio)

        return stop_loss, take_profit


class SupportResistanceStopLoss:
    """
    Stop-loss based on support/resistance levels
    Places stops beyond key technical levels
    """

    def __init__(
        self,
        buffer_pct: float = 0.01,  # 1% buffer beyond S/R
        rr_ratio: float = 2.0,
    ):
        self.buffer_pct = buffer_pct
        self.rr_ratio = rr_ratio

    def calculate(
        self,
        current_price: float,
        support_level: float,
        resistance_level: float,
        side: str,
    ) -> Tuple[float, float]:
        """
        Calculate stops based on S/R levels

        Args:
            current_price: Current market price
            support_level: Support level
            resistance_level: Resistance level
            side: 'BUY' or 'SELL'

        Returns:
            (stop_loss, take_profit)
        """
        if side == "BUY":
            # Place stop below support
            stop_loss = support_level * (1 - self.buffer_pct)

            # Calculate risk
            risk = current_price - stop_loss

            # Take profit at resistance or R/R ratio, whichever is further
            tp_by_rr = current_price + (risk * self.rr_ratio)
            tp_by_resistance = resistance_level * (1 - self.buffer_pct)

            take_profit = max(tp_by_rr, tp_by_resistance)

        else:  # SELL
            # Place stop above resistance
            stop_loss = resistance_level * (1 + self.buffer_pct)

            # Calculate risk
            risk = stop_loss - current_price

            # Take profit at support or R/R ratio
            tp_by_rr = current_price - (risk * self.rr_ratio)
            tp_by_support = support_level * (1 + self.buffer_pct)

            take_profit = min(tp_by_rr, tp_by_support)

        return stop_loss, take_profit


class TrailingStopLoss:
    """
    Trailing stop-loss that moves with price
    """

    def __init__(
        self,
        trail_pct: float = 0.03,  # 3% trailing distance
        activation_pct: float = 0.05,  # Activate after 5% profit
    ):
        self.trail_pct = trail_pct
        self.activation_pct = activation_pct

    def calculate_initial(
        self, entry_price: float, side: str
    ) -> Tuple[float, float]:
        """
        Calculate initial trailing stop

        Args:
            entry_price: Entry price
            side: 'BUY' or 'SELL'

        Returns:
            (stop_loss, activation_price)
        """
        if side == "BUY":
            stop_loss = entry_price * (1 - self.trail_pct)
            activation_price = entry_price * (1 + self.activation_pct)
        else:  # SELL
            stop_loss = entry_price * (1 + self.trail_pct)
            activation_price = entry_price * (1 - self.activation_pct)

        return stop_loss, activation_price

    def update_trailing_stop(
        self,
        current_price: float,
        current_stop: float,
        entry_price: float,
        side: str,
    ) -> float:
        """
        Update trailing stop based on current price

        Args:
            current_price: Current market price
            current_stop: Current stop-loss level
            entry_price: Original entry price
            side: 'BUY' or 'SELL'

        Returns:
            Updated stop-loss level
        """
        if side == "BUY":
            # Check if we've reached activation
            if current_price >= entry_price * (1 + self.activation_pct):
                # Calculate new trailing stop
                new_stop = current_price * (1 - self.trail_pct)

                # Only move stop up, never down
                return max(current_stop, new_stop)

        else:  # SELL
            # Check if we've reached activation
            if current_price <= entry_price * (1 - self.activation_pct):
                # Calculate new trailing stop
                new_stop = current_price * (1 + self.trail_pct)

                # Only move stop down, never up
                return min(current_stop, new_stop)

        return current_stop


class StopLossManager:
    """
    Main stop-loss placement coordinator
    Selects optimal method based on market conditions
    """

    def __init__(
        self,
        default_method: StopLossMethod = StopLossMethod.ATR,
        default_rr_ratio: float = 2.0,
    ):
        self.default_method = default_method
        self.default_rr_ratio = default_rr_ratio

        # Initialize all methods
        self.atr_stop = ATRStopLoss(atr_multiplier=2.0, rr_ratio=2.0)
        self.pct_stop = PercentageStopLoss(stop_pct=0.05, rr_ratio=2.0)
        self.vol_stop = VolatilityStopLoss(std_multiplier=2.0, rr_ratio=2.0)
        self.sr_stop = SupportResistanceStopLoss(
            buffer_pct=0.01, rr_ratio=2.0
        )
        self.trailing_stop = TrailingStopLoss(
            trail_pct=0.03, activation_pct=0.05
        )

    def calculate_stops(
        self,
        symbol: str,
        current_price: float,
        side: str,
        method: Optional[StopLossMethod] = None,
        atr: Optional[float] = None,
        price_std: Optional[float] = None,
        support: Optional[float] = None,
        resistance: Optional[float] = None,
        custom_stop: Optional[float] = None,
        custom_tp: Optional[float] = None,
    ) -> StopLossLevels:
        """
        Calculate optimal stop-loss and take-profit levels

        Args:
            symbol: Trading symbol
            current_price: Current market price
            side: 'BUY' or 'SELL'
            method: Stop-loss method to use
            atr: Average True Range (if available)
            price_std: Price standard deviation (if available)
            support: Support level (if available)
            resistance: Resistance level (if available)
            custom_stop: Custom stop-loss price
            custom_tp: Custom take-profit price

        Returns:
            StopLossLevels with all details
        """
        # Use custom levels if provided
        if custom_stop and custom_tp:
            stop_loss = custom_stop
            take_profit = custom_tp
            method_name = "Custom Levels"

        # Otherwise calculate based on method
        else:
            method = method or self.default_method

            if method == StopLossMethod.ATR and atr:
                stop_loss, take_profit = self.atr_stop.calculate(
                    current_price, atr, side
                )
                method_name = "ATR-based"

            elif method == StopLossMethod.VOLATILITY and price_std:
                stop_loss, take_profit = self.vol_stop.calculate(
                    current_price, price_std, side
                )
                method_name = "Volatility-based"

            elif (
                method == StopLossMethod.SUPPORT_RESISTANCE
                and support
                and resistance
            ):
                stop_loss, take_profit = self.sr_stop.calculate(
                    current_price, support, resistance, side
                )
                method_name = "Support/Resistance"

            else:
                # Default to percentage
                stop_loss, take_profit = self.pct_stop.calculate(
                    current_price, side
                )
                method_name = "Fixed Percentage"

        # Calculate percentages
        if side == "BUY":
            stop_loss_pct = abs(current_price - stop_loss) / current_price
            take_profit_pct = abs(take_profit - current_price) / current_price
        else:  # SELL
            stop_loss_pct = abs(stop_loss - current_price) / current_price
            take_profit_pct = abs(current_price - take_profit) / current_price

        # Calculate R/R ratio
        reward_risk_ratio = take_profit_pct / stop_loss_pct if stop_loss_pct > 0 else 1.0

        # Round to reasonable precision
        stop_loss = round(stop_loss, 2)
        take_profit = round(take_profit, 2)

        # Build reasoning
        reasoning = (
            f"Stop: ${stop_loss:,.2f} ({stop_loss_pct:.1%}) | "
            f"TP: ${take_profit:,.2f} ({take_profit_pct:.1%}) | "
            f"R/R: {reward_risk_ratio:.2f}:1 | "
            f"Method: {method_name}"
        )

        return StopLossLevels(
            stop_loss=stop_loss,
            take_profit=take_profit,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
            reward_risk_ratio=reward_risk_ratio,
            method=method_name,
            reasoning=reasoning,
            metadata={
                "symbol": symbol,
                "current_price": current_price,
                "side": side,
                "atr": atr,
                "price_std": price_std,
                "support": support,
                "resistance": resistance,
            },
        )
