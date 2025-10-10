#!/bin/bash
# Multi-Agent Trading System - Gerçek Zamanlı İzleme

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Clear screen
clear

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        Multi-Agent Trading System - Live Monitor          ║${NC}"
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}\n"

while true; do
    # Cursor'ı yukarı taşı
    tput cup 3 0

    # Timestamp
    echo -e "${CYAN}📅 $(date '+%Y-%m-%d %H:%M:%S')${NC}\n"

    # Agent Durumu
    echo -e "${BLUE}━━━ 🤖 AGENT'LAR ━━━${NC}"
    AGENT_COUNT=$(ps aux | grep 'agents/.*agent.py' | grep -v grep | wc -l | tr -d ' ')
    if [ "$AGENT_COUNT" -eq 5 ]; then
        echo -e "${GREEN}✅ Tüm agent'lar çalışıyor ($AGENT_COUNT/5)${NC}"
    else
        echo -e "${RED}⚠️  Sadece $AGENT_COUNT/5 agent çalışıyor${NC}"
    fi

    # RabbitMQ Kuyruk İstatistikleri
    echo -e "\n${BLUE}━━━ 📨 RABBITMQ KUYRUKLARI ━━━${NC}"
    docker exec trading_rabbitmq rabbitmqctl list_queues name messages consumers 2>/dev/null | tail -n +2 | while read queue msgs consumers; do
        if [ -n "$queue" ]; then
            if [ "$msgs" -gt 0 ]; then
                echo -e "${YELLOW}📬 $queue: ${msgs} mesaj, ${consumers} consumer${NC}"
            else
                echo -e "${GREEN}✓ $queue: ${msgs} mesaj, ${consumers} consumer${NC}"
            fi
        fi
    done

    # Son Log Aktiviteleri
    echo -e "\n${BLUE}━━━ 📝 SON LOG AKTİVİTELERİ ━━━${NC}"
    echo -e "${CYAN}Data Collection:${NC}"
    tail -1 logs/data_collection.log 2>/dev/null | jq -r '.event + " - " + .timestamp' 2>/dev/null || tail -1 logs/data_collection.log 2>/dev/null | cut -c1-80

    echo -e "${CYAN}Technical Analysis:${NC}"
    tail -1 logs/technical_analysis.log 2>/dev/null | jq -r '.event + " - " + .timestamp' 2>/dev/null || tail -1 logs/technical_analysis.log 2>/dev/null | cut -c1-80

    echo -e "${CYAN}Strategy:${NC}"
    tail -1 logs/strategy.log 2>/dev/null | jq -r '.event + " - " + .timestamp' 2>/dev/null || tail -1 logs/strategy.log 2>/dev/null | cut -c1-80

    echo -e "${CYAN}Risk Manager:${NC}"
    tail -1 logs/risk_manager.log 2>/dev/null | jq -r '.event + " - " + .timestamp' 2>/dev/null || tail -1 logs/risk_manager.log 2>/dev/null | cut -c1-80

    echo -e "${CYAN}Execution:${NC}"
    tail -1 logs/execution.log 2>/dev/null | jq -r '.event + " - " + .timestamp' 2>/dev/null || tail -1 logs/execution.log 2>/dev/null | cut -c1-80

    # PostgreSQL Stats
    echo -e "\n${BLUE}━━━ 💾 VERITABANI İSTATİSTİKLERİ ━━━${NC}"
    TRADE_COUNT=$(docker exec trading_postgres psql -U trading -d trading_system -t -c 'SELECT COUNT(*) FROM trades' 2>/dev/null | tr -d ' ')
    SIGNAL_COUNT=$(docker exec trading_postgres psql -U trading -d trading_system -t -c 'SELECT COUNT(*) FROM signals' 2>/dev/null | tr -d ' ')
    echo -e "${GREEN}📊 Trade'ler: ${TRADE_COUNT:-0}${NC}"
    echo -e "${GREEN}📡 Sinyaller: ${SIGNAL_COUNT:-0}${NC}"

    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Çıkmak için CTRL+C${NC}"

    # 2 saniye bekle
    sleep 2
done
