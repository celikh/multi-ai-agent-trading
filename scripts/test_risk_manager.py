#!/usr/bin/env python3
"""
Test Risk Manager
Tests position sizing, risk assessment, and stop-loss placement.
"""

import sys
from pathlib import Path
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.risk_manager.position_sizing import (
    KellyCriterion,
    FixedFractional,
    VolatilityBased,
    PositionSizer,
)
from agents.risk_manager.risk_assessment import (
    VaRCalculator,
    PortfolioRiskAnalyzer,
    TradeValidator,
)
from agents.risk_manager.stop_loss_placement import (
    ATRStopLoss,
    PercentageStopLoss,
    VolatilityStopLoss,
    SupportResistanceStopLoss,
    TrailingStopLoss,
    StopLossManager,
    StopLossMethod,
)


def test_kelly_criterion():
    """Test Kelly Criterion position sizing"""
    print("\n" + "=" * 60)
    print("📊 TESTING KELLY CRITERION")
    print("=" * 60)

    kelly = KellyCriterion(max_kelly_fraction=0.25, min_kelly_fraction=0.01)

    # Test case 1: High win probability, good R/R
    kelly_frac_1 = kelly.calculate(
        win_probability=0.65, reward_risk_ratio=2.0, account_balance=10000
    )

    print(f"\n✅ Test 1: Win prob 65%, R/R 2:1")
    print(f"  Kelly fraction: {kelly_frac_1:.1%}")
    print(f"  Position size: ${10000 * kelly_frac_1:,.2f}")

    # Test case 2: Low win probability
    kelly_frac_2 = kelly.calculate(
        win_probability=0.45, reward_risk_ratio=2.0, account_balance=10000
    )

    print(f"\n⚠️  Test 2: Win prob 45%, R/R 2:1")
    print(f"  Kelly fraction: {kelly_frac_2:.1%}")
    print(f"  Position size: ${10000 * kelly_frac_2:,.2f}")

    # Test case 3: Excellent setup
    kelly_frac_3 = kelly.calculate(
        win_probability=0.70, reward_risk_ratio=3.0, account_balance=10000
    )

    print(f"\n🚀 Test 3: Win prob 70%, R/R 3:1")
    print(f"  Kelly fraction: {kelly_frac_3:.1%}")
    print(f"  Position size: ${10000 * kelly_frac_3:,.2f}")

    assert 0.01 <= kelly_frac_1 <= 0.25, "Kelly fraction out of range"
    assert kelly_frac_2 >= 0.01, "Kelly fraction below minimum"
    print("\n✅ Kelly Criterion tests passed")


def test_position_sizer():
    """Test comprehensive position sizing"""
    print("\n" + "=" * 60)
    print("💰 TESTING POSITION SIZER")
    print("=" * 60)

    sizer = PositionSizer(
        account_balance=10000, max_position_pct=0.10, default_method="hybrid"
    )

    # Test with high confidence trade
    position = sizer.calculate_position_size(
        symbol="BTC/USDT",
        current_price=50000,
        confidence=0.80,
        stop_loss=48000,  # 4% stop
        take_profit=54000,  # 8% target, 2:1 R/R
        atr=1000,
        method="hybrid",
    )

    print(f"\n📈 High Confidence Trade:")
    print(f"  Symbol: BTC/USDT @ ${position.metadata['confidence'] * 100:.0f}% confidence")
    print(f"  Quantity: {position.quantity:.4f} BTC")
    print(f"  Position Size: ${position.size_usd:,.2f}")
    print(f"  Risk Amount: ${position.risk_amount:,.2f}")
    print(f"  Kelly Fraction: {position.kelly_fraction:.1%}")
    print(f"  Method: {position.method}")
    print(f"  Reasoning: {position.reasoning}")

    # Test with low confidence trade
    position_low = sizer.calculate_position_size(
        symbol="ETH/USDT",
        current_price=3000,
        confidence=0.55,
        stop_loss=2850,  # 5% stop
        take_profit=3300,
        method="fixed",
    )

    print(f"\n⚠️  Low Confidence Trade:")
    print(f"  Symbol: ETH/USDT @ {position_low.metadata['confidence'] * 100:.0f}% confidence")
    print(f"  Position Size: ${position_low.size_usd:,.2f}")
    print(f"  Risk Amount: ${position_low.risk_amount:,.2f}")
    print(f"  Method: {position_low.method}")

    assert position.size_usd > 0, "Position size should be positive"
    assert position.size_usd <= 1000, "Position size exceeds max (10%)"
    print("\n✅ Position Sizer tests passed")


def test_var_calculation():
    """Test VaR calculations"""
    print("\n" + "=" * 60)
    print("📉 TESTING VaR CALCULATION")
    print("=" * 60)

    var_calc = VaRCalculator(confidence_level=0.95)

    # Generate sample returns (normally distributed)
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, 100)  # Mean 0.1%, Std 2%

    position_value = 5000

    # Historical VaR
    var_95_hist, var_99_hist = var_calc.historical_var(returns, position_value)

    print(f"\n📊 Historical VaR:")
    print(f"  Position Value: ${position_value:,.2f}")
    print(f"  VaR 95%: ${var_95_hist:,.2f}")
    print(f"  VaR 99%: ${var_99_hist:,.2f}")

    # Parametric VaR
    var_95_param, var_99_param = var_calc.parametric_var(
        returns, position_value
    )

    print(f"\n📐 Parametric VaR:")
    print(f"  VaR 95%: ${var_95_param:,.2f}")
    print(f"  VaR 99%: ${var_99_param:,.2f}")

    # Monte Carlo VaR
    var_95_mc, var_99_mc = var_calc.monte_carlo_var(
        returns, position_value, num_simulations=1000
    )

    print(f"\n🎲 Monte Carlo VaR:")
    print(f"  VaR 95%: ${var_95_mc:,.2f}")
    print(f"  VaR 99%: ${var_99_mc:,.2f}")

    # CVaR
    cvar = var_calc.conditional_var(returns, position_value)

    print(f"\n⚠️  Conditional VaR (Expected Shortfall):")
    print(f"  CVaR 95%: ${cvar:,.2f}")

    assert var_95_hist > 0, "VaR should be positive"
    assert var_99_hist > var_95_hist, "VaR 99% should be higher than 95%"
    print("\n✅ VaR calculation tests passed")


def test_stop_loss_placement():
    """Test stop-loss placement methods"""
    print("\n" + "=" * 60)
    print("🛡️  TESTING STOP-LOSS PLACEMENT")
    print("=" * 60)

    manager = StopLossManager(
        default_method=StopLossMethod.ATR, default_rr_ratio=2.0
    )

    current_price = 50000
    atr = 1000

    # ATR-based stops
    stops_atr = manager.calculate_stops(
        symbol="BTC/USDT",
        current_price=current_price,
        side="BUY",
        method=StopLossMethod.ATR,
        atr=atr,
    )

    print(f"\n📏 ATR-Based Stops (BUY):")
    print(f"  Current Price: ${current_price:,.2f}")
    print(f"  ATR: ${atr:,.2f}")
    print(f"  Stop Loss: ${stops_atr.stop_loss:,.2f} ({stops_atr.stop_loss_pct:.1%})")
    print(f"  Take Profit: ${stops_atr.take_profit:,.2f} ({stops_atr.take_profit_pct:.1%})")
    print(f"  R/R Ratio: {stops_atr.reward_risk_ratio:.2f}:1")
    print(f"  Method: {stops_atr.method}")

    # Percentage-based stops
    stops_pct = manager.calculate_stops(
        symbol="ETH/USDT",
        current_price=3000,
        side="SELL",
        method=StopLossMethod.PERCENTAGE,
    )

    print(f"\n📊 Percentage-Based Stops (SELL):")
    print(f"  Current Price: $3,000")
    print(f"  Stop Loss: ${stops_pct.stop_loss:,.2f}")
    print(f"  Take Profit: ${stops_pct.take_profit:,.2f}")

    # Volatility-based stops
    stops_vol = manager.calculate_stops(
        symbol="SOL/USDT",
        current_price=100,
        side="BUY",
        method=StopLossMethod.VOLATILITY,
        price_std=5,
    )

    print(f"\n📈 Volatility-Based Stops (BUY):")
    print(f"  Current Price: $100")
    print(f"  Price Std: $5")
    print(f"  Stop Loss: ${stops_vol.stop_loss:,.2f}")
    print(f"  Take Profit: ${stops_vol.take_profit:,.2f}")

    assert stops_atr.stop_loss < current_price, "Stop should be below entry for BUY"
    assert stops_pct.stop_loss > 3000, "Stop should be above entry for SELL"
    print("\n✅ Stop-loss placement tests passed")


def test_trade_validator():
    """Test trade validation logic"""
    print("\n" + "=" * 60)
    print("✅ TESTING TRADE VALIDATOR")
    print("=" * 60)

    validator = TradeValidator(
        max_portfolio_risk=0.20,
        max_single_trade_risk=0.05,
        min_reward_risk_ratio=1.5,
        min_confidence=0.6,
    )

    account_balance = 10000

    # Test 1: Good trade
    assessment_good = validator.validate_trade(
        symbol="BTC/USDT",
        confidence=0.75,
        position_size=500,
        risk_amount=100,  # 1% risk
        reward_risk_ratio=2.5,
        current_portfolio_risk=0.05,
        account_balance=account_balance,
    )

    print(f"\n✅ Good Trade Assessment:")
    print(f"  Approved: {assessment_good.approved}")
    print(f"  Risk Score: {assessment_good.risk_score:.2f}")
    print(f"  Position Size: ${assessment_good.position_size:,.2f}")
    print(f"  Max Loss: ${assessment_good.max_loss:,.2f}")
    print(f"  Portfolio Risk After: {assessment_good.portfolio_risk_after:.1%}")

    # Test 2: Low confidence trade
    assessment_low_conf = validator.validate_trade(
        symbol="ETH/USDT",
        confidence=0.50,  # Below threshold
        position_size=500,
        risk_amount=100,
        reward_risk_ratio=2.0,
        current_portfolio_risk=0.05,
        account_balance=account_balance,
    )

    print(f"\n⚠️  Low Confidence Trade:")
    print(f"  Approved: {assessment_low_conf.approved}")
    print(f"  Risk Score: {assessment_low_conf.risk_score:.2f}")
    print(f"  Rejection Reason: {assessment_low_conf.rejection_reason}")

    # Test 3: Excessive risk
    assessment_high_risk = validator.validate_trade(
        symbol="SOL/USDT",
        confidence=0.70,
        position_size=1000,
        risk_amount=800,  # 8% risk - too high!
        reward_risk_ratio=1.8,
        current_portfolio_risk=0.05,
        account_balance=account_balance,
    )

    print(f"\n❌ Excessive Risk Trade:")
    print(f"  Approved: {assessment_high_risk.approved}")
    print(f"  Risk Score: {assessment_high_risk.risk_score:.2f}")
    print(f"  Rejection Reason: {assessment_high_risk.rejection_reason}")

    assert assessment_good.approved == True, "Good trade should be approved"
    assert (
        assessment_low_conf.approved == False
    ), "Low confidence should be rejected"
    assert (
        assessment_high_risk.approved == False
    ), "High risk should be rejected"
    print("\n✅ Trade Validator tests passed")


def test_portfolio_risk_analyzer():
    """Test portfolio risk analysis"""
    print("\n" + "=" * 60)
    print("📊 TESTING PORTFOLIO RISK ANALYZER")
    print("=" * 60)

    analyzer = PortfolioRiskAnalyzer(
        max_portfolio_var=0.10, max_position_risk=0.05
    )

    # Sample positions
    positions = [
        {"symbol": "BTC/USDT", "size_usd": 5000},
        {"symbol": "ETH/USDT", "size_usd": 3000},
        {"symbol": "SOL/USDT", "size_usd": 2000},
    ]

    # Sample returns history
    np.random.seed(42)
    returns_history = {
        "BTC/USDT": np.random.normal(0.001, 0.02, 100),
        "ETH/USDT": np.random.normal(0.0005, 0.025, 100),
        "SOL/USDT": np.random.normal(0.002, 0.03, 100),
    }

    # Calculate portfolio VaR
    portfolio_var = analyzer.calculate_portfolio_var(
        positions, returns_history
    )

    print(f"\n📈 Portfolio Analysis:")
    print(f"  Total Positions: {len(positions)}")
    print(f"  Total Value: ${sum(p['size_usd'] for p in positions):,.2f}")
    print(f"  Portfolio VaR: {portfolio_var:.1%}")

    # Test max drawdown
    equity_curve = np.array([10000, 10500, 10200, 11000, 10800, 11500, 11200])
    max_dd = analyzer.calculate_max_drawdown(equity_curve)

    print(f"\n📉 Max Drawdown Analysis:")
    print(f"  Starting Equity: ${equity_curve[0]:,.2f}")
    print(f"  Peak Equity: ${np.max(equity_curve):,.2f}")
    print(f"  Max Drawdown: {max_dd:.1%}")

    # Test Sharpe ratio
    sharpe = analyzer.calculate_sharpe_ratio(
        returns_history["BTC/USDT"], risk_free_rate=0.02
    )

    print(f"\n📊 Risk-Adjusted Returns:")
    print(f"  Sharpe Ratio: {sharpe:.2f}")

    # Test Sortino ratio
    sortino = analyzer.calculate_sortino_ratio(
        returns_history["BTC/USDT"], risk_free_rate=0.02
    )

    print(f"  Sortino Ratio: {sortino:.2f}")

    assert portfolio_var > 0, "Portfolio VaR should be positive"
    assert max_dd >= 0, "Max drawdown should be non-negative"
    print("\n✅ Portfolio Risk Analyzer tests passed")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🧪 RISK MANAGER - COMPREHENSIVE TESTS")
    print("=" * 60)

    try:
        test_kelly_criterion()
        test_position_sizer()
        test_var_calculation()
        test_stop_loss_placement()
        test_trade_validator()
        test_portfolio_risk_analyzer()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\n📋 Summary:")
        print("  • Kelly Criterion: Optimal position sizing ✅")
        print("  • Position Sizer: Hybrid sizing methods ✅")
        print("  • VaR Calculation: Historical, Parametric, Monte Carlo ✅")
        print("  • Stop-Loss Placement: ATR, Percentage, Volatility ✅")
        print("  • Trade Validator: Risk-based approval ✅")
        print("  • Portfolio Analyzer: VaR, Drawdown, Sharpe/Sortino ✅")
        print("\n💡 Next Steps:")
        print("  1. Start Infrastructure: docker-compose up -d")
        print("  2. Start Data Collection: python agents/data_collection/agent.py")
        print("  3. Start Technical Analysis: python agents/technical_analysis/agent.py")
        print("  4. Start Strategy Agent: python agents/strategy/agent.py")
        print("  5. Start Risk Manager: python agents/risk_manager/agent.py")
        print()

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
