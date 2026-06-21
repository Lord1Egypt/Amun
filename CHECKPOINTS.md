# Amun — Build Checkpoints

A living log of what's done and what's next, so work can resume at any moment.

> Concept locked: reimagining `CoffeeIsAllYouNeed/Invisible-Driver`.
> **Brain**–Computer Interface → **Breath**–Computer Interface (same acronym, new
> principle). Drive-a-car → fly-a-falcon. EEG + Arduino → the microphone every
> device already has. Theme: **Amun**, god of air & the hidden/invisible.

## Phase 0 — Concept & plan ✅
- [x] Studied the original repo (EEG + Arduino + clustering + web UI).
- [x] Chose direction: **Amun**, breath via mic, falcon over Egypt, lean + optional deps.
- [x] Wrote the plan.

## Phase 1 — Scaffold & safety ✅
- [x] Repo structure, `.gitignore`, `LICENSE` (MIT), `pyproject.toml`, `requirements.txt`.
- [x] First commit + GitHub repo + push (work secured).

## Phase 2 — Core engine + signal pipeline ✅
- [x] `engine.py` — deterministic falcon-flight physics (gravity vs breath thrust).
- [x] `features.py` — RMS + zero-crossing (breath vs hum), pure stdlib.
- [x] `preprocessing.py` — EMA envelope + calibrated normalisation.
- [x] `classify.py` — k-means(3) calibration + honest silhouette; pure-stdlib live path.
- [x] `ingestion.py` — sim / replay / mic (optional sounddevice) sources.
- [x] `calibrate.py` — non-blocking calibration + JSON profile.
- [x] Smoke test: engine plays, silhouette ≈ 0.90 on synthetic data.

## Phase 3 — Server + web UI ✅
- [x] `server.py` — stdlib HTTP + hand-rolled RFC 6455 WebSocket (zero deps).
- [x] `templates/index.html` — Egyptian-cyberpunk canvas, Web Audio mic, calibration, SPACE fallback.
- [x] `__main__.py` — non-blocking CLI (serve / sim / replay / mic / calibrate).

## Phase 4 — Tests, sample data, notebook ⏳
- [ ] `tools/make_sample_data.py` + bundled `data/` breath dataset.
- [ ] `tests/` — engine, features, classify, websocket, server.
- [ ] `notebooks/breath_eda.ipynb` — honest silhouette on bundled data.
- [ ] `tools/test_all.py` — full suite, asserts exit 0.

## Phase 5 — Images, demo, docs, README ⏳
- [ ] `tools/gen_assets.py` — Gemini Nano Banana Pro 2 art + bottom-right watermark crop.
- [ ] `tools/make_demo.py` — reproducible gameplay GIF (PIL).
- [ ] `docs/` — ARCHITECTURE, SIGNAL_PIPELINE, CALIBRATION, HARDWARE.
- [ ] `README.md` — hero + demo + quickstart + honest metrics.
- [ ] `hardware/` — optional real wind/pressure breath-sensor notes.

## Phase 6 — Verify & ship ⏳
- [ ] `pytest` + `tools/test_all.py` green (exit 0).
- [ ] Headless run + `curl /health` + WS handshake confirmed.
- [ ] PR `feat/breath-computer-interface` → merge.
