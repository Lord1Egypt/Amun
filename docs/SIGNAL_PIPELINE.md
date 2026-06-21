# The Signal Pipeline — breath to flight

This is the heart of Amun: how an acoustic breath becomes an upward force on the
falcon. It mirrors the original EEG pipeline, one stage at a time.

## 1. Ingestion

A *loudness* value arrives each frame (~60 Hz) from one of:

- the **browser microphone** (default) — the page computes RMS with the Web Audio
  API and streams it (`{"type":"breath","rms":x}`),
- the optional **Amun Amulet** or **NeuroSky** hardware (`ingestion.py`),
- **sim / replay** sources for offline runs and tests.

## 2. Preprocessing (`preprocessing.py`)

Raw loudness is jittery, so we:

1. subtract the calibrated **noise floor** (your silence),
2. apply an **exponential moving average** (`BreathEnvelope`, α≈0.35) for a calm,
   responsive envelope,
3. **normalise** to `[0, 1]` using your soft/hard anchors.

```
intensity = clamp( (raw - noise_floor) / (hard - noise_floor), 0, 1 )
```

## 3. Features (`features.py`)

For the hardware/headless path that sees raw audio samples, we compute:

- **RMS** — loudness (how hard you breathe),
- **Zero-crossing rate** — timbre; breath is broadband (high ZCR), a hum/vowel is
  tonal (low ZCR). `is_breath()` requires *loud **and** noisy* so talking and
  background hum don't fly the falcon.

(The browser path sends RMS directly; these are used by `MicSource` and the EDA.)

## 4. Classify (`classify.py`)

Calibration fits a **k-means(k=3)** model over your recorded frames, producing the
*silence / soft / hard* anchors and a **measured silhouette score** (honest
clustering quality — see `notebooks/breath_eda.ipynb`). At play time the
classifier turns the normalised intensity into:

- a **continuous lift** in `[0, 1]` fed to the engine (analog control, not 3 buckets),
- an advisory **command**: `silence` / `glide` / `climb`.

## 5. Engine (`engine.py`)

Gravity pulls the falcon down at all times; breath adds upward thrust:

```
accel = lift * THRUST_MAX - GRAVITY
vy   += accel * dt
y    += vy * dt
```

So **silence → dive**, **soft breath → glide**, **hard exhale → climb**. Collisions
with temple columns end the flight; ankhs in the gaps add score.

## 6. Render

The server broadcasts the JSON game state at ~60 Hz; the browser canvas draws the
falcon, columns, ankhs and HUD. The same scene is rendered offline by
`tools/_artkit.py` for the banner and demo GIF, so art and gameplay match.

## Tuning cheat-sheet

| Symptom | Knob |
|---|---|
| Falcon too twitchy | lower `BreathEnvelope.alpha` (`preprocessing.py`) |
| Hard to climb | raise `THRUST_MAX` or lower `hard` anchor (re-calibrate) |
| Dives too fast | lower `GRAVITY` (`engine.py`) |
| Talking flies the falcon | raise `min_zcr`/`gate` in `features.is_breath` |
