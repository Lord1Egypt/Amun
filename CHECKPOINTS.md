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

## Phase 5 — Optional hardware ✅
- [x] `thinkgear.py` — NeuroSky ThinkGear parser (pure stdlib, tested).
- [x] `SerialSource` (Amun Amulet) + `NeuroSkySource` (EEG attention) with mic fallback.
- [x] `hardware/amun_amulet.ino` — ESP32/Arduino sketch (sensor + OLED + RGB + buzzer + BT).
- [x] `docs/HARDWARE.md` — BOM (your parts), wiring, both paths, flashing.

## Phase 6 — Images, demo, docs, README ✅
- [x] `tools/gen_assets.py` — Gemini Nano Banana Pro generator + bottom-right watermark crop.
      ⚠ Gemini image quota exhausted (HTTP 429 — needs billing at ai.dev); kept for later.
- [x] `tools/_artkit.py` + `tools/make_banner.py` — **offline** hero + logo (no quota, on-brand).
- [x] `tools/make_demo.py` — reproducible gameplay GIF from the real engine (PIL).
- [x] `docs/` — ARCHITECTURE, SIGNAL_PIPELINE, CALIBRATION, HARDWARE.
- [x] `README.md` — hero + demo + quickstart + hardware tiers + honest metrics.

## Phase 7 — Verify & ship ⏳
- [x] `pytest` + `tools/test_all.py` green (exit 0) — 45 tests.
- [ ] Headless run + `/health` + WS handshake re-confirmed on a clean checkout.
- [ ] PR `feat/breath-computer-interface` → merge.
