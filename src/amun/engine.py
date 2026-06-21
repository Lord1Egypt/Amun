"""Game engine — the falcon and the sky.

Pure standard library. Deterministic given a seed, so it can be unit-tested and
used to render a reproducible demo without a microphone or a browser.

Coordinate system (world units, independent of screen pixels):

    y = HEIGHT  ── top of the sky
    y = 0       ── the ground (sand)

The falcon sits at a fixed ``x`` while the world scrolls left past it. Gravity
constantly pulls the falcon down; *breath* supplies upward thrust proportional
to its intensity (0.0 = silence, 1.0 = a hard exhale). The player threads the
falcon through gaps between temple columns / pyramid peaks and collects ankhs.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


# ── Tunable constants (world units, seconds) ──────────────────────────────────
WIDTH = 100.0
HEIGHT = 100.0
FALCON_X = 28.0
FALCON_RADIUS = 3.2

GRAVITY = 46.0          # downward pull (units / s^2)
THRUST_MAX = 95.0       # full-breath upward force (units / s^2)
VY_MIN, VY_MAX = -40.0, 46.0

SCROLL_SPEED = 26.0     # world units / s the sky moves left
OBSTACLE_SPACING = 46.0  # horizontal distance between obstacle gaps
GAP_HALF_MIN = 13.0     # half-height of the easiest gap
GAP_HALF_MAX = 18.0
GAP_MARGIN = 12.0       # keep gaps away from the very top/bottom


@dataclass
class Obstacle:
    """A pair of columns with a gap the falcon must fly through."""

    x: float
    gap_center: float
    gap_half: float
    has_ankh: bool
    passed: bool = False
    ankh_taken: bool = False


@dataclass
class GameEngine:
    """Deterministic side-scrolling breath-flight simulation.

    Feed it a breath value with :meth:`set_breath`, advance time with
    :meth:`update`, and read :meth:`state` for rendering.
    """

    seed: int = 0
    width: float = WIDTH
    height: float = HEIGHT

    # runtime state
    rng: random.Random = field(init=False)
    falcon_y: float = field(init=False)
    vy: float = field(init=False)
    breath: float = 0.0
    obstacles: list = field(init=False)
    distance: float = 0.0
    ankhs: int = 0
    alive: bool = True
    started: bool = False
    _next_spawn_x: float = field(init=False)
    _wing: float = 0.0  # cosmetic wing-flap phase

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)
        self.reset()

    # ── lifecycle ────────────────────────────────────────────────────────────
    def reset(self) -> None:
        self.rng.seed(self.seed)
        self.falcon_y = self.height * 0.5
        self.vy = 0.0
        self.breath = 0.0
        self.obstacles = []
        self.distance = 0.0
        self.ankhs = 0
        self.alive = True
        self.started = False
        self._next_spawn_x = self.width + 10.0
        self._wing = 0.0
        # pre-seed a couple of obstacles ahead so the sky is never empty
        for _ in range(3):
            self._spawn_obstacle()

    def set_breath(self, value: float) -> None:
        """Set the current breath intensity, clamped to ``[0, 1]``."""
        if value != value:  # NaN guard
            value = 0.0
        self.breath = 0.0 if value < 0 else 1.0 if value > 1 else value

    # ── simulation ───────────────────────────────────────────────────────────
    def _spawn_obstacle(self) -> None:
        half = self.rng.uniform(GAP_HALF_MIN, GAP_HALF_MAX)
        center = self.rng.uniform(GAP_MARGIN + half, self.height - GAP_MARGIN - half)
        self.obstacles.append(
            Obstacle(
                x=self._next_spawn_x,
                gap_center=center,
                gap_half=half,
                has_ankh=self.rng.random() < 0.55,
            )
        )
        self._next_spawn_x += OBSTACLE_SPACING

    def update(self, dt: float) -> None:
        """Advance the simulation by ``dt`` seconds."""
        if not self.alive:
            return
        # The player must breathe at least a little to launch — until then the
        # falcon hovers, giving newcomers a moment to find their breath.
        if not self.started:
            if self.breath > 0.08:
                self.started = True
            else:
                self._wing += dt * 6.0
                return

        # physics
        accel = self.breath * THRUST_MAX - GRAVITY
        self.vy = _clamp(self.vy + accel * dt, VY_MIN, VY_MAX)
        self.falcon_y += self.vy * dt
        self._wing += dt * (6.0 + 10.0 * self.breath)

        # ground / ceiling
        if self.falcon_y <= FALCON_RADIUS:
            self.falcon_y = FALCON_RADIUS
            self.alive = False
            return
        if self.falcon_y >= self.height - FALCON_RADIUS:
            self.falcon_y = self.height - FALCON_RADIUS
            self.vy = min(self.vy, 0.0)

        # scroll world
        step = SCROLL_SPEED * dt
        self.distance += step
        for ob in self.obstacles:
            ob.x -= step

        # spawn / recycle
        self._next_spawn_x -= step
        while self._next_spawn_x < self.width + OBSTACLE_SPACING:
            self._spawn_obstacle()
        self.obstacles = [ob for ob in self.obstacles if ob.x > -8.0]

        # scoring + collisions
        for ob in self.obstacles:
            if not ob.passed and ob.x < FALCON_X:
                ob.passed = True
            if abs(ob.x - FALCON_X) <= FALCON_RADIUS + 2.5:
                in_gap = (
                    ob.gap_center - ob.gap_half + FALCON_RADIUS
                    <= self.falcon_y
                    <= ob.gap_center + ob.gap_half - FALCON_RADIUS
                )
                if not in_gap:
                    self.alive = False
                    return
                if ob.has_ankh and not ob.ankh_taken:
                    if abs(self.falcon_y - ob.gap_center) <= FALCON_RADIUS + 2.0:
                        ob.ankh_taken = True
                        self.ankhs += 1

    # ── output ───────────────────────────────────────────────────────────────
    @property
    def score(self) -> int:
        """Distance flown plus a bonus for every ankh collected."""
        return int(self.distance) + self.ankhs * 25

    def state(self) -> dict:
        """A JSON-serialisable snapshot for the renderer."""
        return {
            "alive": self.alive,
            "started": self.started,
            "falcon": {"x": FALCON_X, "y": round(self.falcon_y, 3), "r": FALCON_RADIUS},
            "vy": round(self.vy, 3),
            "breath": round(self.breath, 3),
            "wing": round(self._wing % (2 * 3.141592653589793), 4),
            "distance": round(self.distance, 2),
            "ankhs": self.ankhs,
            "score": self.score,
            "obstacles": [
                {
                    "x": round(ob.x, 2),
                    "gap_center": round(ob.gap_center, 2),
                    "gap_half": round(ob.gap_half, 2),
                    "ankh": ob.has_ankh and not ob.ankh_taken,
                }
                for ob in self.obstacles
                if -8.0 < ob.x < self.width + 8.0
            ],
            "world": {"w": self.width, "h": self.height},
        }


def _clamp(value: float, low: float, high: float) -> float:
    return low if value < low else high if value > high else value
