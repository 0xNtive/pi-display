#!/bin/bash
# Deploy pi-display to Raspberry Pi and set up auto-start on boot
#
# Usage (from your Mac):
#   bash deploy.sh              # uses default pi@raspberrypi.local
#   bash deploy.sh pi@10.0.0.5  # custom host
#   bash deploy.sh pi@mypi.local ~/pi-display   # custom host + remote dir

set -e

PI_HOST="${1:-pi@raspberrypi.local}"
REMOTE_DIR="${2:-/home/pi/pi-display}"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"

RED='\033[0;31m'
GRN='\033[0;32m'
CYN='\033[0;36m'
BLD='\033[1m'
RST='\033[0m'

ok()   { echo -e "  ${GRN}✓${RST} $1"; }
info() { echo -e "  ${CYN}→${RST} $1"; }
err()  { echo -e "  ${RED}✗${RST} $1"; }

echo -e "${BLD}"
echo "  ┌──────────────────────────────┐"
echo "  │    Pi Display — Deploy       │"
echo "  └──────────────────────────────┘"
echo -e "${RST}"

info "Target: ${BLD}${PI_HOST}:${REMOTE_DIR}${RST}"
echo ""

# ── 1. Check SSH connectivity ────────────────────────────────────
info "Checking SSH connection..."
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$PI_HOST" "echo ok" >/dev/null 2>&1; then
    err "Cannot reach $PI_HOST — check hostname/IP and SSH keys"
    echo "  Tip: ssh-copy-id $PI_HOST"
    exit 1
fi
ok "SSH connected"

# ── 2. Sync project files ────────────────────────────────────────
info "Syncing project files..."
rsync -az --delete \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'venv/' \
    --exclude '.git/' \
    --exclude '.DS_Store' \
    --exclude 'previews/' \
    --exclude 'config.json' \
    "$LOCAL_DIR/" "$PI_HOST:$REMOTE_DIR/"
ok "Files synced"

# ── 3. Remote setup (venv, service, start) ────────────────────────
info "Setting up on Pi (this may take a minute on first run)..."
ssh -t "$PI_HOST" bash -s "$REMOTE_DIR" <<'REMOTE_SCRIPT'
set -e
INSTALL_DIR="$1"
cd "$INSTALL_DIR"

GRN='\033[0;32m'
CYN='\033[0;36m'
RST='\033[0m'
ok()   { echo -e "  ${GRN}✓${RST} $1"; }
info() { echo -e "  ${CYN}→${RST} $1"; }

# ── Create venv if missing ──
if [ ! -d "venv" ]; then
    info "Creating Python venv..."
    python3 -m venv --system-site-packages venv
    ok "Venv created"
else
    ok "Venv exists"
fi

# ── Install inky if missing ──
if ! venv/bin/pip show inky >/dev/null 2>&1; then
    info "Installing inky[rpi]..."
    TMPDIR=/var/tmp/pip-build venv/bin/pip install --no-cache-dir "inky[rpi]>=1.5"
    ok "inky installed"
else
    ok "inky already installed"
fi

# ── Copy config template if no config.json ──
if [ ! -f "config.json" ]; then
    cp config.example.json config.json
    ok "Created config.json from template"
else
    ok "config.json exists"
fi

# ── Install systemd service ──
info "Installing systemd service..."
REAL_USER="$(whoami)"
sudo tee /etc/systemd/system/pi-display.service >/dev/null <<EOF
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

sudo systemctl daemon-reload
sudo systemctl enable pi-display.service -q
ok "Service enabled (auto-starts on boot)"

# ── Start / restart the service ──
info "Restarting pi-display..."
sudo systemctl restart pi-display.service
sleep 2

if systemctl is-active --quiet pi-display.service; then
    ok "Service is running"
else
    echo "  Check logs: journalctl -u pi-display -f"
fi

IP_ADDR="$(hostname -I 2>/dev/null | awk '{print $1}')"
echo ""
echo -e "  ${GRN}✓ Deploy complete!${RST}"
echo -e "  Web panel:  http://${IP_ADDR}:5000"
echo -e "  Logs:       journalctl -u pi-display -f"
echo -e "  Service:    sudo systemctl status pi-display"
echo ""
REMOTE_SCRIPT

echo ""
echo -e "${BLD}${GRN}  ✓ Done!${RST} Pi display is running and will auto-start on boot."
echo ""
