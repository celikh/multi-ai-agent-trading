# Risk Manager Agent

**Risk Yönetimi Ajanı** - Pozisyon boyutlandırma, risk değerlendirme ve trade onaylama

## 📋 İçindekiler

- [Genel Bakış](#genel-bakış)
- [Mimari](#mimari)
- [Position Sizing](#position-sizing)
- [Risk Assessment](#risk-assessment)
- [Stop-Loss Placement](#stop-loss-placement)
- [Kurulum](#kurulum)
- [Kullanım](#kullanım)
- [Test](#test)

## Genel Bakış

Risk Manager Agent, Strategy Agent'tan gelen trade intent'leri alır, risk değerlendirmesi yapar ve optimal pozisyon boyutlandırması ile stop-loss/take-profit seviyeleri belirler. Kelly Criterion, VaR hesaplama ve çoklu risk metriklerini kullanarak trade'leri onaylar veya reddeder.

### Temel Özellikler

- **📊 Kelly Criterion**: Optimal pozisyon boyutlandırma
- **📉 VaR Calculation**: Historical, Parametric, Monte Carlo
- **🛡️ Stop-Loss Placement**: ATR, Percentage, Volatility, S/R based
- **✅ Trade Validation**: Çoklu risk kontrolü
- **📈 Portfolio Risk**: Toplam portföy risk takibi
- **💰 Position Sizing**: Kelly, Fixed, Volatility, Hybrid metotlar
- **🎯 Risk-Adjusted**: Sharpe ve Sortino ratio hesaplama

### Mesaj Akışı

```
Strategy Agent → [trade.intent] → Risk Manager → [trade.order] → Execution Agent
                                          ↓
                                   [trade.rejection]
```

## Mimari

### Sistem Bileşenleri

```
Risk Manager Agent
│
├── Position Sizing
│   ├── Kelly Criterion
│   ├── Fixed Fractional
│   ├── Volatility-Based
│   └── Hybrid (Combined)
│
├── Risk Assessment
│   ├── VaR Calculator
│   │   ├── Historical VaR
│   │   ├── Parametric VaR
│   │   └── Monte Carlo VaR
│   ├── Portfolio Analyzer
│   │   ├── Portfolio VaR
│   │   ├── Max Drawdown
│   │   ├── Sharpe Ratio
│   │   └── Sortino Ratio
│   └── Trade Validator
│       ├── Confidence Check
│       ├── R/R Ratio Check
│       ├── Risk Limit Check
│       └── Correlation Check
│
└── Stop-Loss Placement
    ├── ATR-Based
    ├── Percentage-Based
    ├── Volatility-Based
    ├── Support/Resistance
    └── Trailing Stop
```

## Position Sizing

### 1. Kelly Criterion

Matematiksel olarak optimal pozisyon boyutu hesaplama.

**Formula**:
```
f* = (bp - q) / b

f* = Kelly fraction (sermayenin yüzdesi)
b = Reward/Risk ratio
p = Kazanma olasılığı
q = Kaybetme olasılığı (1-p)
```

**Örnek**:
```python
from agents.risk_manager import KellyCriterion

kelly = KellyCriterion(
    max_kelly_fraction=0.25,  # Max %25 (conservative)
    min_kelly_fraction=0.01,  # Min %1
)

kelly_fraction = kelly.calculate(
    win_probability=0.65,     # %65 kazanma olasılığı
    reward_risk_ratio=2.0,    # 2:1 R/R
    account_balance=10000,
)

# kelly_fraction = 0.15 (15% of capital)
position_size = 10000 * kelly_fraction  # $1,500
```

**Özellikler**:
- Adaptive learning: Geçmiş performansa göre ayarlama
- Conservative cap: Max %25 (full Kelly'nin 1/4'ü)
- Confidence adjustment: Düşük güvende yarı Kelly
- Min/Max constraints: %1-%25 arası sınırlama

### 2. Fixed Fractional

Sabit risk yüzdesi ile pozisyon boyutlandırma.

**Formula**:
```
Position Size = (Account Balance × Risk %) / Stop Loss %

Örnek:
- Account: $10,000
- Risk per trade: 2%
- Stop loss: 5%

Position = ($10,000 × 0.02) / 0.05 = $4,000
```

**Kullanım**:
```python
from agents.risk_manager import FixedFractional

fixed = FixedFractional(
    risk_per_trade=0.02,      # %2 risk per trade
    max_position_size=0.10,   # Max %10 of portfolio
)

position_size = fixed.calculate(
    account_balance=10000,
    stop_loss_pct=0.05,       # %5 stop
)

# position_size = $4,000
```

### 3. Volatility-Based

Piyasa volatilitesine göre dinamik boyutlandırma.

**ATR Yöntemi**:
```
Stop Loss Distance = ATR × Multiplier (2.0)
Position Size = (Risk Amount) / (Stop Loss Distance / Price)

Örnek:
- ATR = $1,000
- Multiplier = 2.0
- Risk Amount = $200
- Price = $50,000

Stop Distance = $1,000 × 2.0 = $2,000
Stop Loss % = $2,000 / $50,000 = 4%
Position Size = $200 / 0.04 = $5,000
```

**Kullanım**:
```python
from agents.risk_manager import VolatilityBased

vol_sizing = VolatilityBased(
    base_risk=0.02,           # %2 base risk
    atr_multiplier=2.0,       # 2× ATR for stop
)

position_size, stop_distance = vol_sizing.calculate(
    account_balance=10000,
    current_price=50000,
    atr=1000,
)
```

### 4. Hybrid Sizing

Tüm metotların kombinasyonu (production için önerilen).

**Algoritma**:
```python
# 1. Kelly hesapla
kelly_size = kelly.calculate(...)

# 2. Fixed hesapla
fixed_size = fixed.calculate(...)

# 3. Daha conservative olanı seç
position_size = min(kelly_size, fixed_size)

# 4. Maksimum limiti uygula
max_size = account_balance × max_position_pct
final_size = min(position_size, max_size)
```

**Kullanım**:
```python
from agents.risk_manager import PositionSizer

sizer = PositionSizer(
    account_balance=10000,
    max_position_pct=0.10,
    max_total_risk=0.20,
    default_method="hybrid",
)

position = sizer.calculate_position_size(
    symbol="BTC/USDT",
    current_price=50000,
    confidence=0.75,
    stop_loss=48000,
    take_profit=54000,
    atr=1000,
    method="hybrid",
)

print(f"Quantity: {position.quantity}")
print(f"Size USD: ${position.size_usd:,.2f}")
print(f"Risk: ${position.risk_amount:,.2f}")
print(f"Kelly Fraction: {position.kelly_fraction:.1%}")
```

## Risk Assessment

### 1. VaR (Value at Risk)

Belirli güven seviyesinde maksimum potansiyel kayıp.

**Historical VaR**:
```python
from agents.risk_manager import VaRCalculator
import numpy as np

var_calc = VaRCalculator(confidence_level=0.95)

# Geçmiş getiriler
returns = np.array([-0.02, 0.01, -0.015, 0.03, -0.01, ...])

var_95, var_99 = var_calc.historical_var(
    returns=returns,
    position_value=5000,
)

print(f"VaR 95%: ${var_95:,.2f}")  # $150
print(f"VaR 99%: ${var_99:,.2f}")  # $250
```

**Parametric VaR** (Normal dağılım varsayımı):
```python
var_95, var_99 = var_calc.parametric_var(
    returns=returns,
    position_value=5000,
)

# Normal dağılım kullanarak hesaplar
# Daha hızlı ama tail risk'i underestimate edebilir
```

**Monte Carlo VaR**:
```python
var_95, var_99 = var_calc.monte_carlo_var(
    returns=returns,
    position_value=5000,
    num_simulations=10000,
)

# 10,000 simülasyon ile daha robust
```

**CVaR (Conditional VaR / Expected Shortfall)**:
```python
cvar = var_calc.conditional_var(
    returns=returns,
    position_value=5000,
)

print(f"CVaR 95%: ${cvar:,.2f}")
# VaR aşıldığında ortalama kayıp
```

### 2. Portfolio Risk Metrics

**Portfolio VaR**:
```python
from agents.risk_manager import PortfolioRiskAnalyzer

analyzer = PortfolioRiskAnalyzer(
    max_portfolio_var=0.10,   # Max %10 VaR
    max_position_risk=0.05,   # Max %5 per position
)

positions = [
    {"symbol": "BTC/USDT", "size_usd": 5000},
    {"symbol": "ETH/USDT", "size_usd": 3000},
]

returns_history = {
    "BTC/USDT": np.array([...]),
    "ETH/USDT": np.array([...]),
}

portfolio_var = analyzer.calculate_portfolio_var(
    positions, returns_history
)

print(f"Portfolio VaR: {portfolio_var:.1%}")
```

**Maximum Drawdown**:
```python
equity_curve = np.array([10000, 10500, 10200, 11000, ...])

max_dd = analyzer.calculate_max_drawdown(equity_curve)

print(f"Max Drawdown: {max_dd:.1%}")
```

**Sharpe Ratio**:
```python
sharpe = analyzer.calculate_sharpe_ratio(
    returns=daily_returns,
    risk_free_rate=0.02,  # %2 annual
)

print(f"Sharpe Ratio: {sharpe:.2f}")
# > 1.0 = Good, > 2.0 = Excellent
```

**Sortino Ratio** (downside deviation only):
```python
sortino = analyzer.calculate_sortino_ratio(
    returns=daily_returns,
    risk_free_rate=0.02,
)

print(f"Sortino Ratio: {sortino:.2f}")
# Sadece negatif getirileri penalize eder
```

### 3. Trade Validation

**Çoklu Risk Kontrolü**:
```python
from agents.risk_manager import TradeValidator

validator = TradeValidator(
    max_portfolio_risk=0.20,       # Max %20 portfolio risk
    max_single_trade_risk=0.05,    # Max %5 per trade
    min_reward_risk_ratio=1.5,     # Min 1.5:1 R/R
    min_confidence=0.6,            # Min %60 confidence
    max_correlation_risk=0.30,     # Max %30 correlated
)

assessment = validator.validate_trade(
    symbol="BTC/USDT",
    confidence=0.75,
    position_size=500,
    risk_amount=100,
    reward_risk_ratio=2.5,
    current_portfolio_risk=0.05,
    account_balance=10000,
    existing_positions=[...],
)

if assessment.approved:
    print(f"✅ Trade Approved")
    print(f"Risk Score: {assessment.risk_score:.2f}")
else:
    print(f"❌ Trade Rejected")
    print(f"Reason: {assessment.rejection_reason}")
```

**Validation Checks**:
1. **Confidence**: >= min_confidence
2. **R/R Ratio**: >= min_reward_risk_ratio
3. **Single Trade Risk**: <= max_single_trade_risk
4. **Portfolio Risk**: new_risk <= max_portfolio_risk
5. **Correlation**: correlated_exposure <= max_correlation_risk

## Stop-Loss Placement

### 1. ATR-Based

Average True Range kullanarak volatiliteye göre stop yerleştirme.

```python
from agents.risk_manager import StopLossManager, StopLossMethod

manager = StopLossManager(
    default_method=StopLossMethod.ATR,
    default_rr_ratio=2.0,
)

stops = manager.calculate_stops(
    symbol="BTC/USDT",
    current_price=50000,
    side="BUY",
    method=StopLossMethod.ATR,
    atr=1000,  # $1,000 ATR
)

print(f"Stop Loss: ${stops.stop_loss:,.2f}")      # $48,000 (2× ATR below)
print(f"Take Profit: ${stops.take_profit:,.2f}")  # $54,000 (2:1 R/R)
print(f"R/R Ratio: {stops.reward_risk_ratio:.2f}:1")
```

**Formula**:
```
Stop Distance = ATR × Multiplier (2.0)

BUY:
  Stop Loss = Price - Stop Distance
  Take Profit = Price + (Stop Distance × R/R Ratio)

SELL:
  Stop Loss = Price + Stop Distance
  Take Profit = Price - (Stop Distance × R/R Ratio)
```

### 2. Percentage-Based

Sabit yüzde ile stop yerleştirme.

```python
stops = manager.calculate_stops(
    symbol="ETH/USDT",
    current_price=3000,
    side="BUY",
    method=StopLossMethod.PERCENTAGE,
)

# Default %5 stop, 2:1 R/R
# Stop: $2,850 (-5%)
# TP: $3,300 (+10%)
```

### 3. Volatility-Based

Standard deviation kullanarak stop hesaplama.

```python
stops = manager.calculate_stops(
    symbol="SOL/USDT",
    current_price=100,
    side="BUY",
    method=StopLossMethod.VOLATILITY,
    price_std=5,  # $5 std deviation
)

# Stop Distance = 5 × 2.0 = $10
# Stop: $90
# TP: $120
```

### 4. Support/Resistance Based

Teknik seviyelere göre stop yerleştirme.

```python
stops = manager.calculate_stops(
    symbol="BTC/USDT",
    current_price=50000,
    side="BUY",
    method=StopLossMethod.SUPPORT_RESISTANCE,
    support=49000,
    resistance=52000,
)

# Stop: $48,510 (1% below support)
# TP: $51,480 (resistance veya R/R, hangisi uzaksa)
```

### 5. Trailing Stop

Fiyatı takip eden dinamik stop.

```python
from agents.risk_manager import TrailingStopLoss

trailing = TrailingStopLoss(
    trail_pct=0.03,           # %3 trailing distance
    activation_pct=0.05,      # %5 kar sonrası aktive
)

# Initial stop
stop, activation = trailing.calculate_initial(
    entry_price=50000,
    side="BUY",
)

# Entry: $50,000
# Initial Stop: $48,500 (-3%)
# Activation at: $52,500 (+5%)

# Update as price moves
new_stop = trailing.update_trailing_stop(
    current_price=53000,      # Fiyat yükseldi
    current_stop=48500,
    entry_price=50000,
    side="BUY",
)

# New Stop: $51,410 (53,000 - 3%)
```

## Kurulum

### Gereksinimler

```bash
# Python bağımlılıkları
numpy>=1.24.0
scipy>=1.10.0
pandas>=2.0.0
```

### Database Schema

Risk assessments tablosu zaten mevcut (`infrastructure/database/schema.sql`):

```sql
CREATE TABLE risk_assessments (
    id UUID PRIMARY KEY,
    signal_id UUID REFERENCES signals(id),
    symbol VARCHAR(50) NOT NULL,
    risk_score DECIMAL(5, 4),
    position_size DECIMAL(20, 8),
    var_estimate DECIMAL(20, 8),
    max_loss DECIMAL(20, 8),
    approved BOOLEAN NOT NULL,
    rejection_reason TEXT,
    assessed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB
);
```

## Kullanım

### Standalone Test

```bash
# Risk Manager testlerini çalıştır
python scripts/test_risk_manager.py
```

### Full System Integration

```bash
# Terminal 1: Infrastructure
docker-compose up -d postgresql rabbitmq influxdb

# Terminal 2: Data Collection
python agents/data_collection/agent.py

# Terminal 3: Technical Analysis
python agents/technical_analysis/agent.py

# Terminal 4: Strategy Agent
python agents/strategy/agent.py

# Terminal 5: Risk Manager
python agents/risk_manager/agent.py
```

### Configuration

```python
from agents.risk_manager import RiskManagerAgent

agent = RiskManagerAgent(
    name="risk_manager_main",
    account_balance=10000.0,
    max_portfolio_risk=0.20,          # Max %20 portfolio risk
    max_position_risk=0.05,           # Max %5 per trade
    position_sizing_method="hybrid",  # kelly|fixed|volatility|hybrid
    stop_loss_method="atr",          # atr|percentage|volatility|support_resistance
    min_confidence=0.6,              # Min %60 confidence
    min_rr_ratio=1.5,                # Min 1.5:1 reward/risk
)

await agent.initialize()
await agent.start()
```

## Test

### Unit Tests

```bash
python scripts/test_risk_manager.py
```

**Test Coverage**:
- ✅ Kelly Criterion calculation
- ✅ Position sizing (all methods)
- ✅ VaR calculation (Historical, Parametric, Monte Carlo)
- ✅ Stop-loss placement (all methods)
- ✅ Trade validation
- ✅ Portfolio risk analysis

**Expected Output**:
```
============================================================
🧪 RISK MANAGER - COMPREHENSIVE TESTS
============================================================

============================================================
📊 TESTING KELLY CRITERION
============================================================

✅ Test 1: Win prob 65%, R/R 2:1
  Kelly fraction: 15.0%
  Position size: $1,500.00

============================================================
✅ ALL TESTS COMPLETED SUCCESSFULLY
============================================================
```

### Integration Test

```bash
# Simulate trade intent
python -c "
import asyncio
from agents.base.protocol import TradeIntent, SignalType

intent = TradeIntent(
    symbol='BTC/USDT',
    side='BUY',
    confidence=0.75,
    price_target=54000,
    stop_loss=48000,
    take_profit=54000,
    reasoning='Strong technical setup',
)

# Publish to RabbitMQ
# Risk Manager will process and approve/reject
"
```

## Monitoring

### PostgreSQL Queries

```sql
-- Risk assessments özeti
SELECT
    DATE(assessed_at) as date,
    COUNT(*) as total_assessments,
    COUNT(*) FILTER (WHERE approved = true) as approved,
    COUNT(*) FILTER (WHERE approved = false) as rejected,
    AVG(risk_score) as avg_risk_score,
    AVG(position_size) as avg_position_size
FROM risk_assessments
WHERE assessed_at > NOW() - INTERVAL '24 hours'
GROUP BY DATE(assessed_at)
ORDER BY date DESC;

-- Rejection reasons
SELECT
    rejection_reason,
    COUNT(*) as count
FROM risk_assessments
WHERE approved = false
AND assessed_at > NOW() - INTERVAL '7 days'
GROUP BY rejection_reason
ORDER BY count DESC;

-- Portfolio risk over time
SELECT
    symbol,
    position_size,
    max_loss,
    var_estimate,
    risk_score,
    approved,
    assessed_at
FROM risk_assessments
ORDER BY assessed_at DESC
LIMIT 20;
```

### Key Metrics

- **Approval Rate**: approved / total
- **Average Risk Score**: avg(risk_score)
- **Average Position Size**: avg(position_size)
- **Total Portfolio Risk**: sum(max_loss) / account_balance
- **VaR Utilization**: portfolio_var / max_var_limit

## Best Practices

### 1. Position Sizing

- **Bull Market**: Use Kelly or Hybrid (more aggressive)
- **Bear Market**: Use Fixed Fractional (conservative)
- **High Volatility**: Reduce position sizes, use ATR-based stops
- **Low Volatility**: Can increase position sizes slightly

### 2. Risk Limits

```python
# Conservative (beginner)
max_portfolio_risk = 0.10  # 10%
max_position_risk = 0.02   # 2%
min_rr_ratio = 2.0         # 2:1

# Moderate (intermediate)
max_portfolio_risk = 0.15  # 15%
max_position_risk = 0.03   # 3%
min_rr_ratio = 1.5         # 1.5:1

# Aggressive (advanced)
max_portfolio_risk = 0.20  # 20%
max_position_risk = 0.05   # 5%
min_rr_ratio = 1.2         # 1.2:1
```

### 3. Stop-Loss Selection

| Market Condition | Recommended Method |
|-----------------|-------------------|
| Trending | ATR-based |
| Ranging | Support/Resistance |
| High volatility | Volatility-based (wider stops) |
| Low volatility | Percentage-based |
| Profitable trade | Trailing Stop |

### 4. Performance Tracking

```python
# Update Kelly weights based on actual performance
await agent.position_sizer.kelly.update_performance(
    win_probability=0.65,  # Actual win rate
)

# Track and log decisions
# Analyze approval/rejection rates
# Adjust thresholds based on backtesting
```

## Troubleshooting

**Problem**: Too many rejections
- **Solution**: Lower min_confidence or min_rr_ratio

**Problem**: Positions too small
- **Solution**: Increase max_position_pct or adjust Kelly max_fraction

**Problem**: High portfolio risk
- **Solution**: Reduce max_single_trade_risk or increase diversification

**Problem**: Stop losses too tight
- **Solution**: Increase ATR multiplier or use wider percentage

## References

- [Kelly Criterion Theory](../docs/KELLY_CRITERION.md)
- [VaR Calculation Methods](../docs/VAR_METHODS.md)
- [Stop-Loss Strategies](../docs/STOP_LOSS_STRATEGIES.md)
- [Position Sizing](../docs/POSITION_SIZING.md)
