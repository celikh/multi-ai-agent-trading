# AI Agent Architecture - Complete System Explanation

## 🚨 IMPORTANT: Rule-Based vs AI System

**Currently, this system is RULE-BASED, not AI/LLM-based.**

Despite having an OpenAI API key configured, the trading agents use:
- ✅ **Technical indicators** (TA-Lib: RSI, MACD, Bollinger Bands)
- ✅ **Mathematical fusion algorithms** (Bayesian, Consensus, Time Decay)
- ✅ **Threshold-based rules** (RSI < 30 = BUY, RSI > 70 = SELL)
- ❌ **NO AI prompts or LLM calls** in trading decisions

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    MULTI-AGENT TRADING SYSTEM                    │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   1. DATA COLLECTION    │
                    │   agents/data_collection│
                    └─────────────────────────┘
                                  │
                    ┌─────────────┴────────────┐
                    │  WebSocket + REST API    │
                    │  Binance Market Data     │
                    └─────────────┬────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   InfluxDB Storage      │
                    │   + RabbitMQ Publish    │
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  2. TECHNICAL ANALYSIS  │
                    │  agents/technical_      │
                    │        analysis         │
                    └─────────────────────────┘
                                  │
                    ┌─────────────┴────────────┐
                    │  Calculate Indicators:   │
                    │  RSI, MACD, BB, SMA, EMA │
                    └─────────────┬────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  Generate Signals       │
                    │  (BUY/SELL/HOLD)        │
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   3. STRATEGY AGENT     │
                    │   agents/strategy       │
                    └─────────────────────────┘
                                  │
                    ┌─────────────┴────────────┐
                    │  Collect Multiple Signals│
                    │  Apply Fusion Algorithm  │
                    └─────────────┬────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │  Calculate Confidence   │
                    │  Generate Trade Intent  │
                    └─────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   4. RISK MANAGER       │
                    │   agents/risk_manager   │
                    └─────────────────────────┘
                                  │
                    ┌─────────────┴────────────┐
                    │  Check Portfolio Risk    │
                    │  Validate Position Size  │
                    │  Set Stop Loss / Take    │
                    │      Profit              │
                    └─────────────┬────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   5. EXECUTION AGENT    │
                    │   agents/execution      │
                    └─────────────────────────┘
                                  │
                    ┌─────────────┴────────────┐
                    │  Place Order on Binance  │
                    │  Monitor Execution       │
                    │  Update Position         │
                    └──────────────────────────┘
```

## Agent Detailed Explanation

### 1. Data Collection Agent (`agents/data_collection/agent.py`)

**Role**: Collect real-time and historical market data

**How it Works**:
```python
# NO AI PROMPTS - Just data fetching
class DataCollectionAgent(PeriodicAgent):
    async def _stream_ticker(self, symbol):
        # WebSocket connection to Binance
        async with websockets.connect(ws_url) as ws:
            while True:
                msg = await ws.recv()
                data = json.loads(msg)

                # Store in InfluxDB
                await self.influx_client.write(data)

                # Publish to RabbitMQ
                await self.publish_message("market.data", {
                    "symbol": symbol,
                    "price": data['price'],
                    "volume": data['volume'],
                    "timestamp": data['timestamp']
                })
```

**Data Collected**:
- OHLCV candles (Open, High, Low, Close, Volume)
- Real-time price ticks
- Order book depth
- Trading volume

**Storage**:
- InfluxDB: Time-series market data
- RabbitMQ: Real-time message bus

### 2. Technical Analysis Agent (`agents/technical_analysis/agent.py`)

**Role**: Calculate technical indicators and generate trading signals

**How it Works**:
```python
# NO AI PROMPTS - Just mathematical indicators
import talib

class TechnicalAnalysisAgent(BaseAgent):
    async def _calculate_indicators(self, candles):
        # Calculate RSI
        rsi = talib.RSI(candles['close'], timeperiod=14)

        # Calculate MACD
        macd, signal, hist = talib.MACD(candles['close'])

        # Calculate Bollinger Bands
        upper, middle, lower = talib.BBANDS(candles['close'])

        return {
            'rsi': rsi[-1],
            'macd': macd[-1],
            'macd_signal': signal[-1],
            'bb_upper': upper[-1],
            'bb_lower': lower[-1]
        }

    async def _generate_signal(self, indicators):
        # Rule-based signal generation
        if indicators['rsi'] < 30:  # Oversold
            return Signal(action="BUY", confidence=0.7)
        elif indicators['rsi'] > 70:  # Overbought
            return Signal(action="SELL", confidence=0.7)

        if indicators['macd'] > indicators['macd_signal']:
            return Signal(action="BUY", confidence=0.6)

        return Signal(action="HOLD", confidence=0.5)
```

**Indicators Used**:
- RSI (Relative Strength Index): 14-period
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands: 20-period, 2 std dev
- SMA (Simple Moving Average): 20, 50, 200-period
- EMA (Exponential Moving Average)
- ADX (Average Directional Index)
- Stochastic Oscillator
- ATR (Average True Range)
- OBV (On-Balance Volume)

**Signal Rules** (from [technical_analysis/README.md](agents/technical_analysis/README.md)):
- RSI < 30 → BUY (oversold)
- RSI > 70 → SELL (overbought)
- MACD bullish crossover → BUY
- Price touches lower Bollinger Band → BUY
- Price touches upper Bollinger Band → SELL

### 3. Strategy Agent (`agents/strategy/agent.py`)

**Role**: Combine multiple signals using fusion algorithms

**How it Works**:
```python
# NO AI PROMPTS - Mathematical fusion algorithms
class StrategyAgent(BaseAgent):
    async def _apply_fusion_strategy(self, signals):
        # Collect signals from multiple sources
        recent_signals = self._filter_recent_signals(signals)

        # Apply fusion strategy
        if self.fusion_strategy == "bayesian":
            return self._bayesian_fusion(recent_signals)
        elif self.fusion_strategy == "consensus":
            return self._consensus_fusion(recent_signals)
        elif self.fusion_strategy == "time_decay":
            return self._time_decay_fusion(recent_signals)
        elif self.fusion_strategy == "hybrid":
            return self._hybrid_fusion(recent_signals)

    def _bayesian_fusion(self, signals):
        # Bayesian probability combination
        buy_prob = 1.0
        sell_prob = 1.0

        for signal in signals:
            if signal.action == "BUY":
                buy_prob *= signal.confidence
            elif signal.action == "SELL":
                sell_prob *= signal.confidence

        # Normalize
        total = buy_prob + sell_prob
        final_confidence = buy_prob / total

        return {
            "action": "BUY" if final_confidence > 0.5 else "SELL",
            "confidence": max(final_confidence, 1 - final_confidence)
        }

    def _consensus_fusion(self, signals):
        # Majority voting
        buy_votes = sum(1 for s in signals if s.action == "BUY")
        sell_votes = sum(1 for s in signals if s.action == "SELL")

        total_votes = buy_votes + sell_votes
        if total_votes == 0:
            return {"action": "HOLD", "confidence": 0.0}

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

    async def _generate_trade_intent(self, symbol, signals, fusion_result):
        # Only generate intent if confidence is high enough
        if fusion_result["confidence"] < self.min_confidence:
            return None

        trade_intent = TradeIntent(
            symbol=symbol,
            action=fusion_result["action"],
            confidence=fusion_result["confidence"],
            signals=signals,
            timestamp=datetime.utcnow()
        )

        # Publish to risk manager
        await self.publish_message("trade.intent", trade_intent)

        return trade_intent
```

**Fusion Strategies**:

1. **Bayesian Fusion**:
   - Combines signal probabilities using Bayes' theorem
   - Multiplies confidence values
   - Good for independent signals

2. **Consensus Fusion**:
   - Majority voting system
   - Counts BUY vs SELL votes
   - Confidence = vote_ratio
   - Simple and transparent

3. **Time Decay Fusion**:
   - Recent signals weighted more heavily
   - Exponential decay: weight = e^(-λ * time_diff)
   - Good for trending markets

4. **Hybrid Fusion**:
   - Combines all above strategies
   - Weighted average of results
   - Most robust approach

### 4. Risk Manager Agent (`agents/risk_manager/agent.py`)

**Role**: Validate trade intent and manage portfolio risk

**How it Works**:
```python
# NO AI PROMPTS - Risk calculation formulas
class RiskManagerAgent(BaseAgent):
    async def _validate_trade_intent(self, trade_intent):
        # Check portfolio exposure
        current_exposure = await self._get_portfolio_exposure()
        if current_exposure > self.max_portfolio_risk:
            return None  # Reject trade

        # Calculate position size
        position_size = await self._calculate_position_size(
            trade_intent.symbol,
            trade_intent.confidence
        )

        # Set stop loss and take profit
        stop_loss = await self._calculate_stop_loss(
            trade_intent.action,
            current_price,
            volatility
        )

        take_profit = await self._calculate_take_profit(
            trade_intent.action,
            current_price,
            risk_reward_ratio=2.0
        )

        # Create validated order
        order = ValidatedOrder(
            symbol=trade_intent.symbol,
            action=trade_intent.action,
            quantity=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit
        )

        # Publish to execution agent
        await self.publish_message("order.validated", order)

        return order

    async def _calculate_position_size(self, symbol, confidence):
        # Kelly Criterion for position sizing
        win_rate = confidence
        risk_reward = 2.0

        kelly_fraction = (win_rate * risk_reward - (1 - win_rate)) / risk_reward

        # Apply conservative multiplier (0.25)
        position_size = self.portfolio_value * kelly_fraction * 0.25

        return position_size
```

**Risk Controls**:
- Max portfolio exposure: 5%
- Max single position: 2%
- Stop loss: ATR-based (2x ATR)
- Take profit: Risk-reward ratio 2:1
- Position sizing: Kelly Criterion

### 5. Execution Agent (`agents/execution/agent.py`)

**Role**: Place orders on Binance and monitor execution

**How it Works**:
```python
# NO AI PROMPTS - Just order execution
import ccxt

class ExecutionAgent(BaseAgent):
    async def _execute_order(self, validated_order):
        # Initialize Binance exchange
        exchange = ccxt.binance({
            'apiKey': self.api_key,
            'secret': self.api_secret
        })

        # Place market order
        order = exchange.create_order(
            symbol=validated_order.symbol,
            type='market',
            side=validated_order.action.lower(),
            amount=validated_order.quantity
        )

        # Place stop loss
        stop_loss_order = exchange.create_order(
            symbol=validated_order.symbol,
            type='stop_loss',
            side='sell' if validated_order.action == 'BUY' else 'buy',
            amount=validated_order.quantity,
            price=validated_order.stop_loss
        )

        # Place take profit
        take_profit_order = exchange.create_order(
            symbol=validated_order.symbol,
            type='take_profit',
            side='sell' if validated_order.action == 'BUY' else 'buy',
            amount=validated_order.quantity,
            price=validated_order.take_profit
        )

        # Store in database
        await self.db.store_trade({
            'order_id': order['id'],
            'symbol': validated_order.symbol,
            'action': validated_order.action,
            'quantity': validated_order.quantity,
            'entry_price': order['price'],
            'stop_loss': validated_order.stop_loss,
            'take_profit': validated_order.take_profit,
            'status': 'filled'
        })

        # Monitor execution
        await self._monitor_order_status(order['id'])
```

**Execution Features**:
- Market orders for immediate execution
- Automatic stop loss placement
- Automatic take profit placement
- Slippage monitoring
- Order status tracking

## Message Flow Between Agents

```
1. Data Collection → "market.data" → Technical Analysis
   {
     "symbol": "BTC/USDT",
     "price": 121617.0,
     "volume": 1234.56,
     "timestamp": "2025-10-10T12:00:00Z"
   }

2. Technical Analysis → "signals.*" → Strategy
   {
     "symbol": "BTC/USDT",
     "action": "BUY",
     "confidence": 0.75,
     "indicators": {
       "rsi": 28.5,
       "macd": "bullish_crossover",
       "bb_position": "lower_band"
     }
   }

3. Strategy → "trade.intent" → Risk Manager
   {
     "symbol": "BTC/USDT",
     "action": "BUY",
     "confidence": 0.82,
     "fusion_strategy": "hybrid",
     "signals_count": 5
   }

4. Risk Manager → "order.validated" → Execution
   {
     "symbol": "BTC/USDT",
     "action": "BUY",
     "quantity": 0.001,
     "stop_loss": 119000.0,
     "take_profit": 126000.0
   }

5. Execution → "trade.executed" → All Agents
   {
     "order_id": "12345",
     "symbol": "BTC/USDT",
     "status": "filled",
     "filled_price": 121650.0,
     "quantity": 0.001
   }
```

## Configuration Files

### Strategy Configuration (`config/strategy.yaml`)
```yaml
strategy:
  fusion_strategy: "hybrid"  # bayesian, consensus, time_decay, hybrid
  min_signals: 3             # Minimum signals before decision
  min_confidence: 0.6        # Minimum confidence threshold
  signal_timeout: 300        # Signals older than 5min ignored

bayesian:
  prior_buy: 0.5
  prior_sell: 0.5

consensus:
  min_agreement: 0.6         # 60% majority required

time_decay:
  decay_lambda: 0.1          # Decay rate

hybrid:
  bayesian_weight: 0.4
  consensus_weight: 0.3
  time_decay_weight: 0.3
```

### Risk Management Configuration (`config/risk.yaml`)
```yaml
risk:
  max_portfolio_risk: 0.05   # 5% max exposure
  max_position_size: 0.02    # 2% per position
  stop_loss_atr_multiplier: 2.0
  take_profit_ratio: 2.0     # Risk:Reward 1:2
  kelly_fraction: 0.25       # Conservative Kelly
```

## Where AI/LLM Could Be Integrated (Future Enhancement)

Currently NO AI prompts exist, but here's where they COULD be added:

### 1. Sentiment Analysis Agent (New)
```python
# FUTURE: Add LLM-based sentiment analysis
import openai

class SentimentAnalysisAgent(BaseAgent):
    async def _analyze_sentiment(self, symbol):
        # Fetch news articles
        news = await self._fetch_news(symbol)

        # LLM prompt for sentiment
        prompt = f"""
        Analyze the sentiment of the following news articles about {symbol}:

        {news}

        Provide:
        1. Overall sentiment: BULLISH/BEARISH/NEUTRAL
        2. Confidence: 0.0 to 1.0
        3. Key factors influencing sentiment
        """

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse LLM response
        sentiment = self._parse_sentiment(response)

        # Publish sentiment signal
        await self.publish_message("signals.sentiment", sentiment)
```

### 2. Pattern Recognition Agent (New)
```python
# FUTURE: Add LLM-based chart pattern recognition
class PatternRecognitionAgent(BaseAgent):
    async def _identify_patterns(self, candles):
        # Convert candles to description
        chart_description = self._describe_price_action(candles)

        prompt = f"""
        Analyze this price action and identify chart patterns:

        {chart_description}

        Identify:
        1. Pattern type: Head & Shoulders, Double Top, Triangle, etc.
        2. Pattern strength: 0.0 to 1.0
        3. Trading implication: BULLISH/BEARISH
        """

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        pattern = self._parse_pattern(response)
        await self.publish_message("signals.pattern", pattern)
```

### 3. Strategy Enhancement with LLM
```python
# FUTURE: Add LLM reasoning to strategy fusion
class EnhancedStrategyAgent(StrategyAgent):
    async def _llm_fusion(self, signals):
        # Current rule-based fusion
        rule_based_result = await self._apply_fusion_strategy(signals)

        # Add LLM reasoning
        prompt = f"""
        Given these trading signals:
        {json.dumps(signals, indent=2)}

        And rule-based fusion result:
        {json.dumps(rule_based_result, indent=2)}

        Provide:
        1. Do you agree with the rule-based decision? Why?
        2. Any additional factors to consider?
        3. Final recommendation: BUY/SELL/HOLD with confidence
        """

        llm_analysis = await self._call_llm(prompt)

        # Combine rule-based + LLM
        final_decision = self._combine_decisions(
            rule_based_result,
            llm_analysis
        )

        return final_decision
```

## Summary

**Current System** (What EXISTS now):
- ✅ Rule-based technical indicators (TA-Lib)
- ✅ Mathematical fusion algorithms
- ✅ Threshold-based decision rules
- ✅ Risk management formulas
- ❌ NO AI prompts
- ❌ NO LLM calls
- ❌ NO sentiment analysis

**Future Enhancements** (What COULD be added):
- 💡 LLM-based sentiment analysis
- 💡 Chart pattern recognition via AI
- 💡 Enhanced decision fusion with LLM reasoning
- 💡 Market regime detection
- 💡 Adaptive strategy selection

The system is **production-ready** with proven quantitative trading methods, but is **NOT AI-based** in the LLM sense. It's a sophisticated rule-based system using mathematical indicators and algorithms.
