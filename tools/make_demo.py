#!/usr/bin/env python3
"""Render a reproducible gameplay GIF — no microphone, no browser, no network.

Runs the real :class:`amun.engine.GameEngine` with a small autopilot that threads
the falcon through the gaps, drawing each frame with Pillow via :mod:`_artkit`.
The result (``assets/demo.gif``) is what the README shows.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from amun.engine import GameEngine, FALCON_X  # noqa: E402
import _artkit as art  # noqa: E402


def autopilot(engine: GameEngine) -> float:
    """A gentle proportional controller: aim for the next gap centre."""
    target = engine.height * 0.5
    nearest_dx = 1e9
    for ob in engine.obstacles:
        dx = ob.x - FALCON_X
        if dx > -4 and dx < nearest_dx:
            nearest_dx = dx
            target = ob.gap_center
    err = target - engine.falcon_y
    # breath ~ hover (0.48) + correct altitude error - damp vertical velocity
    breath = 0.48 + 0.05 * err - 0.012 * engine.vy
    return max(0.0, min(1.0, breath))


def main(out: Path = None, width=720, height=405, seconds=8.0, fps=25) -> int:
    out = out or (ROOT / "assets" / "demo.gif")
    out.parent.mkdir(parents=True, exist_ok=True)

    engine = GameEngine(seed=11)
    engine.set_breath(0.5)
    engine.update(1 / fps)  # launch

    base = art.sky(width, height, seed=11)
    frames = []
    dt = 1.0 / fps
    for _ in range(int(seconds * fps)):
        engine.set_breath(autopilot(engine))
        engine.update(dt)
        if not engine.alive:
            engine.reset()
            engine.set_breath(0.5)
            engine.update(dt)
        frames.append(art.render_scene(engine.state(), width, height, base=base))

    # palette-optimised, looping GIF
    frames[0].save(
        out, save_all=True, append_images=frames[1:],
        duration=int(1000 / fps), loop=0, optimize=True,
    )
    kb = out.stat().st_size / 1024
    print(f"Wrote {len(frames)} frames -> {out}  ({kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
