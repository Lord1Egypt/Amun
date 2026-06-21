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


class SerialSource(BreathSource):
    """Read a normalised signal (0..1, one float per line) from the *Amun Amulet*.

    The Arduino/ESP32 amulet samples a breath/wind sensor, shows status on its
    OLED, blinks an RGB LED, and streams a normalised value over USB serial or a
    Bluetooth (HC-05/HM-10) link that appears as a serial port. Needs the optional
    ``pyserial`` dependency; raises a clear error if it's missing or the port is
    absent, so the app can fall back to the microphone.
    """

    def __init__(self, port: str, baud: int = 115200, timeout: float = 1.0):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self._latest = 0.0
        self._ser = None
        self._thread = None
        self._stop = False

    def start(self) -> None:
        try:
            import serial  # type: ignore  (pyserial)
        except Exception as exc:
            raise RuntimeError(
                "The 'serial' source needs the optional dependency 'pyserial'.\n"
                "Install it with:  pip install 'amun[serial]'\n"
                "Or just use the browser microphone (the default)."
            ) from exc
        try:
            self._ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
        except Exception as exc:
            raise RuntimeError(
                f"Could not open serial port {self.port!r}: {exc}\n"
                "Check the port name / cable, or fall back to the microphone."
            ) from exc
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:  # pragma: no cover - needs a device
        while not self._stop:
            try:
                line = self._ser.readline().decode("ascii", "ignore").strip()
            except Exception:
                break
            if not line:
                continue
            try:
                self._latest = max(0.0, min(1.0, float(line)))
            except ValueError:
                pass

    def read(self) -> float:
        return self._latest

    def close(self) -> None:
        self._stop = True
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None


class NeuroSkySource(BreathSource):
    """Optional *brain* mode — a NeuroSky MindWave headset over Bluetooth serial.

    This brings the original "control with your mind" idea back as a bonus: the
    headset's **attention** value (0..100) becomes the throttle. Parsing is done
    by :mod:`amun.thinkgear` (pure stdlib); the serial link needs ``pyserial``.
    Gracefully degrades — raise on missing dep/port so the app can use the mic.
    """

    def __init__(self, port: str, baud: int = 57600, signal: str = "attention"):
        self.port = port
        self.baud = baud
        self.signal = signal  # "attention" or "meditation"
        self._latest = 0.0
        self._poor = 200
        self._ser = None
        self._thread = None
        self._stop = False

    def start(self) -> None:
        try:
            import serial  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                "The 'neurosky' source needs the optional dependency 'pyserial'.\n"
                "Install it with:  pip install 'amun[serial]'\n"
                "Or use the browser microphone (the default)."
            ) from exc
        try:
            self._ser = serial.Serial(self.port, self.baud, timeout=1.0)
        except Exception as exc:
            raise RuntimeError(
                f"Could not open NeuroSky port {self.port!r}: {exc}\n"
                "Pair the MindWave over Bluetooth, or fall back to the microphone."
            ) from exc
        self._stop = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:  # pragma: no cover - needs a headset
        from .thinkgear import ThinkGearParser

        parser = ThinkGearParser()
        while not self._stop:
            try:
                chunk = self._ser.read(64)
            except Exception:
                break
            for reading in parser.feed(chunk):
                if "poor_signal" in reading:
                    self._poor = reading["poor_signal"]
                if self.signal in reading and self._poor < 100:
                    self._latest = reading[self.signal] / 100.0

    def read(self) -> float:
        return self._latest

    def close(self) -> None:
        self._stop = True
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None


def make_source(kind: str, **kwargs) -> BreathSource:
    """Factory for any signal source.

    ``'sim' | 'replay' | 'mic' | 'serial' | 'neurosky'`` — the last three are the
    optional hardware paths. If a hardware source can't start, the caller should
    fall back to the microphone (the default, always-available path).
    """
    kind = (kind or "sim").lower()
    if kind == "sim":
        return SimSource(**kwargs)
    if kind == "replay":
        return ReplaySource(**kwargs)
    if kind == "mic":
        return MicSource(**kwargs)
    if kind == "serial":
        return SerialSource(**kwargs)
    if kind == "neurosky":
        return NeuroSkySource(**kwargs)
    raise ValueError(f"unknown signal source: {kind!r}")
