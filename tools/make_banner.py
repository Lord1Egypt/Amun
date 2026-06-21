#!/usr/bin/env python3
"""Render Amun's hero banner and logo offline with Pillow (no network/quota).

Produces:
    assets/hero.png    wide README banner with the falcon scene + title
    assets/logo.png    square amulet emblem (falcon + ankh)

When the Gemini image quota is available you can instead/also run
``tools/gen_assets.py`` for AI concept art; this renderer guarantees the repo
always has clean, on-brand artwork with zero dependencies beyond Pillow.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from PIL import Image, ImageDraw, ImageFont, ImageFilter  # noqa: E402
import _artkit as art  # noqa: E402

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _glow_text(img, xy, text, font, fill, glow):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.text(xy, text, font=font, fill=glow + (180,))
    layer = layer.filter(ImageFilter.GaussianBlur(6))
    img.alpha_composite(layer)
    ImageDraw.Draw(img).text(xy, text, font=font, fill=fill + (255,))


def make_hero(out: Path, w=1280, h=640):
    base = art.sky(w, h, seed=4)
    d = ImageDraw.Draw(base, "RGBA")
    art.draw_columns(d, [
        {"x": 92, "gap_center": 55, "gap_half": 20, "ankh": True},
    ], w, h)
    # wind streaks lifting the falcon (kept on the right, clear of the title)
    fx, fy = w * 0.64, h * 0.40
    for i in range(6):
        yy = fy + (i - 3) * 14
        d.line([(fx - 240 - i * 18, yy), (fx - 90, yy)],
               fill=(55, 224, 200, 70), width=3)
    art.draw_falcon(d, fx, fy, max(w, h) * 0.040, wing=0.7, breath=0.0)

    img = base.convert("RGBA")
    title = _font(FONT_BOLD, 118)
    sub = _font(FONT_BOLD, 34)
    tag = _font(FONT, 26)
    _glow_text(img, (70, 70), "AMUN", title, art.GOLD, art.GOLD)
    _glow_text(img, (78, 210), "Breath–Computer Interface", sub, art.TEAL, art.TEAL)
    ImageDraw.Draw(img).text((80, 262), "Same acronym. No electrodes. Just air.",
                             font=tag, fill=(220, 214, 240, 255))
    ImageDraw.Draw(img).text(
        (80, h - 60), "pilot the falcon of Horus with your breath",
        font=tag, fill=(150, 200, 200, 255))
    img.convert("RGB").save(out, "PNG")
    print(f"wrote {out} ({out.stat().st_size//1024} KB)")


def make_logo(out: Path, size=512):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = size / 2
    # amulet disc
    for i in range(int(size * 0.46), 0, -1):
        t = i / (size * 0.46)
        a = int(255 * (1 - t) ** 0.4)
        col = art._lerp((26, 17, 64), (10, 15, 42), t)
        d.ellipse([cx - i, cy - i, cx + i, cy + i], fill=col + (255,))
    d.ellipse([cx - size * 0.46, cy - size * 0.46, cx + size * 0.46, cy + size * 0.46],
              outline=art.GOLD + (255,), width=max(3, size // 90))
    # falcon
    art.draw_falcon(d, cx - size * 0.04, cy - size * 0.02, size * 0.085,
                    wing=0.5, breath=0.0)
    # ankh accent
    art.draw_ankh(d, cx + size * 0.30, cy + size * 0.28, size * 0.05)
    img.save(out, "PNG")
    print(f"wrote {out} ({out.stat().st_size//1024} KB)")


def main() -> int:
    ASSETS = ROOT / "assets"
    ASSETS.mkdir(parents=True, exist_ok=True)
    make_hero(ASSETS / "hero.png")
    make_logo(ASSETS / "logo.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
