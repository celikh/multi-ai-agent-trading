"""
Risk Assessment Module
VaR calculation, portfolio risk metrics, and trade validation.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
from scipy import stats


@dataclass
class RiskMetrics:
    """Risk assessment metrics"""

    var_95: float  # Value at Risk at 95% confidence
    var_99: float  # Value at Risk at 99% confidence
    cvar_95: float  # Conditional VaR (Expected Shortfall)
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    risk_score: float  # 0-1, higher = riskier
    approved: bool
    rejection_reason: Optional[str] = None


@dataclass
class TradeRiskAssessment:
    """Individual trade risk assessment"""

    symbol: str
    approved: bool
    risk_score: float
    position_size: float
    max_loss: float
    var_contribution: float
    portfolio_risk_after: float
    metadata: Dict
    rejection_reason: Optional[str] = None


class VaRCalculator:
    """
    Value at Risk Calculator
    Supports Historical, Parametric, and Monte Carlo methods
    """

    def __init__(self, confidence_level: float = 0.95):
        self.confidence_level = confidence_level

    def historical_var(
        self, returns: np.ndarray, position_value: float
    ) -> Tuple[float, float]:
        """
        Historical VaR using empirical distribution

        Args:
            returns: Array of historical returns
            position_value: Current position value

        Returns:
            (var_95, var_99)
        """
        if len(returns) < 30:
            # Insufficient data, use conservative estimate
            return position_value * 0.05, position_value * 0.10

        # Sort returns
        sorted_returns = np.sort(returns)

        # Calculate VaR at different confidence levels
        var_95_idx = int(len(sorted_returns) * 0.05)
        var_99_idx = int(len(sorted_returns) * 0.01)

        var_95 = abs(sorted_returns[var_95_idx] * position_value)
        var_99 = abs(sorted_returns[var_99_idx] * position_value)

        return var_95, var_99

    def parametric_var(
        self, returns: np.ndarray, position_value: float
    ) -> Tuple[float, float]:
        """
        Parametric VaR assuming normal distribution

        Args:
            returns: Array of historical returns
            position_value: Current position value

        Returns:
            (var_95, var_99)
        """
        if len(returns) < 30:
            return position_value * 0.05, position_value * 0.10

        # Calculate mean and std
        mean_return = np.mean(returns)
        std_return = np.std(returns)

        # Z-scores for confidence levels
        z_95 = stats.norm.ppf(0.05)  # -1.645
        z_99 = stats.norm.ppf(0.01)  # -2.326

        # Calculate VaR
        var_95 = abs((mean_return + z_95 * std_return) * position_value)
        var_99 = abs((mean_return + z_99 * std_return) * position_value)

        return var_95, var_99

    def monte_carlo_var(
        self,
        returns: np.ndarray,
        position_value: float,
        num_simulations: int = 10000,
    ) -> Tuple[float, float]:
        """
        Monte Carlo VaR simulation

        Args:
            returns: Array of historical returns
            position_value: Current position value
            num_simulations: Number of Monte Carlo simulations

        Returns:
            (var_95, var_99)
        """
        if len(returns) < 30:
            return position_value * 0.05, position_value * 0.10

        # Estimate parameters
        mean_return = np.mean(returns)
        std_return = np.std(returns)

        # Generate random scenarios
        simulated_returns = np.random.normal(
            mean_return, std_return, num_simulations
        )

        # Calculate potential losses
        simulated_values = simulated_returns * position_value

        # Calculate VaR
        var_95 = abs(np.percentile(simulated_values, 5))
        var_99 = abs(np.percentile(simulated_values, 1))

        return var_95, var_99

    def conditional_var(
        self, returns: np.ndarray, position_value: float
    ) -> float:
        """
        Conditional VaR (CVaR) / Expected Shortfall
        Average loss beyond VaR threshold

        Args:
            returns: Array of historical returns
            position_value: Current position value

        Returns:
            CVaR at 95% confidence
        """
        if len(returns) < 30:
            return position_value * 0.08

        sorted_returns = np.sort(returns)
        var_95_idx = int(len(sorted_returns) * 0.05)

        # Average of worst 5% scenarios
        worst_returns = sorted_returns[:var_95_idx]
        cvar = abs(np.mean(worst_returns) * position_value)

        return cvar


class PortfolioRiskAnalyzer:
    """
    Portfolio-level risk analysis
    """

    def __init__(
        self,
        max_portfolio_var: float = 0.10,  # Max 10% portfolio VaR
        max_position_risk: float = 0.05,  # Max 5% per position
        max_correlation_exposure: float = 0.30,  # Max 30% in correlated assets
    ):
        self.max_portfolio_var = max_portfolio_var
        self.max_position_risk = max_position_risk
        self.max_correlation_exposure = max_correlation_exposure

        self.var_calc = VaRCalculator()

    def calculate_portfolio_var(
        self,
        positions: List[Dict],
        returns_history: Dict[str, np.ndarray],
    ) -> float:
        """
        Calculate portfolio-level VaR

        Args:
            positions: List of position dicts
            returns_history: Historical returns per symbol

        Returns:
            Portfolio VaR percentage
        """
        if not positions:
            return 0.0

        total_value = sum(p["size_usd"] for p in positions)
        if total_value == 0:
            return 0.0

        # Calculate individual VaRs
        position_vars = []
        for pos in positions:
            symbol = pos["symbol"]
            returns = returns_history.get(symbol, np.array([]))

            if len(returns) > 0:
                var_95, _ = self.var_calc.parametric_var(
                    returns, pos["size_usd"]
                )
                position_vars.append(var_95)
            else:
                # Conservative estimate
                position_vars.append(pos["size_usd"] * 0.05)

        # Simple addition (conservative, assumes perfect correlation)
        # TODO: Add correlation matrix for more accurate calculation
        portfolio_var = sum(position_vars)
        portfolio_var_pct = portfolio_var / total_value

        return portfolio_var_pct

    def calculate_max_drawdown(self, equity_curve: np.ndarray) -> float:
        """
        Calculate maximum drawdown from equity curve

        Args:
            equity_curve: Array of portfolio values over time

        Returns:
            Max drawdown percentage
        """
        if len(equity_curve) < 2:
            return 0.0

        # Calculate running maximum
        running_max = np.maximum.accumulate(equity_curve)

        # Calculate drawdown at each point
        drawdown = (equity_curve - running_max) / running_max

        # Maximum drawdown
        max_dd = abs(np.min(drawdown))

        return max_dd

    def calculate_sharpe_ratio(
        self, returns: np.ndarray, risk_free_rate: float = 0.02
    ) -> float:
        """
        Calculate Sharpe ratio

        Args:
            returns: Array of returns
            risk_free_rate: Annual risk-free rate

        Returns:
            Sharpe ratio
        """
        if len(returns) < 2:
            return 0.0

        excess_returns = returns - (risk_free_rate / 252)  # Daily risk-free
        mean_excess = np.mean(excess_returns)
        std_excess = np.std(excess_returns)

        if std_excess == 0:
            return 0.0

        sharpe = mean_excess / std_excess * np.sqrt(252)  # Annualized

        return sharpe

    def calculate_sortino_ratio(
        self, returns: np.ndarray, risk_free_rate: float = 0.02
    ) -> float:
        """
        Calculate Sortino ratio (downside deviation only)

        Args:
            returns: Array of returns
            risk_free_rate: Annual risk-free rate

        Returns:
            Sortino ratio
        """
        if len(returns) < 2:
            return 0.0

        excess_returns = returns - (risk_free_rate / 252)
        mean_excess = np.mean(excess_returns)

        # Downside deviation (only negative returns)
        downside_returns = excess_returns[excess_returns < 0]
        if len(downside_returns) == 0:
            return float("inf")

        downside_std = np.std(downside_returns)

        if downside_std == 0:
            return 0.0

        sortino = mean_excess / downside_std * np.sqrt(252)

        return sortino

    def calculate_portfolio_heat(
        self,
        positions: List[Dict],
        account_balance: float,
    ) -> Dict[str, float]:
        """
        Calculate portfolio heat (total risk exposure)

        Portfolio heat = sum of all position risks (entry to stop-loss distance)

        Args:
            positions: List of open positions with entry_price, stop_loss, size
            account_balance: Current account balance in USDT

        Returns:
            Dict with:
                - total_heat_usd: Total $ at risk across all positions
                - total_heat_pct: Total risk as % of account balance
                - per_position_heat: List of individual position risks
                - max_heat_allowed: Maximum allowed heat (6% of balance)
                - heat_available: Remaining heat capacity
        """
        if not positions or account_balance <= 0:
            return {
                "total_heat_usd": 0.0,
                "total_heat_pct": 0.0,
                "per_position_heat": [],
                "max_heat_allowed": account_balance * 0.06,  # 6% max
                "heat_available": account_balance * 0.06,
            }

        per_position_heat = []
        total_heat_usd = 0.0

        for pos in positions:
            entry_price = pos.get("entry_price", 0)
            stop_loss = pos.get("stop_loss", 0)
            position_size_usd = pos.get("size_usd", 0)
            symbol = pos.get("symbol", "UNKNOWN")

            if entry_price > 0 and stop_loss > 0 and position_size_usd > 0:
                # Calculate risk percentage (distance from entry to SL)
                risk_pct = abs((stop_loss - entry_price) / entry_price)

                # Calculate dollar risk for this position
                position_heat_usd = position_size_usd * risk_pct

                per_position_heat.append({
                    "symbol": symbol,
                    "position_size_usd": position_size_usd,
                    "risk_pct": risk_pct,
                    "heat_usd": position_heat_usd,
                })

                total_heat_usd += position_heat_usd
            else:
                # Position without stop-loss - assume 5% risk (conservative)
                position_heat_usd = position_size_usd * 0.05
                per_position_heat.append({
                    "symbol": symbol,
                    "position_size_usd": position_size_usd,
                    "risk_pct": 0.05,
                    "heat_usd": position_heat_usd,
                    "warning": "No stop-loss set"
                })
                total_heat_usd += position_heat_usd

        total_heat_pct = (total_heat_usd / account_balance) if account_balance > 0 else 0.0
        max_heat_allowed = account_balance * 0.06  # 6% maximum portfolio heat
        heat_available = max(0, max_heat_allowed - total_heat_usd)

        return {
            "total_heat_usd": total_heat_usd,
            "total_heat_pct": total_heat_pct,
            "per_position_heat": per_position_heat,
            "max_heat_allowed": max_heat_allowed,
            "heat_available": heat_available,
            "within_limits": total_heat_usd <= max_heat_allowed,
        }


class TradeValidator:
    """
    Trade validation and approval logic
    """

    def __init__(
        self,
        max_portfolio_risk: float = 0.20,  # Max 20% portfolio at risk
        max_single_trade_risk: float = 0.05,  # Max 5% per trade
        min_reward_risk_ratio: float = 1.5,  # Min 1.5:1 R/R
        min_confidence: float = 0.6,  # Min 60% confidence
        max_correlation_risk: float = 0.30,  # Max 30% in correlated trades
    ):
        self.max_portfolio_risk = max_portfolio_risk
        self.max_single_trade_risk = max_single_trade_risk
        self.min_reward_risk_ratio = min_reward_risk_ratio
        self.min_confidence = min_confidence
        self.max_correlation_risk = max_correlation_risk

    def validate_trade(
        self,
        symbol: str,
        confidence: float,
        position_size: float,
        risk_amount: float,
        reward_risk_ratio: float,
        current_portfolio_risk: float,
        account_balance: float,
        existing_positions: List[Dict] = None,
    ) -> TradeRiskAssessment:
        """
        Validate if trade should be approved

        Args:
            symbol: Trading symbol
            confidence: Signal confidence
            position_size: Proposed position size
            risk_amount: Risk amount in USD
            reward_risk_ratio: Expected R/R ratio
            current_portfolio_risk: Current portfolio risk %
            account_balance: Account balance
            existing_positions: List of existing positions

        Returns:
            TradeRiskAssessment
        """
        rejections = []
        risk_score = 0.0

        # Check 1: Confidence threshold
        if confidence < self.min_confidence:
            rejections.append(
                f"Low confidence: {confidence:.1%} < {self.min_confidence:.1%}"
            )
            risk_score += 0.3

        # Check 2: Reward/Risk ratio
        if reward_risk_ratio < self.min_reward_risk_ratio:
            rejections.append(
                f"Poor R/R: {reward_risk_ratio:.2f} < {self.min_reward_risk_ratio:.2f}"
            )
            risk_score += 0.2

        # Check 3: Single trade risk
        trade_risk_pct = risk_amount / account_balance
        if trade_risk_pct > self.max_single_trade_risk:
            rejections.append(
                f"Excessive trade risk: {trade_risk_pct:.1%} > {self.max_single_trade_risk:.1%}"
            )
            risk_score += 0.3

        # Check 4: Portfolio risk
        new_portfolio_risk = current_portfolio_risk + trade_risk_pct
        if new_portfolio_risk > self.max_portfolio_risk:
            rejections.append(
                f"Portfolio risk limit: {new_portfolio_risk:.1%} > {self.max_portfolio_risk:.1%}"
            )
            risk_score += 0.4

        # Check 5: Correlation exposure
        if existing_positions:
            # Simple check: count positions in same asset class
            # TODO: Implement proper correlation analysis
            same_class_exposure = sum(
                p["size_usd"]
                for p in existing_positions
                if p["symbol"].split("/")[0]
                == symbol.split("/")[0]  # Same base currency
            )
            correlation_pct = same_class_exposure / account_balance

            if correlation_pct > self.max_correlation_risk:
                rejections.append(
                    f"High correlation exposure: {correlation_pct:.1%}"
                )
                risk_score += 0.2

        # Calculate final risk score (0-1)
        risk_score = min(1.0, risk_score)

        # Approve if no rejections
        approved = len(rejections) == 0
        rejection_reason = "; ".join(rejections) if rejections else None

        # VaR contribution (simple estimate)
        var_contribution = risk_amount * 1.65  # Assuming normal distribution

        return TradeRiskAssessment(
            symbol=symbol,
            approved=approved,
            risk_score=risk_score,
            position_size=position_size,
            max_loss=risk_amount,
            var_contribution=var_contribution,
            portfolio_risk_after=new_portfolio_risk,
            rejection_reason=rejection_reason,
            metadata={
                "confidence": confidence,
                "reward_risk_ratio": reward_risk_ratio,
                "trade_risk_pct": trade_risk_pct,
                "current_portfolio_risk": current_portfolio_risk,
                "new_portfolio_risk": new_portfolio_risk,
            },
        )
