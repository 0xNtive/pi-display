"""Generate preview PNGs of all screens with sample data for visual review."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from display import (
    render_prices, render_weather, render_air_quality, render_headlines,
    WIDTH, HEIGHT,
)

SCALE = 4  # upscale for viewing

sample_tickers = [
    {"symbol": "AAPL", "price": 178.52, "change_pct": 1.24},
    {"symbol": "GOOGL", "price": 141.80, "change_pct": -0.63},
    {"symbol": "MSFT", "price": 415.10, "change_pct": 0.37},
    {"symbol": "BTC", "price": 67521.0, "change_pct": -2.14},
    {"symbol": "ETH", "price": 3284.10, "change_pct": 4.51},
]

sample_weather = {
    "temp": 72,
    "feels_like": 69,
    "temp_min": 65,
    "temp_max": 78,
    "humidity": 45,
    "description": "Partly Cloudy",
    "icon": "02d",
    "wind_speed": 8,
    "wind_deg": 315,
    "temp_unit": "F",
    "speed_unit": "mph",
}

sample_aq = {
    "aqi": 2,
    "label": "Fair",
    "pm2_5": 12.3,
    "pm10": 18.7,
    "no2": 22.1,
    "o3": 45.6,
}

sample_headlines = [
    {"title": "Federal Reserve Holds Rates Steady Amid Persistent Inflation Concerns", "source": "Reuters"},
    {"title": "New Breakthrough in Quantum Computing Achieved by Research Team", "source": "Hacker News"},
    {"title": "Global Markets Rally as Trade Tensions Show Signs of Easing", "source": "Reuters Tech"},
]

screens = {
    "prices": render_prices(sample_tickers),
    "weather": render_weather(sample_weather, "New York"),
    "air_quality": render_air_quality(sample_aq, "New York"),
    "headlines": render_headlines(sample_headlines),
}

out_dir = os.path.join(os.path.dirname(__file__), "previews")
os.makedirs(out_dir, exist_ok=True)

for name, img in screens.items():
    # Save 1:1
    raw = img.convert("RGB")
    raw.save(os.path.join(out_dir, f"{name}_1x.png"))
    # Save scaled up with nearest-neighbor (sharp pixels, e-ink look)
    scaled = raw.resize((WIDTH * SCALE, HEIGHT * SCALE), resample=0)
    scaled.save(os.path.join(out_dir, f"{name}.png"))
    print(f"  Saved {name}.png ({WIDTH*SCALE}x{HEIGHT*SCALE})")

print(f"\nPreviews in: {out_dir}/")
