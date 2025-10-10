#!/usr/bin/env python3
"""
Test Strategy Agent
Tests signal fusion and decision making capabilities.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.strategy.signal_fusion import (
    BayesianFusion,
    ConsensusStrategy,
    TimeDecayFusion,
    HybridFusion,
    Signal,
    SignalType,
)


def test_bayesian_fusion():
    """Test Bayesian fusion strategy"""
    print("\n" + "=" * 60)
    print("🧮 TESTING BAYESIAN FUSION")
    print("=" * 60)

    fusion = BayesianFusion(history_window=100)

    # Simulate agent performance history
    fusion.update_performance("technical_analysis", 0.75)
    fusion.update_performance("technical_analysis", 0.80)
    fusion.update_performance("technical_analysis", 0.78)
    fusion.update_performance("sentiment_analysis", 0.60)
    fusion.update_performance("sentiment_analysis", 0.65)

    # Create test signals
    signals = [
        Signal(
            agent_type="technical_analysis",
            symbol="BTC/USDT",
            signal=SignalType.BUY,
            confidence=0.85,
            timestamp=datetime.utcnow(),
            reasoning="RSI oversold + MACD bullish crossover",
            metadata={"rsi": 28, "macd_signal": "bullish"},
        ),
        Signal(
            agent_type="sentiment_analysis",
            symbol="BTC/USDT",
            signal=SignalType.BUY,
            confidence=0.70,
            timestamp=datetime.utcnow(),
            reasoning="Positive social sentiment spike",
            metadata={"sentiment_score": 0.75},
        ),
        Signal(
            agent_type="fundamental_analysis",
            symbol="BTC/USDT",
            signal=SignalType.HOLD,
            confidence=0.60,
            timestamp=datetime.utcnow(),
            reasoning="Mixed on-chain metrics",
            metadata={"active_addresses": "increasing"},
        ),
    ]

    # Fuse signals
    result = fusion.fuse_signals(signals)

    print(f"\n📊 Result:")
    print(f"  Signal: {result['signal'].value}")
    print(f"  Confidence: {result['confidence']:.2%}")
    print(f"  Buy Score: {result['buy_score']:.2%}")
    print(f"  Sell Score: {result['sell_score']:.2%}")
    print(f"\n🏋️ Agent Weights:")
    for agent, weight in result["weights"].items():
        print(f"  {agent}: {weight:.2%}")
    print(f"\n💭 Reasoning:")
    for reason in result["reasoning"]:
        print(f"  • {reason}")


def test_consensus_fusion():
    """Test consensus fusion strategy"""
    print("\n" + "=" * 60)
    print("🤝 TESTING CONSENSUS FUSION")
    print("=" * 60)

    fusion = ConsensusStrategy(min_confidence=0.6, min_agreement=0.6)

    # Create test signals - strong consensus
    signals_consensus = [
        Signal(
            agent_type="technical_analysis",
            symbol="ETH/USDT",
            signal=SignalType.SELL,
            confidence=0.80,
            timestamp=datetime.utcnow(),
            reasoning="Overbought RSI + resistance level",
            metadata={},
        ),
        Signal(
            agent_type="sentiment_analysis",
            symbol="ETH/USDT",
            signal=SignalType.SELL,
            confidence=0.75,
            timestamp=datetime.utcnow(),
            reasoning="Negative news sentiment",
            metadata={},
        ),
        Signal(
            agent_type="fundamental_analysis",
            symbol="ETH/USDT",
            signal=SignalType.SELL,
            confidence=0.70,
            timestamp=datetime.utcnow(),
            reasoning="Decreasing network activity",
            metadata={},
        ),
    ]

    result_consensus = fusion.fuse_signals(signals_consensus)

    print(f"\n📊 Strong Consensus Result:")
    print(f"  Signal: {result_consensus['signal'].value}")
    print(f"  Confidence: {result_consensus['confidence']:.2%}")
    print(f"  Agreement: {result_consensus.get('agreement', 0):.2%}")

    # Create test signals - no consensus
    signals_no_consensus = [
        Signal(
            agent_type="technical_analysis",
            symbol="SOL/USDT",
            signal=SignalType.BUY,
            confidence=0.70,
            timestamp=datetime.utcnow(),
            reasoning="Bullish pattern",
            metadata={},
        ),
        Signal(
            agent_type="sentiment_analysis",
            symbol="SOL/USDT",
            signal=SignalType.SELL,
            confidence=0.65,
            timestamp=datetime.utcnow(),
            reasoning="Mixed sentiment",
            metadata={},
        ),
    ]

    result_no_consensus = fusion.fuse_signals(signals_no_consensus)

    print(f"\n📊 No Consensus Result:")
    print(f"  Signal: {result_no_consensus['signal'].value}")
    print(f"  Reasoning: {result_no_consensus['reasoning'][0]}")


def test_time_decay_fusion():
    """Test time decay fusion strategy"""
    print("\n" + "=" * 60)
    print("⏰ TESTING TIME DECAY FUSION")
    print("=" * 60)

    fusion = TimeDecayFusion(half_life_minutes=30)

    now = datetime.utcnow()

    # Create signals with different ages
    signals = [
        Signal(
            agent_type="technical_analysis",
            symbol="BTC/USDT",
            signal=SignalType.BUY,
            confidence=0.80,
            timestamp=now - timedelta(minutes=5),  # Recent
            reasoning="Fresh bullish signal",
            metadata={},
        ),
        Signal(
            agent_type="sentiment_analysis",
            symbol="BTC/USDT",
            signal=SignalType.BUY,
            confidence=0.75,
            timestamp=now - timedelta(minutes=45),  # Old
            reasoning="Old bullish signal",
            metadata={},
        ),
        Signal(
            agent_type="fundamental_analysis",
            symbol="BTC/USDT",
            signal=SignalType.SELL,
            confidence=0.70,
            timestamp=now - timedelta(minutes=60),  # Very old
            reasoning="Very old bearish signal",
            metadata={},
        ),
    ]

    result = fusion.fuse_signals(signals)

    print(f"\n📊 Time-Weighted Result:")
    print(f"  Signal: {result['signal'].value}")
    print(f"  Confidence: {result['confidence']:.2%}")
    print(f"  Buy Score: {result['buy_score']:.2%}")
    print(f"  Sell Score: {result['sell_score']:.2%}")
    print(f"\n⏱️ Signal Ages:")
    for sig in signals:
        age = (now - sig.timestamp).total_seconds() / 60
        weight = fusion.calculate_time_weight(sig.timestamp)
        print(f"  {sig.agent_type}: {age:.1f}min old, weight={weight:.2%}")


def test_hybrid_fusion():
    """Test hybrid fusion strategy"""
    print("\n" + "=" * 60)
    print("🔀 TESTING HYBRID FUSION")
    print("=" * 60)

    fusion = HybridFusion()

    # Update Bayesian history
    fusion.bayesian.update_performance("technical_analysis", 0.80)
    fusion.bayesian.update_performance("sentiment_analysis", 0.65)

    # Create test signals
    signals = [
        Signal(
            agent_type="technical_analysis",
            symbol="BTC/USDT",
            signal=SignalType.BUY,
            confidence=0.85,
            timestamp=datetime.utcnow() - timedelta(minutes=10),
            reasoning="Strong technical buy signal",
            metadata={},
        ),
        Signal(
            agent_type="sentiment_analysis",
            symbol="BTC/USDT",
            signal=SignalType.BUY,
            confidence=0.70,
            timestamp=datetime.utcnow() - timedelta(minutes=5),
            reasoning="Positive sentiment",
            metadata={},
        ),
        Signal(
            agent_type="fundamental_analysis",
            symbol="BTC/USDT",
            signal=SignalType.HOLD,
            confidence=0.60,
            timestamp=datetime.utcnow(),
            reasoning="Neutral fundamentals",
            metadata={},
        ),
    ]

    result = fusion.fuse_signals(signals)

    print(f"\n📊 Hybrid Fusion Result:")
    print(f"  Final Signal: {result['signal'].value}")
    print(f"  Final Confidence: {result['confidence']:.2%}")
    print(f"  Method: {result['method']}")

    print(f"\n🔍 Individual Strategy Results:")
    strategies = result["strategies"]
    print(f"  Bayesian: {strategies['bayesian']['signal'].value} ({strategies['bayesian']['confidence']:.2%})")
    print(f"  Consensus: {strategies['consensus']['signal'].value} ({strategies['consensus']['confidence']:.2%})")
    print(f"  TimeDecay: {strategies['time_decay']['signal'].value} ({strategies['time_decay']['confidence']:.2%})")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🧪 STRATEGY AGENT - SIGNAL FUSION TESTS")
    print("=" * 60)

    try:
        test_bayesian_fusion()
        test_consensus_fusion()
        test_time_decay_fusion()
        test_hybrid_fusion()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\n📋 Summary:")
        print("  • Bayesian Fusion: Weights signals by agent performance")
        print("  • Consensus Fusion: Requires majority agreement")
        print("  • Time Decay Fusion: Recent signals weighted more")
        print("  • Hybrid Fusion: Combines all three strategies")
        print("\n💡 Next Steps:")
        print("  1. Start RabbitMQ: docker-compose up -d rabbitmq")
        print("  2. Start Data Collection: python agents/data_collection/agent.py")
        print("  3. Start Technical Analysis: python agents/technical_analysis/agent.py")
        print("  4. Start Strategy Agent: python agents/strategy/agent.py")
        print()

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
