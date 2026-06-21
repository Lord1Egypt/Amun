<div align="center">

# 𓅃 Amun — a Breath–Computer Interface

**Same acronym. No electrodes. Just air.**

Pilot the falcon of Horus across the Egyptian sky using nothing but your breath.
Soft breath glides, a hard exhale climbs, silence dives into gravity.

</div>

---

> A ground-up reimagining of [`CoffeeIsAllYouNeed/Invisible-Driver`](https://github.com/CoffeeIsAllYouNeed/Invisible-Driver).
> The original was a **Brain**–Computer Interface — drive a car with EEG brain waves
> through an Arduino, electrodes and a clustering model. **Amun keeps the exact
> acronym and changes the principle:** here **BCI** means **Breath**–Computer
> Interface. The signal source becomes the microphone every device already has —
> no electrodes, no Arduino, fully offline.

## Why this is "the same idea, but better"

| | Invisible-Driver (original) | **Amun** (this repo) |
|---|---|---|
| Principle | **Brain** waves (EEG) | **Breath** (acoustic) |
| Hardware | Arduino + BioAmp + gel electrodes | **None** — any microphone |
| Acronym | Brain–Computer Interface | **Breath**–Computer Interface |
| Game | drive a racing car | fly a falcon over Egypt |
| Dependencies | Python ML stack + serial | **zero** for the core game |
| Runs offline | partly | **100% offline** |

The science still lives in Python — a real `ingestion → preprocessing → features →
classify → engine` pipeline with k-means calibration — but the microphone moves
into the browser, so the whole thing runs with **no third-party dependencies**.

## Quickstart

```bash
git clone https://github.com/Lord1Egypt/Amun
cd Amun
python -m amun           # opens the game in your browser
```

Allow the microphone and **breathe**. No microphone? Press and hold **SPACE**.

Headless / no browser (great for a quick check or CI):

```bash
python -m amun --source sim --duration 5 --no-input
```

## How the breath becomes flight

```
microphone ─▶ ingestion ─▶ preprocessing ─▶ features ─▶ classify ─▶ engine ─▶ render
 (browser)    loudness      noise-floor +     RMS /      k-means      falcon    canvas
              frames        EMA smoothing     ZCR        anchors      physics
```

- **Silence** → no thrust → gravity → the falcon **dives**.
- **Soft breath** → partial thrust → the falcon **glides** level.
- **Hard exhale** → full thrust → the falcon **climbs**.

See [`docs/`](docs/) for the architecture, the signal pipeline, calibration, and
the optional real wind-sensor hardware path.

## Project layout

```
src/amun/      engine, ingestion, preprocessing, features, classify, calibrate, server
templates/     the browser game (Web Audio mic + canvas renderer)
model/         your calibration profile (JSON)
tools/         sample-data generator, demo-gif renderer, asset generator, test runner
tests/         pytest suite (engine, features, classify, websocket, server)
notebooks/     breath-signal exploration + honest clustering metric
docs/          architecture & guides     hardware/  optional breath-sensor notes
```

## Status

See [`CHECKPOINTS.md`](CHECKPOINTS.md) for the live build log and
[`TESTING.md`](TESTING.md) for how everything is verified.

## License

MIT © 2026 Mohamed Mounir ([Lord1Egypt](https://github.com/Lord1Egypt))
