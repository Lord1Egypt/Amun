"""Calibration — learn your personal silence / soft / hard breath levels.

Two entry points:

* :func:`calibrate_from_samples` — fit a profile from loudness frames you already
  have (used by the browser calibration step, the notebook and the tests).
* :func:`calibrate_cli` — a non-blocking helper that fits from a replay/sample
  file or from bundled sample data, so automation never hangs on ``input()``
  (per the project's CLI rules).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

from .classify import CalibrationProfile, fit_profile

DEFAULT_PROFILE_PATH = Path(__file__).resolve().parents[2] / "model" / "profile.json"


def calibrate_from_samples(samples: Sequence[float],
                           save_to: Optional[Path] = None) -> CalibrationProfile:
    """Fit and (optionally) save a calibration profile from loudness frames."""
    profile = fit_profile(samples)
    if save_to is not None:
        Path(save_to).parent.mkdir(parents=True, exist_ok=True)
        profile.save(save_to)
    return profile


def load_or_default(path: Optional[Path] = None) -> CalibrationProfile:
    """Load the saved profile, or fall back to a sane default."""
    path = Path(path or DEFAULT_PROFILE_PATH)
    if path.exists():
        try:
            return CalibrationProfile.load(path)
        except Exception:
            pass
    return CalibrationProfile.default()


def _read_values(path: Path) -> list:
    return [
        float(line)
        for line in Path(path).read_text().splitlines()
        if line.strip()
    ]


def calibrate_cli(source_file: Optional[Path] = None,
                  save_to: Optional[Path] = None) -> CalibrationProfile:
    """Non-blocking calibration for scripts/CI.

    Reads loudness values from ``source_file`` (one float per line). If none is
    given, uses the bundled sample dataset so it always succeeds offline.
    """
    if source_file is not None:
        values = _read_values(Path(source_file))
    else:
        sample = (Path(__file__).resolve().parents[2]
                  / "data" / "calibration_sample.csv")
        values = _read_values(sample) if sample.exists() else []
    profile = calibrate_from_samples(values, save_to=save_to or DEFAULT_PROFILE_PATH)
    return profile
