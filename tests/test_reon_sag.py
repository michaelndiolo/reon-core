import numpy as np
import pytest

from hackkit import reon_sag as S
from hackkit.reon_window import window_usable

RNG = np.random.default_rng(0)
CAPS = np.clip(1.0 - 0.08 + 0.04 * RNG.standard_normal(250), 0.5, 1.2)


@pytest.mark.parametrize("k", [0, 1, 10, 25, 249])
def test_no_sag_no_floor_reproduces_cell_count_rule(k):
    f, d = S.usable_fraction(CAPS, k, v_floor_frac=0.0, r_cell_ohm=0.0, details=True)
    assert d["ah_equiv"][0] == pytest.approx(window_usable(CAPS, 250 - k), rel=1e-9)
    assert d["stop_by"][0] == "rule" and d["bypassed"][0] == k


def test_floor_zero_no_resistance_means_all_energy_usable():
    assert S.usable_fraction(CAPS, None, v_floor_frac=0.0, r_cell_ohm=0.0) == pytest.approx(1.0, abs=1e-12)
    assert S.usable_fraction(np.ones(250), 0, v_floor_frac=0.0, r_cell_ohm=0.0) == pytest.approx(1.0, abs=1e-12)


def test_plain_string_of_unequal_cells_matches_closed_form():
    # k = 0, no floor, no R: every cell passes min(caps) of charge
    f = S.usable_fraction(CAPS, 0, v_floor_frac=0.0, r_cell_ohm=0.0)
    xs, ys, F = S._curve("sodium-ion")
    q = CAPS.min()
    e = (CAPS * (F[-1] - S._F(xs, ys, F, 1 - q / CAPS))).sum()
    assert f == pytest.approx(e / (CAPS.sum() * F[-1]), rel=1e-9)


@pytest.mark.parametrize("bypass,floor", [(None, 0.0), (25, 0.0), (None, 0.7), (25, 0.85), (0, 0.6)])
def test_higher_resistance_strictly_lowers_usable_energy(bypass, floor):
    fr = [S.usable_fraction(CAPS, bypass, v_floor_frac=floor, r_cell_ohm=r) for r in (0.0, 0.6e-3, 3e-3, 20e-3)]
    assert all(a > b for a, b in zip(fr, fr[1:]))


def test_higher_floor_never_raises_usable_energy():
    fr = [S.usable_fraction(CAPS, None, v_floor_frac=f) for f in (0.0, 0.5, 0.7, 0.8, 0.9)]
    assert all(a >= b for a, b in zip(fr, fr[1:]))


def test_floor_binds_before_cell_count_on_sloped_sodium_curve():
    f_count, d = S.usable_fraction(CAPS, 25, v_floor_frac=0.0, details=True)
    f_sag, d2 = S.usable_fraction(CAPS, 25, v_floor_frac=0.9, details=True)
    assert f_sag < f_count and d2["stop_by"][0] == "floor"


def test_batch_shapes():
    caps = np.clip(0.9 + 0.05 * RNG.standard_normal((7, 250)), 0.5, 1.2)
    f = S.usable_fraction(caps, 25)
    assert f.shape == (7,)
    assert f[3] == pytest.approx(S.usable_fraction(caps[3], 25))
    fk = S.usable_fraction(caps, np.arange(7))
    assert fk.shape == (7,)
    mask = np.zeros((7, 250), bool); mask[:, :5] = True
    assert S.usable_fraction(caps, mask).shape == (7,)
    r = np.full(250, 1e-3)
    assert S.usable_fraction(caps, None, r_cell_ohm=r).shape == (7,)
    assert S.max_bypass(caps, S.soc_after(caps, np.full(7, 0.3))).shape == (7,)


def test_max_bypass_matches_reon_voltage_rule_of_thumb_without_sag():
    from hackkit.reon_voltage import bypass_room, ocv
    # reon_voltage normalises to ocv(0.5) = 3.65 V; pass that nominal for a like-for-like check
    for soc in (1.0, 0.5, 0.2):
        k = S.max_bypass(np.ones(16), soc, v_floor_frac=0.8, r_cell_ohm=0.0, v_nom_cell=float(ocv("sodium-ion", 0.5)))
        assert k == bypass_room(16, soc, "sodium-ion", 0.8)


def test_max_bypass_shrinks_with_soc_and_resistance():
    ks = [S.max_bypass(np.ones(250), s) for s in (1.0, 0.8, 0.5, 0.3)]
    assert ks == sorted(ks, reverse=True)
    assert S.max_bypass(np.ones(250), 0.8, r_cell_ohm=20e-3) <= S.max_bypass(np.ones(250), 0.8, r_cell_ohm=0.0)
    assert S.max_bypass(np.ones(250), 0.0) == -1


def test_bad_inputs():
    with pytest.raises(ValueError):
        S.usable_fraction([1.0, -1.0])
    with pytest.raises(ValueError):
        S.usable_fraction(CAPS, curve="unobtainium")
