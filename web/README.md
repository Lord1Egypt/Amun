<div align="center">

<img src="https://raw.githubusercontent.com/Lord1Egypt/Amun/main/assets/hero.png" alt="Amun — a Breath–Computer Interface" width="100%" />

# 𓅃 Amun — a Breath–Computer Interface (JavaScript edition)

**Same acronym. No electrodes. Just air.**

Pilot the falcon of Horus across the Egyptian sky using nothing but your breath —
right in your browser. Soft breath glides · a hard exhale climbs · silence dives.

<img src="https://raw.githubusercontent.com/Lord1Egypt/Amun/main/assets/demo.gif" alt="Amun gameplay" width="80%" />

</div>

---

A reimagining of [`CoffeeIsAllYouNeed/Invisible-Driver`](https://github.com/CoffeeIsAllYouNeed/Invisible-Driver):
the original was a **Brain**–Computer Interface (drive a car with EEG). Amun keeps
the acronym and changes the principle — **BCI = Breath–Computer Interface**, using
the microphone every device already has. This is the **JavaScript edition**: the
whole game (engine, breath pipeline, renderer) runs in the browser, so you need
**no Python and zero dependencies**.

## Run it

```bash
npx amun-bci          # serve + open the game in your browser
```

Or install it:

```bash
npm install -g amun-bci
amun                  # then open http://127.0.0.1:8011
```

Allow the microphone and **breathe**. No microphone? Press and hold **SPACE**.

```
amun --port 9000      # custom port
amun --no-open        # don't auto-open a browser
amun --selftest       # boot, self-check, exit 0 (for CI)
```

## How the breath becomes flight

- **Silence** → no thrust → gravity → the falcon **dives**.
- **Soft breath** → partial thrust → the falcon **glides** level.
- **Hard exhale** → full thrust → the falcon **climbs**.

A 3-step in-browser calibration learns your silence / soft / hard breath levels.
Nothing ever leaves your device.

## Zero dependencies

- The server is Node's standard library only (`http`, `fs`) — no Express, nothing.
- The game logic in `public/amun-core.js` is a faithful port of the Python engine
  and is unit-tested (`npm test` → `node test/core.test.js`, 10 tests).

## Also available

- **Python edition** (server-side pipeline + optional Arduino/NeuroSky hardware):
  `pip install amun-bci` · see the [main repo](https://github.com/Lord1Egypt/Amun).

## License

MIT © 2026 Mohamed Mounir ([Lord1Egypt](https://github.com/Lord1Egypt))
