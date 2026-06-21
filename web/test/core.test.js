/*
 * Tests for the JS core (engine + pipeline). Plain Node assertions, no deps.
 *   node web/test/core.test.js
 */
"use strict";
const assert = require("assert");
const { Engine, Pipeline } = require("../public/amun-core.js");

let passed = 0;
function test(name, fn) { fn(); passed++; console.log("  ✓ " + name); }

// deterministic RNG for reproducible tests
function seeded(seed) {
  let s = seed >>> 0;
  return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
}

test("breath is clamped to [0,1]", () => {
  const e = new Engine(seeded(1));
  e.setBreath(5); assert.strictEqual(e.breath, 1);
  e.setBreath(-3); assert.strictEqual(e.breath, 0);
  e.setBreath(NaN); assert.strictEqual(e.breath, 0);
});

test("hovers until you breathe", () => {
  const e = new Engine(seeded(1));
  const y0 = e.y;
  for (let i = 0; i < 120; i++) { e.setBreath(0); e.update(1 / 60); }
  assert.strictEqual(e.started, false);
  assert.strictEqual(e.y, y0);
});

test("silence after launch -> dive -> crash", () => {
  const e = new Engine(seeded(2));
  e.setBreath(0.5); e.update(1 / 60);
  for (let i = 0; i < 600; i++) { e.setBreath(0); e.update(1 / 60); }
  assert.strictEqual(e.alive, false);
});

test("hard breath climbs", () => {
  const e = new Engine(seeded(3));
  const y0 = e.y;
  for (let i = 0; i < 20; i++) { e.setBreath(1); e.update(1 / 60); }
  assert.ok(e.y > y0 && e.vy > 0);
});

test("ceiling is capped", () => {
  const e = new Engine(seeded(4));
  for (let i = 0; i < 600; i++) { e.setBreath(1); e.update(1 / 60); }
  assert.ok(e.y <= 100);
});

test("determinism: same seed -> same obstacles", () => {
  const a = new Engine(seeded(42)), b = new Engine(seeded(42));
  for (let i = 0; i < 120; i++) {
    a.setBreath(0.6); a.update(1 / 60);
    b.setBreath(0.6); b.update(1 / 60);
  }
  assert.deepStrictEqual(a.obs, b.obs);
});

test("score combines distance and ankhs", () => {
  const e = new Engine(seeded(5));
  e.dist = 100; e.ankhs = 2;
  assert.strictEqual(e.score, 100 + 50);
});

test("pipeline normalises lift to [0,1]", () => {
  const p = new Pipeline();
  assert.strictEqual(p.lift(-1), 0);
  assert.strictEqual(p.lift(99), 1);
  const v = p.lift(0.05); assert.ok(v >= 0 && v <= 1);
});

test("pipeline EMA smooths toward target", () => {
  const p = new Pipeline();
  let v = 0;
  for (let i = 0; i < 60; i++) v = p.smooth(1);
  assert.ok(v > 0.99);
  p.reset(); assert.strictEqual(p.env, 0);
});

test("calibrate orders anchors and is robust", () => {
  const p = new Pipeline();
  const pr = p.calibrate([0.01, 0.012], [0.06, 0.07], [0.18, 0.2]);
  assert.ok(pr.noise < pr.soft && pr.soft < pr.hard);
  // degenerate input must still order strictly
  const pr2 = p.calibrate([0.1], [0.1], [0.1]);
  assert.ok(pr2.noise < pr2.soft && pr2.soft < pr2.hard);
});

console.log(`\n  ${passed} tests passed`);
