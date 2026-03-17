#!/bin/bash
# Pi Display - Setup script for Raspberry Pi Zero W2
# Run with: sudo bash install.sh

set -e

echo "==============================="
echo "  Pi Display - Setup"
echo "==============================="

# Check if running on Pi
if [ ! -f /proc/device-tree/model ]; then
    echo "Warning: Not running on a Raspberry Pi. Continuing anyway..."
fi

# System packages
echo "[1/5] Installing system packages..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv python3-dev \
    fonts-dejavu-core libopenjp2-7 libtiff5 libatlas-base-dev

# Enable SPI (required for Inky pHAT)
echo "[2/5] Enabling SPI..."
if ! grep -q "^dtparam=spi=on" /boot/config.txt 2>/dev/null && \
   ! grep -q "^dtparam=spi=on" /boot/firmware/config.txt 2>/dev/null; then
    CONFIG_FILE="/boot/config.txt"
    [ -f /boot/firmware/config.txt ] && CONFIG_FILE="/boot/firmware/config.txt"
    echo "dtparam=spi=on" >> "$CONFIG_FILE"
    echo "  SPI enabled (reboot required)"
else
    echo "  SPI already enabled"
fi

# Python venv
INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "[3/5] Setting up Python venv in $INSTALL_DIR/venv ..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# Systemd service
echo "[4/5] Installing systemd service..."
REAL_USER="${SUDO_USER:-pi}"
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

echo "[5/5] Setup complete!"
echo ""
echo "==============================="
echo "  Next steps:"
echo "==============================="
echo ""
echo "  1. Get a free OpenWeatherMap API key:"
echo "     https://home.openweathermap.org/api_keys"
echo ""
echo "  2. Start the service:"
echo "     sudo systemctl start pi-display"
echo ""
echo "  3. Access the web panel:"
echo "     http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "  4. Enter your API key in the web panel"
echo ""
echo "  To view logs:"
echo "     journalctl -u pi-display -f"
echo ""
echo "  To test without hardware (on any machine):"
echo "     ./venv/bin/python server.py --simulate"
echo ""
echo "  If SPI was just enabled, REBOOT first:"
echo "     sudo reboot"
echo ""
