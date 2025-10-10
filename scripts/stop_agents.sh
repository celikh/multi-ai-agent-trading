#!/bin/bash
# Multi-Agent Trading System Durdurma Scripti

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Multi-Agent Trading System Durdurma${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# PID dosyalarından agent'ları durdur
for pidfile in logs/*.pid; do
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile")
        agent_name=$(basename "$pidfile" .pid)

        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${BLUE}🛑 Durduruluyor: ${agent_name}${NC}"
            kill "$pid"
            rm "$pidfile"
        else
            echo -e "${RED}⚠️  Zaten durdurulmuş: ${agent_name}${NC}"
            rm "$pidfile"
        fi
    fi
done

# Emin olmak için process'leri kontrol et
remaining=$(ps aux | grep -E "agents/.*/agent.py" | grep -v grep | wc -l)
if [ "$remaining" -gt 0 ]; then
    echo ""
    echo -e "${RED}⚠️  Bazı agent'lar hala çalışıyor, zorla kapatılıyor...${NC}"
    pkill -f "agents/.*/agent.py"
fi

echo ""
echo -e "${GREEN}✅ Tüm agent'lar durduruldu!${NC}"
