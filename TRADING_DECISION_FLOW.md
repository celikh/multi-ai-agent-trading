# Trading Decision Flow - Step by Step Process

## Complete Trading Workflow

This document explains exactly how a trading decision is made from start to finish.

## Example Scenario: BTC/USDT Buy Signal

Let's follow a real example of how the system decides to buy BTC/USDT.

### Step 1: Market Data Collection (Agent 1)

**Time**: 2025-10-10 12:00:00 UTC

```python
# Data Collection Agent receives WebSocket message from Binance
{
  "symbol": "BTC/USDT",
  "price": 121617.0,
  "volume": 1234.56,
  "timestamp": "2025-10-10T12:00:00Z",
  "bid": 121615.0,
  "ask": 121620.0,
  "high_24h": 122500.0,
  "low_24h": 119800.0
}

# Agent actions:
1. Store in InfluxDB for historical analysis
2. Publish to RabbitMQ topic "market.data.BTC/USDT"
3. Update real-time cache
```

**Output**: Market data available for analysis

---

### Step 2: Technical Analysis (Agent 2)

**Time**: 2025-10-10 12:00:05 UTC (5 seconds later)

Technical Analysis Agent receives market data and fetches historical candles:

```python
# Fetch last 200 candles for indicator calculation
candles = await influxdb.fetch_candles("BTC/USDT", "1h", limit=200)

# Calculate indicators using TA-Lib
import talib

# 1. RSI (Relative Strength Index)
rsi = talib.RSI(candles['close'], timeperiod=14)
current_rsi = rsi[-1]  # 28.5

# 2. MACD (Moving Average Convergence Divergence)
macd, signal, hist = talib.MACD(
    candles['close'],
    fastperiod=12,
    slowperiod=26,
    signalperiod=9
)
current_macd = macd[-1]        # 450.0
current_signal = signal[-1]    # 420.0
current_hist = hist[-1]        # 30.0 (bullish)

# 3. Bollinger Bands
upper, middle, lower = talib.BBANDS(
    candles['close'],
    timeperiod=20,
    nbdevup=2,
    nbdevdn=2
)
current_upper = upper[-1]   # 123000.0
current_middle = middle[-1] # 121000.0
current_lower = lower[-1]   # 119000.0
current_price = 121617.0

# 4. Volume
avg_volume = candles['volume'].rolling(20).mean().iloc[-1]
current_volume = candles['volume'].iloc[-1]
volume_ratio = current_volume / avg_volume  # 1.5 (high volume)
```

**Indicator Analysis**:

| Indicator | Value | Signal | Confidence |
|-----------|-------|--------|-----------|
| RSI | 28.5 | **BUY** (oversold < 30) | 0.85 |
| MACD | 450 > 420 | **BUY** (bullish cross) | 0.75 |
| Bollinger Bands | Price near lower (119k) | **BUY** | 0.70 |
| Volume | 1.5x average | **STRONG** | 0.80 |
| SMA 50 | Price above | **BUY** | 0.60 |

```python
# Generate signals
signals = []

# Signal 1: RSI oversold
if current_rsi < 30:
    signals.append({
        "indicator": "RSI",
        "action": "BUY",
        "confidence": 0.85,
        "reason": f"RSI {current_rsi:.1f} < 30 (oversold)"
    })

# Signal 2: MACD bullish crossover
if current_macd > current_signal and current_hist > 0:
    signals.append({
        "indicator": "MACD",
        "action": "BUY",
        "confidence": 0.75,
        "reason": "MACD bullish crossover"
    })

# Signal 3: Bollinger Bands
price_position = (current_price - current_lower) / (current_upper - current_lower)
if price_position < 0.3:  # Near lower band
    signals.append({
        "indicator": "BB",
        "action": "BUY",
        "confidence": 0.70,
        "reason": "Price near lower Bollinger Band"
    })

# Signal 4: Volume confirmation
if volume_ratio > 1.3:
    signals.append({
        "indicator": "VOLUME",
        "action": "BUY",
        "confidence": 0.80,
        "reason": f"High volume: {volume_ratio:.1f}x average"
    })

# Publish each signal to RabbitMQ
for signal in signals:
    await publish_message(f"signals.{signal['indicator']}", {
        "symbol": "BTC/USDT",
        "action": signal['action'],
        "confidence": signal['confidence'],
        "indicator": signal['indicator'],
        "reason": signal['reason'],
        "timestamp": "2025-10-10T12:00:05Z"
    })
```

**Output**: 4 BUY signals published to message bus

---

### Step 3: Signal Buffering (Agent 3 - Strategy)

**Time**: 2025-10-10 12:00:06 UTC

Strategy Agent collects signals over 5-minute window:

```python
# Signal buffer for BTC/USDT
signal_buffer = {
    "BTC/USDT": {
        "signals": [
            {"source": "RSI", "action": "BUY", "confidence": 0.85, "timestamp": "12:00:05"},
            {"source": "MACD", "action": "BUY", "confidence": 0.75, "timestamp": "12:00:05"},
            {"source": "BB", "action": "BUY", "confidence": 0.70, "timestamp": "12:00:05"},
            {"source": "VOLUME", "action": "BUY", "confidence": 0.80, "timestamp": "12:00:05"},
            {"source": "SMA", "action": "BUY", "confidence": 0.60, "timestamp": "12:00:03"},
        ],
        "last_decision": "12:00:00"
    }
}

# Check if enough signals collected
min_signals = 3  # Configuration
current_signals = len(signal_buffer["BTC/USDT"]["signals"])  # 5

if current_signals >= min_signals:
    # Proceed to fusion
    await apply_fusion_strategy("BTC/USDT", signal_buffer["BTC/USDT"]["signals"])
```

---

### Step 4: Signal Fusion (Agent 3 - Strategy)

**Time**: 2025-10-10 12:00:07 UTC

Apply **Hybrid Fusion Strategy** (combines Bayesian, Consensus, Time Decay):

```python
signals = signal_buffer["BTC/USDT"]["signals"]

# 1. BAYESIAN FUSION
def bayesian_fusion(signals):
    buy_prob = 1.0
    sell_prob = 1.0

    for signal in signals:
        if signal['action'] == 'BUY':
            buy_prob *= signal['confidence']
        elif signal['action'] == 'SELL':
            sell_prob *= signal['confidence']

    # Normalize
    total = buy_prob + sell_prob
    if total == 0:
        return {"action": "HOLD", "confidence": 0.0}

    final_confidence = buy_prob / total

    return {
        "action": "BUY" if final_confidence > 0.5 else "SELL",
        "confidence": max(final_confidence, 1 - final_confidence)
    }

# Calculation for our signals:
buy_prob = 0.85 * 0.75 * 0.70 * 0.80 * 0.60 = 0.214
sell_prob = 1.0 (no sell signals)
total = 0.214 + 1.0 = 1.214
final_confidence = 0.214 / 1.214 = 0.176

# Result: BUY with 0.176 confidence (too low!)

# 2. CONSENSUS FUSION
def consensus_fusion(signals):
    buy_votes = sum(1 for s in signals if s['action'] == 'BUY')  # 5
    sell_votes = sum(1 for s in signals if s['action'] == 'SELL')  # 0

    total_votes = buy_votes + sell_votes  # 5

    if buy_votes > sell_votes:
        return {
            "action": "BUY",
            "confidence": buy_votes / total_votes
        }
    else:
        return {
            "action": "SELL",
            "confidence": sell_votes / total_votes
        }

# Result: BUY with 1.0 confidence (100% agreement!)

# 3. TIME DECAY FUSION
def time_decay_fusion(signals):
    import math
    from datetime import datetime

    now = datetime.utcnow()
    decay_lambda = 0.1  # Decay rate

    weighted_buy = 0.0
    weighted_sell = 0.0
    total_weight = 0.0

    for signal in signals:
        # Calculate time difference in seconds
        signal_time = datetime.fromisoformat(signal['timestamp'])
        time_diff = (now - signal_time).total_seconds()

        # Calculate decay weight: e^(-λ * t)
        weight = math.exp(-decay_lambda * time_diff / 60)  # Convert to minutes

        if signal['action'] == 'BUY':
            weighted_buy += signal['confidence'] * weight
        elif signal['action'] == 'SELL':
            weighted_sell += signal['confidence'] * weight

        total_weight += weight

    if total_weight == 0:
        return {"action": "HOLD", "confidence": 0.0}

    final_buy_confidence = weighted_buy / total_weight
    final_sell_confidence = weighted_sell / total_weight

    if final_buy_confidence > final_sell_confidence:
        return {
            "action": "BUY",
            "confidence": final_buy_confidence
        }
    else:
        return {
            "action": "SELL",
            "confidence": final_sell_confidence
        }

# For our signals (all recent, within 5 seconds):
# RSI (2 sec old): weight = e^(-0.1 * 2/60) = 0.997
# MACD (2 sec old): weight = 0.997
# BB (2 sec old): weight = 0.997
# VOLUME (2 sec old): weight = 0.997
# SMA (4 sec old): weight = e^(-0.1 * 4/60) = 0.993

weighted_buy = (0.85 * 0.997) + (0.75 * 0.997) + (0.70 * 0.997) + (0.80 * 0.997) + (0.60 * 0.993)
            = 0.847 + 0.748 + 0.698 + 0.798 + 0.596
            = 3.687

total_weight = 0.997 + 0.997 + 0.997 + 0.997 + 0.993 = 4.981
final_confidence = 3.687 / 4.981 = 0.740

# Result: BUY with 0.740 confidence

# 4. HYBRID FUSION (combine all strategies)
bayesian_result = bayesian_fusion(signals)    # {"action": "BUY", "confidence": 0.176}
consensus_result = consensus_fusion(signals)  # {"action": "BUY", "confidence": 1.000}
time_decay_result = time_decay_fusion(signals) # {"action": "BUY", "confidence": 0.740}

# Weighted combination
bayesian_weight = 0.4
consensus_weight = 0.3
time_decay_weight = 0.3

final_confidence = (
    bayesian_result['confidence'] * bayesian_weight +
    consensus_result['confidence'] * consensus_weight +
    time_decay_result['confidence'] * time_decay_weight
)

final_confidence = (0.176 * 0.4) + (1.000 * 0.3) + (0.740 * 0.3)
                 = 0.070 + 0.300 + 0.222
                 = 0.592

# All strategies agree on BUY, so action is BUY
final_action = "BUY"

fusion_result = {
    "action": "BUY",
    "confidence": 0.592,
    "fusion_strategy": "hybrid",
    "component_results": {
        "bayesian": bayesian_result,
        "consensus": consensus_result,
        "time_decay": time_decay_result
    }
}
```

**Fusion Result**:
- **Action**: BUY
- **Confidence**: 0.592 (59.2%)
- **Strategy**: Hybrid fusion

---

### Step 5: Confidence Threshold Check (Agent 3)

**Time**: 2025-10-10 12:00:08 UTC

```python
min_confidence = 0.6  # Configuration: only trade if >60% confident

if fusion_result['confidence'] >= min_confidence:
    # Generate trade intent
    await generate_trade_intent(fusion_result)
else:
    # Confidence too low, reject
    logger.info(f"Confidence {fusion_result['confidence']:.2%} < {min_confidence:.2%}, rejecting trade")
    return

# In this case: 0.592 < 0.6
# TRADE REJECTED due to low confidence!
```

**Decision**: **TRADE REJECTED** - Confidence 59.2% below 60% threshold

---

### Alternative Scenario: Higher Confidence

Let's say we had one more strong signal (e.g., EMA crossover with 0.9 confidence):

```python
# Add EMA signal
signals.append({
    "source": "EMA",
    "action": "BUY",
    "confidence": 0.90,
    "timestamp": "12:00:06"
})

# Recalculate hybrid fusion with 6 signals
# New consensus: 6/6 = 1.0
# New time decay: higher average confidence
# New final confidence: 0.682 (68.2%)

if 0.682 >= 0.6:  # PASS!
    # Generate trade intent
    trade_intent = {
        "symbol": "BTC/USDT",
        "action": "BUY",
        "confidence": 0.682,
        "fusion_result": fusion_result,
        "signals": signals,
        "timestamp": "2025-10-10T12:00:08Z"
    }

    # Publish to Risk Manager
    await publish_message("trade.intent", trade_intent, priority=8)
```

---

### Step 6: Risk Validation (Agent 4 - Risk Manager)

**Time**: 2025-10-10 12:00:09 UTC

Risk Manager receives trade intent and validates:

```python
async def validate_trade_intent(trade_intent):
    symbol = trade_intent['symbol']  # BTC/USDT
    action = trade_intent['action']  # BUY
    confidence = trade_intent['confidence']  # 0.682

    # 1. CHECK PORTFOLIO EXPOSURE
    current_positions = await db.get_active_positions()
    total_portfolio_value = 10000.0  # $10,000 USD

    current_exposure = sum(p['value'] for p in current_positions)  # $300
    exposure_ratio = current_exposure / total_portfolio_value  # 0.03 (3%)

    max_portfolio_risk = 0.05  # 5% max

    if exposure_ratio >= max_portfolio_risk:
        logger.warning(f"Portfolio exposure {exposure_ratio:.2%} >= {max_portfolio_risk:.2%}")
        return None  # REJECT

    # PASS: 3% < 5%

    # 2. CALCULATE POSITION SIZE (Kelly Criterion)
    win_rate = confidence  # 0.682
    risk_reward_ratio = 2.0  # Target 2:1 profit

    # Kelly Formula: f = (p * b - q) / b
    # where p = win_rate, q = 1 - win_rate, b = risk_reward_ratio
    kelly_fraction = (win_rate * risk_reward_ratio - (1 - win_rate)) / risk_reward_ratio
    kelly_fraction = (0.682 * 2.0 - 0.318) / 2.0
    kelly_fraction = (1.364 - 0.318) / 2.0
    kelly_fraction = 1.046 / 2.0
    kelly_fraction = 0.523  # 52.3% of portfolio

    # Apply conservative multiplier (0.25x Kelly)
    conservative_kelly = kelly_fraction * 0.25  # 0.131 (13.1%)

    # Apply max position size limit
    max_position_size = 0.02  # 2% max per position
    position_size_ratio = min(conservative_kelly, max_position_size)  # 0.02 (2%)

    position_value = total_portfolio_value * position_size_ratio  # $200

    current_price = 121617.0
    position_quantity = position_value / current_price  # 0.001644 BTC

    # 3. CALCULATE STOP LOSS (ATR-based)
    atr = await calculate_atr(symbol, period=14)  # Average True Range
    atr_value = 1500.0  # $1,500 ATR for BTC

    stop_loss_multiplier = 2.0  # 2x ATR
    stop_loss_distance = atr_value * stop_loss_multiplier  # $3,000

    if action == 'BUY':
        stop_loss_price = current_price - stop_loss_distance  # 121617 - 3000 = 118617
    else:
        stop_loss_price = current_price + stop_loss_distance

    # 4. CALCULATE TAKE PROFIT (Risk:Reward 1:2)
    take_profit_distance = stop_loss_distance * risk_reward_ratio  # $6,000

    if action == 'BUY':
        take_profit_price = current_price + take_profit_distance  # 121617 + 6000 = 127617
    else:
        take_profit_price = current_price - take_profit_distance

    # 5. VALIDATE RISK
    risk_amount = position_quantity * stop_loss_distance  # 0.001644 * 3000 = $4.93
    max_risk_per_trade = total_portfolio_value * 0.01  # 1% max = $100

    if risk_amount > max_risk_per_trade:
        # Reduce position size to meet risk limit
        position_quantity = max_risk_per_trade / stop_loss_distance
        position_quantity = 100 / 3000  # 0.0333 BTC

    # Final position: 0.001644 BTC (risk $4.93 < $100 limit)

    # 6. CREATE VALIDATED ORDER
    validated_order = {
        "symbol": "BTC/USDT",
        "action": "BUY",
        "quantity": 0.001644,  # BTC
        "entry_price": 121617.0,
        "stop_loss": 118617.0,
        "take_profit": 127617.0,
        "risk_amount": 4.93,
        "potential_profit": 9.86,
        "risk_reward_ratio": 2.0,
        "position_value": 200.0,
        "timestamp": "2025-10-10T12:00:09Z"
    }

    # Publish to Execution Agent
    await publish_message("order.validated", validated_order, priority=9)

    return validated_order
```

**Risk Validation Result**:
- ✅ Portfolio exposure: 3% < 5% limit
- ✅ Position size: $200 (2% of portfolio)
- ✅ Risk amount: $4.93 < $100 limit
- ✅ Stop loss: $118,617 (2x ATR below entry)
- ✅ Take profit: $127,617 (2:1 risk-reward)
- **ORDER APPROVED**

---

### Step 7: Order Execution (Agent 5 - Execution)

**Time**: 2025-10-10 12:00:10 UTC

Execution Agent receives validated order and places on Binance:

```python
import ccxt

async def execute_order(validated_order):
    # Initialize Binance
    exchange = ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_API_SECRET'),
        'enableRateLimit': True,
        'options': {'defaultType': 'spot'}
    })

    symbol = validated_order['symbol']
    action = validated_order['action'].lower()  # 'buy'
    quantity = validated_order['quantity']  # 0.001644 BTC

    # 1. PLACE MARKET ORDER
    try:
        order = exchange.create_order(
            symbol=symbol,
            type='market',
            side=action,
            amount=quantity
        )

        logger.info(f"Market order placed: {order}")

        # Order response from Binance:
        # {
        #     'id': '123456789',
        #     'symbol': 'BTC/USDT',
        #     'type': 'market',
        #     'side': 'buy',
        #     'price': 121650.0,  # Filled at slightly higher due to slippage
        #     'amount': 0.001644,
        #     'filled': 0.001644,
        #     'status': 'closed',
        #     'timestamp': 1728561610000
        # }

        filled_price = order['price']  # 121650.0
        slippage = (filled_price - validated_order['entry_price']) / validated_order['entry_price']
        slippage_pct = slippage * 100  # 0.027% slippage

        logger.info(f"Order filled at {filled_price}, slippage: {slippage_pct:.3f}%")

    except ccxt.InsufficientFunds as e:
        logger.error(f"Insufficient funds: {e}")
        return None
    except ccxt.ExchangeError as e:
        logger.error(f"Exchange error: {e}")
        return None

    # 2. PLACE STOP LOSS ORDER
    stop_loss_order = exchange.create_order(
        symbol=symbol,
        type='stop_loss_limit',
        side='sell',  # Close BUY position
        amount=quantity,
        price=validated_order['stop_loss'],  # 118617.0
        params={'stopPrice': validated_order['stop_loss']}
    )

    logger.info(f"Stop loss placed at {validated_order['stop_loss']}")

    # 3. PLACE TAKE PROFIT ORDER
    take_profit_order = exchange.create_order(
        symbol=symbol,
        type='take_profit_limit',
        side='sell',  # Close BUY position
        amount=quantity,
        price=validated_order['take_profit'],  # 127617.0
        params={'stopPrice': validated_order['take_profit']}
    )

    logger.info(f"Take profit placed at {validated_order['take_profit']}")

    # 4. STORE IN DATABASE
    trade_record = {
        'order_id': order['id'],
        'symbol': symbol,
        'action': action,
        'quantity': quantity,
        'entry_price': filled_price,
        'stop_loss': validated_order['stop_loss'],
        'take_profit': validated_order['take_profit'],
        'stop_loss_order_id': stop_loss_order['id'],
        'take_profit_order_id': take_profit_order['id'],
        'status': 'open',
        'risk_amount': validated_order['risk_amount'],
        'potential_profit': validated_order['potential_profit'],
        'opened_at': datetime.utcnow(),
        'slippage_pct': slippage_pct
    }

    await db.insert_trade(trade_record)

    # 5. PUBLISH EXECUTION CONFIRMATION
    await publish_message("trade.executed", {
        "order_id": order['id'],
        "symbol": symbol,
        "action": action,
        "quantity": quantity,
        "entry_price": filled_price,
        "stop_loss": validated_order['stop_loss'],
        "take_profit": validated_order['take_profit'],
        "slippage_pct": slippage_pct,
        "status": "open",
        "timestamp": datetime.utcnow().isoformat()
    })

    logger.info(f"Trade executed successfully: {symbol} {action} {quantity} @ {filled_price}")

    return trade_record
```

**Execution Result**:
- ✅ Market order filled: 0.001644 BTC @ $121,650
- ✅ Slippage: 0.027% ($33 difference)
- ✅ Stop loss placed: $118,617
- ✅ Take profit placed: $127,617
- ✅ Trade stored in database
- **TRADE ACTIVE**

---

### Step 8: Position Monitoring (Agent 5 - Execution)

**Ongoing**: Monitor order status every 30 seconds

```python
async def monitor_positions():
    while True:
        active_trades = await db.get_active_trades()

        for trade in active_trades:
            # Check if stop loss or take profit triggered
            order_status = exchange.fetch_order(trade['stop_loss_order_id'])

            if order_status['status'] == 'closed':
                # Stop loss hit
                await handle_stop_loss_trigger(trade)

            tp_status = exchange.fetch_order(trade['take_profit_order_id'])

            if tp_status['status'] == 'closed':
                # Take profit hit
                await handle_take_profit_trigger(trade)

            # Update unrealized P&L
            current_price = await get_current_price(trade['symbol'])
            unrealized_pnl = (current_price - trade['entry_price']) * trade['quantity']

            await db.update_trade_pnl(trade['order_id'], unrealized_pnl)

        await asyncio.sleep(30)  # Check every 30 seconds
```

---

## Summary: Complete Decision Flow

```
1. DATA COLLECTION (0 sec)
   └─ Receive: WebSocket market data
   └─ Store: InfluxDB
   └─ Publish: RabbitMQ "market.data"

2. TECHNICAL ANALYSIS (5 sec)
   └─ Fetch: Historical candles
   └─ Calculate: RSI, MACD, BB, Volume
   └─ Generate: 4 BUY signals
   └─ Publish: RabbitMQ "signals.*"

3. STRATEGY - SIGNAL BUFFERING (6 sec)
   └─ Collect: 5 signals
   └─ Check: >= 3 signals minimum ✓

4. STRATEGY - SIGNAL FUSION (7 sec)
   └─ Apply: Hybrid fusion
   └─ Bayesian: 0.176 confidence
   └─ Consensus: 1.000 confidence
   └─ Time Decay: 0.740 confidence
   └─ Final: BUY with 0.592 confidence

5. STRATEGY - CONFIDENCE CHECK (8 sec)
   └─ Threshold: 0.6 (60%)
   └─ Current: 0.592 (59.2%)
   └─ Result: REJECTED (too low)

   [With 6th signal: 0.682 confidence → APPROVED]
   └─ Publish: RabbitMQ "trade.intent"

6. RISK MANAGER (9 sec)
   └─ Portfolio exposure: 3% ✓
   └─ Position size: $200 (2%) ✓
   └─ Stop loss: $118,617 (2x ATR) ✓
   └─ Take profit: $127,617 (2:1 RR) ✓
   └─ Risk amount: $4.93 ✓
   └─ Publish: RabbitMQ "order.validated"

7. EXECUTION (10 sec)
   └─ Market order: BUY 0.001644 BTC
   └─ Filled: $121,650 (0.027% slippage)
   └─ Stop loss: $118,617
   └─ Take profit: $127,617
   └─ Status: TRADE ACTIVE
   └─ Publish: RabbitMQ "trade.executed"

8. MONITORING (ongoing)
   └─ Check: Every 30 seconds
   └─ Update: Unrealized P&L
   └─ Trigger: SL/TP if hit
```

**Total Time**: Market data → Trade execution: **10 seconds**

---

## Key Insights

1. **No AI/LLM involved** - Pure mathematical indicators and algorithms
2. **Multiple validation gates** - Confidence threshold, risk checks
3. **Conservative position sizing** - Kelly Criterion * 0.25
4. **Automated risk management** - Stop loss and take profit always set
5. **Real-time monitoring** - Continuous position tracking
6. **Message-driven architecture** - RabbitMQ for agent communication

The system is **deterministic** and **rule-based**, not AI/LLM-based. Every decision can be traced back to mathematical formulas and indicator thresholds.
