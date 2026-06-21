"""Ingestion — where the breath comes from.

Four interchangeable sources implement :class:`BreathSource`:

* ``sim``       — a scripted/auto breath signal (no hardware, no browser).
* ``replay``    — newline-delimited loudness values from a file.
* ``mic``       — live microphone capture via the optional ``sounddevice`` dep.
* (browser)     — the default UI streams loudness over WebSocket; handled in
                  :mod:`amun.server`, not here.

Each source yields a raw loudness value per :meth:`read`; the pipeline
(preprocessing + classify) turns it into lift.
"""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Optional


class BreathSource:
    """Common interface for breath signal sources."""

    def start(self) -> None:  # pragma: no cover - trivial
        pass

    def read(self) -> float:
        """Return the latest raw loudness (>= 0)."""
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover - trivial
        pass


class SimSource(BreathSource):
    """Hardware-free breath signal.

    Produces a gentle, breathing-like oscillation so ``python -m amun --source
    sim`` visibly runs with no microphone. Pass your own ``fn(t)->loudness`` to
    script a specific pattern (used by the demo renderer's autopilot).
    """

    def __init__(self, fn=None, *, amplitude: float = 0.16, period: float = 2.4):
        self.fn = fn
        self.amplitude = amplitude
        self.period = period
        self._t0 = time.monotonic()

    def start(self) -> None:
        self._t0 = time.monotonic()

    def read(self) -> float:
        t = time.monotonic() - self._t0
        if self.fn is not None:
            return max(0.0, float(self.fn(t)))
        # raised sine: mostly breathing softly, periodic stronger exhales
        phase = (t % self.period) / self.period
        base = 0.5 * (1 - math.cos(2 * math.pi * phase))
        return self.amplitude * (0.4 + base)


class ReplaySource(BreathSource):
    """Replay loudness values recorded earlier (one float per line)."""

    def __init__(self, path, loop: bool = True):
        self.values = [
            float(line)
            for line in Path(path).read_text().splitlines()
            if line.strip()
        ]
        self.loop = loop
        self.i = 0

    def read(self) -> float:
        if not self.values:
            return 0.0
        if self.i >= len(self.values):
            if not self.loop:
                return 0.0
            self.i = 0
        v = self.values[self.i]
        self.i += 1
        return v


class MicSource(BreathSource):
    """Live microphone capture via the optional ``sounddevice`` dependency.

    Computes per-block RMS on a background audio callback. Raises a helpful
    error (not an import crash) if ``sounddevice`` isn't installed.
    """

    def __init__(self, samplerate: int = 16000, blocksize: int = 512):
        self.samplerate = samplerate
        self.blocksize = blocksize
        self._latest = 0.0
        self._stream = None

    def start(self) -> None:
        try:
            import sounddevice as sd  # type: ignore
        except Exception as exc:  # pragma: no cover - depends on optional dep
            raise RuntimeError(
                "The 'mic' source needs the optional dependency 'sounddevice'.\n"
                "Install it with:  pip install 'amun[mic]'\n"
                "Or run the browser UI (default) or '--source sim'."
            ) from exc
        from .features import rms

        def _cb(indata, frames, time_info, status):  # pragma: no cover - audio cb
            mono = [float(s[0]) for s in indata]
            self._latest = rms(mono)

        self._stream = sd.InputStream(
            channels=1, samplerate=self.samplerate,
            blocksize=self.blocksize, callback=_cb,
        )
        self._stream.start()

    def read(self) -> float:
        return self._latest

    def close(self) -> None:  # pragma: no cover - audio teardown
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None


def make_source(kind: str, **kwargs) -> BreathSource:
    """Factory: ``make_source('sim' | 'replay' | 'mic', ...)``."""
    kind = (kind or "sim").lower()
    if kind == "sim":
        return SimSource(**kwargs)
    if kind == "replay":
        return ReplaySource(**kwargs)
    if kind == "mic":
        return MicSource(**kwargs)
    raise ValueError(f"unknown breath source: {kind!r}")
