#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# cloudfared-tunnel — VM Setup Script
# ═══════════════════════════════════════════════════════════════
# Interactive script that configures a fresh Linux machine with:
#   • cloudflared tunnel (token-based, systemd-managed)
#   • "duke" sudoer user for remote SSH access
#   • Shell aliases (tunnel, cloudssh)
# Usage:  sudo bash src/scripts/setup-vm.sh
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

# ── Colors ──────────────────────────────────────────────────────
BOLD='\033[1m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; CYAN='\033[0;36m'; GRAY='\033[90m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[ OK ]${NC}   $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $1"; exit 1; }
header(){ echo -e "\n${BOLD}─── $1 ───${NC}"; }

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# ── Root check ──────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    fail "Please run as root: sudo bash src/scripts/setup-vm.sh"
fi

clear
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║       cloudfared-tunneling — VM Setup                   ║"
echo "║       Expose this machine via Cloudflare Tunnel         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ═══════════════════════════════════════════════════════════════
# STEP 1: System packages
# ═══════════════════════════════════════════════════════════════
header "System Dependencies"

if command -v pacman &>/dev/null; then
    pacman -Sy --noconfirm cloudflared python python-pip git openssh 2>/dev/null || true
elif command -v apt &>/dev/null; then
    apt update -qq && apt install -y -qq cloudflared python3 python3-pip python3-venv git openssh-server 2>/dev/null || true
elif command -v dnf &>/dev/null; then
    dnf install -y cloudflared python3 python3-pip git openssh-server 2>/dev/null || true
fi
ok "System packages installed"

# ═══════════════════════════════════════════════════════════════
# STEP 2: Create duke sudoer user (no password — set on TUI)
# ═══════════════════════════════════════════════════════════════
header "Sudoer User (duke)"

read -rp "Create 'duke' sudoer user? [Y/n] " ans
if [[ ! "$ans" =~ ^[Nn]$ ]]; then
    if id "duke" &>/dev/null; then
        info "User 'duke' already exists"
        if groups duke | grep -q wheel; then
            ok "duke is in wheel group"
        else
            usermod -aG wheel duke
            ok "Added duke to wheel group"
        fi
    else
        useradd -m -G wheel -s /bin/bash duke
        # Lock account — password set on first TUI launch
        passwd -d duke
        ok "User 'duke' created — password will be set on first TUI launch"
    fi
    # SSH key setup
    if [[ ! -d /home/duke/.ssh ]]; then
        mkdir -p /home/duke/.ssh
        chmod 700 /home/duke/.ssh
    fi
    echo ""
    echo -e "  ${BOLD}Remote SSH access:${NC}"
    echo "    ssh duke@$(hostname -I | awk '{print $1}')"
    echo "    (set password via TUI: python3 -m src)"
    echo ""
fi

# ═══════════════════════════════════════════════════════════════
# STEP 3: Cloudflare Tunnel Token
# ═══════════════════════════════════════════════════════════════
header "Cloudflare Tunnel"

TOKEN_FILE="/home/duke/.cloudflared/tunnel-token"
if [[ -f "$TOKEN_FILE" ]]; then
    info "Tunnel token found at $TOKEN_FILE"
    read -rp "  Replace it? [y/N] " replace
    if [[ "$replace" =~ ^[Yy]$ ]]; then
        read -rp "  Paste your tunnel token: " token
        mkdir -p "$(dirname "$TOKEN_FILE")"
        echo "$token" > "$TOKEN_FILE"
        chmod 600 "$TOKEN_FILE"
        ok "Token saved"
    fi
else
    read -rp "Paste your Cloudflare tunnel token (or leave blank to skip): " token
    if [[ -n "$token" ]]; then
        mkdir -p "$(dirname "$TOKEN_FILE")"
        echo "$token" > "$TOKEN_FILE"
        chmod 600 "$TOKEN_FILE"
        ok "Token saved to $TOKEN_FILE"
    else
        warn "No token provided — tunnel will not start"
        warn "You can add it later: echo 'TOKEN' > $TOKEN_FILE"
    fi
fi

# ── Install systemd service ─────────────────────────────────────
if [[ -f "$TOKEN_FILE" ]]; then
    cp "$PROJECT_DIR/src/scripts/cloudflared-tunnel.service" /etc/systemd/system/
    sed -i "s|%h/.cloudfared-tunnel/src/scripts/run-cloudflared-tunnel.sh|$PROJECT_DIR/src/scripts/run-cloudflared-tunnel.sh|" /etc/systemd/system/cloudflared-tunnel.service
    systemctl daemon-reload
    systemctl enable cloudflared-tunnel.service
    systemctl restart cloudflared-tunnel.service
    ok "cloudflared-tunnel.service installed and started"
    sleep 2
    systemctl status cloudflared-tunnel.service --no-pager | head -5
fi

# ═══════════════════════════════════════════════════════════════
# STEP 4: Shell Aliases (for duke)
# ═══════════════════════════════════════════════════════════════
header "Shell Aliases"

add_aliases() {
    local user_home="$1"
    local rc_file="$user_home/.zshrc"
    [[ ! -f "$rc_file" ]] && rc_file="$user_home/.bashrc"

    grep -q "cloudfared-tunneling" "$rc_file" 2>/dev/null && return 0

    cat >> "$rc_file" << 'EOF'

# ── cloudfared-tunnel ────────────────────────────────────────
alias tunnel='python3 -m src'
alias cloudssh='echo -e "\033[1;36m╔══════════════════════════════════════════════════════╗\033[0m"; echo -e "\033[1;36m║ Connect from another machine                         ║\033[0m"; echo -e "\033[1;36m╚══════════════════════════════════════════════════════╝\033[0m"; echo ""; echo -e "\033[1;33m1.\033[0m Install cloudflared on client"; echo -e "\033[1;33m2.\033[0m Add to ~/.ssh/config: ProxyCommand cloudflared access ssh --hostname %h"; echo -e "\033[1;33m3.\033[0m Connect: ssh duke@ssh.your-domain.com"
EOF
}

add_aliases "/root"
if id "duke" &>/dev/null; then
    add_aliases "/home/duke"
    chown duke:duke "/home/duke/.zshrc" 2>/dev/null || true
    chown duke:duke "/home/duke/.bashrc" 2>/dev/null || true
fi
ok "Aliases added to shell rc files"

# ═══════════════════════════════════════════════════════════════
# STEP 5: Verify
# ═══════════════════════════════════════════════════════════════
header "Verification"

cd "$PROJECT_DIR"
echo -e "  ${BOLD}Service:${NC}"
systemctl is-active cloudflared-tunnel.service &>/dev/null && ok "cloudflared-tunnel: active" || warn "cloudflared-tunnel: inactive"

# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Setup Complete!                                         ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Quick commands:"
echo "    tunnel            Launch TUI dashboard"
echo "    cloudssh          Show SSH connection instructions"
echo ""
echo "  SSH access:"
echo "    ssh duke@$(hostname -I | awk '{print $1}')    (set password via TUI)"
echo ""
echo -e "  ${GRAY}To connect from anywhere, set up your domain in Cloudflare${NC}"
echo -e "  ${GRAY}Zero Trust dashboard and configure the ingress rule.${NC}"
echo ""
