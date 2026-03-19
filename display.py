"""Render screens for the Inky pHAT (250x122, black & white).

Renders in grayscale ("L" mode) for correct previews, then converts
to the Inky's palette format at display time.
"""

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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_image():
    """Create a blank white canvas."""
    return Image.new("L", (WIDTH, HEIGHT), WHITE)


def _header_bar(draw, title, y=0, height=17):
    """Draw an inverted (white on black) header bar with current time."""
    draw.rectangle([0, y, WIDTH - 1, y + height - 1], fill=BLACK)
    draw.text((4, y + 1), title.upper(), fill=WHITE, font=FONT_SM_B)
    now = datetime.now().strftime("%H:%M")
    tw = draw.textlength(now, font=FONT_XS)
    draw.text((WIDTH - tw - 4, y + 4), now, fill=WHITE, font=FONT_XS)


def _dotted_hline(draw, y, x0=4, x1=None):
    """Draw a dotted horizontal line."""
    if x1 is None:
        x1 = WIDTH - 4
    for x in range(x0, x1, 3):
        draw.point((x, y), fill=BLACK)


def _wind_dir(deg):
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[round(deg / 45) % 8]


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

def render_prices(tickers: list[dict]) -> Image.Image:
    img = _new_image()
    draw = ImageDraw.Draw(img)
    _header_bar(draw, "Prices")

    if not tickers:
        draw.text((10, 45), "No tickers configured", font=FONT_MD, fill=BLACK)
        return img

    # Column positions
    COL_SYM = 4
    PRICE_RIGHT = 140  # right edge of price column
    max_rows = 5
    row_h = 17
    y = 20

    for i, t in enumerate(tickers[:max_rows]):
        sym = t["symbol"][:5]
        price_str = _format_price(t.get("price"))
        pct = t.get("change_pct", 0)

        # Symbol (bold)
        draw.text((COL_SYM, y), sym, font=FONT_SM_B, fill=BLACK)

        # Price (right-aligned to PRICE_RIGHT)
        pw = draw.textlength(price_str, font=FONT_SM)
        draw.text((PRICE_RIGHT - pw, y), price_str, font=FONT_SM, fill=BLACK)

        # Change % with direction indicator
        sign = "+" if pct > 0 else ""
        chg_str = f"{sign}{pct:.1f}%"
        tw = draw.textlength(chg_str, font=FONT_SM)
        chg_x = WIDTH - tw - 4
        draw.text((chg_x, y), chg_str, font=FONT_SM, fill=BLACK)

        # Small filled/empty triangle as direction indicator
        tri_x = chg_x - 9
        tri_cy = y + 6
        if pct > 0:
            # Up triangle (filled)
            draw.polygon([(tri_x, tri_cy + 4), (tri_x + 7, tri_cy + 4),
                          (tri_x + 3, tri_cy - 3)], fill=BLACK)
        elif pct < 0:
            # Down triangle (filled)
            draw.polygon([(tri_x, tri_cy - 3), (tri_x + 7, tri_cy - 3),
                          (tri_x + 3, tri_cy + 4)], fill=BLACK)

        # Separator between rows
        if i < min(len(tickers), max_rows) - 1:
            _dotted_hline(draw, y + row_h - 3)

        y += row_h

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

    # ---- Top section: big temp + conditions ----
    temp_str = f"{data['temp']}\u00b0"
    draw.text((6, 19), temp_str, font=FONT_XL, fill=BLACK)
    temp_w = draw.textlength(temp_str, font=FONT_XL)

    # Unit label
    draw.text((6 + temp_w, 22), unit, font=FONT_MD_B, fill=BLACK)

    # Condition + feels-like to the right of temp
    right_x = 6 + temp_w + 20
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

_AQI_LABELS = {1: "Good", 2: "Fair", 3: "Moderate", 4: "Poor", 5: "Very Poor"}


def render_air_quality(data: dict, city: str) -> Image.Image:
    img = _new_image()
    draw = ImageDraw.Draw(img)
    _header_bar(draw, f"Air Quality \u2014 {city[:10]}")

    if not data:
        draw.text((10, 40), "No AQ data", font=FONT_MD, fill=BLACK)
        draw.text((10, 58), "Set API key in panel", font=FONT_SM, fill=BLACK)
        return img

    aqi = data["aqi"]
    label = data["label"]

    # ---- AQI value and label ----
    aqi_str = str(aqi)
    draw.text((6, 20), aqi_str, font=FONT_XL, fill=BLACK)
    aqi_w = draw.textlength(aqi_str, font=FONT_XL)
    draw.text((aqi_w + 12, 22), "/ 5", font=FONT_SM, fill=BLACK)
    draw.text((aqi_w + 12, 36), label, font=FONT_MD_B, fill=BLACK)

    # ---- AQI gauge bar (5 segments) ----
    bar_y = 55
    seg_w = 37  # (WIDTH - 10 - 4 gaps) / 5 ≈ 37
    gap = 3
    for i in range(5):
        x0 = 6 + i * (seg_w + gap)
        x1 = x0 + seg_w
        if i < aqi:
            draw.rectangle([x0, bar_y, x1, bar_y + 8], fill=BLACK)
        else:
            draw.rectangle([x0, bar_y, x1, bar_y + 8], outline=BLACK, width=1)

    # Scale labels under bar
    draw.text((6, bar_y + 11), "Good", font=FONT_XS, fill=BLACK)
    mid_label = "Moderate"
    mid_w = draw.textlength(mid_label, font=FONT_XS)
    draw.text(((WIDTH - mid_w) // 2, bar_y + 11), mid_label, font=FONT_XS, fill=BLACK)
    vp_label = "V.Poor"
    vp_w = draw.textlength(vp_label, font=FONT_XS)
    draw.text((WIDTH - 6 - vp_w, bar_y + 11), vp_label, font=FONT_XS, fill=BLACK)

    # ---- Pollutant details ----
    draw.line([(4, 80), (WIDTH - 4, 80)], fill=BLACK, width=1)
    y = 84
    draw.text((6, y), f"PM2.5: {data['pm2_5']}", font=FONT_SM, fill=BLACK)
    draw.text((75, y), f"PM10: {data['pm10']}", font=FONT_SM, fill=BLACK)
    draw.text((140, y), f"O\u2083: {data['o3']}", font=FONT_SM, fill=BLACK)

    return img


# ---------------------------------------------------------------------------
# Screen: Headlines
# ---------------------------------------------------------------------------

def render_headlines(headlines: list[dict]) -> Image.Image:
    img = _new_image()
    draw = ImageDraw.Draw(img)
    _header_bar(draw, "Headlines")

    if not headlines:
        draw.text((10, 45), "No headlines available", font=FONT_MD, fill=BLACK)
        return img

    y = 19
    max_text_w = WIDTH - 10
    shown = 0

    for h in headlines:
        if shown >= 3 or y > HEIGHT - 18:
            break

        title = h.get("title", "").strip()
        source = h.get("source", "")
        if not title:
            continue

        # Source badge: compact inverted label
        src_text = source[:12]
        src_w = draw.textlength(src_text, font=FONT_XS)
        badge_w = src_w + 6
        draw.rectangle([4, y, 4 + badge_w, y + 10], fill=BLACK)
        draw.text((7, y + 1), src_text, fill=WHITE, font=FONT_XS)

        # Headline text — 2 lines for first item, 1 line for rest
        max_lines = 2 if shown == 0 else 1
        lines = _wrap_text(title, FONT_SM, max_text_w, draw)
        text_y = y + 11
        for line_text in lines[:max_lines]:
            if text_y > HEIGHT - 4:
                break
            # Add ellipsis if we're truncating
            if line_text == lines[max_lines - 1] and len(lines) > max_lines:
                while draw.textlength(line_text + "...", font=FONT_SM) > max_text_w and len(line_text) > 5:
                    line_text = line_text[:-1]
                line_text += "..."
            draw.text((5, text_y), line_text, font=FONT_SM, fill=BLACK)
            text_y += 12

        y = text_y + 1
        shown += 1

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
    bw = img.point(lambda x: 0 if x < 128 else 1, mode="1")
    pal_img = Image.new("P", (WIDTH, HEIGHT))
    # Inky palette: index 0 = black, index 1 = white
    palette = [0, 0, 0, 255, 255, 255] + [0, 0, 0] * 254
    pal_img.putpalette(palette)
    pixels = list(bw.getdata())
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
        pal_img = _to_inky_palette(img)
        inky_display.set_image(pal_img)
        inky_display.show()
        log.info("Display updated")
    except Exception as e:
        log.error("Display error: %s", e)
        img.save("/tmp/inkyphat_preview.png")
