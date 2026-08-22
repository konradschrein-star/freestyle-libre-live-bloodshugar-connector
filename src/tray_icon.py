"""
FreeStyle Libre Live Blood Sugar Connector - Dynamic Tray Icon Generator (Redesigned for Maximum Legibility)
Renders high-contrast, ultra-bold taskbar icons optimized for 16x16, 24x24, 32x32, and high-DPI scaling.
"""

from __future__ import annotations
import os
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter


# Modern High-Contrast Medical Color Palette (RGB)
COLOR_GREEN = (22, 163, 74)       # #16a34a High-Contrast Emerald Green (Normal)
COLOR_YELLOW = (217, 119, 6)      # #d97706 High-Contrast Amber (High)
COLOR_ORANGE = (234, 88, 12)      # #ea580c High-Contrast Orange (Low)
COLOR_RED = (220, 38, 38)         # #dc2626 Bright Urgent Red (Critical)
COLOR_GRAY = (75, 85, 99)         # #4b5563 Offline / Disconnected
COLOR_DARK_SLATE = (15, 23, 42)   # #0f172a Deep Background
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


def _find_heavy_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load the heaviest, most readable bold font available on Windows."""
    font_candidates = [
        r"C:\Windows\Fonts\ariblk.ttf",     # Arial Black (Maximum weight & readability)
        r"C:\Windows\Fonts\segoeuib.ttf",   # Segoe UI Bold
        r"C:\Windows\Fonts\arialbd.ttf",    # Arial Bold
        r"C:\Windows\Fonts\calibrib.ttf",   # Calibri Bold
        r"C:\Windows\Fonts\trebucbd.ttf",   # Trebuchet MS Bold
        r"C:\Windows\Fonts\impact.ttf",     # Impact
    ]
    for path in font_candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue

    return ImageFont.load_default()


def _find_arrow_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load font for directional trend arrows."""
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\calibrib.ttf",
    ]
    for path in candidates:
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
    Generate an ultra-readable High-DPI icon image for the Windows taskbar.
    
    Design principles:
    - Zero wasted margin: Badge fills 96% of the icon box.
    - Large, heavy-weight typography with maximum contrast.
    - For decimal numbers (e.g. "8.6"), renders the number large and centered.
    - Directional indicator badge placed in the corner so it NEVER compresses the main number!
    """
    # Supersampling 2x (128x128) then downscaling with Lanczos for razor-sharp edges
    canvas_size = size * 2
    img = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Draw rounded background badge with dark border for high contrast against light or dark taskbars
    pad = 2
    corner_radius = 22
    
    # Outer dark shadow/border
    draw.rounded_rectangle(
        [pad, pad, canvas_size - pad, canvas_size - pad],
        radius=corner_radius,
        fill=bg_color,
        outline=(0, 0, 0, 180),
        width=2,
    )

    # Clean trend arrow symbol
    arrow_char = trend_symbol.strip()
    if arrow_char in ("↓↓", "⇊"):
        arrow_char = "↓"
    elif arrow_char in ("↑↑", "⇈"):
        arrow_char = "↑"

    val_len = len(value_str)

    # 2. Maximize Font Size for Huge Readability
    if val_len <= 2:  # e.g. "8", "92"
        val_font_size = 76
    elif val_len == 3:  # e.g. "8.6", "115"
        val_font_size = 62
    elif val_len == 4:  # e.g. "11.4", "240"
        val_font_size = 48
    else:
        val_font_size = 40

    font_val = _find_heavy_font(val_font_size)

    # Measure main glucose number
    val_bbox = draw.textbbox((0, 0), value_str, font=font_val)
    val_w = val_bbox[2] - val_bbox[0]
    val_h = val_bbox[3] - val_bbox[1]

    # Center number vertically and horizontally
    val_x = (canvas_size - val_w) // 2
    val_y = (canvas_size - val_h) // 2 - (val_bbox[1])  # exact baseline correction

    # If an arrow is present, draw a high-contrast indicator in the top right corner
    if arrow_char and arrow_char != "—":
        # Draw mini corner badge for arrow
        arrow_font_size = 36
        font_arrow = _find_arrow_font(arrow_font_size)
        
        arrow_bbox = draw.textbbox((0, 0), arrow_char, font=font_arrow)
        arrow_w = arrow_bbox[2] - arrow_bbox[0]
        arrow_h = arrow_bbox[3] - arrow_bbox[1]

        # Draw a small pill in top-right or bottom-right
        indicator_size = 32
        ix = canvas_size - indicator_size - 4
        iy = 4
        
        draw.rounded_rectangle(
            [ix, iy, ix + indicator_size, iy + indicator_size],
            radius=8,
            fill=(0, 0, 0, 210),
            outline=(255, 255, 255, 100),
            width=1,
        )

        ax = ix + (indicator_size - arrow_w) // 2 - arrow_bbox[0]
        ay = iy + (indicator_size - arrow_h) // 2 - arrow_bbox[1]
        draw.text((ax, ay), arrow_char, fill=COLOR_WHITE, font=font_arrow)

        # Shift text slightly left for balanced look if needed
        val_x = max(6, (canvas_size - val_w) // 2 - 4)

    # 3. Draw Main Glucose Number with subtle drop shadow for maximum punch
    shadow_offset = 2
    draw.text((val_x + shadow_offset, val_y + shadow_offset), value_str, fill=(0, 0, 0, 160), font=font_val)
    draw.text((val_x, val_y), value_str, fill=COLOR_WHITE, font=font_val)

    # High-quality Lanczos downsampling to native resolution
    img_smooth = img.resize((size, size), Image.Resampling.LANCZOS)
    return img_smooth


def create_offline_icon(size: int = 64) -> Image.Image:
    """Generate placeholder tray icon when disconnected or connecting."""
    return create_glucose_icon("...", trend_symbol="", bg_color=COLOR_GRAY, size=size)
