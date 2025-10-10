# Technical Analysis Agent

AI-powered technical analysis agent that analyzes market data using technical indicators and generates trading signals.

## 🎯 Features

### Technical Indicators
- **Trend Indicators**
  - SMA (20, 50, 200 periods)
  - EMA (20, 50 periods)
  - ADX (trend strength)

- **Momentum Indicators**
  - RSI (Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)
  - Stochastic Oscillator

- **Volatility Indicators**
  - Bollinger Bands
  - ATR (Average True Range)

- **Volume Indicators**
  - OBV (On-Balance Volume)

### Signal Generation
- **RSI-based signals**
  - Oversold (< 30): BUY signal
  - Overbought (> 70): SELL signal

- **MACD-based signals**
  - Bullish crossover: BUY signal
  - Bearish crossover: SELL signal

- **Bollinger Bands signals**
  - Price at lower band: BUY signal
  - Price at upper band: SELL signal

- **Moving Average signals**
  - Price above MAs: BUY signal (uptrend)
  - Price below MAs: SELL signal (downtrend)

### Signal Combination
- Weighted signal fusion
- Confidence scoring (0-1)
- Multiple indicator consensus
- Detailed reasoning for each signal

## 🚀 Usage

### Run the Agent

```bash
# Activate virtual environment
source venv/bin/activate

# Run technical analysis agent
python -m agents.technical_analysis.agent
```

### Test Indicators

```bash
# Run test script
python scripts/test_technical_analysis.py
```

Expected output:
```
🧪 Testing Technical Indicators...
============================================================

📊 Latest Indicator Values:
------------------------------------------------------------
  rsi                 :      45.2341
  macd                :       0.0123
  macd_signal         :       0.0098
  macd_hist           :       0.0025
  bb_upper            :   50245.6789
  bb_middle           :   50123.4567
  bb_lower            :   50001.2345
  ...

🎯 Combined Signal:
============================================================
  Final Signal: BUY
  Confidence: 67.50%
  Buy Strength: 2.70
  Sell Strength: 1.30

  Reasoning:
    • RSI oversold at 28.45
    • MACD bullish crossover (hist: 0.0025)
    • Price at lower BB (50000.00 <= 50001.23)
```

## 📊 Data Flow

```
InfluxDB (OHLCV data)
        ↓
Technical Analysis Agent
        ↓
Calculate Indicators
        ↓
Generate Signals
        ↓
Combine with Confidence
        ↓
RabbitMQ (signals.tech) + PostgreSQL
```

## 🛠️ Architecture

### Components

1. **indicators.py**
   - `TechnicalIndicators` class
   - Wraps TA-Lib functions
   - Calculates all indicators
   - Extracts latest values

2. **agent.py**
   - `TechnicalAnalysisAgent` class
   - Fetches OHLCV data from InfluxDB
   - Analyzes each symbol periodically
   - Publishes signals to RabbitMQ
   - Stores signals in PostgreSQL

### Message Protocol

**Input**: Market data from `ticks.raw` topic
```json
{
  "type": "market.data",
  "exchange": "binance",
  "symbol": "BTC/USDT",
  "data": {
    "type": "ohlcv",
    "close": 50000.00,
    ...
  }
}
```

**Output**: Trading signals to `signals.tech` topic
```json
{
  "type": "signal",
  "agent_type": "TECHNICAL_ANALYSIS",
  "symbol": "BTC/USDT",
  "signal": "BUY",
  "confidence": 0.75,
  "reasoning": "RSI oversold at 28.45 | MACD bullish crossover",
  "indicators": {
    "rsi": 28.45,
    "macd": 0.0123,
    ...
  }
}
```

## ⚙️ Configuration

### Agent Parameters

```python
agent = TechnicalAnalysisAgent(
    symbols=["BTC/USDT", "ETH/USDT"],  # Symbols to analyze
    lookback_periods=100,               # Historical data points
    interval=60,                        # Analysis interval (seconds)
)
```

### Indicator Settings

Edit in `indicators.py`:
```python
# RSI
rsi = talib.RSI(close, timeperiod=14)

# MACD
macd, signal, hist = talib.MACD(
    close,
    fastperiod=12,
    slowperiod=26,
    signalperiod=9
)

# Bollinger Bands
upper, middle, lower = talib.BBANDS(
    close,
    timeperiod=20,
    nbdevup=2,
    nbdevdn=2
)
```

## 📈 Signal Strength Calculation

### Individual Indicators

**RSI Strength**:
```python
if rsi < 30:
    strength = (30 - rsi) / 30  # 0 to 1
elif rsi > 70:
    strength = (rsi - 70) / 30  # 0 to 1
```

**MACD Strength**:
```python
strength = min(abs(histogram) / 10, 1.0)
```

**Bollinger Bands Strength**:
```python
band_width = upper - lower
strength = min((lower - close) / band_width * 2, 1.0)
```

### Combined Signal

```python
buy_strength = sum(signal.strength for signal in signals if signal == "BUY")
sell_strength = sum(signal.strength for signal in signals if signal == "SELL")

confidence = max(buy_strength, sell_strength) / len(signals)
```

## 🧪 Testing

### Unit Tests (Coming Soon)

```bash
pytest tests/unit/test_technical_analysis.py
```

### Integration Tests (Coming Soon)

```bash
pytest tests/integration/test_ta_agent.py
```

### Manual Testing

```bash
# 1. Start infrastructure
docker-compose up -d

# 2. Run data collector (to populate InfluxDB)
python -m agents.data_collection.agent

# Wait 2-3 minutes for data...

# 3. Run technical analysis
python -m agents.technical_analysis.agent

# 4. Check signals in RabbitMQ
open http://localhost:15672  # Login: trading/trading_pass
# Navigate to Queues → signals.tech

# 5. Check signals in PostgreSQL
docker-compose exec postgres psql -U trading_user -d trading_db
SELECT * FROM signals WHERE agent_type = 'TECHNICAL_ANALYSIS' ORDER BY created_at DESC LIMIT 10;
```

## 📊 Performance

### Metrics
- **Analysis Time**: ~100ms per symbol
- **Memory Usage**: ~50MB
- **Data Requirements**: 100+ candles for accurate indicators

### Optimization Tips
1. Adjust `lookback_periods` based on indicators used
2. Increase `interval` to reduce CPU usage
3. Use parallel analysis for multiple symbols (future)

## 🔍 Debugging

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
python -m agents.technical_analysis.agent
```

### Check Indicator Values

```python
from agents.technical_analysis.indicators import TechnicalIndicators
import pandas as pd

# Your OHLCV data
df = pd.DataFrame(...)

indicators = TechnicalIndicators()
all_indicators = indicators.calculate_all_indicators(df)
latest = indicators.get_latest_values(all_indicators)

print(latest)
```

### Verify Signals

```sql
-- Check recent signals
SELECT
    symbol,
    signal_type,
    confidence,
    reasoning,
    created_at
FROM signals
WHERE agent_type = 'TECHNICAL_ANALYSIS'
ORDER BY created_at DESC
LIMIT 10;
```

## 🐛 Troubleshooting

### Issue: "TA-Lib not installed"

**Solution**:
```bash
# macOS
brew install ta-lib
pip install TA-Lib

# Ubuntu
sudo apt-get install ta-lib
pip install TA-Lib

# Windows
# Download from: http://mrjbq7.github.io/ta-lib/install.html
pip install TA-Lib
```

### Issue: "Insufficient data"

**Solution**:
- Ensure Data Collection Agent is running
- Wait for at least 100 candles to accumulate
- Check InfluxDB has data:
```python
from infrastructure.database.influxdb import get_influx
influx = get_influx()
data = influx.query_ohlcv("BTC/USDT", "binance", ...)
print(len(data))  # Should be > 100
```

### Issue: "No signals generated"

**Solution**:
- Check indicator values are not NaN
- Verify lookback period is sufficient
- Review signal thresholds in `indicators.py`

## 🚀 Next Steps

1. **Add More Indicators**
   - Ichimoku Cloud
   - Fibonacci retracements
   - Volume Profile

2. **Machine Learning**
   - Train ML model on historical signals
   - Adaptive indicator weights
   - Pattern recognition

3. **Advanced Features**
   - Multi-timeframe analysis
   - Correlation analysis
   - Sentiment integration

## 📚 Resources

- **TA-Lib Documentation**: https://mrjbq7.github.io/ta-lib/
- **Technical Analysis**: https://www.investopedia.com/technical-analysis-4689657
- **Indicator Guide**: https://www.tradingview.com/scripts/

---

**Built with ❤️ using Python, TA-Lib, and AsyncIO**
