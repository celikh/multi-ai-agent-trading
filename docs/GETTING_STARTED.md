## 🚀 Getting Started Guide

This guide will help you set up and run the Multi-Agent AI Trading System locally.

---

## Prerequisites

### Required
- **Python 3.10+** - [Download](https://www.python.org/downloads/)
- **Docker & Docker Compose** - [Download](https://www.docker.com/products/docker-desktop)
- **Git** - [Download](https://git-scm.com/downloads)

### Optional
- **TA-Lib** - For technical analysis (installation instructions below)
- **PostgreSQL Client** - For database management
- **Make** - For convenient commands

### Minimum Hardware
- **CPU**: 4 cores
- **RAM**: 16 GB
- **Storage**: 50 GB free space
- **Network**: Stable internet connection

---

## 📦 Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd multi-ai-agent-trading
```

### Step 2: Run Setup Script

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

This script will:
- ✅ Check Python version
- ✅ Create virtual environment
- ✅ Install dependencies
- ✅ Create .env file
- ✅ Setup directories

### Step 3: Configure Environment

Edit the `.env` file with your API keys:

```bash
# Open in your editor
nano .env
# or
code .env
```

**Required Configuration:**
```env
# OpenAI API (for AI agents)
OPENAI_API_KEY=sk-your-actual-openai-key

# Exchange API (at least one)
BINANCE_API_KEY=your-binance-api-key
BINANCE_SECRET_KEY=your-binance-secret

# Set trading mode
TRADING_MODE=paper  # Start with paper trading!
```

### Step 4: Install TA-Lib (Optional but Recommended)

#### macOS
```bash
brew install ta-lib
pip install TA-Lib
```

#### Ubuntu/Debian
```bash
sudo apt-get install ta-lib
pip install TA-Lib
```

#### Windows
Download from: http://mrjbq7.github.io/ta-lib/install.html

---

## 🐳 Start Infrastructure

### Option 1: All Services (Recommended for first run)

```bash
docker-compose up -d
```

This starts:
- PostgreSQL (with TimescaleDB)
- InfluxDB
- RabbitMQ
- Prometheus
- Grafana

### Option 2: Essential Services Only

```bash
docker-compose up -d postgres influxdb rabbitmq
```

### Verify Services

```bash
# Check all services are running
docker-compose ps

# Check PostgreSQL
docker-compose exec postgres psql -U trading_user -d trading_db -c "SELECT version();"

# Check InfluxDB
curl -I http://localhost:8086/health

# Check RabbitMQ
curl -u trading:trading_pass http://localhost:15672/api/overview
```

---

## 🗄️ Database Setup

### Initialize PostgreSQL Schema

```bash
# Run migrations
docker-compose exec postgres psql -U trading_user -d trading_db -f /docker-entrypoint-initdb.d/schema.sql
```

Or manually:
```bash
psql -h localhost -U trading_user -d trading_db -f infrastructure/database/schema.sql
```

### Verify Database Setup

```bash
# Connect to database
docker-compose exec postgres psql -U trading_user -d trading_db

# List tables
\dt

# Should see: trades, positions, signals, risk_assessments, etc.
\q
```

---

## 🤖 Run Your First Agent

### Activate Virtual Environment

```bash
source venv/bin/activate
```

### Run Data Collection Agent

```bash
python -m agents.data_collection.agent
```

You should see:
```
🚀 Data Collection Agent starting...
✓ Connected to Binance
✓ Connected to InfluxDB
✓ Connected to RabbitMQ
📊 Streaming BTC/USDT, ETH/USDT, SOL/USDT
```

### Test in Another Terminal

```bash
# Activate venv
source venv/bin/activate

# Check InfluxDB for data
python << EOF
from infrastructure.database.influxdb import get_influx
from datetime import datetime, timedelta

influx = get_influx()
data = influx.query_ohlcv(
    symbol="BTC/USDT",
    exchange="binance",
    start_time=datetime.utcnow() - timedelta(minutes=5)
)
print(f"Got {len(data)} candles")
for candle in data[:3]:
    print(candle)
EOF
```

---

## 🧪 Run Tests

### Run All Tests

```bash
pytest
```

### Run Specific Tests

```bash
# Unit tests only
pytest tests/unit

# Integration tests
pytest tests/integration

# With coverage
pytest --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html
```

---

## 📊 Access Dashboards

### RabbitMQ Management
- **URL**: http://localhost:15672
- **User**: trading
- **Pass**: trading_pass

### Grafana (Visualization)
- **URL**: http://localhost:3000
- **User**: admin
- **Pass**: admin

### Prometheus (Metrics)
- **URL**: http://localhost:9090

---

## 🔧 Development Workflow

### 1. Start Development Environment

```bash
# Start infrastructure
docker-compose up -d

# Activate virtual environment
source venv/bin/activate

# Run agent in development mode
python -m agents.data_collection.agent
```

### 2. Code Quality

```bash
# Format code
black .

# Lint
ruff check .

# Type check
mypy .

# Run all checks
black . && ruff check . && mypy .
```

### 3. Testing Workflow

```bash
# Run tests
pytest

# Watch mode (re-run on changes)
pytest-watch

# Specific test
pytest tests/unit/test_data_collection.py -v
```

---

## 🐛 Troubleshooting

### Issue: "Database connection failed"

**Solution:**
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Restart PostgreSQL
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

### Issue: "InfluxDB connection failed"

**Solution:**
```bash
# Check InfluxDB health
curl http://localhost:8086/health

# Restart InfluxDB
docker-compose restart influxdb

# Check token in .env matches docker-compose.yml
```

### Issue: "RabbitMQ connection failed"

**Solution:**
```bash
# Check RabbitMQ
docker-compose ps rabbitmq

# Access management UI
open http://localhost:15672

# Check credentials in .env
```

### Issue: "Module not found"

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "Exchange API rate limit"

**Solution:**
```bash
# Check rate limits in logs
grep "rate_limit" logs/*.log

# Adjust interval in agent:
python -m agents.data_collection.agent --interval 5m
```

---

## 📚 Next Steps

### 1. Configure Paper Trading

```env
# In .env
TRADING_MODE=paper
MAX_POSITION_SIZE_PCT=2.0
```

### 2. Add More Symbols

```python
# In agents/data_collection/agent.py
symbols=["BTC/USDT", "ETH/USDT", "SOL/USDT", "AVAX/USDT"]
```

### 3. Implement Analysis Agents

```bash
# Coming soon:
python -m agents.technical_analysis.agent
python -m agents.strategy.agent
```

### 4. Run Backtests

```bash
# Coming soon:
python -m backtesting.engine --strategy momentum --start 2024-01-01
```

---

## 🔐 Security Best Practices

### API Keys
- ✅ Never commit `.env` file
- ✅ Use read-only keys for paper trading
- ✅ Enable IP whitelist on exchange
- ✅ Use 2FA for exchange accounts

### Database
- ✅ Use strong passwords
- ✅ Don't expose ports in production
- ✅ Regular backups
- ✅ Encrypt sensitive data

### Network
- ✅ Use TLS for all connections
- ✅ Firewall rules
- ✅ VPN for remote access

---

## 📞 Support

### Documentation
- [Project Status](PROJECT_STATUS.md)
- [Architecture](ARCHITECTURE.md) (coming soon)
- [API Reference](API.md) (coming soon)

### Community
- GitHub Issues: Report bugs
- Discussions: Ask questions
- Wiki: Additional guides

### Logs & Debugging

```bash
# View application logs
tail -f logs/agent.log

# View Docker logs
docker-compose logs -f data_collector

# Enable debug logging
export LOG_LEVEL=DEBUG
python -m agents.data_collection.agent
```

---

## 🎯 Quick Reference

### Common Commands

```bash
# Environment
source venv/bin/activate           # Activate venv
deactivate                         # Deactivate venv

# Docker
docker-compose up -d               # Start all services
docker-compose down                # Stop all services
docker-compose logs -f <service>   # View logs
docker-compose restart <service>   # Restart service

# Database
psql -h localhost -U trading_user -d trading_db  # Connect to PostgreSQL
docker-compose exec influxdb influx              # Connect to InfluxDB

# Testing
pytest                             # Run all tests
pytest -v                          # Verbose output
pytest --cov                       # With coverage
pytest -k test_name               # Specific test

# Code Quality
black .                           # Format code
ruff check .                      # Lint code
mypy .                            # Type check
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TRADING_MODE` | Trading mode (paper/live) | `paper` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `POSTGRES_HOST` | PostgreSQL host | `localhost` |
| `INFLUXDB_URL` | InfluxDB URL | `http://localhost:8086` |
| `RABBITMQ_HOST` | RabbitMQ host | `localhost` |

---

## ✅ Checklist

Before you start:
- [ ] Python 3.10+ installed
- [ ] Docker running
- [ ] .env file configured
- [ ] API keys obtained
- [ ] Virtual environment created
- [ ] Dependencies installed
- [ ] Infrastructure running
- [ ] Database schema loaded
- [ ] First agent tested

You're ready to trade! 📈

---

**Happy Trading!** 🚀
