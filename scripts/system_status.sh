#!/bin/bash
# Multi-Agent Trading System - Durum Kontrolü

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Trading System Durum Kontrolü${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Docker servisleri
echo -e "${BLUE}📊 Docker Servisleri:${NC}"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep trading

echo -e "\n${BLUE}🤖 Çalışan Agent'lar:${NC}"
AGENT_COUNT=$(ps aux | grep 'agents/.*agent.py' | grep -v grep | wc -l | tr -d ' ')
if [ "$AGENT_COUNT" -eq 5 ]; then
    echo -e "${GREEN}✅ Tüm agent'lar çalışıyor ($AGENT_COUNT/5)${NC}"
    ps aux | grep 'agents/.*agent.py' | grep -v grep | awk '{print "  - " $NF}'
else
    echo -e "${RED}⚠️  Sadece $AGENT_COUNT/5 agent çalışıyor${NC}"
    ps aux | grep 'agents/.*agent.py' | grep -v grep | awk '{print "  - " $NF}'
fi

echo -e "\n${BLUE}📨 RabbitMQ Durumu:${NC}"
docker exec trading_rabbitmq rabbitmqctl list_connections name state channels 2>/dev/null | grep running | wc -l | xargs -I {} echo "  Bağlantılar: {} aktif"
docker exec trading_rabbitmq rabbitmqctl list_queues name messages consumers 2>/dev/null | tail -n +2 | wc -l | xargs -I {} echo "  Kuyruklar: {} adet"

echo -e "\n${BLUE}💾 PostgreSQL Durumu:${NC}"
docker exec trading_postgres psql -U trading -d trading_system -c 'SELECT 1' > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ PostgreSQL bağlantısı OK${NC}"
else
    echo -e "${RED}❌ PostgreSQL bağlantı hatası${NC}"
fi

echo -e "\n${BLUE}📝 Son Log Mesajları:${NC}"
echo -e "${YELLOW}Data Collection:${NC}"
tail -2 logs/data_collection.log 2>/dev/null | head -1 || echo "  Log yok"

echo -e "${YELLOW}Technical Analysis:${NC}"
tail -2 logs/technical_analysis.log 2>/dev/null | head -1 || echo "  Log yok"

echo -e "${YELLOW}Strategy:${NC}"
tail -2 logs/strategy.log 2>/dev/null | head -1 || echo "  Log yok"

echo -e "\n${BLUE}🌐 Erişim Noktaları:${NC}"
echo "  Grafana: http://192.168.1.150:3000"
echo "  Prometheus: http://192.168.1.150:9090"

echo -e "\n${BLUE}========================================${NC}"
