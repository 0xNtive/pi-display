#!/bin/bash
# Set up pi-display to auto-start on boot
#
# Run directly on your Raspberry Pi:
#   cd ~/pi-display && sudo bash deploy.sh

set -e

RED='\033[0;31m'
GRN='\033[0;32m'
CYN='\033[0;36m'
BLD='\033[1m'
RST='\033[0m'

ok()   { echo -e "  ${GRN}✓${RST} $1"; }
info() { echo -e "  ${CYN}→${RST} $1"; }

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
REAL_USER="${SUDO_USER:-${USER:-pi}}"

echo -e "${BLD}"
echo "  ┌──────────────────────────────┐"
echo "  │  Pi Display — Auto-Start     │"
echo "  └──────────────────────────────┘"
echo -e "${RST}"

if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}Error: Run with sudo →  sudo bash deploy.sh${RST}"
    exit 1
fi

# ── 1. Venv ──────────────────────────────────────────────────────
if [ ! -d "$INSTALL_DIR/venv" ]; then
    info "Creating Python venv..."
    python3 -m venv --system-site-packages "$INSTALL_DIR/venv"
    ok "Venv created"
else
    ok "Venv exists"
fi

# ── 2. Install inky if missing ───────────────────────────────────
if ! "$INSTALL_DIR/venv/bin/pip" show inky >/dev/null 2>&1; then
    info "Installing inky[rpi]..."
    TMPDIR=/var/tmp/pip-build "$INSTALL_DIR/venv/bin/pip" install --no-cache-dir "inky[rpi]>=1.5"
    ok "inky installed"
else
    ok "inky already installed"
fi

# ── 3. Config ────────────────────────────────────────────────────
if [ ! -f "$INSTALL_DIR/config.json" ]; then
    cp "$INSTALL_DIR/config.example.json" "$INSTALL_DIR/config.json"
    chown "$REAL_USER:$REAL_USER" "$INSTALL_DIR/config.json"
    ok "Created config.json from template"
else
    ok "config.json exists"
fi

# ── 4. Systemd service ──────────────────────────────────────────
info "Installing systemd service..."
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

systemctl daemon-reload
systemctl enable pi-display.service -q
ok "Service enabled (auto-starts on boot)"

# ── 5. Start it now ─────────────────────────────────────────────
info "Starting pi-display..."
systemctl restart pi-display.service
sleep 2

if systemctl is-active --quiet pi-display.service; then
    ok "Service is running"
else
    echo "  Check logs: journalctl -u pi-display -f"
fi

# ── Done ─────────────────────────────────────────────────────────
chown -R "$REAL_USER:$REAL_USER" "$INSTALL_DIR"
IP_ADDR="$(hostname -I 2>/dev/null | awk '{print $1}')"

echo ""
echo -e "${BLD}${GRN}  ✓ Done!${RST} Pi display will auto-start on every boot."
echo ""
echo -e "  Web panel:  http://${IP_ADDR}:5000"
echo -e "  Logs:       journalctl -u pi-display -f"
echo -e "  Service:    sudo systemctl status pi-display"
echo ""
