#!/usr/bin/env python3
"""Generate branding art with Gemini (Nano Banana Pro) and strip the watermark.

Reads the API key from ``~/.config/gemini/api_key`` and asks
``gemini-3-pro-image`` (Nano Banana Pro) for each asset, then crops the bottom
strip where the Gemini badge sits so the saved PNGs are clean.

    python tools/gen_assets.py            # generate all assets
    python tools/gen_assets.py hero logo  # just these

Network + API key required; this is a one-off authoring tool, not part of the
game runtime. Uses only urllib (stdlib) for the request and Pillow for cropping.
"""

from __future__ import annotations

import base64
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
KEY_PATH = Path.home() / ".config" / "gemini" / "api_key"
MODEL = "gemini-3-pro-image"  # Nano Banana Pro
ENDPOINT = (f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{MODEL}:generateContent")

STYLE = ("Egyptian-cyberpunk concept art, deep navy night sky with teal (#37e0d8) "
         "and gold (#f5c451) lighting, glowing neon hieroglyphs, fine particles of "
         "wind, cinematic, high detail, no text, no words, no letters, no logo.")

ASSETS_SPEC = {
    "hero": {
        "aspect": "16:9",
        "prompt": ("A majestic golden falcon of Horus gliding through a twilight "
                   "sky between towering glowing Egyptian temple columns, pyramids "
                   "silhouetted on the horizon, the disc of Ra setting, streams of "
                   "luminous breath/wind lifting the falcon. " + STYLE),
    },
    "logo": {
        "aspect": "1:1",
        "prompt": ("A minimalist circular amulet emblem: a stylised falcon merged "
                   "with an ankh, radiant gold on deep navy, subtle glow, emblem "
                   "centered, clean negative space. " + STYLE),
    },
    "social": {
        "aspect": "16:9",
        "prompt": ("A wide atmospheric banner: a lone falcon ascending on a column "
                   "of glowing teal wind through a vast Egyptian sky, pyramids and "
                   "stars, lots of open sky, cinematic and minimal. " + STYLE),
    },
}


def _api_key() -> str:
    return KEY_PATH.read_text().strip()


def generate(name: str, spec: dict) -> Path:
    body = {
        "contents": [{"parts": [{"text": spec["prompt"]}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": spec["aspect"]},
        },
    }
    req = urllib.request.Request(
        f"{ENDPOINT}?key={_api_key()}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    print(f"  · requesting {name} ({spec['aspect']}) …", flush=True)
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())

    b64 = None
    for part in data["candidates"][0]["content"]["parts"]:
        inline = part.get("inlineData") or part.get("inline_data")
        if inline and "data" in inline:
            b64 = inline["data"]
            break
    if b64 is None:
        raise RuntimeError(f"no image in response for {name}: {json.dumps(data)[:300]}")

    ASSETS.mkdir(parents=True, exist_ok=True)
    raw = ASSETS / f"{name}.raw.png"
    raw.write_bytes(base64.b64decode(b64))
    out = strip_watermark(raw, ASSETS / f"{name}.png")
    raw.unlink(missing_ok=True)
    print(f"    saved {out}")
    return out


def strip_watermark(src: Path, dst: Path, crop_frac: float = 0.07) -> Path:
    """Crop the bottom strip where the Gemini badge sits (bottom-right corner)."""
    from PIL import Image

    img = Image.open(src).convert("RGB")
    w, h = img.size
    cropped = img.crop((0, 0, w, int(h * (1 - crop_frac))))
    cropped.save(dst, "PNG")
    return dst


def main(argv=None) -> int:
    names = argv or list(ASSETS_SPEC)
    unknown = [n for n in names if n not in ASSETS_SPEC]
    if unknown:
        print(f"unknown assets: {unknown}; choices: {list(ASSETS_SPEC)}", file=sys.stderr)
        return 2
    if not KEY_PATH.exists():
        print(f"no API key at {KEY_PATH}", file=sys.stderr)
        return 1
    ok = True
    for name in names:
        try:
            generate(name, ASSETS_SPEC[name])
        except Exception as exc:  # keep going; assets are optional polish
            ok = False
            print(f"    ! failed {name}: {exc}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:] or None))
