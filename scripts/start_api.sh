#!/bin/bash
# Start FastAPI backend server for dashboard

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Starting Dashboard API Server${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Virtual environment kontrol
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment bulunamadı!${NC}"
    echo "Önce şunu çalıştır: python -m venv venv && source venv/bin/activate"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Install API requirements
echo -e "${BLUE}📦 API dependencies kontrol ediliyor...${NC}"
pip install -q -r api/requirements.txt
echo -e "${GREEN}✅ Dependencies hazır${NC}"
echo ""

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Create log directory
mkdir -p logs

# Start API server
echo -e "${GREEN}🚀 API Server başlatılıyor...${NC}"
echo -e "${BLUE}URL: http://192.168.1.150:8000${NC}"
echo -e "${BLUE}Docs: http://192.168.1.150:8000/docs${NC}"
echo ""

# Run API server
cd api && uvicorn main:app --host 0.0.0.0 --port 8000 --reload
