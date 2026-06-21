/*
 * Amun core — engine + breath pipeline, a faithful port of src/amun/engine.py,
 * preprocessing.py and classify.py. UMD: usable both in the browser (window.AmunCore)
 * and in Node (require) so it can be unit-tested without a browser.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.AmunCore = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // world constants (mirror engine.py)
  const W = 100, H = 100, FALCON_X = 28, FALCON_R = 3.2;
  const GRAVITY = 46, THRUST_MAX = 95, VY_MIN = -40, VY_MAX = 46;
  const SCROLL = 26, SPACING = 46, GAP_MIN = 13, GAP_MAX = 18, MARGIN = 12;

  const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);

  class Engine {
    constructor(rng) {
      this.rng = rng || Math.random; // injectable for deterministic tests
      this.reset();
    }
    _rand(a, b) { return a + this.rng() * (b - a); }
    reset() {
      this.y = H * 0.5; this.vy = 0; this.breath = 0; this.obs = [];
      this.dist = 0; this.ankhs = 0; this.alive = true; this.started = false;
      this.wing = 0; this._next = W + 10;
      for (let i = 0; i < 3; i++) this.spawn();
    }
    spawn() {
      const half = this._rand(GAP_MIN, GAP_MAX);
      const center = this._rand(MARGIN + half, H - MARGIN - half);
      this.obs.push({ x: this._next, c: center, h: half,
        ankh: this.rng() < 0.55, passed: false, taken: false });
      this._next += SPACING;
    }
    setBreath(v) { this.breath = clamp(isNaN(v) ? 0 : v, 0, 1); }
    get score() { return Math.floor(this.dist) + this.ankhs * 25; }
    update(dt) {
      if (!this.alive) return;
      if (!this.started) {
        if (this.breath > 0.08) this.started = true;
        else { this.wing += dt * 6; return; }
      }
      const accel = this.breath * THRUST_MAX - GRAVITY;
      this.vy = clamp(this.vy + accel * dt, VY_MIN, VY_MAX);
      this.y += this.vy * dt;
      this.wing += dt * (6 + 10 * this.breath);
      if (this.y <= FALCON_R) { this.y = FALCON_R; this.alive = false; return; }
      if (this.y >= H - FALCON_R) { this.y = H - FALCON_R; this.vy = Math.min(this.vy, 0); }
      const step = SCROLL * dt; this.dist += step;
      for (const o of this.obs) o.x -= step;
      this._next -= step;
      while (this._next < W + SPACING) this.spawn();
      this.obs = this.obs.filter((o) => o.x > -8);
      for (const o of this.obs) {
        if (!o.passed && o.x < FALCON_X) o.passed = true;
        if (Math.abs(o.x - FALCON_X) <= FALCON_R + 2.5) {
          const inGap = o.c - o.h + FALCON_R <= this.y && this.y <= o.c + o.h - FALCON_R;
          if (!inGap) { this.alive = false; return; }
          if (o.ankh && !o.taken && Math.abs(this.y - o.c) <= FALCON_R + 2) {
            o.taken = true; this.ankhs++;
          }
        }
      }
    }
  }

  class Pipeline {
    constructor() {
      this.profile = { noise: 0.01, soft: 0.06, hard: 0.18 };
      this.env = 0; this.alpha = 0.35;
    }
    smooth(x) {
      this.env = this.alpha * (isNaN(x) ? 0 : x) + (1 - this.alpha) * this.env;
      return this.env;
    }
    lift(raw) {
      const span = this.profile.hard - this.profile.noise;
      if (span <= 1e-9) return 0;
      return clamp((raw - this.profile.noise) / span, 0, 1);
    }
    reset() { this.env = 0; }
    calibrate(noiseArr, softArr, hardArr) {
      const mean = (a) => (a && a.length ? a.reduce((x, y) => x + y, 0) / a.length : 0);
      const n = mean(noiseArr), s = mean(softArr), h = mean(hardArr);
      this.profile.noise = n;
      this.profile.soft = Math.max(s, n + 1e-4);
      this.profile.hard = Math.max(h, this.profile.soft + 1e-4);
      return this.profile;
    }
  }

  return { Engine, Pipeline, constants: { W, H, FALCON_X, FALCON_R, GRAVITY, THRUST_MAX } };
});
