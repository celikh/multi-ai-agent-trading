"""
Position Sizing Module
Kelly Criterion and risk-based position sizing algorithms.
"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from decimal import Decimal
import math


@dataclass
class PositionSize:
    """Position size calculation result"""

    quantity: float
    size_usd: float
    risk_amount: float
    kelly_fraction: float
    method: str
    reasoning: str
    metadata: Dict


class KellyCriterion:
    """
    Kelly Criterion for optimal position sizing

    Formula: f* = (bp - q) / b
    where:
    - f* = fraction of capital to bet
    - b = odds received on bet (reward/risk ratio)
    - p = probability of winning
    - q = probability of losing (1-p)
    """

    def __init__(
        self,
        max_kelly_fraction: float = 0.25,  # Conservative: 25% of full Kelly
        min_kelly_fraction: float = 0.01,  # Minimum 1%
        confidence_threshold: float = 0.5,
    ):
        self.max_kelly_fraction = max_kelly_fraction
        self.min_kelly_fraction = min_kelly_fraction
        self.confidence_threshold = confidence_threshold

    def calculate(
        self,
        win_probability: float,
        reward_risk_ratio: float,
        account_balance: float,
    ) -> float:
        """
        Calculate Kelly fraction

        Args:
            win_probability: Probability of winning (0-1)
            reward_risk_ratio: Expected reward / risk ratio
            account_balance: Total account balance

        Returns:
            Optimal position size fraction
        """
        # Validate inputs
        if win_probability <= 0 or win_probability >= 1:
            return self.min_kelly_fraction

        if reward_risk_ratio <= 0:
            return self.min_kelly_fraction

        # Kelly formula
        lose_probability = 1 - win_probability
        kelly_fraction = (
            win_probability * reward_risk_ratio - lose_probability
        ) / reward_risk_ratio

        # Apply constraints
        kelly_fraction = max(self.min_kelly_fraction, kelly_fraction)
        kelly_fraction = min(self.max_kelly_fraction, kelly_fraction)

        # Additional safety: reduce if confidence is low
        if win_probability < self.confidence_threshold:
            kelly_fraction *= 0.5  # Half Kelly for low confidence

        return kelly_fraction


class FixedFractional:
    """
    Fixed Fractional position sizing
    Fixed percentage of capital per trade
    """

    def __init__(
        self,
        risk_per_trade: float = 0.02,  # 2% risk per trade
        max_position_size: float = 0.10,  # Max 10% of portfolio
    ):
        self.risk_per_trade = risk_per_trade
        self.max_position_size = max_position_size

    def calculate(
        self,
        account_balance: float,
        stop_loss_pct: float,
    ) -> float:
        """
        Calculate position size based on fixed risk

        Args:
            account_balance: Total account balance
            stop_loss_pct: Stop loss as percentage (e.g., 0.05 for 5%)

        Returns:
            Position size in USD
        """
        if stop_loss_pct <= 0:
            return account_balance * self.max_position_size

        # Risk amount
        risk_amount = account_balance * self.risk_per_trade

        # Position size
        position_size = risk_amount / stop_loss_pct

        # Cap at max position size
        max_size = account_balance * self.max_position_size
        position_size = min(position_size, max_size)

        return position_size


class VolatilityBased:
    """
    Volatility-based position sizing
    Adjust position size based on market volatility (ATR)
    """

    def __init__(
        self,
        base_risk: float = 0.02,  # 2% base risk
        atr_multiplier: float = 2.0,  # ATR multiplier for stop loss
    ):
        self.base_risk = base_risk
        self.atr_multiplier = atr_multiplier

    def calculate(
        self,
        account_balance: float,
        current_price: float,
        atr: float,
    ) -> Tuple[float, float]:
        """
        Calculate position size based on ATR

        Args:
            account_balance: Total account balance
            current_price: Current asset price
            atr: Average True Range

        Returns:
            (position_size_usd, stop_loss_distance)
        """
        # Stop loss distance based on ATR
        stop_loss_distance = atr * self.atr_multiplier

        # Risk amount
        risk_amount = account_balance * self.base_risk

        # Position size in quote currency (USD)
        stop_loss_pct = stop_loss_distance / current_price
        position_size = risk_amount / stop_loss_pct

        return position_size, stop_loss_distance


class PositionSizer:
    """
    Main position sizing coordinator
    Combines multiple sizing methods
    """

    def __init__(
        self,
        account_balance: float,
        max_position_pct: float = 0.10,  # Max 10% per position
        max_total_risk: float = 0.20,  # Max 20% total portfolio risk
        default_method: str = "kelly",
    ):
        self.account_balance = account_balance
        self.max_position_pct = max_position_pct
        self.max_total_risk = max_total_risk
        self.default_method = default_method

        # Initialize sizing methods
        self.kelly = KellyCriterion(max_kelly_fraction=0.25)
        self.fixed = FixedFractional(risk_per_trade=0.02)
        self.volatility = VolatilityBased(base_risk=0.02)

    def calculate_position_size(
        self,
        symbol: str,
        current_price: float,
        confidence: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        atr: Optional[float] = None,
        method: Optional[str] = None,
        current_portfolio_risk: float = 0.0,
    ) -> PositionSize:
        """
        Calculate optimal position size

        Args:
            symbol: Trading symbol
            current_price: Current price
            confidence: Signal confidence (0-1)
            stop_loss: Stop loss price
            take_profit: Take profit price
            atr: Average True Range
            method: Sizing method (kelly, fixed, volatility, hybrid)
            current_portfolio_risk: Current portfolio risk percentage

        Returns:
            PositionSize object with all details
        """
        method = method or self.default_method

        # Calculate reward/risk ratio
        if stop_loss and take_profit:
            risk = abs(current_price - stop_loss)
            reward = abs(take_profit - current_price)
            reward_risk_ratio = reward / risk if risk > 0 else 1.5
        else:
            reward_risk_ratio = 1.5  # Default 1.5:1

        # Calculate stop loss percentage
        if stop_loss:
            stop_loss_pct = abs(current_price - stop_loss) / current_price
        elif atr:
            stop_loss_pct = (atr * 2.0) / current_price
        else:
            stop_loss_pct = 0.05  # Default 5%

        # Use confidence as win probability (with adjustment)
        # Confidence 0.6 -> 55% win probability
        # Confidence 0.8 -> 65% win probability
        win_probability = 0.50 + (confidence - 0.5) * 0.3
        win_probability = max(0.51, min(0.70, win_probability))

        # Calculate based on method
        if method == "kelly":
            kelly_fraction = self.kelly.calculate(
                win_probability, reward_risk_ratio, self.account_balance
            )
            position_size = self.account_balance * kelly_fraction
            sizing_method = "Kelly Criterion"

        elif method == "fixed":
            position_size = self.fixed.calculate(
                self.account_balance, stop_loss_pct
            )
            kelly_fraction = position_size / self.account_balance
            sizing_method = "Fixed Fractional"

        elif method == "volatility" and atr:
            position_size, _ = self.volatility.calculate(
                self.account_balance, current_price, atr
            )
            kelly_fraction = position_size / self.account_balance
            sizing_method = "Volatility-Based (ATR)"

        elif method == "hybrid":
            # Combine Kelly and Fixed methods
            kelly_fraction = self.kelly.calculate(
                win_probability, reward_risk_ratio, self.account_balance
            )
            kelly_size = self.account_balance * kelly_fraction

            fixed_size = self.fixed.calculate(
                self.account_balance, stop_loss_pct
            )

            # Use the more conservative (smaller) size, but respect max_position_pct
            # For small accounts, max_position_pct may be higher to meet exchange minimums
            conservative_size = min(kelly_size, fixed_size)
            max_allowed = self.account_balance * self.max_position_pct

            # If both methods suggest less than max, use conservative
            # But allow max if it's needed for small accounts
            if conservative_size < max_allowed and max_allowed <= self.account_balance * 0.80:
                # Small account optimization: use max_position_pct if reasonable
                position_size = max_allowed
                sizing_method = "Hybrid (Kelly + Fixed, max-adjusted)"
            else:
                position_size = conservative_size
                sizing_method = "Hybrid (Kelly + Fixed)"

            kelly_fraction = position_size / self.account_balance

        else:
            # Default to fixed fractional
            position_size = self.fixed.calculate(
                self.account_balance, stop_loss_pct
            )
            kelly_fraction = position_size / self.account_balance
            sizing_method = "Fixed Fractional (default)"

        # Apply maximum position size constraint
        max_position_size = self.account_balance * self.max_position_pct
        if position_size > max_position_size:
            position_size = max_position_size
            kelly_fraction = self.max_position_pct

        # Check portfolio risk limit
        risk_amount = position_size * stop_loss_pct
        new_total_risk = current_portfolio_risk + (
            risk_amount / self.account_balance
        )

        if new_total_risk > self.max_total_risk:
            # Reduce position size to stay within portfolio risk limit
            available_risk = self.max_total_risk - current_portfolio_risk
            position_size = (
                available_risk * self.account_balance
            ) / stop_loss_pct
            kelly_fraction = position_size / self.account_balance
            sizing_method += " (risk-adjusted)"

        # Calculate quantity in base currency
        quantity = position_size / current_price

        # Round to reasonable precision
        quantity = round(quantity, 8)
        position_size = round(position_size, 2)
        risk_amount = round(position_size * stop_loss_pct, 2)

        # Build reasoning
        reasoning = (
            f"Position size: ${position_size:,.2f} ({kelly_fraction:.1%} of portfolio) | "
            f"Risk: ${risk_amount:,.2f} ({stop_loss_pct:.1%} stop) | "
            f"R:R {reward_risk_ratio:.2f}:1 | "
            f"Win prob: {win_probability:.1%} | "
            f"Method: {sizing_method}"
        )

        return PositionSize(
            quantity=quantity,
            size_usd=position_size,
            risk_amount=risk_amount,
            kelly_fraction=kelly_fraction,
            method=sizing_method,
            reasoning=reasoning,
            metadata={
                "win_probability": win_probability,
                "reward_risk_ratio": reward_risk_ratio,
                "stop_loss_pct": stop_loss_pct,
                "confidence": confidence,
                "current_portfolio_risk": current_portfolio_risk,
                "new_total_risk": new_total_risk,
            },
        )

    def update_account_balance(self, new_balance: float) -> None:
        """Update account balance"""
        self.account_balance = new_balance
