# Pi Display — Setup Guide

Tabletop info screen for Raspberry Pi Zero W2 + Inky pHAT (212x104, black & white).

Cycles between stock/crypto prices, weather, air quality, and news headlines.
Includes a web panel accessible from any device to configure everything.

## Project Structure

```
pi/
├── config.json          # All settings (tickers, location, feeds, API keys)
├── data_fetchers.py     # Cached API fetchers (stocks, crypto, weather, AQ, RSS)
├── display.py           # Pillow-based renderer for 212x104 B&W Inky pHAT
├── server.py            # Flask web panel + background display cycling loop
├── templates/
│   └── panel.html       # Dark-themed mobile-friendly control panel
├── requirements.txt     # Python dependencies
├── install.sh           # One-command Pi setup (packages, SPI, venv, systemd)
└── pi-display.service   # Systemd service template
```

## How It Works

**Display** — cycles between 4 screens (all designed for 212x104 B&W):
- **Prices** — up to 5 stock/crypto tickers with symbol, price, % change
- **Weather** — large temp, conditions, hi/lo, humidity, wind
- **Air Quality** — AQI gauge bar, pollutant breakdown (PM2.5, PM10, NO2, O3)
- **Headlines** — word-wrapped headlines from RSS feeds with source labels

Uses inverted header bars (white text on black) and dotted separators for
readability on the monochrome screen.

**Data sources** (all free):
- **Stocks**: yfinance (no API key needed)
- **Crypto**: CoinGecko (no API key needed)
- **Weather + AQ**: OpenWeatherMap (free tier, 1 key covers both)
- **Headlines**: RSS feeds (no key, fully configurable)

**Web panel** at `http://<pi-ip>:5000` — dark theme, mobile-friendly:
- Add/remove stock & crypto tickers
- Set location (city, lat/lon, units)
- Toggle RSS feeds on/off, add custom feeds
- Enable/disable each screen, set cycle interval
- Pause, skip, and preview buttons
- Enter your OpenWeatherMap API key

## Install (one command)

SSH into your Pi and run:

```bash
git clone https://github.com/YOUR_USER/pi.git ~/pi-display && cd ~/pi-display && sudo bash install.sh
```

The installer handles everything:
- Installs system packages and Python dependencies
- Enables SPI (needed for the Inky pHAT)
- Creates a Python venv with all deps
- Sets up a systemd service that starts on boot
- Prompts for your free OpenWeatherMap API key
- Reboots if needed, otherwise starts the service immediately

After install, open `http://<pi-ip>:5000` from any device to configure.

## API Key

Get your free OpenWeatherMap key at:
https://home.openweathermap.org/api_keys

The free tier gives 1000 calls/day, which is more than enough.
Stocks and crypto work without any API key.

## Test Locally (No Pi Required)

```bash
pip install flask yfinance requests feedparser Pillow
python server.py --simulate
# Preview renders saved to /tmp/inkyphat_preview.png
```

## Remote Access

The web panel works on your local network out of the box. For access from
anywhere, install Tailscale (free) on both the Pi and your phone/laptop:
https://tailscale.com/

## Service Management

```bash
sudo systemctl start pi-display     # Start
sudo systemctl stop pi-display      # Stop
sudo systemctl restart pi-display   # Restart
sudo systemctl status pi-display    # Status
journalctl -u pi-display -f         # Live logs
```
