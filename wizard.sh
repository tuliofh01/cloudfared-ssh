#!/bin/bash
set -e

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[ OK ]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail()  { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    else
        echo "unknown"
    fi
}

DISTRO=$(detect_distro)
info "Detected distribution: ${CYAN}$DISTRO${NC}"

install_cloudflared() {
    case "$DISTRO" in
        arch|manjaro)
            sudo pacman -Syu --noconfirm cloudflared 2>/dev/null || {
                warn "cloudflared not in repos, trying AUR..."
                if command -v yay &>/dev/null; then yay -S --noconfirm cloudflared
                elif command -v paru &>/dev/null; then paru -S --noconfirm cloudflared
                else fail "Install yay/paru first or get cloudflared from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
                fi
            }
            ;;
        debian|ubuntu|zorin)
            sudo mkdir -p /usr/share/keyrings && \
            curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null && \
            echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/cloudflared.list && \
            sudo apt update && sudo apt install -y cloudflared
            ;;
        fedora)
            sudo dnf install -y cloudflared 2>/dev/null || \
            curl -fsSL https://pkg.cloudflare.com/cloudflared.repo | sudo tee /etc/yum.repos.d/cloudflared.repo && \
            sudo dnf install -y cloudflared
            ;;
        opensuse*)
            sudo zypper install -y cloudflared 2>/dev/null || \
            fail "cloudflared not found in openSUSE repos. Manual install: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
            ;;
        *)
            fail "Unsupported distro: $DISTRO. Manual install: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
            ;;
    esac
    ok "cloudflared installed: $(cloudflared --version)"
}

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

show_help() {
    echo "Usage: bash wizard.sh [--check|--help]"
    echo ""
    echo "  --check    Check prerequisites (distro, cloudflared, Python)"
    echo "  --help     Show this help"
    echo ""
    echo "Without arguments, runs the full interactive setup wizard."
    exit 0
}

if [ "$1" = "--help" ]; then show_help; fi
if [ "$1" = "--check" ]; then
    info "Distribution: $(detect_distro)"
    if command -v cloudflared &>/dev/null; then ok "cloudflared: $(cloudflared --version 2>&1 | head -1)"
    else warn "cloudflared not installed"
    fi
    if python3 -c "import flask, rich, psutil, requests" 2>/dev/null; then ok "Python deps satisfied"
    else warn "Python deps missing (run: pip install -r <(echo))"
    fi
    exit 0
fi

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  cloudfared-tunneling Setup Wizard${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# Step 1: cloudflared
if ! command -v cloudflared &>/dev/null; then
    warn "cloudflared not found"
    read -rp "Install cloudflared? [Y/n] " ans
    if [[ "$ans" =~ ^[Nn]$ ]]; then info "Skip cloudflared install"
    else install_cloudflared
    fi
else
    ok "cloudflared: $(cloudflared --version 2>&1 | head -1)"
fi

# Step 2: Python venv
if [ ! -f "$PROJECT_DIR/.venv/bin/python" ]; then
    info "Creating Python virtual environment..."
    python3 -m venv "$PROJECT_DIR/.venv"
fi
info "Installing Python dependencies..."
"$PROJECT_DIR/.venv/bin/pip" install --quiet flask flask-cors requests python-dotenv psutil rich cryptography
ok "Python deps installed"

# Step 3: systemd service
SERVICE_FILE="$PROJECT_DIR/scripts/tunnel.service"
if [ -f "$SERVICE_FILE" ]; then
    info "Installing systemd service..."
    sudo cp "$SERVICE_FILE" /etc/systemd/system/cloudfared-tunnel.service
    sudo systemctl daemon-reload
    sudo systemctl enable cloudfared-tunnel.service
    ok "systemd service installed & enabled"
    info "Start with: sudo systemctl start cloudfared-tunnel"
fi

# Step 4: Polybar module (optional)
if [ -d "$HOME/.config/polybar" ]; then
    read -rp "Add Polybar tunnel module? [Y/n] " ans
    if [[ "$ans" =~ ^[Nn]$ ]]; then info "Skip Polybar module"
    else
        mkdir -p "$HOME/.config/polybar/scripts"
        cat > "$HOME/.config/polybar/scripts/tunnel_status.sh" << 'POLYBAR'
#!/bin/bash
~/cloudfared-tunneling/.venv/bin/python -m cloudfared_tunnel.main --polybar
POLYBAR
        chmod +x "$HOME/.config/polybar/scripts/tunnel_status.sh"

        MODULE_FILE="$HOME/.config/polybar/user_modules.ini"
        if [ -f "$MODULE_FILE" ] && grep -q "cloudfared-tunnel" "$MODULE_FILE" 2>/dev/null; then
            info "Polybar module already exists"
        else
            cat >> "$MODULE_FILE" << 'EOF'

[module/cloudfared-tunnel]
type = custom/script
exec = ~/.config/polybar/scripts/tunnel_status.sh
interval = 5
click-left = curl -s -X POST http://localhost:5000/api/tunnel/start >/dev/null
click-right = curl -s -X POST http://localhost:5000/api/tunnel/stop >/dev/null
format = <label>
label = %output%
EOF
            ok "Polybar module added to $MODULE_FILE"
            info "Add 'cloudfared-tunnel' to your bar modules in bars.ini"
        fi
    fi
fi

# Step 5: Shell aliases
read -rp "Add shell aliases (tunnel-wizard, tunnel-status, tunnel-ui) to ~/.zshrc? [Y/n] " ans
if [[ "$ans" =~ ^[Nn]$ ]]; then info "Skip aliases"
else
    ALIAS_FILE="$HOME/.zshrc"
    if [ ! -f "$ALIAS_FILE" ]; then ALIAS_FILE="$HOME/.bashrc"; fi
    grep -q "tunnel-wizard" "$ALIAS_FILE" 2>/dev/null && info "Aliases already exist" || {
        echo "" >> "$ALIAS_FILE"
        echo "# cloudfared-tunneling aliases" >> "$ALIAS_FILE"
        echo "alias tunnel-wizard='bash $PROJECT_DIR/wizard.sh'" >> "$ALIAS_FILE"
        echo "alias tunnel-status='$PROJECT_DIR/.venv/bin/python -m cloudfared_tunnel.main status'" >> "$ALIAS_FILE"
        echo "alias tunnel-ui='$PROJECT_DIR/.venv/bin/python -m cloudfared_tunnel.main --serve'" >> "$ALIAS_FILE"
        ok "Aliases added to $ALIAS_FILE"
    }
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "  Quick commands:"
echo "    tunnel-status     # Check tunnel status"
echo "    tunnel-ui         # Start API server (port 5000)"
echo "    tunnel-wizard     # Re-run this wizard"
echo ""
echo "  Or directly:"
echo "    .venv/bin/python -m cloudfared_tunnel.main start"
echo "    .venv/bin/python -m cloudfared_tunnel.main --serve"
echo ""
