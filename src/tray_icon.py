"""
FreeStyle Libre Live Blood Sugar Connector - Dynamic Tray Icon Generator
Renders high-DPI, color-coded taskbar icons with live glucose value and trend arrow.
"""

from __future__ import annotations
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import os


# High-contrast modern color palette (RGB)
COLOR_GREEN = (34, 197, 94)      # #22c55e In target (70 - 180 mg/dL)
COLOR_YELLOW = (234, 179, 8)     # #eab308 Warning / High (180 - 250 mg/dL)
COLOR_ORANGE = (249, 115, 22)    # #f97316 Low (54 - 70 mg/dL)
COLOR_RED = (239, 68, 68)        # #ef4444 Critical (<54 or >250 mg/dL)
COLOR_GRAY = (100, 116, 139)     # #64748b Offline / Connecting
COLOR_DARK_BG = (15, 23, 42)     # #0f172a Deep Slate Background
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)


def get_status_color(
    value_mgdl: float,
    very_low: float = 54.0,
    low: float = 70.0,
    target_high: float = 180.0,
    high: float = 250.0,
) -> Tuple[int, int, int]:
    """Determine icon badge color according to clinical thresholds."""
    if value_mgdl <= 0:
        return COLOR_GRAY
    if value_mgdl < very_low:
        return COLOR_RED
    if value_mgdl < low:
        return COLOR_ORANGE
    if value_mgdl <= target_high:
        return COLOR_GREEN
    if value_mgdl <= high:
        return COLOR_YELLOW
    return COLOR_RED


def _find_system_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load Segoe UI / Arial from Windows fonts directory or fallback to default font."""
    font_candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf",  # Segoe UI Bold
        r"C:\Windows\Fonts\arialbd.ttf",   # Arial Bold
        r"C:\Windows\Fonts\calibrib.ttf",  # Calibri Bold
        r"C:\Windows\Fonts\segoeui.ttf",   # Segoe UI Regular
        r"C:\Windows\Fonts\arial.ttf",     # Arial Regular
    ]
    for path in font_candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue

    return ImageFont.load_default()


def create_glucose_icon(
    value_str: str,
    trend_symbol: str = "",
    bg_color: Tuple[int, int, int] = COLOR_GREEN,
    size: int = 64,
) -> Image.Image:
    """
    Generate a dynamic 64x64 High-DPI icon image for the Windows system tray.
    
    Layout:
    - Rounded rectangle badge with antialiased borders.
    - Large bold glucose number (e.g. "118" or "6.5").
    - Directional arrow ("↑", "↗", "→", "↘", "↓") badge.
    """
    # Supersampling 2x (128x128) then downscaling to 64x64 for crystal clear edges
    canvas_size = size * 2
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw rounded background badge
    pad = 4
    corner_radius = 24
    draw.rounded_rectangle(
        [pad, pad, canvas_size - pad, canvas_size - pad],
        radius=corner_radius,
        fill=bg_color,
    )

    # Prepare typography
    # Number font size depends on string length (e.g. "95" vs "180" vs "6.5")
    val_len = len(value_str)
    if val_len <= 2:
        val_font_size = 54
    elif val_len == 3:
        val_font_size = 46
    else:
        val_font_size = 38

    font_val = _find_system_font(val_font_size)
    font_arrow = _find_system_font(42)

    # Arrow symbols mapping for clean rendering
    arrow_char = trend_symbol.strip()
    if arrow_char == "↓↓":
        arrow_char = "⇊"
    elif arrow_char == "↑↑":
        arrow_char = "⇈"

    if arrow_char and arrow_char != "—":
        # Draw number in top/middle and arrow at bottom right or next to it
        # Compute bounding boxes
        val_bbox = draw.textbbox((0, 0), value_str, font=font_val)
        val_w = val_bbox[2] - val_bbox[0]
        val_h = val_bbox[3] - val_bbox[1]

        arrow_bbox = draw.textbbox((0, 0), arrow_char, font=font_arrow)
        arrow_w = arrow_bbox[2] - arrow_bbox[0]
        arrow_h = arrow_bbox[3] - arrow_bbox[1]

        # Stack or layout horizontally
        val_x = (canvas_size - val_w) // 2
        val_y = (canvas_size - val_h - arrow_h) // 2 + 2

        # Draw glucose text
        draw.text((val_x, val_y), value_str, fill=COLOR_WHITE, font=font_val)

        # Draw arrow below centered
        arrow_x = (canvas_size - arrow_w) // 2
        arrow_y = val_y + val_h + 4
        draw.text((arrow_x, arrow_y), arrow_char, fill=COLOR_WHITE, font=font_arrow)
    else:
        # Just center the value
        val_bbox = draw.textbbox((0, 0), value_str, font=font_val)
        val_w = val_bbox[2] - val_bbox[0]
        val_h = val_bbox[3] - val_bbox[1]
        val_x = (canvas_size - val_w) // 2
        val_y = (canvas_size - val_h) // 2 - 2
        draw.text((val_x, val_y), value_str, fill=COLOR_WHITE, font=font_val)

    # High quality downsampling
    img_smooth = img.resize((size, size), Image.Resampling.LANCZOS)
    return img_smooth


def create_offline_icon(size: int = 64) -> Image.Image:
    """Generate placeholder tray icon when disconnected or connecting."""
    return create_glucose_icon("...", trend_symbol="", bg_color=COLOR_GRAY, size=size)
