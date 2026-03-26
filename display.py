"""Render screens for the Inky pHAT (250x122, black & white).

Renders in grayscale ("L" mode) for correct previews, then converts
to the Inky's palette format at display time.
"""

import math
import os
import logging
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger(__name__)

WIDTH, HEIGHT = 250, 122
BLACK = 0
WHITE = 255

# ---------------------------------------------------------------------------
# Font loading — tries Pi paths first, then macOS, then Pillow default
# ---------------------------------------------------------------------------
_FONT_SEARCH = [
    # Raspberry Pi OS / Debian
    "/usr/share/fonts/truetype/dejavu/DejaVuSans{0}.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans{0}.ttf",
    # macOS
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/SFCompact.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
]


def _load_font(size, bold=False):
    suffix = "-Bold" if bold else ""
    for pattern in _FONT_SEARCH:
        path = pattern.format(suffix)
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        # Try without suffix for files that don't have bold variants
        if suffix:
            path_plain = pattern.format("")
            if os.path.exists(path_plain):
                try:
                    return ImageFont.truetype(path_plain, size)
                except Exception:
                    continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


# Pre-load fonts at various sizes
FONT_XS = _load_font(9)
FONT_SM = _load_font(11)
FONT_SM_B = _load_font(11, bold=True)
FONT_MD = _load_font(13)
FONT_MD_B = _load_font(13, bold=True)
FONT_LG = _load_font(20, bold=True)
FONT_XL = _load_font(30, bold=True)
FONT_HEADLINE = _load_font(16, bold=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_image():
    """Create a blank white canvas."""
    return Image.new("L", (WIDTH, HEIGHT), WHITE)


def _header_bar(draw, title, y=0, height=17):
    """Draw an inverted (white on black) header bar with date and time."""
    draw.rectangle([0, y, WIDTH - 1, y + height - 1], fill=BLACK)
    draw.text((4, y + 1), title.upper(), fill=WHITE, font=FONT_SM_B)
    now = datetime.now()
    date_time = now.strftime("%b %d  %H:%M")
    tw = draw.textlength(date_time, font=FONT_XS)
    draw.text((WIDTH - tw - 4, y + 4), date_time, fill=WHITE, font=FONT_XS)


def _dotted_hline(draw, y, x0=4, x1=None):
    """Draw a dotted horizontal line."""
    if x1 is None:
        x1 = WIDTH - 4
    for x in range(x0, x1, 3):
        draw.point((x, y), fill=BLACK)


def _wind_dir(deg):
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[round(deg / 45) % 8]


def _draw_weather_icon(draw, x, y, icon_code):
    """Draw a simple weather icon based on OpenWeatherMap icon code."""
    code = icon_code[:2] if icon_code else "01"
    is_night = icon_code.endswith("n") if icon_code else False

    if code == "01":  # clear sky
        # Sun or moon
        cx, cy, r = x + 16, y + 16, 10
        if is_night:
            draw.arc([cx - r, cy - r, cx + r, cy + r], 220, 80, fill=BLACK, width=2)
            draw.arc([cx - r + 4, cy - r - 2, cx + r + 4, cy + r - 2], 220, 80, fill=WHITE, width=3)
        else:
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BLACK)
            # Rays
            for angle in range(0, 360, 45):
                rx = cx + int((r + 5) * math.cos(math.radians(angle)))
                ry = cy + int((r + 5) * math.sin(math.radians(angle)))
                rx2 = cx + int((r + 2) * math.cos(math.radians(angle)))
                ry2 = cy + int((r + 2) * math.sin(math.radians(angle)))
                draw.line([(rx2, ry2), (rx, ry)], fill=BLACK, width=1)

    elif code == "02":  # few clouds
        # Small sun + cloud
        draw.ellipse([x + 4, y + 6, x + 18, y + 20], fill=BLACK)  # sun
        _draw_cloud(draw, x + 8, y + 12, 24, 14)

    elif code in ("03", "04"):  # clouds
        _draw_cloud(draw, x + 4, y + 8, 26, 16)
        if code == "04":
            _draw_cloud(draw, x + 10, y + 14, 22, 14)

    elif code == "09":  # shower rain
        _draw_cloud(draw, x + 4, y + 4, 26, 14)
        for rx in [x + 10, x + 18, x + 26]:
            draw.line([(rx, y + 22), (rx - 3, y + 28)], fill=BLACK, width=1)

    elif code == "10":  # rain
        _draw_cloud(draw, x + 4, y + 4, 26, 14)
        for rx in [x + 8, x + 14, x + 20, x + 26]:
            draw.line([(rx, y + 22), (rx - 3, y + 28)], fill=BLACK, width=1)
            draw.line([(rx - 1, y + 24), (rx - 4, y + 30)], fill=BLACK, width=1)

    elif code == "11":  # thunderstorm
        _draw_cloud(draw, x + 4, y + 4, 26, 14)
        # Lightning bolt
        draw.polygon([(x + 16, y + 19), (x + 13, y + 25), (x + 17, y + 25),
                       (x + 14, y + 32)], fill=BLACK)

    elif code == "13":  # snow
        _draw_cloud(draw, x + 4, y + 4, 26, 14)
        for sx, sy in [(x + 10, y + 24), (x + 18, y + 22), (x + 26, y + 26)]:
            draw.text((sx, sy), "*", fill=BLACK, font=FONT_SM_B)

    elif code == "50":  # mist
        for ly in range(y + 8, y + 30, 5):
            draw.line([(x + 4, ly), (x + 28, ly)], fill=BLACK, width=1)
            draw.line([(x + 8, ly + 2), (x + 30, ly + 2)], fill=BLACK, width=1)

    else:  # fallback
        _draw_cloud(draw, x + 4, y + 8, 26, 16)


def _draw_cloud(draw, x, y, w, h):
    """Draw a simple cloud shape."""
    # Main body
    draw.ellipse([x, y + h // 3, x + w, y + h], fill=BLACK)
    # Top bumps
    draw.ellipse([x + w // 6, y, x + w // 2 + 2, y + h * 2 // 3], fill=BLACK)
    draw.ellipse([x + w // 3, y + 2, x + w - w // 6, y + h * 2 // 3 + 2], fill=BLACK)


def _wrap_text(text, font, max_width, draw):
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if draw.textlength(test, font=font) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _format_price(price):
    if price is None:
        return "--"
    if price >= 10000:
        return f"${price:,.0f}"
    if price >= 100:
        return f"${price:,.0f}"
    if price >= 1:
        return f"${price:,.2f}"
    return f"${price:.4f}"


# ---------------------------------------------------------------------------
# Screen: Prices
# ---------------------------------------------------------------------------

_ticker_index = 0


def _draw_sparkline(draw, spark, x, y, w, h, prev_close=None):
    """Draw a sparkline chart from price data."""
    if len(spark) < 2:
        return
    mn = min(spark)
    mx = max(spark)
    if mn == mx:
        mx = mn + 1  # avoid division by zero

    # Include prev_close in scale so the baseline is visible
    if prev_close is not None:
        mn = min(mn, prev_close)
        mx = max(mx, prev_close)

    # Draw previous close baseline (dotted)
    if prev_close is not None:
        base_y = y + h - int((prev_close - mn) / (mx - mn) * h)
        for bx in range(x, x + w, 4):
            draw.point((bx, base_y), fill=BLACK)

    # Draw the sparkline
    points = []
    for i, val in enumerate(spark):
        px = x + int(i / (len(spark) - 1) * (w - 1))
        py = y + h - int((val - mn) / (mx - mn) * h)
        points.append((px, py))

    for i in range(len(points) - 1):
        draw.line([points[i], points[i + 1]], fill=BLACK, width=2)


def render_prices(tickers: list[dict]) -> Image.Image:
    global _ticker_index
    img = _new_image()
    draw = ImageDraw.Draw(img)

    if not tickers:
        _header_bar(draw, "Prices")
        draw.text((10, 45), "No tickers configured", font=FONT_MD, fill=BLACK)
        return img

    # Cycle through tickers one at a time
    _ticker_index = _ticker_index % len(tickers)
    t = tickers[_ticker_index]
    _ticker_index += 1

    sym = t["symbol"]
    name = t.get("name", sym)
    price_str = _format_price(t.get("price"))
    pct = t.get("change_pct", 0)
    spark = t.get("spark", [])
    prev_close = t.get("prev_close")

    # Header with name and symbol
    display_name = name if len(name) <= 20 else name[:20]
    _header_bar(draw, f"{display_name} ({sym})")

    # Sparkline chart — main area
    chart_y = 20
    chart_h = 60
    chart_x = 6
    chart_w = WIDTH - 12
    _draw_sparkline(draw, spark, chart_x, chart_y, chart_w, chart_h, prev_close)

    # Price and change below chart
    y = chart_y + chart_h + 6

    # Big price
    draw.text((6, y), price_str, font=FONT_LG, fill=BLACK)
    price_w = draw.textlength(price_str, font=FONT_LG)

    # Change % with triangle
    sign = "+" if pct > 0 else ""
    chg_str = f"{sign}{pct:.2f}%"
    tw = draw.textlength(chg_str, font=FONT_MD_B)
    chg_x = WIDTH - tw - 6
    draw.text((chg_x, y + 4), chg_str, font=FONT_MD_B, fill=BLACK)

    # Triangle
    tri_x = chg_x - 12
    tri_cy = y + 12
    if pct > 0:
        draw.polygon([(tri_x, tri_cy + 5), (tri_x + 9, tri_cy + 5),
                      (tri_x + 4, tri_cy - 4)], fill=BLACK)
    elif pct < 0:
        draw.polygon([(tri_x, tri_cy - 4), (tri_x + 9, tri_cy - 4),
                      (tri_x + 4, tri_cy + 5)], fill=BLACK)

    # Page indicator
    page_str = f"{_ticker_index}/{len(tickers)}"
    pw = draw.textlength(page_str, font=FONT_XS)
    draw.text((WIDTH - pw - 6, HEIGHT - 12), page_str, font=FONT_XS, fill=BLACK)

    return img


# ---------------------------------------------------------------------------
# Screen: Weather
# ---------------------------------------------------------------------------

def render_weather(data: dict, city: str) -> Image.Image:
    img = _new_image()
    draw = ImageDraw.Draw(img)
    _header_bar(draw, f"Weather \u2014 {city[:14]}")

    if not data:
        draw.text((10, 40), "No weather data", font=FONT_MD, fill=BLACK)
        draw.text((10, 58), "Set API key in panel", font=FONT_SM, fill=BLACK)
        return img

    unit = data.get("temp_unit", "F")
    icon_code = data.get("icon", "01d")

    # ---- Weather icon (top left) ----
    _draw_weather_icon(draw, 6, 18, icon_code)

    # ---- Big temp to the right of icon ----
    temp_str = f"{data['temp']}\u00b0"
    draw.text((44, 19), temp_str, font=FONT_XL, fill=BLACK)
    temp_w = draw.textlength(temp_str, font=FONT_XL)

    # Unit label
    draw.text((44 + temp_w, 22), unit, font=FONT_MD_B, fill=BLACK)

    # Condition + feels-like further right
    right_x = 44 + temp_w + 16
    desc = data.get("description", "")
    draw.text((right_x, 22), desc, font=FONT_SM_B, fill=BLACK)
    draw.text((right_x, 36), f"Feels like {data['feels_like']}\u00b0", font=FONT_SM, fill=BLACK)

    # ---- Divider ----
    draw.line([(4, 56), (WIDTH - 4, 56)], fill=BLACK, width=1)

    # ---- Bottom section: details in two columns ----
    y = 61
    # Left column
    draw.text((6, y), f"Hi {data['temp_max']}\u00b0  Lo {data['temp_min']}\u00b0", font=FONT_SM, fill=BLACK)
    draw.text((6, y + 15), f"Wind {data['wind_speed']}{data.get('speed_unit','mph')} {_wind_dir(data.get('wind_deg',0))}", font=FONT_SM, fill=BLACK)

    # Right column
    draw.text((125, y), f"Humidity {data['humidity']}%", font=FONT_SM, fill=BLACK)

    # Mini humidity bar
    bar_x = 125
    bar_y = y + 17
    bar_w = 75
    bar_h = 6
    draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], outline=BLACK, width=1)
    fill_w = int((data['humidity'] / 100) * bar_w)
    if fill_w > 0:
        draw.rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], fill=BLACK)

    return img


# ---------------------------------------------------------------------------
# Screen: Air Quality
# ---------------------------------------------------------------------------

def render_air_quality(data: dict, city: str) -> Image.Image:
    img = _new_image()
    draw = ImageDraw.Draw(img)
    _header_bar(draw, f"Air Quality \u2014 {city[:10]}")

    if not data:
        draw.text((10, 40), "No AQ data", font=FONT_MD, fill=BLACK)
        draw.text((10, 58), "Set IQAir API key in panel", font=FONT_SM, fill=BLACK)
        return img

    aqi = data["aqi"]
    label = data["label"]
    main_poll = data.get("main_pollutant", "")

    # ---- Big AQI number ----
    aqi_str = str(aqi)
    draw.text((6, 18), aqi_str, font=FONT_XL, fill=BLACK)
    aqi_w = draw.textlength(aqi_str, font=FONT_XL)

    # ---- Label + main pollutant to the right ----
    draw.text((aqi_w + 14, 20), "US AQI", font=FONT_SM, fill=BLACK)
    draw.text((aqi_w + 14, 34), label, font=FONT_MD_B, fill=BLACK)

    # ---- AQI gauge bar (6 segments: 0-50, 51-100, ..., 301-500) ----
    bar_y = 58
    seg_w = 36
    gap = 3
    thresholds = [50, 100, 150, 200, 300, 500]
    for i, thr in enumerate(thresholds):
        x0 = 6 + i * (seg_w + gap)
        x1 = x0 + seg_w
        if aqi > (thresholds[i - 1] if i > 0 else 0):
            draw.rectangle([x0, bar_y, x1, bar_y + 10], fill=BLACK)
        else:
            draw.rectangle([x0, bar_y, x1, bar_y + 10], outline=BLACK, width=1)

    # Scale labels
    draw.text((6, bar_y + 13), "Good", font=FONT_XS, fill=BLACK)
    mid_w = draw.textlength("Moderate", font=FONT_XS)
    draw.text(((WIDTH - mid_w) // 2, bar_y + 13), "Moderate", font=FONT_XS, fill=BLACK)
    haz = "Hazardous"
    haz_w = draw.textlength(haz, font=FONT_XS)
    draw.text((WIDTH - 6 - haz_w, bar_y + 13), haz, font=FONT_XS, fill=BLACK)

    # ---- Details ----
    draw.line([(4, 86), (WIDTH - 4, 86)], fill=BLACK, width=1)
    y = 91
    if main_poll:
        draw.text((6, y), f"Main pollutant: {main_poll}", font=FONT_SM, fill=BLACK)
    iq_city = data.get("city", "")
    if iq_city:
        draw.text((6, y + 14), f"Station: {iq_city}", font=FONT_XS, fill=BLACK)

    return img


# ---------------------------------------------------------------------------
# Screen: Headlines
# ---------------------------------------------------------------------------

_headline_index = 0


def render_headlines(headlines: list[dict]) -> Image.Image:
    global _headline_index
    img = _new_image()
    draw = ImageDraw.Draw(img)

    if not headlines:
        _header_bar(draw, "Headlines")
        draw.text((10, 45), "No headlines available", font=FONT_MD, fill=BLACK)
        return img

    # Pick one headline, cycle through them
    _headline_index = _headline_index % len(headlines)
    h = headlines[_headline_index]
    _headline_index += 1

    title = h.get("title", "").strip()
    source = h.get("source", "")

    _header_bar(draw, f"News \u2014 {source[:16]}")

    # Wrap title with bigger font, use full screen area
    max_text_w = WIDTH - 16
    lines = _wrap_text(title, FONT_HEADLINE, max_text_w, draw)

    # Center vertically in available space (below header)
    line_h = 22
    max_lines = 4
    display_lines = lines[:max_lines]
    total_h = len(display_lines) * line_h
    start_y = 20 + (HEIGHT - 20 - total_h) // 2

    for i, line_text in enumerate(display_lines):
        # Add ellipsis to last line if truncated
        if i == max_lines - 1 and len(lines) > max_lines:
            while draw.textlength(line_text + "...", font=FONT_HEADLINE) > max_text_w and len(line_text) > 5:
                line_text = line_text[:-1]
            line_text += "..."
        draw.text((8, start_y + i * line_h), line_text, font=FONT_HEADLINE, fill=BLACK)

    # Page indicator at bottom right
    page_str = f"{_headline_index}/{len(headlines)}"
    pw = draw.textlength(page_str, font=FONT_XS)
    draw.text((WIDTH - pw - 6, HEIGHT - 12), page_str, font=FONT_XS, fill=BLACK)

    return img


# ---------------------------------------------------------------------------
# Screen: System Info
# ---------------------------------------------------------------------------

def render_system_info() -> Image.Image:
    import subprocess
    img = _new_image()
    draw = ImageDraw.Draw(img)
    _header_bar(draw, "System")

    y = 22

    # CPU temperature
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            cpu_temp = int(f.read().strip()) / 1000
        draw.text((6, y), f"CPU Temp: {cpu_temp:.1f}C", font=FONT_MD_B, fill=BLACK)
    except Exception:
        draw.text((6, y), "CPU Temp: --", font=FONT_MD_B, fill=BLACK)
    y += 20

    # IP address
    try:
        ip = subprocess.check_output(["hostname", "-I"], timeout=5).decode().split()[0]
    except Exception:
        ip = "--"
    draw.text((6, y), f"IP: {ip}", font=FONT_SM, fill=BLACK)
    y += 16

    # Uptime
    try:
        with open("/proc/uptime") as f:
            secs = int(float(f.read().split()[0]))
        days, rem = divmod(secs, 86400)
        hours, rem = divmod(rem, 3600)
        mins = rem // 60
        if days > 0:
            uptime_str = f"{days}d {hours}h {mins}m"
        else:
            uptime_str = f"{hours}h {mins}m"
        draw.text((6, y), f"Uptime: {uptime_str}", font=FONT_SM, fill=BLACK)
    except Exception:
        draw.text((6, y), "Uptime: --", font=FONT_SM, fill=BLACK)
    y += 16

    # Memory
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        mem_total = int(lines[0].split()[1]) // 1024
        mem_avail = int(lines[2].split()[1]) // 1024
        mem_used = mem_total - mem_avail
        draw.text((6, y), f"RAM: {mem_used}MB / {mem_total}MB", font=FONT_SM, fill=BLACK)
    except Exception:
        draw.text((6, y), "RAM: --", font=FONT_SM, fill=BLACK)
    y += 16

    # Disk
    try:
        stat = os.statvfs("/")
        total_gb = (stat.f_blocks * stat.f_frsize) / (1024 ** 3)
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
        draw.text((6, y), f"Disk: {free_gb:.1f}GB free / {total_gb:.1f}GB", font=FONT_SM, fill=BLACK)
    except Exception:
        draw.text((6, y), "Disk: --", font=FONT_SM, fill=BLACK)

    return img


# ---------------------------------------------------------------------------
# Screen: Error / Status
# ---------------------------------------------------------------------------

def render_error(message: str) -> Image.Image:
    img = _new_image()
    draw = ImageDraw.Draw(img)
    _header_bar(draw, "Status")
    lines = _wrap_text(message, FONT_MD, WIDTH - 12, draw)
    y = 30
    for line in lines[:4]:
        draw.text((6, y), line, font=FONT_MD, fill=BLACK)
        y += 18
    return img


# ---------------------------------------------------------------------------
# Display output
# ---------------------------------------------------------------------------

def _to_inky_palette(img):
    """Convert grayscale image to Inky pHAT's 2-color palette format."""
    pal_img = Image.new("P", (WIDTH, HEIGHT))
    # Inky palette: index 0 = white, index 1 = black
    palette = [255, 255, 255, 0, 0, 0] + [0, 0, 0] * 254
    pal_img.putpalette(palette)
    # Map grayscale to palette indices: light → 0 (white), dark → 1 (black)
    pixels = [1 if p < 128 else 0 for p in img.getdata()]
    pal_img.putdata(pixels)
    return pal_img


def display_image(img: Image.Image, simulate: bool = False):
    """Push image to Inky pHAT or save as PNG in simulate mode."""
    if simulate:
        img.save("/tmp/inkyphat_preview.png")
        log.info("Saved preview to /tmp/inkyphat_preview.png")
        return

    try:
        from inky.auto import auto
        inky_display = auto()
        img = img.rotate(180)
        pal_img = _to_inky_palette(img)
        inky_display.set_image(pal_img)
        inky_display.show()
        log.info("Display updated")
    except Exception as e:
        log.error("Display error: %s", e)
        img.save("/tmp/inkyphat_preview.png")
