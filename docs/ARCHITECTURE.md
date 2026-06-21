# Architecture

Amun mirrors the original *Invisible-Driver* pipeline but moves the sensor into
the browser, so the **core game has zero third-party dependencies** and runs fully
offline.

```
┌──────────────────────────── browser (templates/index.html) ────────────────────────────┐
│  Web Audio mic ─▶ per-frame RMS ──┐                          ┌──▶ <canvas> renderer      │
│  (or SPACE key)                   │  WebSocket (RFC 6455)    │     falcon · columns · HUD │
└───────────────────────────────────┼─────────────────────────┼────────────────────────────┘
                                     ▼                         │
┌──────────────────────────── server (src/amun/server.py) ────┼────────────────────────────┐
│  stdlib http.server + hand-rolled WebSocket                  │                             │
│                                                              │                             │
│   ingestion ─▶ preprocessing ─▶ features ─▶ classify ─▶ engine ─▶ state ──────────────────┘
│   raw loudness  noise-floor +     RMS/ZCR    k-means     falcon physics  (60 Hz broadcast) │
│                 EMA smoothing                anchors                                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
        ▲
        │ optional hardware (falls back to the mic if absent)
   ┌────┴───────────────────────────────────────────┐
   │ SerialSource  ── Amun Amulet (Arduino + sensor) │
   │ NeuroSkySource ─ MindWave EEG (thinkgear.py)    │
   └─────────────────────────────────────────────────┘
```

## Modules (`src/amun/`)

| Module | Responsibility | Deps |
|---|---|---|
| `engine.py` | deterministic falcon-flight physics, obstacles, scoring | stdlib |
| `features.py` | RMS + zero-crossing-rate, breath/silence/tone gate | stdlib |
| `preprocessing.py` | EMA envelope + calibrated normalisation | stdlib |
| `classify.py` | calibration profile, **k-means(3)** fit + silhouette, live classifier | stdlib live; numpy to fit |
| `ingestion.py` | signal sources: sim / replay / mic / serial / neurosky | stdlib; sounddevice/pyserial optional |
| `calibrate.py` | non-blocking calibration + JSON profile load/save | stdlib |
| `thinkgear.py` | NeuroSky ThinkGear protocol parser | stdlib |
| `server.py` | HTTP + RFC 6455 WebSocket, per-session game loop, headless runner | stdlib |
| `__main__.py` | CLI; graceful fallback from hardware → browser mic | stdlib |

## Why a hand-rolled WebSocket?

The game needs a low-latency, bidirectional stream (breath frames up, game state
down). Implementing RFC 6455 in ~80 lines of stdlib keeps the project genuinely
dependency-free and offline — and it's small enough to unit-test (handshake vector
+ frame codec in `tests/test_websocket.py`).

## Determinism

`GameEngine` is seeded, so the same seed + same breath sequence yields identical
obstacles and outcomes. This powers reproducible tests and the offline demo GIF
(`tools/make_demo.py`).
