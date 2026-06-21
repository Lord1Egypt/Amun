#!/usr/bin/env python3
"""Generate a deterministic sample breath dataset.

So the tests, the notebook and offline calibration all work with **no
microphone**, we synthesise a labelled loudness dataset that imitates three
breath states (silence / soft / hard). The output is fully reproducible.

Writes:
    data/calibration_sample.csv   one loudness value per line (unlabelled)
    data/breath_labelled.csv      loudness,label   (for the EDA notebook)

Uses numpy if available; falls back to the stdlib ``random`` module otherwise.
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

# (label, mean loudness, std, count) — values on the Web-Audio RMS scale (~0..0.3)
STATES = [
    ("silence", 0.010, 0.004, 220),
    ("soft", 0.065, 0.010, 220),
    ("hard", 0.190, 0.022, 220),
]
SEED = 7


def _generate():
    try:
        import numpy as np

        rng = np.random.default_rng(SEED)
        rows = []
        for label, mean, std, n in STATES:
            vals = np.clip(rng.normal(mean, std, n), 0.0, None)
            rows += [(float(v), label) for v in vals]
        rng.shuffle(rows)
        return rows
    except Exception:
        import random

        rng = random.Random(SEED)
        rows = []
        for label, mean, std, n in STATES:
            for _ in range(n):
                rows.append((max(0.0, rng.gauss(mean, std)), label))
        rng.shuffle(rows)
        return rows


def main() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    rows = _generate()

    with (DATA / "calibration_sample.csv").open("w") as f:
        for value, _ in rows:
            f.write(f"{value:.6f}\n")

    with (DATA / "breath_labelled.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["loudness", "label"])
        for value, label in rows:
            w.writerow([f"{value:.6f}", label])

    print(f"Wrote {len(rows)} frames -> {DATA/'calibration_sample.csv'}")
    print(f"Wrote {len(rows)} labelled frames -> {DATA/'breath_labelled.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
