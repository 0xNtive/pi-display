"""Data fetchers with caching for stocks, crypto, weather, AQ, and headlines."""

import time
import logging
import requests
import feedparser

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache helper
# ---------------------------------------------------------------------------
_cache = {}


def _cached(key, ttl_seconds, fetch_fn):
    """Return cached data if fresh, otherwise call fetch_fn and cache result."""
    now = time.time()
    if key in _cache:
        data, ts = _cache[key]
        if now - ts < ttl_seconds:
            return data
    try:
        data = fetch_fn()
        _cache[key] = (data, now)
        return data
    except Exception as e:
        log.error("Fetch %s failed: %s", key, e)
        if key in _cache:
            return _cache[key][0]  # stale is better than nothing
        return None


# ---------------------------------------------------------------------------
# Stock prices via Yahoo Finance API (no yfinance/pandas dependency)
# ---------------------------------------------------------------------------
def fetch_stocks(symbols: list[str], ttl: int = 120) -> list[dict] | None:
    def _fetch():
        results = []
        url = "https://query1.finance.yahoo.com/v7/finance/quote"
        params = {
            "symbols": ",".join(symbols),
            "fields": "regularMarketPrice,regularMarketChangePercent",
        }
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, params=params, headers=headers, timeout=15)
        r.raise_for_status()
        quotes = r.json().get("quoteResponse", {}).get("result", [])
        quote_map = {q["symbol"]: q for q in quotes}
        for sym in symbols:
            q = quote_map.get(sym)
            if q:
                results.append({
                    "symbol": sym,
                    "price": q.get("regularMarketPrice"),
                    "change_pct": round(q.get("regularMarketChangePercent", 0), 2),
                })
            else:
                log.warning("Stock %s: no data returned", sym)
                results.append({"symbol": sym, "price": None, "change_pct": 0})
        return results

    return _cached("stocks", ttl, _fetch)


# ---------------------------------------------------------------------------
# Crypto prices via CoinGecko (free, no API key)
# ---------------------------------------------------------------------------
def fetch_crypto(coin_ids: list[str], ttl: int = 120) -> list[dict] | None:
    def _fetch():
        ids_str = ",".join(coin_ids)
        url = (
            "https://api.coingecko.com/api/v3/simple/price"
            f"?ids={ids_str}&vs_currencies=usd&include_24hr_change=true"
        )
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
        results = []
        for cid in coin_ids:
            if cid in data:
                d = data[cid]
                results.append({
                    "symbol": cid.upper()[:5],
                    "price": d.get("usd", 0),
                    "change_pct": round(d.get("usd_24h_change", 0), 2),
                })
        return results

    return _cached("crypto", ttl, _fetch)


# ---------------------------------------------------------------------------
# Weather via OpenWeatherMap
# ---------------------------------------------------------------------------
def fetch_weather(lat: float, lon: float, api_key: str,
                  units: str = "imperial", ttl: int = 600) -> dict | None:
    if not api_key:
        return None

    def _fetch():
        url = (
            "https://api.openweathermap.org/data/2.5/weather"
            f"?lat={lat}&lon={lon}&units={units}&appid={api_key}"
        )
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        d = r.json()
        temp_unit = "F" if units == "imperial" else "C"
        speed_unit = "mph" if units == "imperial" else "m/s"
        return {
            "temp": round(d["main"]["temp"]),
            "feels_like": round(d["main"]["feels_like"]),
            "temp_min": round(d["main"]["temp_min"]),
            "temp_max": round(d["main"]["temp_max"]),
            "humidity": d["main"]["humidity"],
            "description": d["weather"][0]["description"].title(),
            "icon": d["weather"][0]["icon"],
            "wind_speed": round(d["wind"]["speed"]),
            "wind_deg": d["wind"].get("deg", 0),
            "temp_unit": temp_unit,
            "speed_unit": speed_unit,
        }

    return _cached(f"weather_{lat}_{lon}", ttl, _fetch)


# ---------------------------------------------------------------------------
# Air Quality via OpenWeatherMap
# ---------------------------------------------------------------------------
_AQI_LABELS = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}


def fetch_air_quality(lat: float, lon: float, api_key: str,
                      ttl: int = 600) -> dict | None:
    if not api_key:
        return None

    def _fetch():
        url = (
            "https://api.openweathermap.org/data/2.5/air_pollution"
            f"?lat={lat}&lon={lon}&appid={api_key}"
        )
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        d = r.json()
        item = d["list"][0]
        aqi = item["main"]["aqi"]
        components = item["components"]
        return {
            "aqi": aqi,
            "label": _AQI_LABELS.get(aqi, "Unknown"),
            "pm2_5": round(components.get("pm2_5", 0), 1),
            "pm10": round(components.get("pm10", 0), 1),
            "no2": round(components.get("no2", 0), 1),
            "o3": round(components.get("o3", 0), 1),
        }

    return _cached(f"aq_{lat}_{lon}", ttl, _fetch)


# ---------------------------------------------------------------------------
# Headlines via RSS
# ---------------------------------------------------------------------------
def fetch_headlines(feeds: list[dict], ttl: int = 900) -> list[dict] | None:
    enabled = [f for f in feeds if f.get("enabled")]
    if not enabled:
        return []

    def _fetch():
        headlines = []
        for feed_cfg in enabled:
            try:
                parsed = feedparser.parse(feed_cfg["url"])
                for entry in parsed.entries[:5]:
                    headlines.append({
                        "title": entry.get("title", ""),
                        "source": feed_cfg["name"],
                        "link": entry.get("link", ""),
                    })
            except Exception as e:
                log.warning("RSS %s error: %s", feed_cfg["name"], e)
        return headlines

    return _cached("headlines", ttl, _fetch)


def clear_cache():
    """Clear all cached data to force fresh fetches."""
    _cache.clear()
