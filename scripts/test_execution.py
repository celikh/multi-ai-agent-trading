#!/usr/bin/env python3
"""
Test Execution Agent
Tests order execution, slippage calculation, and position management.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agents.execution.execution_quality import (
    SlippageCalculator,
    ExecutionCostAnalyzer,
    ExecutionReporter,
    ExecutionBenchmark,
)
from agents.execution.position_manager import PositionManager, PositionSide


def test_slippage_calculation():
    """Test slippage calculation"""
    print("\n" + "=" * 60)
    print("📉 TESTING SLIPPAGE CALCULATION")
    print("=" * 60)

    calc = SlippageCalculator()

    # Test 1: BUY with positive slippage (paid more)
    slippage_buy = calc.calculate_slippage(
        expected_price=50000,
        actual_price=50100,  # Paid $100 more
        quantity=0.1,
        side="buy",
    )

    print(f"\n📊 BUY Order Slippage:")
    print(f"  Expected: $50,000")
    print(f"  Actual: $50,100")
    print(f"  Slippage: ${slippage_buy.slippage_amount:,.2f}")
    print(f"  Slippage %: {slippage_buy.slippage_percentage:.2f}%")
    print(f"  Slippage BPS: {slippage_buy.slippage_bps:.0f}")
    print(f"  Cost Impact: ${slippage_buy.cost_impact:,.2f}")
    print(f"  Quality: {slippage_buy.quality_rating.value}")
    print(f"  Favorable: {slippage_buy.is_favorable}")

    # Test 2: SELL with negative slippage (got less)
    slippage_sell = calc.calculate_slippage(
        expected_price=3000,
        actual_price=2985,  # Got $15 less
        quantity=1.0,
        side="sell",
    )

    print(f"\n📊 SELL Order Slippage:")
    print(f"  Expected: $3,000")
    print(f"  Actual: $2,985")
    print(f"  Slippage: ${slippage_sell.slippage_amount:,.2f}")
    print(f"  Slippage %: {slippage_sell.slippage_percentage:.2f}%")
    print(f"  Quality: {slippage_sell.quality_rating.value}")

    # Test 3: Price improvement (negative slippage)
    price_improvement = calc.calculate_price_improvement(
        expected_price=50000, actual_price=49950, side="buy"
    )

    print(f"\n✅ Price Improvement:")
    print(f"  Improvement: ${price_improvement:,.2f}")
    print(f"  Got better price than expected!")

    assert slippage_buy.slippage_amount > 0, "BUY slippage should be positive"
    assert slippage_sell.slippage_amount > 0, "SELL slippage should be positive"
    print("\n✅ Slippage calculation tests passed")


def test_execution_cost():
    """Test execution cost analysis"""
    print("\n" + "=" * 60)
    print("💰 TESTING EXECUTION COST ANALYSIS")
    print("=" * 60)

    analyzer = ExecutionCostAnalyzer()

    # BUY order cost
    cost = analyzer.calculate_execution_cost(
        symbol="BTC/USDT",
        quantity=0.1,
        average_price=50100,
        expected_price=50000,
        exchange_fees=25.05,  # 0.05% of $5,010
        side="buy",
    )

    print(f"\n💵 Execution Cost Breakdown:")
    print(f"  Symbol: {cost.symbol}")
    print(f"  Quantity: {cost.quantity} BTC")
    print(f"  Gross Cost: ${cost.gross_cost:,.2f}")
    print(f"  Slippage Cost: ${cost.slippage_cost:,.2f}")
    print(f"  Exchange Fees: ${cost.exchange_fees:,.2f}")
    print(f"  Total Cost: ${cost.total_cost:,.2f}")
    print(f"  Cost per Unit: ${cost.cost_per_unit:,.2f}")
    print(f"  Cost %: {cost.cost_percentage:.2f}%")

    assert cost.gross_cost > 0, "Gross cost should be positive"
    assert cost.total_cost >= cost.gross_cost, "Total cost should include fees"
    print("\n✅ Execution cost tests passed")


def test_execution_report():
    """Test execution report generation"""
    print("\n" + "=" * 60)
    print("📊 TESTING EXECUTION REPORT")
    print("=" * 60)

    reporter = ExecutionReporter()

    execution_start = datetime.utcnow()
    execution_end = execution_start + timedelta(seconds=2)

    report = reporter.generate_report(
        order_id="test_order_123",
        symbol="BTC/USDT",
        side="buy",
        quantity=0.1,
        expected_price=50000,
        average_fill_price=50050,
        fills=[
            {"quantity": 0.05, "price": 50040},
            {"quantity": 0.05, "price": 50060},
        ],
        exchange_fees=25.03,
        execution_start=execution_start,
        execution_end=execution_end,
    )

    print(f"\n📈 Execution Report:")
    print(f"  Order ID: {report.order_id}")
    print(f"  Symbol: {report.symbol}")
    print(f"  Side: {report.side}")
    print(f"  Quantity: {report.quantity}")
    print(f"  Expected Price: ${report.expected_price:,.2f}")
    print(f"  Average Fill: ${report.average_fill_price:,.2f}")
    print(f"\n  Slippage:")
    print(f"    Amount: ${report.slippage.slippage_amount:,.2f}")
    print(f"    Percentage: {report.slippage.slippage_percentage:.2f}%")
    print(f"    Quality: {report.slippage.quality_rating.value}")
    print(f"\n  Costs:")
    print(f"    Gross: ${report.costs.gross_cost:,.2f}")
    print(f"    Fees: ${report.costs.exchange_fees:,.2f}")
    print(f"    Total: ${report.costs.total_cost:,.2f}")
    print(f"\n  Performance:")
    print(f"    Execution Time: {report.execution_time_ms:.0f}ms")
    print(f"    Quality Score: {report.quality_score}/100")

    assert report.quality_score > 0, "Quality score should be positive"
    assert report.quality_score <= 100, "Quality score should be <= 100"
    print("\n✅ Execution report tests passed")


def test_position_management():
    """Test position manager"""
    print("\n" + "=" * 60)
    print("📍 TESTING POSITION MANAGEMENT")
    print("=" * 60)

    manager = PositionManager()

    # Open long position
    position = manager.open_position(
        symbol="BTC/USDT",
        side="long",
        quantity=0.1,
        entry_price=50000,
        stop_loss=48000,
        take_profit=54000,
    )

    print(f"\n🟢 Position Opened:")
    print(f"  ID: {position.position_id}")
    print(f"  Symbol: {position.symbol}")
    print(f"  Side: {position.side.value}")
    print(f"  Quantity: {position.quantity}")
    print(f"  Entry: ${position.entry_price:,.2f}")
    print(f"  Stop Loss: ${position.stop_loss:,.2f}")
    print(f"  Take Profit: ${position.take_profit:,.2f}")

    # Update price (profit)
    updated = manager.update_position_price(
        position.position_id, 52000
    )

    print(f"\n📈 Price Update (Profit):")
    print(f"  Current Price: ${updated.current_price:,.2f}")
    print(f"  Unrealized P&L: ${updated.unrealized_pnl:,.2f}")
    print(f"  P&L %: {updated.unrealized_pnl_pct:.2f}%")

    # Check take profit
    hit_tp, tp_price = manager.check_take_profit(position.position_id)
    print(f"\n  Take Profit Check: {'✅ HIT' if hit_tp else '❌ Not hit'}")

    # Partial close
    partial = manager.decrease_position(
        position.position_id, 0.05, 52000
    )

    print(f"\n🔻 Partial Close:")
    print(f"  Closed Quantity: 0.05")
    print(f"  Remaining: {partial.quantity}")
    print(f"  Realized P&L: ${partial.realized_pnl:,.2f}")
    print(f"  Unrealized P&L: ${partial.unrealized_pnl:,.2f}")

    # Full close
    closed = manager.close_position(position.position_id, 53000)

    print(f"\n🔴 Position Closed:")
    print(f"  Exit Price: ${closed.current_price:,.2f}")
    print(f"  Total Realized P&L: ${closed.realized_pnl:,.2f}")
    print(f"  Status: {closed.status.value}")

    # Performance stats
    stats = manager.get_performance_stats()

    print(f"\n📊 Performance Stats:")
    print(f"  Total Trades: {stats['total_trades']}")
    print(f"  Winning Trades: {stats['winning_trades']}")
    print(f"  Win Rate: {stats['win_rate']:.1f}%")
    print(f"  Total P&L: ${stats['total_pnl']:,.2f}")

    assert closed.status.value == "closed", "Position should be closed"
    assert closed.realized_pnl > 0, "Should have profit"
    print("\n✅ Position management tests passed")


def test_execution_benchmark():
    """Test execution benchmarking"""
    print("\n" + "=" * 60)
    print("📈 TESTING EXECUTION BENCHMARK")
    print("=" * 60)

    benchmark = ExecutionBenchmark()
    reporter = ExecutionReporter()

    # Add sample executions
    for i in range(5):
        execution_start = datetime.utcnow()
        execution_end = execution_start + timedelta(seconds=1 + i * 0.5)

        report = reporter.generate_report(
            order_id=f"order_{i}",
            symbol="BTC/USDT",
            side="buy",
            quantity=0.1,
            expected_price=50000,
            average_fill_price=50000 + (i * 10),  # Increasing slippage
            fills=[],
            exchange_fees=25.0,
            execution_start=execution_start,
            execution_end=execution_end,
        )

        benchmark.add_execution(report)

    # Get statistics
    avg_slippage = benchmark.get_average_slippage("BTC/USDT")
    avg_cost = benchmark.get_average_cost("BTC/USDT")
    avg_quality = benchmark.get_average_quality_score("BTC/USDT")

    print(f"\n📊 Benchmark Statistics (5 executions):")
    print(f"  Average Slippage: {avg_slippage:.2f}%")
    print(f"  Average Cost: {avg_cost:.2f}%")
    print(f"  Average Quality Score: {avg_quality:.1f}/100")

    # Summary
    summary = benchmark.get_execution_summary("BTC/USDT")

    print(f"\n📋 Execution Summary:")
    print(f"  Total Executions: {summary['total_executions']}")
    print(f"  Total Volume: ${summary['total_volume']:,.2f}")
    print(f"  Total Fees: ${summary['total_fees']:,.2f}")
    print(f"  Favorable Slippage Rate: {summary['favorable_slippage_rate']:.1f}%")

    assert summary["total_executions"] == 5, "Should have 5 executions"
    print("\n✅ Execution benchmark tests passed")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🧪 EXECUTION AGENT - COMPREHENSIVE TESTS")
    print("=" * 60)

    try:
        test_slippage_calculation()
        test_execution_cost()
        test_execution_report()
        test_position_management()
        test_execution_benchmark()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\n📋 Summary:")
        print("  • Slippage Calculation: BUY/SELL scenarios ✅")
        print("  • Execution Cost: Full breakdown analysis ✅")
        print("  • Execution Report: Quality scoring ✅")
        print("  • Position Management: Open/Update/Close ✅")
        print("  • Execution Benchmark: Performance tracking ✅")
        print("\n💡 Next Steps:")
        print("  1. Full System: Start all 5 agents")
        print("  2. Monitor: Check execution reports in PostgreSQL")
        print("  3. Track: Position P&L in real-time")
        print()

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
