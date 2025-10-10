# 🚀 Quick Command Reference

## Start/Stop Services

### Start All Infrastructure
```bash
docker-compose -f docker-compose.production.yml up -d
```

### Stop All Services
```bash
docker-compose -f docker-compose.production.yml down
```

### Restart Specific Service
```bash
docker-compose -f docker-compose.production.yml restart [service_name]
# Example: docker-compose -f docker-compose.production.yml restart trading_postgres
```

## Check Status

### View All Services
```bash
docker-compose -f docker-compose.production.yml ps
```

### View Logs
```bash
# All services
docker-compose -f docker-compose.production.yml logs -f

# Specific service
docker-compose -f docker-compose.production.yml logs -f trading_postgres
```

### Check Database
```bash
# Connect to PostgreSQL
docker exec -it trading_postgres psql -U trading -d trading_system

# List tables
docker exec trading_postgres psql -U trading -d trading_system -c '\dt'

# View recent trades
docker exec trading_postgres psql -U trading -d trading_system -c 'SELECT * FROM trades ORDER BY created_at DESC LIMIT 10;'
```

### Check RabbitMQ
```bash
# List queues
docker exec trading_rabbitmq rabbitmqctl list_queues

# List exchanges
docker exec trading_rabbitmq rabbitmqctl list_exchanges
```

## Run Agents

### Activate Virtual Environment
```bash
cd ~/projects/multi-ai-agent-trading
source venv/bin/activate
```

### Run Individual Agents
```bash
# Data Collection Agent
python agents/data_collection/agent.py

# Technical Analysis Agent
python agents/technical_analysis/agent.py

# Strategy Agent
python agents/strategy/agent.py

# Risk Manager Agent
python agents/risk_manager/agent.py

# Execution Agent
python agents/execution/agent.py
```

### Run All Agents (Background)
```bash
# In separate terminals or use screen/tmux
python agents/data_collection/agent.py &
python agents/technical_analysis/agent.py &
python agents/strategy/agent.py &
python agents/risk_manager/agent.py &
python agents/execution/agent.py &
```

## Run Tests

### Integration Tests
```bash
python scripts/test_integration.py
```

### Paper Trading Demo
```bash
python scripts/paper_trading.py
```

### Backtesting
```bash
python scripts/backtesting_engine.py
```

### Individual Agent Tests
```bash
python scripts/test_technical_analysis.py
python scripts/test_strategy.py
python scripts/test_risk_manager.py
python scripts/test_execution.py
```

## Monitor System

### Open Dashboards
```bash
# RabbitMQ Management
open http://mac-mini:15672  # trading/trading123

# Grafana
open http://mac-mini:3000   # admin/admin

# Prometheus
open http://mac-mini:9090
```

### View Metrics
```bash
# Container stats
docker stats

# Service health
docker-compose -f docker-compose.production.yml ps

# Disk usage
docker system df
```

## Maintenance

### Update Code
```bash
# From local machine
rsync -avz --exclude 'venv' --exclude '__pycache__' --exclude '.git' \
  /Users/hasancelik/Development/Projects/Multi AI Agent Trading/ \
  mac-mini:~/projects/multi-ai-agent-trading/
```

### Backup Database
```bash
docker exec trading_postgres pg_dump -U trading trading_system > backup_$(date +%Y%m%d).sql
```

### Restore Database
```bash
cat backup_20251010.sql | docker exec -i trading_postgres psql -U trading -d trading_system
```

### Clean Up
```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Full cleanup
docker system prune -a --volumes
```

## Troubleshooting

### Service Won't Start
```bash
# Check logs
docker-compose -f docker-compose.production.yml logs [service_name]

# Recreate service
docker-compose -f docker-compose.production.yml up -d --force-recreate [service_name]
```

### Port Conflicts
```bash
# Check what's using a port
lsof -i :5432
lsof -i :5672

# Kill process using port
kill -9 $(lsof -t -i:5432)
```

### Reset Everything
```bash
# Stop and remove all
docker-compose -f docker-compose.production.yml down -v

# Restart from scratch
docker-compose -f docker-compose.production.yml up -d
```

---

**Service URLs**:
- RabbitMQ: http://mac-mini:15672
- Grafana: http://mac-mini:3000
- Prometheus: http://mac-mini:9090
- InfluxDB: http://mac-mini:8086
- PostgreSQL: mac-mini:5434
