#!/bin/bash
# Multi-Agent Trading System Başlatma Scripti

set -e

# Renkler
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Multi-Agent Trading System Başlatma${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Python virtual environment kontrol
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment bulunamadı!${NC}"
    echo "Önce şunu çalıştır: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Set PYTHONPATH to project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Infrastructure kontrol
echo -e "${BLUE}📊 Infrastructure servisleri kontrol ediliyor...${NC}"
docker ps | grep trading_rabbitmq > /dev/null || { echo -e "${RED}❌ RabbitMQ çalışmıyor!${NC}"; exit 1; }
docker ps | grep trading_postgres > /dev/null || { echo -e "${RED}❌ PostgreSQL çalışmıyor!${NC}"; exit 1; }
echo -e "${GREEN}✅ Infrastructure hazır${NC}"
echo ""

# Log directory
mkdir -p logs

# Agent'ları başlat
echo -e "${BLUE}🚀 Agent'lar başlatılıyor...${NC}"

echo -e "${GREEN}1/5 Data Collection Agent...${NC}"
nohup python agents/data_collection/agent.py > logs/data_collection.log 2>&1 &
echo $! > logs/data_collection.pid
sleep 2

echo -e "${GREEN}2/5 Technical Analysis Agent...${NC}"
nohup python agents/technical_analysis/agent.py > logs/technical_analysis.log 2>&1 &
echo $! > logs/technical_analysis.pid
sleep 2

echo -e "${GREEN}3/5 Strategy Agent...${NC}"
nohup python agents/strategy/agent.py > logs/strategy.log 2>&1 &
echo $! > logs/strategy.pid
sleep 2

echo -e "${GREEN}4/5 Risk Manager Agent...${NC}"
nohup python agents/risk_manager/agent.py > logs/risk_manager.log 2>&1 &
echo $! > logs/risk_manager.pid
sleep 2

echo -e "${GREEN}5/5 Execution Agent...${NC}"
nohup python agents/execution/agent.py > logs/execution.log 2>&1 &
echo $! > logs/execution.pid
sleep 2

echo ""
echo -e "${BLUE}📋 Çalışan Agent'lar:${NC}"
ps aux | grep -E "agents/.*/agent.py" | grep -v grep

echo ""
echo -e "${GREEN}✅ Tüm agent'lar başlatıldı!${NC}"
echo ""
echo -e "${BLUE}📝 Log'ları izlemek için:${NC}"
echo "  tail -f logs/data_collection.log"
echo "  tail -f logs/technical_analysis.log"
echo "  tail -f logs/strategy.log"
echo "  tail -f logs/risk_manager.log"
echo "  tail -f logs/execution.log"
echo ""
echo -e "${BLUE}🛑 Durdurmak için:${NC}"
echo "  ./scripts/stop_agents.sh"
