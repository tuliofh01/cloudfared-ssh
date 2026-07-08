#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# cloudfared-tunnel — One-command VM setup (user-level systemd)
# ═══════════════════════════════════════════════════════════════
# Usage:  sudo bash src/scripts/setup.sh
#
# What it does:
#   1. Install cloudflared (Arch/Debian/Fedora/openSUSE)
#   2. Create 'duke' sudoer user (password set on first TUI run)
#   3. Save tunnel token  → ~/.cloudflared/tunnel-token
#   4. Install systemd user service → cloudflared-tunnel.service
#   5. Enable linger + start tunnel
#   6. Add shell aliases (tunnel, cloudssh)
# ═══════════════════════════════════════════════════════════════

set -euo pipefail
BOLD='\033[1m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $1"; }
ok()    { echo -e "${GREEN}[ OK ]${NC}   $1"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $1"; exit 1; }
header(){ echo -e "\n${BOLD}─── $1 ───${NC}"; }

[[ $EUID -ne 0 ]] && fail "Run as root: sudo bash src/scripts/setup.sh"

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
clear
echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════╗"
echo "║     cloudfared-tunnel — VM Setup                        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ── 1. Install cloudflared ─────────────────────────────────────────
header "Install cloudflared"
if command -v cloudflared &>/dev/null; then
    ok "Already installed: $(cloudflared --version 2>&1 | head -1)"
else
    if   command -v pacman &>/dev/null; then pacman -Sy --noconfirm cloudflared
    elif command -v apt   &>/dev/null; then
        curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
        echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -sc) main" | tee /etc/apt/sources.list.d/cloudflared.list
        apt update -qq && apt install -y -qq cloudflared
    elif command -v dnf   &>/dev/null; then
        curl -fsSL https://pkg.cloudflare.com/cloudflared.repo | tee /etc/yum.repos.d/cloudflared.repo
        dnf install -y cloudflared
    else fail "Unsupported distro — install cloudflared manually"
    fi
    ok "cloudflared installed: $(cloudflared --version 2>&1 | head -1)"
fi

# ── 2. Create duke user (no password — set on first TUI run) ───────
header "Sudoer user (duke)"
if ! id duke &>/dev/null; then
    useradd -m -G wheel -s /bin/bash duke
    # Lock account — password will be set on first TUI launch
    passwd -d duke
    ok "User 'duke' created — password will be set on first TUI launch"
else
    usermod -aG wheel duke 2>/dev/null || true
    ok "User 'duke' already exists"
fi
# Copy SSH keys from current user if available
if [[ -d ~/.ssh ]]; then
    mkdir -p /home/duke/.ssh
    cp ~/.ssh/authorized_keys /home/duke/.ssh/ 2>/dev/null || true
    chmod 600 /home/duke/.ssh/authorized_keys 2>/dev/null || true
    chown -R duke:duke /home/duke/.ssh 2>/dev/null || true
fi

# ── 3. Tunnel token ────────────────────────────────────────────────
header "Tunnel token"
echo "Get it from: https://dash.cloudflare.com → Zero Trust → Networks → Tunnels"
echo "(Create a tunnel named 'ssh-tunnel', public hostname: ssh.your-domain.com → SSH → localhost:22)"
echo ""
read -rp "Paste your tunnel token (eyJ...): " TOKEN
if [[ -z "$TOKEN" ]]; then
    fail "No token provided. Run again with a valid token."
fi

for dir in /home/duke /root; do
    mkdir -p "$dir/.cloudflared"
    echo "$TOKEN" > "$dir/.cloudflared/tunnel-token"
    chmod 600 "$dir/.cloudflared/tunnel-token"
done
chown -R duke:duke /home/duke/.cloudflared
ok "Token saved to ~/.cloudflared/tunnel-token"

# ── 4. Systemd user service ────────────────────────────────────────
header "Systemd user service (user-level)"

_install_user_service() {
    local user="$1" home="$2"
    local uid
    uid=$(id -u "$user" 2>/dev/null) || return 0
    local user_systemd="$home/.config/systemd/user"
    mkdir -p "$user_systemd"
    cp "$PROJECT_DIR/src/scripts/cloudflared-tunnel.service" "$user_systemd/"
    # Fix ExecStart path to point to actual project location
    sed -i "s|%h/.cloudfared-tunnel/src/scripts/run-cloudflared-tunnel.sh|$PROJECT_DIR/src/scripts/run-cloudflared-tunnel.sh|" "$user_systemd/cloudflared-tunnel.service"
    chown -R "$user": "$user_systemd"
    loginctl enable-linger "$user" 2>/dev/null || true
    XDG_RUNTIME_DIR="/run/user/$uid" sudo -u "$user" systemctl --user daemon-reload 2>/dev/null || true
    XDG_RUNTIME_DIR="/run/user/$uid" sudo -u "$user" systemctl --user enable cloudflared-tunnel.service 2>/dev/null || true
    XDG_RUNTIME_DIR="/run/user/$uid" sudo -u "$user" systemctl --user start cloudflared-tunnel.service 2>/dev/null || true
}

_install_user_service duke /home/duke
ok "User service installed & started (linger enabled)"

# ── 5. Shell aliases ───────────────────────────────────────────────
header "Shell aliases"
_add_alias() {
    local user="$1" home="$2"
    local rc="$home/.zshrc"
    [[ -f "$rc" ]] || rc="$home/.bashrc"
    [[ -f "$rc" ]] || return 0
    grep -q "cloudfared-tunnel" "$rc" && return 0
    cat >> "$rc" << 'EOF'

# ── cloudfared-tunnel ──────────────────────────────────────────
alias tunnel='python3 -m src'
alias cloudssh='echo -e "\033[1;36m╔══════════════════════════════════════════════════════╗\033[0m"; echo -e "\033[1;36m║ Connect from another machine                         ║\033[0m"; echo -e "\033[1;36m╚══════════════════════════════════════════════════════╝\033[0m"; echo ""; echo "  ssh duke@ssh.your-domain.com  (requires cloudflared + ProxyCommand)"'
EOF
    chown "$user": "$rc" 2>/dev/null || true
}
_add_alias root /root
_add_alias duke /home/duke
ok "Aliases added (tunnel, cloudssh)"

# ── 6. Verify ──────────────────────────────────────────────────────
header "Verification"
sleep 2
uid=$(id -u duke 2>/dev/null) || true
if [[ -n "$uid" ]]; then
    status=$(XDG_RUNTIME_DIR="/run/user/$uid" sudo -u duke systemctl --user is-active cloudflared-tunnel.service 2>/dev/null || echo "inactive")
    if [[ "$status" == "active" ]]; then
        ok "duke: tunnel ACTIVE"
    else
        info "duke: tunnel $status"
    fi
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Setup Complete                                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  TUI dashboard:  tunnel"
echo "  First run:      python3 -m src   (will prompt for duke password)"
echo "  Cloudflare:     https://dash.cloudflare.com → Zero Trust"
echo ""
