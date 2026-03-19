#!/bin/bash
# Pi Display - Fast installer for Raspberry Pi
#
# Usage:
#   cd ~/pi && sudo bash install.sh
#
# Uses apt packages (pre-compiled) instead of pip to avoid slow builds on Pi Zero.

set -e

RED='\033[0;31m'
GRN='\033[0;32m'
CYN='\033[0;36m'
BLD='\033[1m'
RST='\033[0m'

step()  { echo -e "\n${BLD}[$1/$TOTAL] $2${RST}"; }
ok()    { echo -e "  ${GRN}✓${RST} $1"; }
warn()  { echo -e "  ${RED}!${RST} $1"; }
info()  { echo -e "  ${CYN}→${RST} $1"; }

TOTAL=5
INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
REAL_USER="${SUDO_USER:-${USER:-pi}}"
NEED_REBOOT=false
IP_ADDR="$(hostname -I 2>/dev/null | awk '{print $1}')"

echo -e "${BLD}"
echo "  ┌─────────────────────────────┐"
echo "  │     Pi Display Installer    │"
echo "  │   E-ink Tabletop Dashboard  │"
echo "  └─────────────────────────────┘"
echo -e "${RST}"

if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}Error: Run with sudo →  sudo bash install.sh${RST}"
    exit 1
fi

# ── 1. System packages (all pre-compiled, fast) ──────────────────

step 1 "Installing system packages"
info "Updating package lists..."
apt-get update -qq

# Core + Python packages via apt (no compilation needed)
PKGS="python3 python3-pip python3-venv python3-dev git"
PKGS="$PKGS fonts-dejavu-core libopenjp2-7 libatlas-base-dev"
# libtiff6 or libtiff5 depending on OS version
apt-cache show libtiff6 >/dev/null 2>&1 && PKGS="$PKGS libtiff6" || PKGS="$PKGS libtiff5"
# Python libraries as apt packages (pre-compiled, instant install)
PKGS="$PKGS python3-flask python3-pil python3-requests python3-feedparser python3-rpi.gpio python3-spidev"

info "Installing packages..."
apt-get install -y -qq $PKGS 2>/dev/null
ok "System packages installed"

# ── 2. Enable SPI ───────────────────────────────────────────────

step 2 "Enabling SPI interface"

spi_enabled=false
for cfg in /boot/firmware/config.txt /boot/config.txt; do
    if [ -f "$cfg" ] && grep -q "^dtparam=spi=on" "$cfg" 2>/dev/null; then
        spi_enabled=true
        break
    fi
done

if [ "$spi_enabled" = false ]; then
    CONFIG_FILE="/boot/config.txt"
    [ -f /boot/firmware/config.txt ] && CONFIG_FILE="/boot/firmware/config.txt"
    echo "dtparam=spi=on" >> "$CONFIG_FILE"
    ok "SPI enabled in $CONFIG_FILE"
    NEED_REBOOT=true
else
    ok "SPI already enabled"
fi

# ── 3. Python venv + inky ────────────────────────────────────────

step 3 "Setting up Python environment"

export TMPDIR="/var/tmp/pip-build"
mkdir -p "$TMPDIR"

info "Creating venv (with system packages)..."
python3 -m venv --system-site-packages "$INSTALL_DIR/venv"

# Only pip-install inky — everything else comes from apt
pkg_name="inky"
if "$INSTALL_DIR/venv/bin/pip" show "$pkg_name" >/dev/null 2>&1; then
    ok "inky already installed — skipping"
else
    info "Installing inky[rpi] (only pip package needed)..."
    "$INSTALL_DIR/venv/bin/pip" install --no-cache-dir "inky[rpi]>=1.5" || {
        warn "Failed to install inky"
        exit 1
    }
fi
ok "Python environment ready"

# ── 4. Systemd service ──────────────────────────────────────────

step 4 "Installing system service"

cat > /etc/systemd/system/pi-display.service <<EOF
[Unit]
Description=Pi Display - E-ink Info Screen
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$REAL_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python server.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

info "Reloading systemd..."
systemctl daemon-reload
info "Enabling service..."
systemctl enable pi-display.service -q
ok "Service installed and enabled (starts on boot)"

# ── 5. File permissions ─────────────────────────────────────────

step 5 "Setting permissions"
chown -R "$REAL_USER:$REAL_USER" "$INSTALL_DIR"
ok "Files owned by $REAL_USER"

# ── Optional: prompt for API key ────────────────────────────────

echo ""
echo -e "${BLD}─── Quick Setup ───${RST}"
echo ""

EXISTING_KEY=$(python3 -c "import json; print(json.load(open('$INSTALL_DIR/config.json'))['api_keys']['openweathermap'])" 2>/dev/null || echo "")

if [ -z "$EXISTING_KEY" ]; then
    echo "  Weather & air quality need a free OpenWeatherMap API key."
    echo "  Get one at: https://home.openweathermap.org/api_keys"
    echo ""
    read -p "  Paste your API key (or press Enter to skip): " OWM_KEY
    if [ -n "$OWM_KEY" ]; then
        python3 -c "
import json
with open('$INSTALL_DIR/config.json', 'r') as f:
    cfg = json.load(f)
cfg['api_keys']['openweathermap'] = '$OWM_KEY'
with open('$INSTALL_DIR/config.json', 'w') as f:
    json.dump(cfg, f, indent=2)
"
        ok "API key saved"
    else
        info "Skipped — you can add it later via the web panel"
    fi
else
    ok "API key already configured"
fi

# ── Done ─────────────────────────────────────────────────────────

echo ""
echo -e "${BLD}${GRN}  ✓ Installation complete!${RST}"
echo ""

if [ "$NEED_REBOOT" = true ]; then
    echo -e "  ${RED}SPI was just enabled. Reboot required before starting.${RST}"
    echo ""
    read -p "  Reboot now? [Y/n] " REBOOT_ANS
    if [ "$REBOOT_ANS" != "n" ] && [ "$REBOOT_ANS" != "N" ]; then
        echo "  Rebooting... service will start automatically."
        reboot
    else
        echo "  Run 'sudo reboot' when ready, then the display starts automatically."
    fi
else
    echo "  Starting service now..."
    systemctl restart pi-display.service
    sleep 2
    if systemctl is-active --quiet pi-display.service; then
        ok "Service is running"
    else
        warn "Service may still be starting — check: journalctl -u pi-display -f"
    fi
    echo ""
    echo -e "  ${BLD}Web panel:${RST}  http://${IP_ADDR}:5000"
    echo -e "  ${BLD}Logs:${RST}       journalctl -u pi-display -f"
    echo ""
fi
