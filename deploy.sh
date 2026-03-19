#!/bin/bash
# Enable pi-display to auto-start on boot
#
# Run on your Raspberry Pi:
#   cd ~/pi-display && sudo bash deploy.sh

set -e

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
REAL_USER="${SUDO_USER:-${USER:-pi}}"

if [ "$(id -u)" -ne 0 ]; then
    echo "Error: Run with sudo →  sudo bash deploy.sh"
    exit 1
fi

# ── Install systemd service ─────────────────────────────────────
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
systemctl enable pi-display.service
systemctl restart pi-display.service

echo ""
echo "Done. pi-display will auto-start on every boot."
echo ""
echo "  Status:  sudo systemctl status pi-display"
echo "  Logs:    journalctl -u pi-display -f"
echo ""
