"""
Signal Fusion Module
Combines signals from multiple agents using Bayesian averaging and weighted fusion.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import numpy as np
from core.logging.logger import get_logger

logger = get_logger(__name__)


class SignalType(str, Enum):
    """Signal types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class Signal:
    """Unified signal structure"""
    agent_type: str
    symbol: str
    signal: SignalType
    confidence: float
    timestamp: datetime
    reasoning: str
    metadata: Dict[str, Any]


class BayesianFusion:
    """
    Bayesian signal fusion using agent performance history.

    Calculates optimal weights based on:
    - Historical accuracy
    - Recent performance
    - Signal confidence
    """

    def __init__(self, history_window: int = 100):
        self.history_window = history_window
        self.agent_performance: Dict[str, List[float]] = {}

    def update_performance(self, agent_type: str, accuracy: float) -> None:
        """Update agent performance history"""
        if agent_type not in self.agent_performance:
            self.agent_performance[agent_type] = []

        self.agent_performance[agent_type].append(accuracy)

        # Keep only recent history
        if len(self.agent_performance[agent_type]) > self.history_window:
            self.agent_performance[agent_type].pop(0)

    def get_agent_weight(self, agent_type: str, base_confidence: float = 0.5) -> float:
        """
        Calculate agent weight based on historical performance.

        Returns weight between 0 and 1
        """
        if agent_type not in self.agent_performance:
            return base_confidence

        history = self.agent_performance[agent_type]
        if not history:
            return base_confidence

        # Recent performance is more important (exponential decay)
        weights = np.exp(np.linspace(-1, 0, len(history)))
        weights /= weights.sum()

        weighted_accuracy = np.average(history, weights=weights)
        return float(weighted_accuracy)

    def fuse_signals(self, signals: List[Signal]) -> Dict[str, Any]:
        """
        Fuse multiple signals using Bayesian averaging.

        Returns:
            {
                "signal": "BUY" | "SELL" | "HOLD",
                "confidence": float,
                "weights": Dict[str, float],
                "reasoning": List[str]
            }
        """
        if not signals:
            return {
                "signal": SignalType.HOLD,
                "confidence": 0.0,
                "weights": {},
                "reasoning": ["No signals available"],
            }

        # Calculate weights for each agent
        agent_weights = {}
        for sig in signals:
            base_weight = self.get_agent_weight(sig.agent_type)
            # Combine with signal confidence
            agent_weights[sig.agent_type] = base_weight * sig.confidence

        # Normalize weights
        total_weight = sum(agent_weights.values())
        if total_weight > 0:
            agent_weights = {k: v / total_weight for k, v in agent_weights.items()}

        # Calculate weighted vote
        buy_score = 0.0
        sell_score = 0.0

        for sig in signals:
            weight = agent_weights.get(sig.agent_type, 0.0)
            if sig.signal == SignalType.BUY:
                buy_score += weight
            elif sig.signal == SignalType.SELL:
                sell_score += weight

        # Determine final signal
        if buy_score > sell_score and buy_score > 0.3:
            final_signal = SignalType.BUY
            confidence = buy_score
        elif sell_score > buy_score and sell_score > 0.3:
            final_signal = SignalType.SELL
            confidence = sell_score
        else:
            final_signal = SignalType.HOLD
            confidence = max(buy_score, sell_score)

        # Collect reasoning
        reasoning = [
            f"{sig.agent_type}: {sig.signal.value} ({sig.confidence:.2%}) - {sig.reasoning}"
            for sig in signals
        ]

        logger.info(
            "signals_fused",
            signal=final_signal.value,
            confidence=confidence,
            buy_score=buy_score,
            sell_score=sell_score,
            num_signals=len(signals),
        )

        return {
            "signal": final_signal,
            "confidence": confidence,
            "buy_score": buy_score,
            "sell_score": sell_score,
            "weights": agent_weights,
            "reasoning": reasoning,
            "num_signals": len(signals),
        }


class ConsensusStrategy:
    """
    Simple consensus-based fusion.
    Requires majority agreement with minimum confidence threshold.
    """

    def __init__(self, min_confidence: float = 0.6, min_agreement: float = 0.6):
        self.min_confidence = min_confidence
        self.min_agreement = min_agreement

    def fuse_signals(self, signals: List[Signal]) -> Dict[str, Any]:
        """
        Fuse signals based on consensus.

        Requires:
        - Majority agreement (>60%)
        - Minimum confidence threshold
        """
        if not signals:
            return {
                "signal": SignalType.HOLD,
                "confidence": 0.0,
                "reasoning": ["No signals"],
            }

        # Filter high-confidence signals
        strong_signals = [s for s in signals if s.confidence >= self.min_confidence]

        if not strong_signals:
            return {
                "signal": SignalType.HOLD,
                "confidence": 0.0,
                "reasoning": ["No strong signals"],
            }

        # Count votes
        buy_count = sum(1 for s in strong_signals if s.signal == SignalType.BUY)
        sell_count = sum(1 for s in strong_signals if s.signal == SignalType.SELL)
        total = len(strong_signals)

        buy_agreement = buy_count / total
        sell_agreement = sell_count / total

        # Check for consensus
        if buy_agreement >= self.min_agreement:
            avg_confidence = np.mean([s.confidence for s in strong_signals if s.signal == SignalType.BUY])
            return {
                "signal": SignalType.BUY,
                "confidence": float(avg_confidence),
                "agreement": buy_agreement,
                "reasoning": [s.reasoning for s in strong_signals if s.signal == SignalType.BUY],
            }
        elif sell_agreement >= self.min_agreement:
            avg_confidence = np.mean([s.confidence for s in strong_signals if s.signal == SignalType.SELL])
            return {
                "signal": SignalType.SELL,
                "confidence": float(avg_confidence),
                "agreement": sell_agreement,
                "reasoning": [s.reasoning for s in strong_signals if s.signal == SignalType.SELL],
            }
        else:
            return {
                "signal": SignalType.HOLD,
                "confidence": 0.0,
                "agreement": 0.0,
                "reasoning": ["No consensus reached"],
            }


class TimeDecayFusion:
    """
    Time-weighted signal fusion.
    Recent signals have more weight.
    """

    def __init__(self, half_life_minutes: int = 30):
        self.half_life_minutes = half_life_minutes

    def calculate_time_weight(self, signal_time: datetime) -> float:
        """Calculate exponential decay weight based on signal age"""
        now = datetime.utcnow()
        age_minutes = (now - signal_time).total_seconds() / 60

        # Exponential decay: weight = 0.5^(age/half_life)
        weight = 0.5 ** (age_minutes / self.half_life_minutes)
        return weight

    def fuse_signals(self, signals: List[Signal]) -> Dict[str, Any]:
        """Fuse signals with time decay weighting"""
        if not signals:
            return {
                "signal": SignalType.HOLD,
                "confidence": 0.0,
                "reasoning": ["No signals"],
            }

        # Calculate time-weighted scores
        buy_score = 0.0
        sell_score = 0.0
        total_weight = 0.0

        for sig in signals:
            time_weight = self.calculate_time_weight(sig.timestamp)
            signal_weight = time_weight * sig.confidence

            total_weight += signal_weight

            if sig.signal == SignalType.BUY:
                buy_score += signal_weight
            elif sig.signal == SignalType.SELL:
                sell_score += signal_weight

        # Normalize
        if total_weight > 0:
            buy_score /= total_weight
            sell_score /= total_weight

        # Determine final signal
        if buy_score > sell_score and buy_score > 0.3:
            final_signal = SignalType.BUY
            confidence = buy_score
        elif sell_score > buy_score and sell_score > 0.3:
            final_signal = SignalType.SELL
            confidence = sell_score
        else:
            final_signal = SignalType.HOLD
            confidence = max(buy_score, sell_score)

        return {
            "signal": final_signal,
            "confidence": confidence,
            "buy_score": buy_score,
            "sell_score": sell_score,
            "reasoning": [s.reasoning for s in signals],
        }


class HybridFusion:
    """
    Hybrid fusion combining Bayesian, consensus, and time decay.
    """

    def __init__(self):
        self.bayesian = BayesianFusion()
        self.consensus = ConsensusStrategy()
        self.time_decay = TimeDecayFusion()

    def fuse_signals(self, signals: List[Signal]) -> Dict[str, Any]:
        """
        Multi-strategy fusion with voting.

        Uses all three strategies and combines results.
        """
        if not signals:
            return {
                "signal": SignalType.HOLD,
                "confidence": 0.0,
                "method": "none",
                "reasoning": ["No signals"],
            }

        # Get results from all strategies
        bayesian_result = self.bayesian.fuse_signals(signals)
        consensus_result = self.consensus.fuse_signals(signals)
        time_decay_result = self.time_decay.fuse_signals(signals)

        # Collect votes
        votes = [
            (bayesian_result["signal"], bayesian_result["confidence"]),
            (consensus_result["signal"], consensus_result["confidence"]),
            (time_decay_result["signal"], time_decay_result["confidence"]),
        ]

        # Majority vote with confidence weighting
        signal_scores = {SignalType.BUY: 0.0, SignalType.SELL: 0.0, SignalType.HOLD: 0.0}

        for signal, conf in votes:
            signal_scores[signal] += conf

        # Final signal is the one with highest score
        final_signal = max(signal_scores, key=signal_scores.get)
        final_confidence = signal_scores[final_signal] / 3  # Average

        logger.info(
            "hybrid_fusion_complete",
            final_signal=final_signal.value,
            final_confidence=final_confidence,
            bayesian=bayesian_result["signal"].value,
            consensus=consensus_result["signal"].value,
            time_decay=time_decay_result["signal"].value,
        )

        return {
            "signal": final_signal,
            "confidence": final_confidence,
            "method": "hybrid",
            "strategies": {
                "bayesian": bayesian_result,
                "consensus": consensus_result,
                "time_decay": time_decay_result,
            },
            "reasoning": bayesian_result["reasoning"],
        }
