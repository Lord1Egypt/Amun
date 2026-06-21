"""Classification — breath intensity to a flight command.

The original *Invisible-Driver* fit an **unsupervised clustering model** over EEG
features. We keep that idea honestly: calibration records a few seconds of your
silence / soft breath / hard breath and fits a **k-means (k=3)** model over the
loudness frames. The three cluster centres become the silence / soft / hard
anchors used to normalise the live signal.

* The live path (:class:`BreathClassifier`) is **pure standard library** — it
  only needs the three numbers from the profile.
* Fitting the clusters (:func:`fit_profile`) uses **numpy** when available and
  transparently falls back to a pure-Python percentile fit otherwise, so
  calibration never hard-fails.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Sequence

from .preprocessing import normalize

# Flight commands
SILENCE = "silence"  # below the breath gate -> gravity takes over (dive)
GLIDE = "glide"      # a calm sustained breath -> roughly hovering
CLIMB = "climb"      # a forceful exhale -> gain altitude


@dataclass
class CalibrationProfile:
    """Anchors learned during calibration."""

    noise_floor: float = 0.01
    soft: float = 0.06
    hard: float = 0.18
    glide_threshold: float = 0.30   # normalised level separating dive from glide
    climb_threshold: float = 0.66   # normalised level separating glide from climb
    silhouette: float = 0.0         # quality of the 3-way clustering (honest metric)
    n_frames: int = 0

    # ── persistence ──────────────────────────────────────────────────────────
    def save(self, path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2) + "\n")

    @classmethod
    def load(cls, path) -> "CalibrationProfile":
        return cls(**json.loads(Path(path).read_text()))

    @classmethod
    def default(cls) -> "CalibrationProfile":
        return cls()


class BreathClassifier:
    """Maps a smoothed raw loudness to a continuous lift and a discrete command.

    Pure standard library: only needs the three anchors from a profile.
    """

    def __init__(self, profile: CalibrationProfile):
        self.profile = profile

    def lift(self, raw: float) -> float:
        """Continuous upward intensity in ``[0, 1]`` fed to the engine."""
        return normalize(raw, self.profile.noise_floor, self.profile.soft,
                         self.profile.hard)

    def command(self, raw: float) -> str:
        level = self.lift(raw)
        if level < self.profile.glide_threshold:
            return SILENCE
        if level < self.profile.climb_threshold:
            return GLIDE
        return CLIMB


# ── calibration fit ───────────────────────────────────────────────────────────
def fit_profile(samples: Sequence[float]) -> CalibrationProfile:
    """Fit a :class:`CalibrationProfile` from recorded loudness frames.

    Tries a numpy k-means(k=3) and computes a real silhouette score; falls back
    to a percentile fit if numpy is unavailable or there are too few frames.
    """
    data = [float(s) for s in samples if s == s]  # drop NaNs
    if len(data) < 9:
        return _percentile_profile(data)
    try:
        return _kmeans_profile(data)
    except Exception:
        return _percentile_profile(data)


def _percentile_profile(data: List[float]) -> CalibrationProfile:
    if not data:
        return CalibrationProfile.default()
    s = sorted(data)

    def pct(p: float) -> float:
        if len(s) == 1:
            return s[0]
        i = p * (len(s) - 1)
        lo = int(i)
        frac = i - lo
        hi = min(lo + 1, len(s) - 1)
        return s[lo] * (1 - frac) + s[hi] * frac

    noise = pct(0.10)
    soft = pct(0.55)
    hard = pct(0.95)
    return _finalize(noise, soft, hard, silhouette=0.0, n=len(data))


def _kmeans_profile(data: List[float]) -> CalibrationProfile:
    import numpy as np

    x = np.asarray(data, dtype=float).reshape(-1, 1)
    centers = _kmeans_1d(x.ravel(), k=3, iters=60, seed=7)
    centers.sort()
    noise, soft, hard = (float(c) for c in centers)
    sil = _silhouette_1d(x.ravel(), centers)
    return _finalize(noise, soft, hard, silhouette=sil, n=len(data))


def _kmeans_1d(x, k, iters, seed):
    import numpy as np

    rng = np.random.default_rng(seed)
    # k-means++-ish init spread across the observed range
    lo, hi = float(x.min()), float(x.max())
    if hi - lo < 1e-9:
        return np.array([lo, lo, lo])
    centers = np.linspace(lo, hi, k) + rng.normal(0, (hi - lo) * 1e-3, k)
    for _ in range(iters):
        d = np.abs(x[:, None] - centers[None, :])
        labels = d.argmin(axis=1)
        new = centers.copy()
        for j in range(k):
            members = x[labels == j]
            if members.size:
                new[j] = members.mean()
        if np.allclose(new, centers):
            centers = new
            break
        centers = new
    return centers


def _silhouette_1d(x, centers) -> float:
    """Mean silhouette score for the 1-D k-means assignment (honest metric)."""
    import numpy as np

    centers = np.asarray(centers)
    d = np.abs(x[:, None] - centers[None, :])
    labels = d.argmin(axis=1)
    if len(np.unique(labels)) < 2:
        return 0.0
    sil = np.zeros(len(x))
    for i in range(len(x)):
        same = x[labels == labels[i]]
        a = np.abs(x[i] - same).mean() if same.size > 1 else 0.0
        b = np.inf
        for j in np.unique(labels):
            if j == labels[i]:
                continue
            other = x[labels == j]
            b = min(b, np.abs(x[i] - other).mean())
        denom = max(a, b)
        sil[i] = 0.0 if denom == 0 else (b - a) / denom
    return float(sil.mean())


def _finalize(noise, soft, hard, silhouette, n) -> CalibrationProfile:
    # guarantee a strictly increasing, sane ordering
    soft = max(soft, noise + 1e-4)
    hard = max(hard, soft + 1e-4)
    return CalibrationProfile(
        noise_floor=round(noise, 6),
        soft=round(soft, 6),
        hard=round(hard, 6),
        glide_threshold=0.30,
        climb_threshold=0.66,
        silhouette=round(float(silhouette), 4),
        n_frames=int(n),
    )
