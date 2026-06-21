"""Feature extraction: RMS, zero-crossing, breath/silence/tone discrimination."""

import math
import random

from amun.features import rms, zero_crossing_rate, is_breath, frame_features


def test_rms_of_silence_is_zero():
    assert rms([0.0] * 100) == 0.0
    assert rms([]) == 0.0


def test_rms_of_constant():
    assert abs(rms([0.5] * 50) - 0.5) < 1e-9


def test_rms_of_sine_is_amplitude_over_sqrt2():
    n = 2000
    sig = [math.sin(2 * math.pi * 5 * i / n) for i in range(n)]
    assert abs(rms(sig) - (1 / math.sqrt(2))) < 0.02


def test_zcr_silence_and_alternating():
    assert zero_crossing_rate([0.1] * 10) == 0.0
    alt = [1.0 if i % 2 == 0 else -1.0 for i in range(10)]
    assert zero_crossing_rate(alt) == 1.0


def test_breath_is_loud_and_noisy():
    rng = random.Random(0)
    breath = [rng.uniform(-0.2, 0.2) for _ in range(512)]   # broadband noise
    assert is_breath(rms(breath), zero_crossing_rate(breath))


def test_quiet_is_not_breath():
    quiet = [0.001] * 512
    assert not is_breath(rms(quiet), zero_crossing_rate(quiet))


def test_pure_tone_is_not_breath():
    # a low-frequency hum is loud but tonal (low ZCR) -> rejected
    n = 512
    tone = [0.3 * math.sin(2 * math.pi * 3 * i / n) for i in range(n)]
    assert not is_breath(rms(tone), zero_crossing_rate(tone))


def test_frame_features_keys():
    f = frame_features([0.1, -0.1, 0.2, -0.2] * 50)
    assert set(f) == {"rms", "zcr", "is_breath"}
