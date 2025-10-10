#!/bin/bash

# Multi-Agent AI Trading System - Setup Script
# This script sets up the development environment

set -e

echo "🚀 Multi-Agent AI Trading System - Setup"
echo "========================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python version
echo -e "\n${YELLOW}Checking Python version...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3.10+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}Python $REQUIRED_VERSION or higher is required. Found: $PYTHON_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python version: $PYTHON_VERSION${NC}"

# Create virtual environment
echo -e "\n${YELLOW}Creating virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo -e "\n${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "\n${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip setuptools wheel

# Install dependencies
echo -e "\n${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt

echo -e "${GREEN}✓ Dependencies installed${NC}"

# Setup environment file
echo -e "\n${YELLOW}Setting up environment file...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env file from template${NC}"
    echo -e "${YELLOW}⚠️  Please edit .env and add your API keys${NC}"
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi

# Check for Docker
echo -e "\n${YELLOW}Checking Docker installation...${NC}"
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓ Docker is installed${NC}"

    # Check if Docker is running
    if docker info &> /dev/null; then
        echo -e "${GREEN}✓ Docker is running${NC}"
    else
        echo -e "${YELLOW}⚠️  Docker is installed but not running${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Docker is not installed (optional for development)${NC}"
fi

# Create necessary directories
echo -e "\n${YELLOW}Creating directories...${NC}"
mkdir -p logs data models

echo -e "${GREEN}✓ Directories created${NC}"

# Install TA-Lib (if not installed)
echo -e "\n${YELLOW}Checking TA-Lib...${NC}"
if python3 -c "import talib" 2>/dev/null; then
    echo -e "${GREEN}✓ TA-Lib is installed${NC}"
else
    echo -e "${YELLOW}⚠️  TA-Lib is not installed${NC}"
    echo -e "${YELLOW}   Install instructions:${NC}"
    echo -e "   macOS: brew install ta-lib"
    echo -e "   Ubuntu: sudo apt-get install ta-lib"
    echo -e "   Then: pip install TA-Lib"
fi

# Summary
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\nNext steps:"
echo -e "1. Edit .env file with your API keys"
echo -e "2. Start infrastructure: ${YELLOW}docker-compose up -d${NC}"
echo -e "3. Run migrations: ${YELLOW}./scripts/migrate.sh${NC}"
echo -e "4. Run tests: ${YELLOW}pytest${NC}"
echo -e "5. Start agents: ${YELLOW}python -m agents.data_collection.agent${NC}"

echo -e "\nUseful commands:"
echo -e "  Activate venv:  ${YELLOW}source venv/bin/activate${NC}"
echo -e "  Run tests:      ${YELLOW}pytest tests/${NC}"
echo -e "  Code format:    ${YELLOW}black .${NC}"
echo -e "  Type check:     ${YELLOW}mypy .${NC}"
echo -e "  Lint:           ${YELLOW}ruff check .${NC}"

echo -e "\nHappy trading! 📈"
