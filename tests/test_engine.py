"""Engine physics, scoring, collisions and determinism."""

from amun.engine import GameEngine, FALCON_X


def run(engine, breath, ticks, dt=1 / 60):
    for _ in range(ticks):
        engine.set_breath(breath)
        engine.update(dt)


def test_breath_clamped():
    e = GameEngine(seed=1)
    e.set_breath(5.0)
    assert e.breath == 1.0
    e.set_breath(-3.0)
    assert e.breath == 0.0
    e.set_breath(float("nan"))
    assert e.breath == 0.0


def test_does_not_start_without_breath():
    e = GameEngine(seed=1)
    y0 = e.falcon_y
    run(e, 0.0, 120)
    assert not e.started
    assert e.falcon_y == y0  # hovers until you breathe


def test_gravity_pulls_down_then_crashes():
    e = GameEngine(seed=1)
    e.set_breath(0.5)
    e.update(1 / 60)        # launch
    run(e, 0.0, 600)        # then go silent
    assert not e.alive      # silence -> dive -> ground


def test_hard_breath_climbs():
    e = GameEngine(seed=1)
    start = e.falcon_y
    run(e, 1.0, 20)
    assert e.falcon_y > start
    assert e.vy > 0


def test_ceiling_is_capped():
    e = GameEngine(seed=2)
    run(e, 1.0, 600)
    assert e.falcon_y <= e.height


def test_score_increases_while_flying():
    e = GameEngine(seed=3)
    # feed a balanced breath that roughly holds altitude
    for i in range(300):
        e.set_breath(0.55)
        e.update(1 / 60)
        if not e.alive:
            break
    assert e.score >= 0
    assert e.distance > 0


def test_determinism_same_seed_same_obstacles():
    a, b = GameEngine(seed=42), GameEngine(seed=42)
    for _ in range(120):
        for e in (a, b):
            e.set_breath(0.6)
            e.update(1 / 60)
    sa = a.state()["obstacles"]
    sb = b.state()["obstacles"]
    assert sa == sb


def test_state_is_json_serialisable():
    import json

    e = GameEngine(seed=5)
    run(e, 0.7, 60)
    json.dumps(e.state())  # must not raise


def test_reset_restores_initial_altitude():
    e = GameEngine(seed=5)
    run(e, 1.0, 60)
    e.reset()
    assert e.falcon_y == e.height * 0.5
    assert e.alive and not e.started and e.score == 0
