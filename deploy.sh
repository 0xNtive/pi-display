#!/bin/bash
# Set up pi-display service + auto-updater on boot
#
# Run on your Raspberry Pi:
#   cd ~/pi && sudo bash deploy.sh

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

# ── Install auto-updater (checks GitHub every 5 min) ────────────
cat > /etc/systemd/system/pi-display-updater.service <<EOF
[Unit]
Description=Pi Display Auto-Updater
After=network-online.target

[Service]
Type=oneshot
User=$REAL_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/bin/bash $INSTALL_DIR/autoupdate.sh
EOF

cat > /etc/systemd/system/pi-display-updater.timer <<EOF
[Unit]
Description=Check for pi-display updates every 5 minutes

[Timer]
OnBootSec=120
OnUnitActiveSec=300
RandomizedDelaySec=30

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable pi-display.service
systemctl restart pi-display.service
systemctl enable --now pi-display-updater.timer

echo ""
echo "Done. pi-display will auto-start on every boot."
echo "Auto-updater checks GitHub every 5 minutes."
echo ""
echo "  Status:   sudo systemctl status pi-display"
echo "  Updates:  sudo systemctl status pi-display-updater.timer"
echo "  Logs:     journalctl -u pi-display -f"
echo ""
