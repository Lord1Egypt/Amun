#!/usr/bin/env python3
"""Run the whole Amun verification suite and assert a clean exit.

Mirrors the project rule "test before completion": regenerate sample data, run
calibration non-blocking, run a headless game, and run the pytest suite. Exits
non-zero if anything fails, so CI and automation can rely on it.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def step(title: str, cmd: list) -> None:
    print(f"\n=== {title} ===")
    env_cmd = [sys.executable, *cmd]
    result = subprocess.run(env_cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"FAILED: {title} (exit {result.returncode})")
        sys.exit(result.returncode)


def main() -> int:
    # 1. regenerate sample data deterministically
    step("sample data", ["tools/make_sample_data.py"])

    # 2. non-blocking calibration from the bundled sample
    step("calibrate (non-blocking)", ["-m", "amun", "calibrate"])

    # 3. a short headless game must run and exit cleanly
    step("headless run", ["-m", "amun", "--source", "sim",
                          "--duration", "1", "--no-input", "--quiet"])

    # 4. the pytest suite
    print("\n=== pytest ===")
    result = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT)
    if result.returncode != 0:
        print(f"FAILED: pytest (exit {result.returncode})")
        sys.exit(result.returncode)

    print("\n✅ ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    # ensure `amun` is importable for the -m steps
    import os

    os.environ["PYTHONPATH"] = str(SRC) + os.pathsep + os.environ.get("PYTHONPATH", "")
    raise SystemExit(main())
