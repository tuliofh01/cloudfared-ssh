#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Cloudflare Tunneling Setup ===${NC}"

# 1. Check for cloudflared
echo -e "\n${YELLOW}[1/3] Checking cloudflared installation...${NC}"
if ! command -v cloudflared &> /dev/null; then
    echo -e "${RED}cloudflared is not installed.${NC}"
    echo "Please install it using your package manager."
    echo "Arch Linux: sudo pacman -S cloudflared"
    exit 1
else
    echo -e "${GREEN}cloudflared is installed.$(cloudflared --version | head -n 1)${NC}"
fi

# 2. Secret Generation
echo -e "\n${YELLOW}[2/3] Configuring Security...${NC}"
if [ ! -f .env ]; then
    echo "Generating tunnel secret..."
    if command -v openssl &> /dev/null; then
        SECRET=$(openssl rand -hex 32)
    else
        SECRET="dev-secret-$(date +%s)" # Fallback
    fi
    echo "TUNNEL_SECRET=$SECRET" > .env
    echo -e "${GREEN}Generated new secret in .env${NC}"
    echo -e "${YELLOW}IMPORTANT: You must set this secret in your Cloudflare Worker settings!${NC}"
    echo "Run: npx wrangler secret put TUNNEL_SECRET"
    echo "Value: $SECRET"
    echo ""
    read -p "Press Enter when done..."
else
    echo -e "${GREEN}.env file exists. Skipping secret generation.${NC}"
fi

# 3. Migrations
echo -e "\n${YELLOW}[3/3] Running Migrations...${NC}"
echo "Running DB migrations..."
npx wrangler d1 migrations apply DB --local
echo -e "${GREEN}Migration complete.${NC}"

echo -e "\n${GREEN}=== Setup Complete ===${NC}"
echo "1. Run './build.sh' to deploy the updated Worker."
echo "2. Run './run.sh' to start the tunnel."
