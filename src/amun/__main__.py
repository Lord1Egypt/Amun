"""Command-line entry point for Amun.

    amun                              # serve the browser game (mic in the browser)
    amun --no-browser                 # serve without opening a browser
    amun --source sim --duration 5    # headless run, no browser, no mic
    amun --source mic                 # headless run using the optional sounddevice mic
    amun --source replay --file f.csv # headless run from recorded loudness
    amun calibrate --from data.csv    # fit a calibration profile (non-blocking)

Every mode is non-blocking when given arguments: nothing waits on ``input()``,
so CI and the test runner never hang.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .calibrate import DEFAULT_PROFILE_PATH, calibrate_cli, load_or_default


def _banner() -> str:
    return (
        "\n  𓅃  A M U N  —  Breath–Computer Interface\n"
        "      pilot a falcon with your breath · no electrodes · just air\n"
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="amun", description="Amun — a Breath–Computer Interface.")
    sub = p.add_subparsers(dest="command")

    # default: serve / run
    p.add_argument("--source", choices=["browser", "sim", "replay", "mic"],
                   default="browser", help="breath source (default: browser mic)")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8011)
    p.add_argument("--file", type=Path, help="loudness file for --source replay")
    p.add_argument("--duration", type=float, default=None,
                   help="seconds to run a headless source then exit")
    p.add_argument("--no-browser", action="store_true", help="don't auto-open a browser")
    p.add_argument("--no-input", action="store_true",
                   help="never wait for keyboard input (for automation)")
    p.add_argument("--quiet", action="store_true")

    cal = sub.add_parser("calibrate", help="fit a calibration profile (non-blocking)")
    cal.add_argument("--from", dest="from_file", type=Path, default=None,
                     help="loudness file (one float/line); defaults to bundled sample")
    cal.add_argument("--out", type=Path, default=DEFAULT_PROFILE_PATH)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "calibrate":
        profile = calibrate_cli(source_file=args.from_file, save_to=args.out)
        print(f"Calibrated from {profile.n_frames} frames "
              f"(silhouette={profile.silhouette:.3f})")
        print(f"  noise_floor={profile.noise_floor}  soft={profile.soft}  "
              f"hard={profile.hard}")
        print(f"Saved profile -> {args.out}")
        return 0

    profile = load_or_default()

    # Headless sources run the engine directly without a browser.
    if args.source in ("sim", "replay", "mic"):
        from .ingestion import make_source
        from .server import run_headless

        kwargs = {}
        if args.source == "replay":
            if not args.file:
                print("error: --source replay requires --file", file=sys.stderr)
                return 2
            kwargs["path"] = args.file
        source = make_source(args.source, **kwargs)
        if not args.quiet:
            print(_banner())
            print(f"  running headless source={args.source} "
                  f"duration={args.duration or '∞'}\n")
        final = run_headless(source, profile=profile, duration=args.duration,
                             quiet=args.quiet)
        if not args.quiet:
            print(f"  final score: {final['score']}  ankhs: {final['ankhs']}")
        return 0

    # Default: browser game.
    from .server import run_server

    httpd = run_server(host=args.host, port=args.port, profile=profile,
                       open_browser=not args.no_browser)
    url = f"http://{args.host}:{httpd.server_address[1]}/"
    if not args.quiet:
        print(_banner())
        print(f"  🜂  serving at {url}")
        print("     open it, allow the microphone, and breathe.")
        print("     (no mic? press & hold SPACE to breathe.  Ctrl+C to stop.)\n")

    if args.no_input:
        # bounded run for automation
        deadline = time.monotonic() + (args.duration or 1.0)
        import threading

        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        while time.monotonic() < deadline:
            time.sleep(0.1)
        httpd.shutdown()
        return 0

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  𓂀  may Ma'at weigh your flight kindly. Goodbye.")
    finally:
        httpd.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
