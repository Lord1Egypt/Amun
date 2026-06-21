"""Feature extraction from a raw audio frame.

Pure standard library — no numpy required — so the live game path and the unit
tests run anywhere. These features turn a buffer of microphone samples into the
two numbers that matter for breath control:

* **RMS**  — loudness, i.e. *how hard* you are breathing.
* **ZCR**  — zero-crossing rate, a cheap timbre measure. Breath is broadband
  noise (high ZCR); a hum or vowel is more tonal (low ZCR). We use it to keep
  talking and background hum from accidentally flying the falcon.

When the microphone lives in the browser (the default), the page computes RMS
with the Web Audio API and streams it directly; these helpers are used by the
optional ``sounddevice`` capture path and by the tests/notebook.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence


def rms(samples: Sequence[float]) -> float:
    """Root-mean-square amplitude of ``samples`` (expects values in ~[-1, 1])."""
    n = len(samples)
    if n == 0:
        return 0.0
    total = 0.0
    for s in samples:
        total += s * s
    return math.sqrt(total / n)


def zero_crossing_rate(samples: Sequence[float]) -> float:
    """Fraction of adjacent sample pairs whose sign changes (0..1)."""
    n = len(samples)
    if n < 2:
        return 0.0
    crossings = 0
    prev = samples[0]
    for s in samples[1:]:
        if (s >= 0.0) != (prev >= 0.0):
            crossings += 1
        prev = s
    return crossings / (n - 1)


def is_breath(rms_value: float, zcr_value: float, *, gate: float = 0.02,
              min_zcr: float = 0.10) -> bool:
    """Heuristic: loud *and* noisy enough to be a breath rather than a hum/silence."""
    return rms_value >= gate and zcr_value >= min_zcr


def frame_features(samples: Sequence[float]) -> dict:
    """Bundle the per-frame features used downstream."""
    r = rms(samples)
    z = zero_crossing_rate(samples)
    return {"rms": r, "zcr": z, "is_breath": is_breath(r, z)}


def envelope(frames: Iterable[Sequence[float]]) -> list:
    """RMS envelope across a sequence of frames (handy for the notebook/EDA)."""
    return [rms(f) for f in frames]
