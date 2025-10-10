#!/usr/bin/env python3
"""
Test script for Technical Analysis Agent
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.technical_analysis.indicators import TechnicalIndicators, SignalGenerator
import pandas as pd
import numpy as np


def test_indicators():
    """Test indicator calculations with sample data"""
    print("🧪 Testing Technical Indicators...")
    print("=" * 60)

    # Create sample OHLCV data
    np.random.seed(42)
    dates = pd.date_range(start="2024-01-01", periods=100, freq="1min")

    # Simulate realistic price movement
    base_price = 50000
    returns = np.random.normal(0, 0.001, 100)
    prices = base_price * (1 + returns).cumprod()

    df = pd.DataFrame({
        "timestamp": dates,
        "open": prices + np.random.normal(0, 10, 100),
        "high": prices + np.abs(np.random.normal(20, 10, 100)),
        "low": prices - np.abs(np.random.normal(20, 10, 100)),
        "close": prices,
        "volume": np.random.uniform(100, 1000, 100),
    })

    # Calculate indicators
    indicators = TechnicalIndicators()
    all_indicators = indicators.calculate_all_indicators(df)
    latest = indicators.get_latest_values(all_indicators)

    print("\n📊 Latest Indicator Values:")
    print("-" * 60)
    for key, value in latest.items():
        if value is not None:
            print(f"  {key:20s}: {value:12.4f}")
        else:
            print(f"  {key:20s}: {'N/A':>12s}")

    return df, latest


def test_signal_generation(df, latest_indicators):
    """Test signal generation"""
    print("\n🎯 Testing Signal Generation...")
    print("=" * 60)

    signal_gen = SignalGenerator()
    current_price = df["close"].iloc[-1]

    # Test RSI
    if latest_indicators.get("rsi"):
        rsi_signal = signal_gen.analyze_rsi(latest_indicators["rsi"])
        print(f"\n📈 RSI Signal:")
        print(f"  Signal: {rsi_signal['signal']}")
        print(f"  Strength: {rsi_signal['strength']:.2f}")
        print(f"  Reason: {rsi_signal['reason']}")

    # Test MACD
    if all(latest_indicators.get(k) for k in ["macd", "macd_signal", "macd_hist"]):
        macd_signal = signal_gen.analyze_macd(
            latest_indicators["macd"],
            latest_indicators["macd_signal"],
            latest_indicators["macd_hist"],
        )
        print(f"\n📊 MACD Signal:")
        print(f"  Signal: {macd_signal['signal']}")
        print(f"  Strength: {macd_signal['strength']:.2f}")
        print(f"  Reason: {macd_signal['reason']}")

    # Test Bollinger Bands
    if all(latest_indicators.get(k) for k in ["bb_upper", "bb_lower", "bb_middle"]):
        bb_signal = signal_gen.analyze_bollinger_bands(
            current_price,
            latest_indicators["bb_upper"],
            latest_indicators["bb_lower"],
            latest_indicators["bb_middle"],
        )
        print(f"\n📉 Bollinger Bands Signal:")
        print(f"  Signal: {bb_signal['signal']}")
        print(f"  Strength: {bb_signal['strength']:.2f}")
        print(f"  Reason: {bb_signal['reason']}")

    # Test Moving Averages
    if all(latest_indicators.get(k) for k in ["sma_20", "sma_50", "ema_20"]):
        ma_signal = signal_gen.analyze_moving_averages(
            current_price,
            latest_indicators["sma_20"],
            latest_indicators["sma_50"],
            latest_indicators["ema_20"],
        )
        print(f"\n📐 Moving Average Signal:")
        print(f"  Signal: {ma_signal['signal']}")
        print(f"  Strength: {ma_signal['strength']:.2f}")
        print(f"  Reason: {ma_signal['reason']}")

    # Combine all signals
    all_signals = []
    if latest_indicators.get("rsi"):
        all_signals.append(signal_gen.analyze_rsi(latest_indicators["rsi"]))
    if all(latest_indicators.get(k) for k in ["macd", "macd_signal", "macd_hist"]):
        all_signals.append(signal_gen.analyze_macd(
            latest_indicators["macd"],
            latest_indicators["macd_signal"],
            latest_indicators["macd_hist"],
        ))
    if all(latest_indicators.get(k) for k in ["bb_upper", "bb_lower", "bb_middle"]):
        all_signals.append(signal_gen.analyze_bollinger_bands(
            current_price,
            latest_indicators["bb_upper"],
            latest_indicators["bb_lower"],
            latest_indicators["bb_middle"],
        ))

    combined = signal_gen.combine_signals(all_signals)

    print(f"\n🎯 Combined Signal:")
    print("=" * 60)
    print(f"  Final Signal: {combined['signal']}")
    print(f"  Confidence: {combined['confidence']:.2%}")
    print(f"  Buy Strength: {combined['buy_strength']:.2f}")
    print(f"  Sell Strength: {combined['sell_strength']:.2f}")
    print(f"\n  Reasoning:")
    for reason in combined['reasoning']:
        print(f"    • {reason}")


def main():
    """Run tests"""
    print("\n🚀 Technical Analysis Agent - Test Suite")
    print("=" * 60)

    try:
        # Test indicators
        df, latest_indicators = test_indicators()

        # Test signal generation
        test_signal_generation(df, latest_indicators)

        print("\n" + "=" * 60)
        print("✅ All tests completed successfully!")
        print("=" * 60)

    except ImportError as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 To fix this:")
        print("   1. Install TA-Lib: brew install ta-lib (macOS)")
        print("   2. Install Python package: pip install TA-Lib")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
