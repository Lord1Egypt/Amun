"""Shared Pillow drawing primitives for Amun's banner and demo GIF.

Renders the same scene the browser canvas draws (Egyptian-cyberpunk sky, temple
columns, ankhs, the falcon of Horus) so the offline art matches the live game.
Fully offline and deterministic — no network, no API quota.
"""

from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw

# palette (matches templates/index.html)
INK = (10, 15, 42)
GOLD = (245, 196, 81)
TEAL = (55, 224, 200)
ROSE = (255, 107, 157)
SAND = (202, 164, 106)

WORLD_W = 100.0
WORLD_H = 100.0


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def sky(w: int, h: int, *, seed: int = 7, with_pyramids: bool = True) -> Image.Image:
    """A gradient night sky with stars, the disc of Ra, and pyramids."""
    img = Image.new("RGB", (w, h), INK)
    px = img.load()
    top, mid, low, base = (10, 15, 42), (26, 17, 64), (58, 33, 80), (90, 47, 68)
    for y in range(h):
        t = y / max(1, h - 1)
        if t < 0.45:
            c = _lerp(top, mid, t / 0.45)
        elif t < 0.8:
            c = _lerp(mid, low, (t - 0.45) / 0.35)
        else:
            c = _lerp(low, base, (t - 0.8) / 0.2)
        for x in range(w):
            px[x, y] = c

    d = ImageDraw.Draw(img, "RGBA")
    rng = random.Random(seed)
    for _ in range(int(w * h / 1400)):
        sx, sy = rng.randint(0, w - 1), rng.randint(0, int(h * 0.7))
        r = rng.choice([1, 1, 1, 2])
        a = rng.randint(60, 200)
        d.ellipse([sx - r, sy - r, sx + r, sy + r], fill=(255, 255, 255, a))

    # disc of Ra (soft glow)
    sun_x, sun_y, sr = int(w * 0.78), int(h * 0.30), int(min(w, h) * 0.16)
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for i in range(sr, 0, -1):
        a = int(120 * (1 - i / sr) ** 1.6)
        gd.ellipse([sun_x - i, sun_y - i, sun_x + i, sun_y + i],
                   fill=(255, 214, 130, a))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")

    if with_pyramids:
        d = ImageDraw.Draw(img, "RGBA")
        _pyramids(d, w, h, base_y=int(h * 0.82), color=(46, 33, 71, 220), n=4, spread=0)
        _pyramids(d, w, h, base_y=int(h * 0.88), color=(36, 26, 58, 255), n=3, spread=1)
        d.rectangle([0, int(h * 0.9), w, h], fill=(28, 18, 38, 255))
    return img


def _pyramids(d, w, h, base_y, color, n, spread):
    span = w / n
    for i in range(-1, n + 1):
        cx = i * span + span * (0.5 + 0.18 * spread)
        pw, ph = span * 0.85, span * 0.62
        d.polygon([(cx - pw / 2, base_y), (cx, base_y - ph), (cx + pw / 2, base_y)],
                  fill=color)


def _sx(x, w):
    return x / WORLD_W * w


def _sy(y, h):
    return (1 - y / WORLD_H) * h


def draw_columns(d, obstacles, w, h):
    cw = _sx(6, w)
    for ob in obstacles:
        x = _sx(ob["x"], w)
        gap_top = _sy(ob["gap_center"] + ob["gap_half"], h)
        gap_bot = _sy(ob["gap_center"] - ob["gap_half"], h)
        # columns
        d.rectangle([x - cw / 2, 0, x + cw / 2, gap_top], fill=(120, 86, 40))
        d.rectangle([x - cw / 2, gap_bot, x + cw / 2, h], fill=(120, 86, 40))
        # capitals
        d.rectangle([x - cw / 2 - 4, gap_top - 12, x + cw / 2 + 4, gap_top], fill=SAND)
        d.rectangle([x - cw / 2 - 4, gap_bot, x + cw / 2 + 4, gap_bot + 12], fill=SAND)
        # teal gap rims
        d.rectangle([x - cw / 2, gap_top, x + cw / 2, gap_top + 3], fill=TEAL)
        d.rectangle([x - cw / 2, gap_bot - 3, x + cw / 2, gap_bot], fill=TEAL)
        if ob.get("ankh"):
            draw_ankh(d, x, _sy(ob["gap_center"], h), max(w, h) * 0.016)


def draw_ankh(d, x, y, s):
    d.ellipse([x - s, y - 2.2 * s, x + s, y - 0.2 * s], outline=GOLD, width=max(2, int(s / 2)))
    d.line([x, y - 0.6 * s, x, y + 2 * s], fill=GOLD, width=max(2, int(s / 2)))
    d.line([x - 1.4 * s, y + 0.4 * s, x + 1.4 * s, y + 0.4 * s], fill=GOLD, width=max(2, int(s / 2)))


def draw_falcon(d, x, y, s, wing=0.0, breath=0.0):
    """Stylised falcon of Horus, gliding to the right."""
    flap = math.sin(wing) * 0.5
    # thrust aura
    if breath > 0.05:
        r = int(s * 6 * breath)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(55, 224, 200, 45))

    dark = (24, 32, 58)
    # tail (back-left)
    d.polygon([(x - s * 1.0, y), (x - s * 3.0, y - s * 0.5),
               (x - s * 3.0, y + s * 0.7), (x - s * 1.0, y + s * 0.4)], fill=dark)
    # far wing (slightly behind, dimmer gold)
    d.polygon([(x - s * 0.3, y - s * 0.2),
               (x - s * 2.0, y - s * (1.9 + flap)),
               (x + s * 0.9, y - s * (1.1 + flap)),
               (x + s * 0.4, y - s * 0.2)], fill=(196, 150, 50))
    # body
    d.ellipse([x - s * 1.6, y - s * 0.85, x + s * 1.6, y + s * 0.85], fill=dark)
    # near wing (bright gold, big sweep up-and-back)
    d.polygon([(x - s * 0.2, y),
               (x - s * 2.6, y - s * (2.2 + flap)),
               (x + s * 0.6, y - s * (1.2 + flap)),
               (x + s * 1.0, y + s * 0.1)], fill=GOLD)
    # head
    hx, hy = x + s * 1.5, y - s * 0.35
    d.ellipse([hx - s * 0.7, hy - s * 0.7, hx + s * 0.7, hy + s * 0.7], fill=dark)
    # beak (forward)
    d.polygon([(hx + s * 0.5, hy - s * 0.05), (hx + s * 1.4, hy + s * 0.15),
               (hx + s * 0.5, hy + s * 0.45)], fill=GOLD)
    # eye + eye-of-horus stroke
    d.ellipse([hx - s * 0.1, hy - s * 0.35, hx + s * 0.28, hy + s * 0.03], fill=TEAL)
    d.line([hx - s * 0.2, hy + s * 0.25, hx + s * 0.5, hy + s * 0.25],
           fill=TEAL, width=max(1, int(s / 4)))


def render_scene(state, w, h, *, base=None):
    """Render one game state to an RGB image."""
    img = (base.copy() if base is not None else sky(w, h))
    d = ImageDraw.Draw(img, "RGBA")
    draw_columns(d, state["obstacles"], w, h)
    f = state["falcon"]
    draw_falcon(d, _sx(f["x"], w), _sy(f["y"], h), max(w, h) * 0.021,
                wing=state.get("wing", 0.0), breath=state.get("breath", 0.0))
    return img
