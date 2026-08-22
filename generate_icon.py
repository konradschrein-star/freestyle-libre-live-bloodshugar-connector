"""
Generate Windows .ICO icon file for standalone executable
"""

from PIL import Image, ImageDraw
from pathlib import Path

def generate_ico():
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw rounded gradient badge
    draw.rounded_rectangle([8, 8, 248, 248], radius=56, fill=(16, 185, 129))
    
    # Inner blood drop
    draw.ellipse([64, 72, 192, 200], fill=(239, 68, 68))
    # Drop tip
    draw.polygon([(128, 28), (68, 120), (188, 120)], fill=(239, 68, 68))

    # White shine
    draw.ellipse([100, 100, 130, 140], fill=(255, 255, 255, 180))

    assets_dir = Path(__file__).resolve().parent / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    ico_path = assets_dir / "app_icon.ico"
    
    img.save(
        str(ico_path),
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )
    print(f"Generated {ico_path}")

if __name__ == "__main__":
    generate_ico()
