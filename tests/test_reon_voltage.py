import numpy as np
from hackkit import reon_voltage as V

CAPS = np.array([1.0] * 15 + [0.8])


def test_ideal_beats_plain_and_floor_is_between():
    p, _ = V.run(CAPS, "LFP", "plain", 0.7)
    i, _ = V.run(CAPS, "LFP", "ideal", 0.7)
    f, _ = V.run(CAPS, "LFP", "floor", 0.7)
    assert p < f <= i


def test_higher_minimum_voltage_keeps_less_of_the_gain():
    gains = [V.run(CAPS, "NMC", "floor", f)[0] for f in (0.6, 0.7, 0.8)]
    assert gains[0] >= gains[1] >= gains[2]


def test_flat_curve_keeps_more_than_sloping_curve_at_same_floor():
    flat = V.run(CAPS, "LFP", "floor", 0.7)[0] / V.run(CAPS, "LFP", "plain", 0.7)[0]
    slope = V.run(CAPS, "sodium-ion", "floor", 0.7)[0] / V.run(CAPS, "sodium-ion", "plain", 0.7)[0]
    assert flat >= slope


def test_bypass_room_shrinks_as_cells_empty():
    r = [V.bypass_room(16, s, "sodium-ion", 0.8) for s in (1.0, 0.5, 0.2, 0.05)]
    assert r == sorted(r, reverse=True) and r[0] >= 3 and r[-1] == 0
