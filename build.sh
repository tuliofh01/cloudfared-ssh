#!/bin/bash
set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

echo -e "${GREEN}=== cloudfared-tunneling — Build Pipeline ===${NC}"

echo -e "\n${YELLOW}[1/3] Python virtual environment...${NC}"
if [ ! -d ".venv" ]; then python3 -m venv .venv; fi

echo -e "\n${YELLOW}[2/3] Installing dependencies...${NC}"
.venv/bin/pip install --quiet flask flask-cors requests python-dotenv psutil rich cryptography pytest

echo -e "\n${YELLOW}[3/3] Running tests...${NC}"
.venv/bin/python -m pytest tests/ -v

echo -e "\n${GREEN}=== Build Complete ===${NC}"
echo "Run './run.sh serve' to start the API server."
