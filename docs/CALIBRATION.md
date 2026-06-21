# Calibration

Every microphone, room and pair of lungs is different. Calibration learns *your*
silence / soft / hard breath levels so the falcon responds the way you expect.

## In the browser (recommended)

When you choose **"Use my breath"**, Amun runs a 3-step wizard:

1. **Be still** — records your silence (noise floor).
2. **Soft breath** — a gentle, steady exhale.
3. **Hard exhale** — blow like you're putting out candles.

It streams the recorded frames to the server, which fits the model and replies with
your profile (and its silhouette score). You can re-calibrate any time from the
game-over screen.

## From the command line (non-blocking)

```bash
# fit from a recorded loudness file (one float per line)
amun calibrate --from my_breath.csv --out model/profile.json

# or from the bundled sample data (always works offline)
amun calibrate
```

## What gets learned

A small JSON profile (`model/profile.json`):

```json
{
  "noise_floor": 0.0096,
  "soft": 0.064,
  "hard": 0.187,
  "glide_threshold": 0.30,
  "climb_threshold": 0.66,
  "silhouette": 0.84,
  "n_frames": 660
}
```

- **noise_floor / soft / hard** — the three k-means cluster centres used to
  normalise your live breath.
- **silhouette** — *measured* clustering quality on your data (1.0 = perfectly
  separated). It is computed, never hard-coded.
- thresholds — where dive becomes glide becomes climb.

> JSON, not pickle: profiles are human-readable, safe to share, and portable.

## How the fit works

`classify.fit_profile()` runs a 1-D **k-means(3)** (numpy) and computes a real
silhouette score; if numpy is unavailable or there are too few frames it falls
back to a percentile fit, so calibration never hard-fails. See
`notebooks/breath_eda.ipynb` for the analysis on bundled sample data.

## Troubleshooting

| Problem | Fix |
|---|---|
| Falcon climbs at the slightest sound | re-calibrate; ensure step 1 is truly silent |
| Can't climb even at full breath | re-calibrate closer to the mic; lower the `hard` value |
| Numbers look wrong | delete `model/profile.json` to fall back to defaults, then re-calibrate |
