"""Calibration fit + live classification."""

import random
from pathlib import Path

from amun.classify import (
    CalibrationProfile, BreathClassifier, fit_profile,
    SILENCE, GLIDE, CLIMB,
)
from amun.preprocessing import BreathEnvelope, normalize


def make_samples(seed=0):
    rng = random.Random(seed)
    sil = [max(0.0, rng.gauss(0.01, 0.004)) for _ in range(200)]
    soft = [max(0.0, rng.gauss(0.065, 0.01)) for _ in range(200)]
    hard = [max(0.0, rng.gauss(0.19, 0.02)) for _ in range(200)]
    return sil + soft + hard


def test_fit_orders_anchors():
    p = fit_profile(make_samples())
    assert p.noise_floor < p.soft < p.hard
    assert p.n_frames == 600


def test_fit_silhouette_is_high_for_separated_clusters():
    p = fit_profile(make_samples())
    # three well-separated clusters -> a strong silhouette (honest, measured)
    assert p.silhouette > 0.6


def test_fit_tiny_input_falls_back_safely():
    p = fit_profile([0.02, 0.03])
    assert isinstance(p, CalibrationProfile)
    assert p.noise_floor <= p.soft <= p.hard


def test_classifier_commands():
    p = CalibrationProfile(noise_floor=0.01, soft=0.06, hard=0.18)
    c = BreathClassifier(p)
    assert c.command(0.005) == SILENCE
    assert c.command(0.18) == CLIMB
    # something between soft and hard should glide or climb, never silence
    assert c.command(0.12) in (GLIDE, CLIMB)


def test_lift_is_bounded():
    c = BreathClassifier(CalibrationProfile())
    assert c.lift(-1.0) == 0.0
    assert c.lift(99.0) == 1.0
    assert 0.0 <= c.lift(0.05) <= 1.0


def test_normalize_degenerate_profile():
    assert normalize(0.5, 0.2, 0.2, 0.2) == 0.0  # zero span -> safe


def test_envelope_smooths_toward_target():
    env = BreathEnvelope(alpha=0.5)
    for _ in range(40):
        v = env.update(1.0)
    assert v > 0.99
    env.reset()
    assert env.value == 0.0


def test_profile_roundtrip(tmp_path: Path):
    p = fit_profile(make_samples())
    f = tmp_path / "profile.json"
    p.save(f)
    q = CalibrationProfile.load(f)
    assert q.noise_floor == p.noise_floor
    assert q.hard == p.hard
    assert q.silhouette == p.silhouette
