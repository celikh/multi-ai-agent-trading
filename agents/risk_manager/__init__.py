"""
Risk Manager Agent Module
Position sizing, risk assessment, and trade validation.
"""

from agents.risk_manager.agent import RiskManagerAgent
from agents.risk_manager.position_sizing import (
    PositionSizer,
    KellyCriterion,
    FixedFractional,
    VolatilityBased,
    PositionSize,
)
from agents.risk_manager.risk_assessment import (
    VaRCalculator,
    PortfolioRiskAnalyzer,
    TradeValidator,
    RiskMetrics,
    TradeRiskAssessment,
)
from agents.risk_manager.stop_loss_placement import (
    StopLossManager,
    ATRStopLoss,
    PercentageStopLoss,
    VolatilityStopLoss,
    SupportResistanceStopLoss,
    TrailingStopLoss,
    StopLossMethod,
    StopLossLevels,
)

__all__ = [
    "RiskManagerAgent",
    "PositionSizer",
    "KellyCriterion",
    "FixedFractional",
    "VolatilityBased",
    "PositionSize",
    "VaRCalculator",
    "PortfolioRiskAnalyzer",
    "TradeValidator",
    "RiskMetrics",
    "TradeRiskAssessment",
    "StopLossManager",
    "ATRStopLoss",
    "PercentageStopLoss",
    "VolatilityStopLoss",
    "SupportResistanceStopLoss",
    "TrailingStopLoss",
    "StopLossMethod",
    "StopLossLevels",
]
