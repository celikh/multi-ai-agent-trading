# Execution Agent

**Emir Gerçekleştirme Ajanı** - Order execution, position management, ve execution reporting

## 📋 İçindekiler

- [Genel Bakış](#genel-bakış)
- [Mimari](#mimari)
- [Order Execution](#order-execution)
- [Slippage & Costs](#slippage--costs)
- [Position Management](#position-management)
- [Kullanım](#kullanım)
- [Test](#test)

## Genel Bakış

Execution Agent, Risk Manager'dan onaylanan emirleri alır, exchange'e gönderir ve execution kalitesini izler. Slippage calculation, position management ve comprehensive reporting yapar.

### Temel Özellikler

- **📤 Order Placement**: Market, Limit, Stop-Loss, Take-Profit
- **📊 Execution Quality**: Slippage, cost, speed scoring
- **💰 Position Management**: P&L tracking, partial fills
- **📈 Performance Tracking**: Execution benchmarking
- **🔄 Real-time Updates**: WebSocket order monitoring

### Mesaj Akışı

```
Risk Manager → [trade.order] → Execution Agent → Exchange
                                        ↓
                                [execution.report]
                                [position.update]
```

## Mimari

### Bileşenler

```
Execution Agent
│
├── Order Executor
│   ├── Market Orders
│   ├── Limit Orders
│   ├── Stop-Loss Orders
│   └── Take-Profit Orders
│
├── Execution Quality
│   ├── Slippage Calculator
│   ├── Cost Analyzer
│   ├── Quality Reporter
│   └── Benchmark Tracker
│
└── Position Manager
    ├── Position Open/Close
    ├── P&L Calculation
    ├── Stop/TP Monitoring
    └── Performance Stats
```

## Order Execution

### Market Orders

```python
from agents.execution import OrderExecutor

executor = OrderExecutor(
    exchange_id="binance",
    testnet=True,
)

execution = await executor.place_market_order(
    symbol="BTC/USDT",
    side="buy",
    quantity=0.1,
)

print(f"Order ID: {execution.order_id}")
print(f"Status: {execution.status}")
print(f"Avg Price: ${execution.average_fill_price:,.2f}")
```

### Stop-Loss & Take-Profit

```python
# Place stop-loss
stop_exec = await executor.place_stop_loss_order(
    symbol="BTC/USDT",
    side="sell",
    quantity=0.1,
    stop_price=48000,  # Stop at $48K
)

# Place take-profit
tp_exec = await executor.place_take_profit_order(
    symbol="BTC/USDT",
    side="sell",
    quantity=0.1,
    take_profit_price=54000,  # TP at $54K
)
```

## Slippage & Costs

### Slippage Calculation

```python
from agents.execution import SlippageCalculator

calc = SlippageCalculator()

slippage = calc.calculate_slippage(
    expected_price=50000,
    actual_price=50100,  # Paid $100 more
    quantity=0.1,
    side="buy",
)

print(f"Slippage: {slippage.slippage_percentage:.2f}%")
print(f"Cost Impact: ${slippage.cost_impact:,.2f}")
print(f"Quality: {slippage.quality_rating.value}")
# Output: excellent (<0.1%), good (0.1-0.3%), acceptable, poor
```

### Execution Cost Analysis

```python
from agents.execution import ExecutionCostAnalyzer

analyzer = ExecutionCostAnalyzer()

cost = analyzer.calculate_execution_cost(
    symbol="BTC/USDT",
    quantity=0.1,
    average_price=50100,
    expected_price=50000,
    exchange_fees=25.05,
    side="buy",
)

print(f"Gross Cost: ${cost.gross_cost:,.2f}")
print(f"Slippage Cost: ${cost.slippage_cost:,.2f}")
print(f"Fees: ${cost.exchange_fees:,.2f}")
print(f"Total: ${cost.total_cost:,.2f}")
print(f"Cost %: {cost.cost_percentage:.2f}%")
```

### Quality Scoring

Execution quality score (0-100):
- **Slippage (50%)**: Lower is better
- **Cost (30%)**: Lower is better
- **Speed (20%)**: Faster is better

| Score | Rating | Criteria |
|-------|--------|----------|
| 90-100 | Excellent | < 0.1% slippage, < 1s execution |
| 70-89 | Good | 0.1-0.3% slippage, < 5s execution |
| 50-69 | Acceptable | 0.3-0.5% slippage, < 10s |
| < 50 | Poor | > 0.5% slippage or > 10s |

## Position Management

### Open Position

```python
from agents.execution import PositionManager

manager = PositionManager()

position = manager.open_position(
    symbol="BTC/USDT",
    side="long",
    quantity=0.1,
    entry_price=50000,
    stop_loss=48000,
    take_profit=54000,
)

print(f"Position ID: {position.position_id}")
print(f"Entry: ${position.entry_price:,.2f}")
```

### Update & Track P&L

```python
# Update with current price
updated = manager.update_position_price(
    position.position_id,
    current_price=52000,
)

print(f"Unrealized P&L: ${updated.unrealized_pnl:,.2f}")
print(f"P&L %: {updated.unrealized_pnl_pct:.2f}%")

# Check stop/take profit
hit_stop, stop_price = manager.check_stop_loss(position.position_id)
hit_tp, tp_price = manager.check_take_profit(position.position_id)
```

### Close Position

```python
# Partial close
partial = manager.decrease_position(
    position.position_id,
    reduce_quantity=0.05,
    price=52000,
)

# Full close
closed = manager.close_position(
    position.position_id,
    exit_price=53000,
)

print(f"Realized P&L: ${closed.realized_pnl:,.2f}")
```

### Performance Stats

```python
stats = manager.get_performance_stats()

print(f"Total Trades: {stats['total_trades']}")
print(f"Win Rate: {stats['win_rate']:.1f}%")
print(f"Avg Win: ${stats['average_win']:,.2f}")
print(f"Avg Loss: ${stats['average_loss']:,.2f}")
print(f"Profit Factor: {stats['profit_factor']:.2f}")
```

## Kullanım

### Standalone Agent

```bash
python agents/execution/agent.py
```

### Configuration

```python
from agents.execution import ExecutionAgent

agent = ExecutionAgent(
    name="execution_agent_main",
    exchange_id="binance",
    testnet=True,
    max_slippage_pct=1.0,  # Max 1% slippage
)

await agent.initialize()
await agent.start()
```

### Full System (5 Agents)

```bash
# Terminal 1: Infrastructure
docker-compose up -d postgresql rabbitmq influxdb

# Terminal 2-6: Agents
python agents/data_collection/agent.py
python agents/technical_analysis/agent.py
python agents/strategy/agent.py
python agents/risk_manager/agent.py
python agents/execution/agent.py  # ← NEW!
```

## Test

### Run Tests

```bash
python scripts/test_execution.py
```

**Test Coverage**:
- ✅ Slippage calculation (BUY/SELL)
- ✅ Execution cost analysis
- ✅ Quality scoring
- ✅ Position management
- ✅ Execution benchmarking

**Expected Output**:
```
============================================================
✅ ALL TESTS COMPLETED SUCCESSFULLY
============================================================

📋 Summary:
  • Slippage Calculation: BUY/SELL scenarios ✅
  • Execution Cost: Full breakdown analysis ✅
  • Execution Report: Quality scoring ✅
  • Position Management: Open/Update/Close ✅
  • Execution Benchmark: Performance tracking ✅
```

## Monitoring

### PostgreSQL Queries

```sql
-- Recent executions
SELECT
    symbol,
    side,
    quantity,
    price,
    fee,
    status,
    metadata->>'slippage_pct' as slippage,
    metadata->>'quality_score' as quality,
    execution_time
FROM trades
ORDER BY execution_time DESC
LIMIT 20;

-- Execution statistics
SELECT
    symbol,
    COUNT(*) as total_trades,
    AVG((metadata->>'slippage_pct')::float) as avg_slippage,
    AVG((metadata->>'quality_score')::float) as avg_quality,
    SUM(fee) as total_fees
FROM trades
WHERE execution_time > NOW() - INTERVAL '24 hours'
GROUP BY symbol;

-- Best/worst executions
SELECT
    order_id,
    symbol,
    metadata->>'slippage_pct' as slippage,
    metadata->>'quality_score' as quality
FROM trades
WHERE execution_time > NOW() - INTERVAL '7 days'
ORDER BY (metadata->>'quality_score')::float DESC
LIMIT 10;
```

## Best Practices

### 1. Slippage Management
- Set max slippage limits (1% recommended)
- Use limit orders for large positions
- Monitor market depth before orders
- Avoid illiquid trading hours

### 2. Order Types
- **Market**: Fast execution, variable price
- **Limit**: Price control, may not fill
- **Stop-Loss**: Risk management, must place
- **Take-Profit**: Profit protection, recommended

### 3. Position Sizing
- Follow Risk Manager recommendations
- Use fractional positions for testing
- Monitor total exposure
- Track correlation risk

### 4. Performance Tracking
- Benchmark all executions
- Analyze slippage patterns
- Track fee costs
- Monitor quality scores

## Troubleshooting

**Problem**: High slippage
- **Solution**: Use limit orders, check liquidity, avoid volatile periods

**Problem**: Orders not filling
- **Solution**: Adjust limit price, use market orders, check exchange status

**Problem**: Position tracking errors
- **Solution**: Verify fills in database, check position reconciliation

**Problem**: Exchange connection errors
- **Solution**: Check API keys, verify exchange status, review rate limits

## References

- [Order Executor](order_executor.py)
- [Execution Quality](execution_quality.py)
- [Position Manager](position_manager.py)
- [Main Agent](agent.py)
- [Test Suite](../../scripts/test_execution.py)
