# 🚀 Production Deployment Guide

**Multi-Agent AI Trading System**
**Version**: 1.0.0
**Last Updated**: 2025-10-10

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Docker Deployment](#docker-deployment)
4. [Monitoring Setup](#monitoring-setup)
5. [Health Checks](#health-checks)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum**:
- CPU: 4 cores
- RAM: 8GB
- Disk: 50GB SSD
- OS: Linux (Ubuntu 20.04+), macOS, Windows with WSL2

**Recommended**:
- CPU: 8 cores
- RAM: 16GB
- Disk: 100GB SSD
- Network: 100Mbps+

### Software Dependencies

```bash
# Docker & Docker Compose
docker --version  # >= 24.0.0
docker-compose --version  # >= 2.20.0

# Python (for development)
python3 --version  # >= 3.11

# PostgreSQL Client (optional)
psql --version  # >= 14
```

---

## Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd Multi\ AI\ Agent\ Trading
```

### 2. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit with your settings
vim .env
```

**Required Variables**:

```bash
# Database
POSTGRES_DB=trading_system
POSTGRES_USER=trading
POSTGRES_PASSWORD=<secure_password>

# RabbitMQ
RABBITMQ_USER=trading
RABBITMQ_PASSWORD=<secure_password>

# InfluxDB
INFLUXDB_TOKEN=<secure_token>
INFLUXDB_ORG=trading_org
INFLUXDB_BUCKET=market_data

# Exchange (for live trading)
EXCHANGE_API_KEY=<your_api_key>
EXCHANGE_API_SECRET=<your_api_secret>
EXCHANGE_TESTNET=true  # Set to false for live trading

# Monitoring
GRAFANA_ADMIN_PASSWORD=<secure_password>
```

### 3. Security Setup

```bash
# Generate secure passwords
openssl rand -base64 32  # For PostgreSQL
openssl rand -base64 32  # For RabbitMQ
openssl rand -base64 64  # For InfluxDB token

# Update .env with generated passwords
```

---

## Docker Deployment

### 1. Build Images

```bash
# Build all agent images
docker-compose -f docker-compose.production.yml build

# Or build individually
docker build -t trading/risk-manager ./agents/risk_manager
docker build -t trading/execution ./agents/execution
```

### 2. Start Infrastructure

```bash
# Start infrastructure services only
docker-compose -f docker-compose.production.yml up -d \
  postgresql rabbitmq influxdb grafana prometheus

# Wait for services to be healthy
docker-compose -f docker-compose.production.yml ps
```

### 3. Initialize Database

```bash
# Run database migrations
docker-compose -f docker-compose.production.yml exec postgresql \
  psql -U trading -d trading_system -f /docker-entrypoint-initdb.d/init.sql

# Verify tables
docker-compose -f docker-compose.production.yml exec postgresql \
  psql -U trading -d trading_system -c "\dt"
```

### 4. Start Trading Agents

```bash
# Start all agents
docker-compose -f docker-compose.production.yml up -d \
  data_collection technical_analysis strategy risk_manager execution

# Check agent status
docker-compose -f docker-compose.production.yml ps
docker-compose -f docker-compose.production.yml logs -f
```

### 5. Verify Deployment

```bash
# Check all services are running
docker-compose -f docker-compose.production.yml ps

# Expected output:
# NAME                    STATUS    PORTS
# agent_data_collection   Up        healthy
# agent_technical_...     Up        healthy
# agent_strategy          Up        healthy
# agent_risk_manager      Up        healthy
# agent_execution         Up        healthy
# trading_postgres        Up        healthy
# trading_rabbitmq        Up        healthy
# trading_influxdb        Up        healthy
# trading_grafana         Up        3000
# trading_prometheus      Up        9090
```

---

## Monitoring Setup

### 1. Access Grafana

```bash
# Open Grafana in browser
http://localhost:3000

# Default credentials
Username: admin
Password: admin123  # Change this!
```

### 2. Import Dashboards

**Trading System Dashboard**:
1. Go to Dashboards → Import
2. Upload `monitoring/grafana/dashboards/trading-system.json`
3. Select PostgreSQL as datasource
4. Click Import

**Metrics to Monitor**:
- Trade execution rate
- Win/Loss ratio
- Portfolio P&L
- Position count
- Order slippage
- Agent health status

### 3. Setup Alerts

**Critical Alerts**:
```yaml
- Agent Down (any agent stops)
- Database Connection Lost
- RabbitMQ Queue Full
- High Slippage (>1%)
- Portfolio Drawdown (>10%)
```

**Configure in Grafana**:
1. Dashboard → Panel → Alert
2. Set conditions
3. Configure notification channels (Email, Slack, etc.)

---

## Health Checks

### 1. Agent Health

```bash
# Check individual agent health
curl http://localhost:8000/health  # data_collection
curl http://localhost:8001/health  # technical_analysis
curl http://localhost:8002/health  # strategy
curl http://localhost:8003/health  # risk_manager
curl http://localhost:8004/health  # execution

# Expected response: {"status": "healthy", "uptime": 3600}
```

### 2. Database Health

```bash
# PostgreSQL
docker-compose exec postgresql pg_isready -U trading

# Check recent trades
docker-compose exec postgresql psql -U trading -d trading_system -c \
  "SELECT COUNT(*) FROM trades WHERE execution_time > NOW() - INTERVAL '1 hour';"
```

### 3. Message Queue Health

```bash
# RabbitMQ
curl -u trading:trading123 http://localhost:15672/api/queues

# Check message rates
curl -u trading:trading123 http://localhost:15672/api/overview
```

---

## Operations

### Starting/Stopping System

```bash
# Stop all services
docker-compose -f docker-compose.production.yml down

# Stop preserving data
docker-compose -f docker-compose.production.yml stop

# Start all services
docker-compose -f docker-compose.production.yml up -d

# Restart specific agent
docker-compose -f docker-compose.production.yml restart risk_manager
```

### Logs Management

```bash
# View all logs
docker-compose -f docker-compose.production.yml logs -f

# View specific agent logs
docker-compose -f docker-compose.production.yml logs -f risk_manager

# Filter by time
docker-compose -f docker-compose.production.yml logs --since 1h

# Export logs
docker-compose -f docker-compose.production.yml logs > system.log
```

### Backup & Restore

**Database Backup**:
```bash
# Backup PostgreSQL
docker-compose exec postgresql pg_dump -U trading trading_system > backup.sql

# Restore
docker-compose exec -T postgresql psql -U trading trading_system < backup.sql
```

**InfluxDB Backup**:
```bash
# Backup InfluxDB
docker-compose exec influxdb influx backup /tmp/backup
docker cp trading_influxdb:/tmp/backup ./influx_backup

# Restore
docker cp ./influx_backup trading_influxdb:/tmp/backup
docker-compose exec influxdb influx restore /tmp/backup
```

---

## Troubleshooting

### Common Issues

#### 1. Agent Won't Start

**Symptoms**: Agent container exits immediately

**Debug**:
```bash
# Check logs
docker-compose logs risk_manager

# Common causes:
# - Database not ready → Wait for PostgreSQL health check
# - RabbitMQ connection failed → Check credentials
# - Missing environment variables → Verify .env file
```

**Fix**:
```bash
# Restart with dependency wait
docker-compose up -d postgresql rabbitmq
sleep 30
docker-compose up -d risk_manager
```

#### 2. High Memory Usage

**Symptoms**: System slowdown, OOM errors

**Debug**:
```bash
# Check container stats
docker stats

# Identify high memory container
docker-compose top
```

**Fix**:
```bash
# Add memory limits to docker-compose.yml
services:
  risk_manager:
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
```

#### 3. Database Connection Errors

**Symptoms**: "Connection refused" in logs

**Debug**:
```bash
# Test database connection
docker-compose exec risk_manager \
  psql -h postgresql -U trading -d trading_system

# Check PostgreSQL logs
docker-compose logs postgresql
```

**Fix**:
```bash
# Ensure PostgreSQL is healthy
docker-compose ps postgresql

# Restart database
docker-compose restart postgresql
```

#### 4. RabbitMQ Queue Buildup

**Symptoms**: Messages not being processed

**Debug**:
```bash
# Check queue depth
curl -u trading:trading123 \
  http://localhost:15672/api/queues/%2F/trade.order

# Check consumer count
curl -u trading:trading123 \
  http://localhost:15672/api/consumers
```

**Fix**:
```bash
# Restart slow consumer
docker-compose restart execution

# Purge queue if needed (BE CAREFUL!)
curl -u trading:trading123 -X DELETE \
  http://localhost:15672/api/queues/%2F/trade.order/contents
```

---

## Performance Tuning

### PostgreSQL

```sql
-- Add indexes for common queries
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_execution_time ON trades(execution_time);
CREATE INDEX idx_positions_status ON positions(status);

-- Analyze tables
ANALYZE trades;
ANALYZE positions;
ANALYZE risk_assessments;
```

### RabbitMQ

```bash
# Increase message TTL
rabbitmqctl set_policy TTL ".*" '{"message-ttl":3600000}' --apply-to queues

# Set queue length limit
rabbitmqctl set_policy queue-limit ".*" '{"max-length":10000}' --apply-to queues
```

### Docker

```yaml
# In docker-compose.production.yml
services:
  execution:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
    environment:
      - PYTHONUNBUFFERED=1
      - WORKERS=4
```

---

## Security Best Practices

### 1. Secrets Management

```bash
# Use Docker secrets instead of environment variables
echo "secure_password" | docker secret create postgres_password -

# Reference in docker-compose.yml
services:
  postgresql:
    secrets:
      - postgres_password
```

### 2. Network Isolation

```yaml
# Separate networks for different services
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # No external access
```

### 3. SSL/TLS

```bash
# Enable PostgreSQL SSL
docker-compose exec postgresql \
  psql -U trading -c "ALTER SYSTEM SET ssl = on;"

# Generate certificates
openssl req -new -x509 -days 365 -nodes \
  -out server.crt -keyout server.key
```

---

## Monitoring Checklist

### Daily
- [ ] Check agent health status
- [ ] Review error logs
- [ ] Verify trade execution
- [ ] Check portfolio P&L
- [ ] Monitor system resources

### Weekly
- [ ] Database backup
- [ ] Review performance metrics
- [ ] Check disk space
- [ ] Update dependencies
- [ ] Review trading strategy performance

### Monthly
- [ ] Security audit
- [ ] Performance optimization
- [ ] Disaster recovery test
- [ ] Documentation update

---

## Emergency Procedures

### System Shutdown

```bash
# Graceful shutdown
docker-compose -f docker-compose.production.yml down --timeout 60

# Force shutdown (if needed)
docker-compose -f docker-compose.production.yml kill
```

### Disaster Recovery

```bash
# 1. Stop all services
docker-compose down

# 2. Restore database
docker-compose up -d postgresql
docker-compose exec -T postgresql psql -U trading < backup.sql

# 3. Restore InfluxDB
docker-compose up -d influxdb
docker-compose exec influxdb influx restore /backup

# 4. Start agents
docker-compose up -d
```

---

## Support

**Documentation**: `docs/`
**Logs**: `docker-compose logs`
**Health**: `http://localhost:3000` (Grafana)
**Issues**: File in project repository

---

**Deployment Status**: Ready for Production ✅
**Last Tested**: 2025-10-10
**Next Review**: 2025-11-10
