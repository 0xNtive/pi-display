"""Main server: Flask web panel + display cycling loop."""

import json
import os
import sys
import time
import logging
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify
import requests as http_requests

import data_fetchers as fetchers
import display

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Config management
# ---------------------------------------------------------------------------

def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)


# ---------------------------------------------------------------------------
# Display state
# ---------------------------------------------------------------------------

_state = {
    "current_screen": "prices",
    "screen_index": 0,
    "last_update": {},
    "paused": False,
    "simulate": "--simulate" in sys.argv,
}


def _get_enabled_screens(cfg):
    order = ["prices", "weather", "air_quality", "headlines", "system"]
    enabled = cfg["display"]["screens_enabled"]
    return [s for s in order if enabled.get(s, False)]


def _is_night_mode(cfg):
    """Check if current time is within quiet hours."""
    night = cfg["display"].get("night_mode", {})
    if not night.get("enabled", False):
        return False
    now = datetime.now()
    hour = now.hour
    start = night.get("start_hour", 23)
    end = night.get("end_hour", 7)
    if start > end:  # wraps midnight (e.g. 23-7)
        return hour >= start or hour < end
    return start <= hour < end


def _cycle_display(cfg):
    """Render and display the next screen."""
    if _is_night_mode(cfg):
        log.info("Night mode active — skipping refresh")
        return

    screens = _get_enabled_screens(cfg)
    if not screens:
        display.display_image(
            display.render_error("No screens enabled. Use web panel to configure."),
            simulate=_state["simulate"],
        )
        return

    idx = _state["screen_index"] % len(screens)
    screen = screens[idx]
    _state["current_screen"] = screen
    _state["screen_index"] = idx + 1

    img = None

    if screen == "prices":
        tickers = []
        stocks = fetchers.fetch_stocks(cfg["tickers"]["stocks"])
        if stocks:
            tickers.extend(stocks)
        crypto = fetchers.fetch_crypto(cfg["tickers"]["crypto"])
        if crypto:
            tickers.extend(crypto)
        img = display.render_prices(tickers)

    elif screen == "weather":
        w = cfg["weather"]
        data = fetchers.fetch_weather(
            w["lat"], w["lon"],
            cfg["api_keys"]["openweathermap"],
            w.get("units", "imperial"),
        )
        img = display.render_weather(data, w.get("city_name", ""))

    elif screen == "air_quality":
        w = cfg["weather"]
        data = fetchers.fetch_air_quality(
            w["lat"], w["lon"],
            cfg["api_keys"].get("iqair", ""),
        )
        img = display.render_air_quality(data, w.get("city_name", ""))

    elif screen == "headlines":
        data = fetchers.fetch_headlines(cfg["headlines"]["feeds"])
        img = display.render_headlines(data or [])

    elif screen == "system":
        img = display.render_system_info()

    if img:
        display.display_image(img, simulate=_state["simulate"])
        _state["last_update"][screen] = time.strftime("%H:%M:%S")
        log.info("Displayed: %s", screen)


def _display_loop():
    """Background thread that cycles through screens."""
    time.sleep(3)  # let Flask start
    while True:
        if not _state["paused"]:
            try:
                cfg = load_config()
                _cycle_display(cfg)
            except Exception as e:
                log.error("Display loop error: %s", e)
        cfg = load_config()
        interval = cfg["display"].get("cycle_seconds", 45)
        time.sleep(interval)


# ---------------------------------------------------------------------------
# Web routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("panel.html")


@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(load_config())


@app.route("/api/config", methods=["POST"])
def update_config():
    cfg = load_config()
    updates = request.json

    if "tickers" in updates:
        cfg["tickers"] = updates["tickers"]
    if "weather" in updates:
        cfg["weather"] = updates["weather"]
    if "headlines" in updates:
        cfg["headlines"] = updates["headlines"]
    if "display" in updates:
        cfg["display"] = updates["display"]
    if "api_keys" in updates:
        cfg["api_keys"] = updates["api_keys"]

    save_config(cfg)
    fetchers.clear_cache()
    return jsonify({"status": "ok"})


@app.route("/api/status")
def get_status():
    return jsonify({
        "current_screen": _state["current_screen"],
        "last_update": _state["last_update"],
        "paused": _state["paused"],
        "simulate": _state["simulate"],
    })


@app.route("/api/pause", methods=["POST"])
def toggle_pause():
    _state["paused"] = not _state["paused"]
    return jsonify({"paused": _state["paused"]})


@app.route("/api/skip", methods=["POST"])
def skip_screen():
    """Force advance to next screen immediately."""
    try:
        cfg = load_config()
        _cycle_display(cfg)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"status": "ok", "screen": _state["current_screen"]})


@app.route("/api/preview/<screen_name>")
def preview_screen(screen_name):
    """Render a screen and return as PNG (for web preview)."""
    from io import BytesIO
    from flask import send_file

    cfg = load_config()
    img = None

    if screen_name == "prices":
        tickers = []
        stocks = fetchers.fetch_stocks(cfg["tickers"]["stocks"])
        if stocks:
            tickers.extend(stocks)
        crypto = fetchers.fetch_crypto(cfg["tickers"]["crypto"])
        if crypto:
            tickers.extend(crypto)
        img = display.render_prices(tickers)
    elif screen_name == "weather":
        w = cfg["weather"]
        data = fetchers.fetch_weather(
            w["lat"], w["lon"],
            cfg["api_keys"]["openweathermap"],
            w.get("units", "imperial"),
        )
        img = display.render_weather(data, w.get("city_name", ""))
    elif screen_name == "air_quality":
        w = cfg["weather"]
        data = fetchers.fetch_air_quality(
            w["lat"], w["lon"],
            cfg["api_keys"].get("iqair", ""),
        )
        img = display.render_air_quality(data, w.get("city_name", ""))
    elif screen_name == "headlines":
        data = fetchers.fetch_headlines(cfg["headlines"]["feeds"])
        img = display.render_headlines(data or [])
    elif screen_name == "system":
        img = display.render_system_info()

    if img is None:
        img = display.render_error(f"Unknown screen: {screen_name}")

    # Scale up 3x for web preview (212x104 is tiny on screen)
    preview = img.convert("RGB").resize((WIDTH_PREVIEW, HEIGHT_PREVIEW))
    buf = BytesIO()
    preview.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


WIDTH_PREVIEW = 250 * 3
HEIGHT_PREVIEW = 122 * 3


@app.route("/api/search/stock")
def search_stock():
    q = request.args.get("q", "").strip()
    if len(q) < 1:
        return jsonify([])
    try:
        url = "https://query1.finance.yahoo.com/v1/finance/search"
        r = http_requests.get(url, params={"q": q, "quotesCount": 8, "newsCount": 0},
                              headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        results = []
        for item in r.json().get("quotes", []):
            results.append({
                "symbol": item.get("symbol", ""),
                "name": item.get("shortname") or item.get("longname", ""),
                "type": item.get("quoteType", ""),
                "exchange": item.get("exchDisp", ""),
            })
        return jsonify(results)
    except Exception as e:
        return jsonify([])


@app.route("/api/validate/stock")
def validate_stock():
    sym = request.args.get("symbol", "").upper()
    if not sym:
        return jsonify({"valid": False, "error": "No symbol"})
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
        r = http_requests.get(url, params={"range": "1d", "interval": "1d"},
                              headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = r.json()
        result = data.get("chart", {}).get("result")
        if result and result[0].get("meta", {}).get("regularMarketPrice"):
            price = result[0]["meta"]["regularMarketPrice"]
            name = result[0]["meta"].get("shortName", sym)
            return jsonify({"valid": True, "symbol": sym, "price": price, "name": name})
        return jsonify({"valid": False, "error": f"'{sym}' not found"})
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)})


@app.route("/api/validate/crypto")
def validate_crypto():
    coin = request.args.get("id", "").lower()
    if not coin:
        return jsonify({"valid": False, "error": "No coin ID"})
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        r = http_requests.get(url, params={"ids": coin, "vs_currencies": "usd"}, timeout=10)
        data = r.json()
        if coin in data and "usd" in data[coin]:
            return jsonify({"valid": True, "id": coin, "price": data[coin]["usd"]})
        return jsonify({"valid": False, "error": f"'{coin}' not found on CoinGecko"})
    except Exception as e:
        return jsonify({"valid": False, "error": str(e)})


@app.route("/api/geocode")
def geocode():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    try:
        url = "https://nominatim.openstreetmap.org/search"
        r = http_requests.get(url, params={"q": q, "format": "json", "limit": 5,
                                            "addressdetails": 1},
                              headers={"User-Agent": "PiDisplay/1.0"}, timeout=10)
        results = []
        for item in r.json():
            results.append({
                "name": item.get("display_name", ""),
                "lat": float(item["lat"]),
                "lon": float(item["lon"]),
            })
        return jsonify(results)
    except Exception as e:
        return jsonify([])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if _state["simulate"]:
        log.info("Running in SIMULATE mode (no Inky hardware)")

    thread = threading.Thread(target=_display_loop, daemon=True)
    thread.start()

    cfg = load_config()
    port = cfg.get("web_port", 5000)
    log.info("Web panel at http://0.0.0.0:%d", port)
    app.run(host="0.0.0.0", port=port, debug=False)
