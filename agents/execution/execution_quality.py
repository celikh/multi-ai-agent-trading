"""
Execution Quality Module
Slippage calculation, execution cost analysis, and performance tracking.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import numpy as np


class ExecutionQuality(str, Enum):
    """Execution quality ratings"""

    EXCELLENT = "excellent"  # < 0.1% slippage
    GOOD = "good"  # 0.1-0.3% slippage
    ACCEPTABLE = "acceptable"  # 0.3-0.5% slippage
    POOR = "poor"  # 0.5-1.0% slippage
    VERY_POOR = "very_poor"  # > 1.0% slippage


@dataclass
class SlippageAnalysis:
    """Slippage analysis result"""

    symbol: str
    expected_price: float
    actual_price: float
    slippage_amount: float
    slippage_percentage: float
    slippage_bps: float  # Basis points (1 bp = 0.01%)
    cost_impact: float  # Dollar cost of slippage
    quality_rating: ExecutionQuality
    is_favorable: bool  # True if got better price than expected


@dataclass
class ExecutionCost:
    """Total execution cost breakdown"""

    symbol: str
    quantity: float
    gross_cost: float  # Quantity × Price
    slippage_cost: float
    exchange_fees: float
    total_cost: float
    cost_per_unit: float
    cost_percentage: float  # % of gross cost


@dataclass
class ExecutionReport:
    """Comprehensive execution report"""

    order_id: str
    symbol: str
    side: str
    quantity: float
    expected_price: float
    average_fill_price: float
    slippage: SlippageAnalysis
    costs: ExecutionCost
    fills: List[Dict]
    execution_time_ms: float
    timestamp: datetime
    quality_score: float  # 0-100


class SlippageCalculator:
    """
    Calculate and analyze slippage
    """

    def calculate_slippage(
        self,
        expected_price: float,
        actual_price: float,
        quantity: float,
        side: str,
    ) -> SlippageAnalysis:
        """
        Calculate slippage for an execution

        Args:
            expected_price: Price at order decision time
            actual_price: Average fill price
            quantity: Order quantity
            side: "buy" or "sell"

        Returns:
            SlippageAnalysis
        """
        # Calculate slippage amount
        slippage_amount = actual_price - expected_price

        # For sells, negative slippage is bad (got less than expected)
        # For buys, positive slippage is bad (paid more than expected)
        if side.lower() == "sell":
            slippage_amount = -slippage_amount

        # Calculate slippage percentage
        slippage_pct = (slippage_amount / expected_price) * 100

        # Calculate basis points (1 bp = 0.01%)
        slippage_bps = slippage_pct * 100

        # Calculate dollar cost impact
        cost_impact = abs(slippage_amount * quantity)

        # Determine if slippage was favorable (negative slippage)
        is_favorable = slippage_amount < 0

        # Rate execution quality
        abs_slippage_pct = abs(slippage_pct)
        if abs_slippage_pct < 0.1:
            quality = ExecutionQuality.EXCELLENT
        elif abs_slippage_pct < 0.3:
            quality = ExecutionQuality.GOOD
        elif abs_slippage_pct < 0.5:
            quality = ExecutionQuality.ACCEPTABLE
        elif abs_slippage_pct < 1.0:
            quality = ExecutionQuality.POOR
        else:
            quality = ExecutionQuality.VERY_POOR

        return SlippageAnalysis(
            symbol="",  # To be filled by caller
            expected_price=expected_price,
            actual_price=actual_price,
            slippage_amount=slippage_amount,
            slippage_percentage=slippage_pct,
            slippage_bps=slippage_bps,
            cost_impact=cost_impact,
            quality_rating=quality,
            is_favorable=is_favorable,
        )

    def calculate_price_improvement(
        self, expected_price: float, actual_price: float, side: str
    ) -> float:
        """
        Calculate price improvement (negative slippage)

        Returns:
            Positive value if got better price, negative if worse
        """
        if side.lower() == "buy":
            # Better price = lower price for buy
            return expected_price - actual_price
        else:
            # Better price = higher price for sell
            return actual_price - expected_price


class ExecutionCostAnalyzer:
    """
    Analyze total execution costs
    """

    def calculate_execution_cost(
        self,
        symbol: str,
        quantity: float,
        average_price: float,
        expected_price: float,
        exchange_fees: float,
        side: str,
    ) -> ExecutionCost:
        """
        Calculate total execution cost breakdown

        Args:
            symbol: Trading pair
            quantity: Executed quantity
            average_price: Average fill price
            expected_price: Expected price at decision
            exchange_fees: Exchange trading fees
            side: "buy" or "sell"

        Returns:
            ExecutionCost
        """
        # Gross cost
        gross_cost = quantity * average_price

        # Slippage cost
        slippage_amount = average_price - expected_price
        if side.lower() == "sell":
            slippage_amount = -slippage_amount

        slippage_cost = slippage_amount * quantity

        # Total cost
        total_cost = gross_cost + exchange_fees + abs(slippage_cost)

        # Cost per unit
        cost_per_unit = total_cost / quantity if quantity > 0 else 0

        # Cost as percentage of gross
        cost_pct = (
            ((exchange_fees + abs(slippage_cost)) / gross_cost) * 100
            if gross_cost > 0
            else 0
        )

        return ExecutionCost(
            symbol=symbol,
            quantity=quantity,
            gross_cost=gross_cost,
            slippage_cost=slippage_cost,
            exchange_fees=exchange_fees,
            total_cost=total_cost,
            cost_per_unit=cost_per_unit,
            cost_percentage=cost_pct,
        )


class ExecutionReporter:
    """
    Generate execution reports and quality metrics
    """

    def __init__(self):
        self.slippage_calc = SlippageCalculator()
        self.cost_analyzer = ExecutionCostAnalyzer()

    def generate_report(
        self,
        order_id: str,
        symbol: str,
        side: str,
        quantity: float,
        expected_price: float,
        average_fill_price: float,
        fills: List[Dict],
        exchange_fees: float,
        execution_start: datetime,
        execution_end: datetime,
    ) -> ExecutionReport:
        """
        Generate comprehensive execution report

        Args:
            order_id: Order ID
            symbol: Trading pair
            side: "buy" or "sell"
            quantity: Total quantity
            expected_price: Expected price at decision
            average_fill_price: Actual average fill price
            fills: List of individual fills
            exchange_fees: Total exchange fees
            execution_start: Order creation time
            execution_end: Final fill time

        Returns:
            ExecutionReport
        """
        # Calculate slippage
        slippage = self.slippage_calc.calculate_slippage(
            expected_price, average_fill_price, quantity, side
        )
        slippage.symbol = symbol

        # Calculate execution costs
        costs = self.cost_analyzer.calculate_execution_cost(
            symbol,
            quantity,
            average_fill_price,
            expected_price,
            exchange_fees,
            side,
        )

        # Calculate execution time
        execution_time_ms = (
            execution_end - execution_start
        ).total_seconds() * 1000

        # Calculate quality score (0-100)
        quality_score = self._calculate_quality_score(
            slippage, costs, execution_time_ms
        )

        return ExecutionReport(
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            expected_price=expected_price,
            average_fill_price=average_fill_price,
            slippage=slippage,
            costs=costs,
            fills=fills,
            execution_time_ms=execution_time_ms,
            timestamp=execution_end,
            quality_score=quality_score,
        )

    def _calculate_quality_score(
        self,
        slippage: SlippageAnalysis,
        costs: ExecutionCost,
        execution_time_ms: float,
    ) -> float:
        """
        Calculate overall execution quality score (0-100)

        Factors:
        - Slippage (50%): Lower is better
        - Cost (30%): Lower is better
        - Speed (20%): Faster is better
        """
        # Slippage score (0-100, higher is better)
        abs_slippage_pct = abs(slippage.slippage_percentage)
        if abs_slippage_pct < 0.1:
            slippage_score = 100
        elif abs_slippage_pct < 0.3:
            slippage_score = 80
        elif abs_slippage_pct < 0.5:
            slippage_score = 60
        elif abs_slippage_pct < 1.0:
            slippage_score = 40
        else:
            slippage_score = max(0, 20 - (abs_slippage_pct - 1.0) * 10)

        # Cost score (0-100, lower cost % is better)
        cost_pct = costs.cost_percentage
        if cost_pct < 0.1:
            cost_score = 100
        elif cost_pct < 0.3:
            cost_score = 80
        elif cost_pct < 0.5:
            cost_score = 60
        else:
            cost_score = max(0, 40 - (cost_pct - 0.5) * 20)

        # Speed score (0-100, faster is better)
        # < 1s = 100, < 5s = 80, < 10s = 60, < 30s = 40, > 30s = 20
        if execution_time_ms < 1000:
            speed_score = 100
        elif execution_time_ms < 5000:
            speed_score = 80
        elif execution_time_ms < 10000:
            speed_score = 60
        elif execution_time_ms < 30000:
            speed_score = 40
        else:
            speed_score = 20

        # Weighted average
        quality_score = (
            slippage_score * 0.5 + cost_score * 0.3 + speed_score * 0.2
        )

        return round(quality_score, 1)


class ExecutionBenchmark:
    """
    Track and benchmark execution performance over time
    """

    def __init__(self):
        self.executions: List[ExecutionReport] = []

    def add_execution(self, report: ExecutionReport):
        """Add execution to benchmark history"""
        self.executions.append(report)

    def get_average_slippage(self, symbol: Optional[str] = None) -> float:
        """Calculate average slippage percentage"""
        reports = self._filter_by_symbol(symbol)
        if not reports:
            return 0.0

        slippages = [r.slippage.slippage_percentage for r in reports]
        return np.mean(slippages)

    def get_average_cost(self, symbol: Optional[str] = None) -> float:
        """Calculate average execution cost percentage"""
        reports = self._filter_by_symbol(symbol)
        if not reports:
            return 0.0

        costs = [r.costs.cost_percentage for r in reports]
        return np.mean(costs)

    def get_average_quality_score(
        self, symbol: Optional[str] = None
    ) -> float:
        """Calculate average execution quality score"""
        reports = self._filter_by_symbol(symbol)
        if not reports:
            return 0.0

        scores = [r.quality_score for r in reports]
        return np.mean(scores)

    def get_fill_rate(self, symbol: Optional[str] = None) -> float:
        """Calculate percentage of fully filled orders"""
        reports = self._filter_by_symbol(symbol)
        if not reports:
            return 0.0

        # Assuming all in history are filled (we only add completed orders)
        return 100.0

    def get_execution_summary(
        self, symbol: Optional[str] = None
    ) -> Dict:
        """Get comprehensive execution statistics"""
        reports = self._filter_by_symbol(symbol)

        if not reports:
            return {
                "total_executions": 0,
                "average_slippage_pct": 0.0,
                "average_cost_pct": 0.0,
                "average_quality_score": 0.0,
                "total_volume": 0.0,
                "total_fees": 0.0,
            }

        return {
            "total_executions": len(reports),
            "average_slippage_pct": self.get_average_slippage(symbol),
            "average_cost_pct": self.get_average_cost(symbol),
            "average_quality_score": self.get_average_quality_score(symbol),
            "total_volume": sum(r.costs.gross_cost for r in reports),
            "total_fees": sum(r.costs.exchange_fees for r in reports),
            "favorable_slippage_rate": sum(
                1 for r in reports if r.slippage.is_favorable
            )
            / len(reports)
            * 100,
        }

    def _filter_by_symbol(
        self, symbol: Optional[str]
    ) -> List[ExecutionReport]:
        """Filter executions by symbol"""
        if symbol:
            return [e for e in self.executions if e.symbol == symbol]
        return self.executions
