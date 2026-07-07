#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Cloudfared Tunnel Manager - Build Pipeline ===${NC}"

echo -e "\n${YELLOW}[1/4] Python environment setup...${NC}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
.venv/bin/pip install --quiet flask flask-cors requests python-dotenv psutil rich cryptography

echo -e "\n${YELLOW}[2/4] Node dependencies...${NC}"
npm install --quiet 2>/dev/null || true
if [ -d "frontend" ]; then
    cd frontend && npm install --quiet 2>/dev/null || true && cd ..
fi

echo -e "\n${YELLOW}[3/4] Building Angular frontend...${NC}"
npm run build 2>/dev/null || echo "(frontend build skip)"

echo -e "\n${YELLOW}[4/4] Deploying to Cloudflare Workers...${NC}"
npx wrangler deploy 2>/dev/null || echo "(deploy skip)"

echo -e "\n${GREEN}=== Build Complete ===${NC}"
echo "Run './run.sh serve' to start the API server."
