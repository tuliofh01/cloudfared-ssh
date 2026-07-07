#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# cloudfared-tunneling — VM Setup Script
# ═══════════════════════════════════════════════════════════════
# Interactive script that configures a fresh Linux machine with:
#   • cloudflared tunnel (token-based, systemd-managed)
#   • "duke" sudoer user for remote SSH access
#   • Polybar toggle widget
#   • Shell aliases (tunnel-status, tunnel-ui, cloudssh)
#
# Usage:  sudo bash scripts/setup-vm.sh
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
    fail "Please run as root: sudo bash scripts/setup-vm.sh"
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
# STEP 2: Create duke sudoer user
# ═══════════════════════════════════════════════════════════════
header "Sudoer User (duke)"

read -rp "Create 'duke' sudoer user? [Y/n] " ans
if [[ ! "$ans" =~ ^[Nn]$ ]]; then
    if id "duke" &>/dev/null; then
        info "User 'duke' already exists"
        read -rp "  Set/reset password? [Y/n] " setpw
        if [[ ! "$setpw" =~ ^[Nn]$ ]]; then
            echo "duke:1123581321" | chpasswd
            ok "Password set to Fibonacci sequence: ${GRAY}1123581321${NC}"
        fi
        if groups duke | grep -q wheel; then
            ok "duke is in wheel group"
        else
            usermod -aG wheel duke
            ok "Added duke to wheel group"
        fi
    else
        useradd -m -G wheel -s /bin/bash duke
        echo "duke:1123581321" | chpasswd
        ok "User 'duke' created, password: ${GRAY}1123581321${NC}"
        info "Fibonacci sequence (1,1,2,3,5,8,13,21 + ...)"
    fi
    # SSH key setup
    if [[ ! -d /home/duke/.ssh ]]; then
        mkdir -p /home/duke/.ssh
        chmod 700 /home/duke/.ssh
        # If current user has an SSH key, copy it
        if [[ -f /home/tuliofh01/.ssh/authorized_keys ]]; then
            cp /home/tuliofh01/.ssh/authorized_keys /home/duke/.ssh/
            chmod 600 /home/duke/.ssh/authorized_keys
            chown -R duke:duke /home/duke/.ssh
            ok "Copied SSH authorized_keys to duke"
        fi
    fi
    echo ""
    echo -e "  ${BOLD}Remote SSH access:${NC}"
    echo "    ssh duke@$(hostname -I | awk '{print $1}')"
    echo "    Password: 1123581321"
    echo ""
fi

# ═══════════════════════════════════════════════════════════════
# STEP 3: Python environment
# ═══════════════════════════════════════════════════════════════
header "Python Environment"

cd "$PROJECT_DIR"
if [[ ! -d .venv ]]; then
    python3 -m venv .venv
    ok "Virtual environment created"
fi
.venv/bin/pip install -q flask flask-cors requests python-dotenv psutil rich cryptography pytest
ok "Python dependencies installed"

# ═══════════════════════════════════════════════════════════════
# STEP 4: Cloudflare Tunnel Token
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
    # Copy service to systemd
    cp "$PROJECT_DIR/scripts/cloudflared-tunnel.service" /etc/systemd/system/
    # Adjust path in service file for root
    sed -i "s|/home/tuliofh01/cloudfared-tunneling|$PROJECT_DIR|g" /etc/systemd/system/cloudflared-tunnel.service
    sed -i "s|Environment=HOME=/home/tuliofh01|Environment=HOME=/root|" /etc/systemd/system/cloudflared-tunnel.service

    systemctl daemon-reload
    systemctl enable cloudflared-tunnel.service
    systemctl restart cloudflared-tunnel.service
    ok "cloudflared-tunnel.service installed and started"

    # Show status
    sleep 2
    systemctl status cloudflared-tunnel.service --no-pager | head -5
fi

# ═══════════════════════════════════════════════════════════════
# STEP 5: Shell Aliases (for duke)
# ═══════════════════════════════════════════════════════════════
header "Shell Aliases"

add_aliases() {
    local user_home="$1"
    local rc_file="$user_home/.zshrc"
    [[ ! -f "$rc_file" ]] && rc_file="$user_home/.bashrc"
    
    grep -q "cloudfared-tunneling" "$rc_file" 2>/dev/null && return 0
    
    cat >> "$rc_file" << 'EOF'

# ── cloudfared-tunneling ─────────────────────────────────────
alias tunnel-status='python3 -m cloudfared_tunnel.main status'
alias tunnel-ui='python3 -m cloudfared_tunnel.main --serve'
alias cloudssh='echo -e "\033[1;36m╔══════════════════════════════════════════════════════╗\033[0m"; echo -e "\033[1;36m║  Connect to this machine from another computer        ║\033[0m"; echo -e "\033[1;36m╚══════════════════════════════════════════════════════╝\033[0m"; echo ""; echo -e "\033[1;33m1.\033[0m Install \033[1mcloudflared\033[0m on the client: brew install cloudflared"; echo ""; echo -e "\033[1;33m2.\033[0m Add to \033[1m~/.ssh/config\033[0m:"; echo "   Host ssh.your-domain.com"; echo "       ProxyCommand cloudflared access ssh --hostname %h"; echo ""; echo -e "\033[1;33m3.\033[0m Connect: ssh your-user@ssh.your-domain.com"
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
# STEP 6: Polybar (if available)
# ═══════════════════════════════════════════════════════════════
header "Polybar Widget"

if command -v polybar &>/dev/null; then
    for user_home in /home/*; do
        user="$(basename "$user_home")"
        [[ "$user" == "duke" ]] || continue
        POLYBAR_DIR="$user_home/.config/polybar"
        mkdir -p "$POLYBAR_DIR/scripts"
        
        # Copy toggle script
        cp "$PROJECT_DIR/scripts/cloudflared-toggle.sh" "$POLYBAR_DIR/scripts/" 2>/dev/null || true
        
        # Add module
        if ! grep -q "cloudfared-tunnel" "$POLYBAR_DIR/user_modules.ini" 2>/dev/null; then
            cat >> "$POLYBAR_DIR/user_modules.ini" 2>/dev/null << 'EOF'

[module/cloudfared-tunnel]
type = custom/script
exec = ~/.config/polybar/scripts/cloudflared-toggle.sh
interval = 5
click-left = ~/.config/polybar/scripts/cloudflared-toggle.sh toggle
format = <label>
label = %output%
EOF
        fi
        ok "Polybar module added for user '$user'"
    done
else
    info "Polybar not installed — skip widget setup"
fi

# ═══════════════════════════════════════════════════════════════
# STEP 7: Verify
# ═══════════════════════════════════════════════════════════════
header "Verification"

cd "$PROJECT_DIR"
echo -e "  ${BOLD}CLI:${NC}"
python3 -m cloudfared_tunnel.main status || warn "Tunnel not running"

echo -e "\n  ${BOLD}Tests:${NC}"
.venv/bin/python -m pytest tests/ -q 2>/dev/null && ok "All tests passing" || warn "Tests need attention"

echo -e "\n  ${BOLD}Services:${NC}"
systemctl is-active cloudflared-tunnel.service &>/dev/null && ok "cloudflared-tunnel: active" || warn "cloudflared-tunnel: inactive"

# ═══════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Setup Complete!                                         ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Quick commands:"
echo "    tunnel-status     Check tunnel state"
echo "    tunnel-ui         Start API dashboard (:5000)"
echo "    cloudssh          Show SSH connection instructions"
echo ""
echo "  SSH access:"
echo "    ssh duke@$(hostname -I | awk '{print $1}')    (password: 1123581321)"
echo ""
echo -e "  ${GRAY}To connect from anywhere, set up your domain in Cloudflare${NC}"
echo -e "  ${GRAY}Zero Trust dashboard and configure the ingress rule.${NC}"
echo ""
