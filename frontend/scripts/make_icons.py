#!/usr/bin/env python3
"""
Generate the placeholder app icons, favicons, and OG image.

The mark is a rounded square with a play triangle. Change BRAND / NAME below
and rerun to rebrand. Needs Pillow:

    uv run --no-project --with pillow python frontend/scripts/make_icons.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "frontend" / "public"
MOBILE = ROOT / "mobile" / "assets" / "images"
FONT = PUBLIC / "fonts" / "GlassAntiqua-Regular.ttf"

NAME = "Studio"
BRAND = (0, 122, 255)
BG = (10, 10, 10)
WHITE = (255, 255, 255)
SS = 4  # supersample factor for smooth edges


def mark(size: int, tile: tuple[int, int, int] | None = BRAND, glyph=WHITE) -> Image.Image:
    """Rounded tile with a play triangle, transparent outside the tile."""
    s = size * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if tile is not None:
        d.rounded_rectangle((0, 0, s - 1, s - 1), radius=int(s * 0.22), fill=tile)
    # Play triangle, nudged right so it looks optically centered.
    cx, cy, r = s * 0.53, s * 0.5, s * 0.24
    d.polygon([(cx - r * 0.8, cy - r), (cx - r * 0.8, cy + r), (cx + r, cy)], fill=glyph)
    return img.resize((size, size), Image.LANCZOS)


def on_bg(size: int, scale: float, bg=BG) -> Image.Image:
    """Mark centered on a solid background at `scale` of the canvas."""
    canvas = Image.new("RGB", (size, size), bg)
    m = mark(int(size * scale))
    off = (size - m.width) // 2
    canvas.paste(m, (off, off), m)
    return canvas


def og_image() -> Image.Image:
    w, h = 1200, 630
    img = Image.new("RGB", (w, h), (0, 0, 0))
    m = mark(220)
    font = ImageFont.truetype(str(FONT), 150)
    d = ImageDraw.Draw(img)
    tw = d.textlength(NAME, font=font)
    gap = 48
    x = int((w - (m.width + gap + tw)) / 2)
    img.paste(m, (x, (h - m.height) // 2), m)
    d.text((x + m.width + gap, h / 2), NAME, font=font, fill=WHITE, anchor="lm")
    return img


def main() -> None:
    on_bg(1024, 0.62).save(MOBILE / "icon.png")
    on_bg(512, 0.5).save(MOBILE / "splash-icon.png")
    on_bg(48, 0.9).save(MOBILE / "favicon.png")
    Image.new("RGB", (1024, 1024), BG).save(MOBILE / "android-icon-background.png")
    # Adaptive icons crop to the inner ~66%, so keep the mark inside that.
    fg = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    m = mark(540)
    fg.paste(m, ((1024 - 540) // 2,) * 2, m)
    fg.save(MOBILE / "android-icon-foreground.png")
    mono = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    mm = mark(540, tile=WHITE, glyph=(0, 0, 0, 0))
    mono.paste(mm, ((1024 - 540) // 2,) * 2, mm)
    mono.save(MOBILE / "android-icon-monochrome.png")

    for size, name in ((192, "android-chrome-192x192.png"), (512, "android-chrome-512x512.png"),
                       (180, "apple-touch-icon.png")):
        on_bg(size, 0.72).save(PUBLIC / name)
    for size in (16, 32):
        on_bg(size, 1.0, bg=(0, 0, 0)).save(PUBLIC / f"favicon-{size}x{size}.png")
    on_bg(256, 1.0, bg=(0, 0, 0)).save(PUBLIC / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    og_image().save(PUBLIC / "og-default.png")
    print("icons written")


if __name__ == "__main__":
    main()
