# Testing & Verification

Amun follows a "test before completion" rule: every option and code path is
exercised by automated tests that must return exit code `0`.

## Run everything

```bash
pip install -e ".[dev]"     # pytest + numpy + pillow
python tools/test_all.py    # data + calibration + headless run + pytest, asserts exit 0
```

Or just the unit tests:

```bash
PYTHONPATH=src python -m pytest -q
```

## What `tools/test_all.py` does

1. **Sample data** — regenerates the deterministic breath dataset (`tools/make_sample_data.py`).
2. **Calibration** — runs `amun calibrate` non-blocking on the bundled sample.
3. **Headless run** — `amun --source sim --duration 1 --no-input --quiet` must exit cleanly.
4. **pytest** — the full suite below.

## Test suite (`tests/`)

| File | Covers |
|---|---|
| `test_engine.py` | physics, gravity vs thrust, ceiling/ground, scoring, **determinism**, JSON state, reset |
| `test_features.py` | RMS, zero-crossing, breath-vs-silence-vs-tone discrimination |
| `test_classify.py` | k-means calibration fit, **measured silhouette**, anchor ordering, live commands, profile round-trip |
| `test_websocket.py` | RFC 6455 handshake vector, frame encode/decode, masking, partial/extended lengths |
| `test_server.py` | server boots, `/health` 200, index served, **real WebSocket upgrade (101)** + state stream, headless sim |
| `test_thinkgear.py` | NeuroSky ThinkGear parser: checksum, multi-code, split feeds, resync, multi-byte skip |

All tests run with **no microphone and no hardware** — synthetic signals and an
in-process server stand in for real devices.

## Non-blocking CLI guarantee

Every CLI entry point takes flags and never waits on `input()` when arguments are
given, so CI and `tools/test_all.py` never hang:

```bash
amun --source sim --duration 5 --no-input --quiet
amun calibrate --from data/calibration_sample.csv
amun --no-browser --no-input --duration 1     # serve briefly, then exit
```

## Manual smoke test (with a browser)

```bash
python -m amun
# open the page, allow the mic, breathe → falcon climbs; hold breath → it dives.
# no mic? hold SPACE. The game must work either way.
```
