"""
Build clean per-brand ambient wallpapers.
No multi-color bokeh balls — soft monochrome/brand gradient only.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1] / "public" / "wallpapers"

# Soft brand glows only (no pink / rainbow)
BRANDS = {
    "champagne": {"dark": (212, 180, 140), "light": (154, 115, 72), "base_dark": (8, 6, 4), "base_light": (248, 244, 238)},
    "gold": {"dark": (232, 197, 71), "light": (166, 124, 18), "base_dark": (10, 8, 0), "base_light": (250, 246, 232)},
    "indigo": {"dark": (123, 147, 255), "light": (74, 92, 173), "base_dark": (4, 6, 14), "base_light": (242, 244, 250)},
    "moss": {"dark": (111, 191, 115), "light": (47, 122, 74), "base_dark": (4, 10, 6), "base_light": (242, 248, 244)},
    # Black: pure black base, soft violet accent glow
    "black": {"dark": (184, 164, 255), "light": (88, 64, 180), "base_dark": (0, 0, 0), "base_light": (246, 244, 252)},
}
W, H = 1280, 720


def soft_orb(draw: ImageDraw.ImageDraw, cx: int, cy: int, rad: int, rgb: tuple[int, int, int], alpha: int) -> None:
    r, g, b = rgb
    for i in range(10, 0, -1):
        a = int(alpha * (i / 10) ** 1.6 * 0.55)
        rr = int(rad * (i / 10))
        draw.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(r, g, b, a))


def build(mode: str, brand: str, cfg: dict) -> Image.Image:
    base_rgb = cfg["base_dark"] if mode == "dark" else cfg["base_light"]
    accent = cfg["dark"] if mode == "dark" else cfg["light"]

    im = Image.new("RGB", (W, H), base_rgb)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    if brand == "black" and mode == "dark":
        # Near-black field with soft violet corner glows
        soft_orb(draw, int(W * 0.15), int(H * 0.1), int(W * 0.38), (184, 164, 255), 42)
        soft_orb(draw, int(W * 0.9), int(H * 0.85), int(W * 0.32), (140, 120, 230), 34)
        soft_orb(draw, int(W * 0.55), int(H * 0.4), int(W * 0.28), (120, 90, 210), 22)
    else:
        # Brand-only soft washes (same hue as brand — no foreign pink/blue balls)
        soft_orb(draw, int(W * 0.12), int(H * 0.08), int(W * 0.45), accent, 95 if mode == "dark" else 70)
        soft_orb(draw, int(W * 0.92), int(H * 0.2), int(W * 0.38), accent, 70 if mode == "dark" else 55)
        soft_orb(draw, int(W * 0.55), int(H * 0.95), int(W * 0.5), accent, 55 if mode == "dark" else 45)

    layer = layer.filter(ImageFilter.GaussianBlur(radius=48 if brand != "black" else 56))
    out = Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")
    # Gentle overall soften — still clearly brand-tinted
    out = out.filter(ImageFilter.GaussianBlur(radius=6 if brand != "black" else 10))
    return out


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    rows: list[tuple[str, int]] = []
    for brand, cfg in BRANDS.items():
        for mode in ("dark", "light"):
            im = build(mode, brand, cfg)
            path = ROOT / f"{brand}-{mode}.jpg"
            # Black dark: max compress pure black; others small but visible
            q = 60 if brand == "black" and mode == "dark" else 70
            im.save(path, "JPEG", quality=q, optimize=True, progressive=True)
            rows.append((path.name, path.stat().st_size))

    # Defaults = champagne
    for mode in ("dark", "light"):
        src = ROOT / f"champagne-{mode}.jpg"
        dst = ROOT / f"studio-{mode}.jpg"
        dst.write_bytes(src.read_bytes())
        rows.append((dst.name, dst.stat().st_size))

    for name, size in rows:
        print(f"{name:28} {size / 1024:6.1f} KB")
    print("done")


if __name__ == "__main__":
    main()
