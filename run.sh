#!/bin/bash
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Cloudfared Tunnel Manager ===${NC}"

# Check for cloudflared
if ! command -v cloudflared &> /dev/null; then
    echo -e "${RED}cloudflared is not installed.${NC}"
    echo "Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
    exit 1
fi

# Check venv
if [ ! -f ".venv/bin/python" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv .venv
    .venv/bin/pip install flask flask-cors requests python-dotenv psutil rich cryptography
fi

CMD=".venv/bin/python -m cloudfared_tunnel.main"

case "${1:-status}" in
    serve|server|--serve)
        echo -e "${GREEN}Starting API server on port 5000...${NC}"
        exec $CMD --serve
        ;;
    start)
        echo -e "${YELLOW}Starting tunnel...${NC}"
        exec $CMD start
        ;;
    stop)
        echo -e "${YELLOW}Stopping tunnel...${NC}"
        exec $CMD stop
        ;;
    status)
        exec $CMD status
        ;;
    logs)
        exec $CMD logs
        ;;
    health)
        exec $CMD health
        ;;
    *)
        echo "Usage: $0 {serve|start|stop|status|logs|health}"
        exit 1
        ;;
esac
