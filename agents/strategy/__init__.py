"""
Strategy Agent Module
Signal fusion and trading decision making.
"""

from agents.strategy.agent import StrategyAgent
from agents.strategy.signal_fusion import (
    BayesianFusion,
    ConsensusStrategy,
    TimeDecayFusion,
    HybridFusion,
    Signal,
    SignalType,
)

__all__ = [
    "StrategyAgent",
    "BayesianFusion",
    "ConsensusStrategy",
    "TimeDecayFusion",
    "HybridFusion",
    "Signal",
    "SignalType",
]
