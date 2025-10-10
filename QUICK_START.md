# 🚀 Multi-Agent AI Trading - Quick Start

## ⚡ 3-Minute Setup

### 1️⃣ Setup (2 minutes)
```bash
git clone <your-repo>
cd multi-ai-agent-trading
chmod +x scripts/setup.sh
./scripts/setup.sh
```

### 2️⃣ Configure (30 seconds)
```bash
# Edit .env with your API keys
nano .env

# Minimum required:
OPENAI_API_KEY=sk-your-key
BINANCE_API_KEY=your-key
BINANCE_SECRET_KEY=your-secret
TRADING_MODE=paper  # IMPORTANT: Start with paper!
```

### 3️⃣ Run (30 seconds)
```bash
# Start infrastructure
docker-compose up -d

# Run agent
source venv/bin/activate
python -m agents.data_collection.agent
```

## ✅ You Should See:
```
✓ Connected to Binance
✓ Connected to InfluxDB
✓ Connected to RabbitMQ
📊 Streaming BTC/USDT, ETH/USDT, SOL/USDT
```

## 🎯 Next Steps

### Verify Everything Works
```bash
# Check services
docker-compose ps

# View messages (RabbitMQ UI)
open http://localhost:15672  # Login: trading/trading_pass

# View dashboards (Grafana)
open http://localhost:3000   # Login: admin/admin
```

### Access Your Data
```python
# In Python shell
from infrastructure.database.influxdb import get_influx
from datetime import datetime, timedelta

influx = get_influx()
data = influx.query_ohlcv(
    symbol="BTC/USDT",
    exchange="binance", 
    start_time=datetime.utcnow() - timedelta(minutes=5)
)
print(f"Collected {len(data)} candles")
```

## 📚 Full Documentation

- **Setup**: [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)
- **Status**: [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md)
- **Complete**: [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md)

## 🐛 Troubleshooting

### Issue: Services not starting
```bash
docker-compose down
docker-compose up -d
docker-compose ps
```

### Issue: Agent crashes
```bash
# Check logs
docker-compose logs -f

# Verify .env settings
cat .env
```

### Issue: No data in InfluxDB
```bash
# Check agent is running
ps aux | grep python

# Check InfluxDB health
curl http://localhost:8086/health
```

## 🎉 Success!

You now have:
- ✅ Real-time market data collection
- ✅ Time-series database storage
- ✅ Message bus for agent communication
- ✅ Complete monitoring stack
- ✅ Production-ready foundation

**Ready to build AI trading agents! 🤖📈**

---

*Need help? Read [GETTING_STARTED.md](docs/GETTING_STARTED.md)*
