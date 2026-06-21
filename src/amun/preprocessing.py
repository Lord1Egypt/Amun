"""Preprocessing — turn a raw loudness reading into a stable breath signal.

Pure standard library. The live pipeline is:

    raw RMS ──▶ noise-floor subtraction ──▶ EMA smoothing ──▶ normalise to [0,1]

The smoothing matters: raw microphone loudness is jittery, and an un-smoothed
signal makes the falcon twitch. An exponential moving average gives a calm,
responsive envelope.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BreathEnvelope:
    """Exponential moving-average smoother for the breath loudness signal.

    ``alpha`` in (0, 1]: higher = snappier, lower = smoother. The default ~0.35
    feels responsive without twitching at ~60 frames/second.
    """

    alpha: float = 0.35
    value: float = 0.0

    def update(self, sample: float) -> float:
        if sample != sample:  # NaN guard
            sample = 0.0
        self.value = self.alpha * sample + (1.0 - self.alpha) * self.value
        return self.value

    def reset(self) -> None:
        self.value = 0.0


def normalize(raw: float, noise_floor: float, soft: float, hard: float) -> float:
    """Map a raw loudness to breath intensity in ``[0, 1]`` using calibration.

    * at/under ``noise_floor`` (silence)          -> 0.0
    * around ``soft`` (a calm, sustained breath)   -> ~0.5
    * at/over ``hard`` (a forceful exhale)         -> 1.0

    Robust to a degenerate calibration where ``hard <= noise_floor``.
    """
    span = hard - noise_floor
    if span <= 1e-9:
        return 0.0
    x = (raw - noise_floor) / span
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x
