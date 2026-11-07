"""reon_window and reon_spread against hand-worked cases and a brute-force discharge simulation."""
import numpy as np
import pytest

from hackkit import reon_spread as S
from hackkit import reon_window as W

CAPS = [100, 90, 80, 70]


def test_window_by_hand():
    assert W.window_usable(CAPS, 4) == pytest.approx(280)        # conventional
    assert W.window_usable(CAPS, 3) == pytest.approx(310)        # 80 + 80 + 80 + 70
    assert W.window_usable(CAPS, 2) == pytest.approx(330)        # 90 + 90 + 80 + 70
    assert W.window_usable(CAPS, 1) == pytest.approx(340)        # ideal sum
    assert W.window_gain(CAPS, 3) == pytest.approx(310 / 280 - 1)
    rows = W.window_curve(CAPS)
    assert [r["n_min"] for r in rows] == [4, 3, 2, 1]
    assert [r["share_of_ideal_gain"] for r in rows] == pytest.approx([0, 0.5, 5 / 6, 1.0])
    assert W.narrowest_window_for_share(CAPS, 0.5)["n_min"] == 3
    assert W.narrowest_window_for_share(CAPS, 0.8)["n_min"] == 2
    assert W.narrowest_window_for_share(CAPS, 1.0)["n_min"] == 1


def test_equal_cells_and_errors():
    assert W.window_usable([100, 100, 100], 1) == pytest.approx(300)
    assert W.narrowest_window_for_share([100, 100, 100], 0.9)["n_min"] == 3
    for bad in (0, 5, 2.5):
        with pytest.raises(ValueError):
            W.window_usable(CAPS, bad)
    with pytest.raises(ValueError):
        W.narrowest_window_for_share(CAPS, 0.0)


def test_window_matches_discharge_simulation():
    rng = np.random.default_rng(5)
    for _ in range(25):
        caps = rng.uniform(40, 110, int(rng.integers(2, 12)))
        n_min = int(rng.integers(1, caps.size + 1))
        dq = 0.002                                                # Ah per step; a cell is in circuit while it still has charge
        q, used = 0.0, 0.0
        while True:
            active = int((caps > q + dq / 2).sum())
            if active < n_min:
                break
            used += active * dq
            q += dq
        assert used == pytest.approx(W.window_usable(caps, n_min), abs=0.5 + 0.002 * caps.size)


def test_fragility_by_hand():
    f = S.fragility(CAPS)
    assert f["gain"] == pytest.approx(340 / 280 - 1)             # 21.43 %
    assert f["gain_without_weakest"] == pytest.approx(90 / 80 - 1)   # 12.5 %
    assert f["share_lost"] == pytest.approx(1 - 0.125 / (340 / 280 - 1))
    assert S.fragility([100, 100, 100])["share_lost"] == 0.0
    with pytest.raises(ValueError):
        S.fragility([100])


def test_noise_bias_and_iid():
    zero = S.noise_bias(CAPS, 0.0)
    assert zero["apparent_mean"] == pytest.approx(zero["true_gain"])
    eq = S.noise_bias([100.0] * 12, 0.02)
    assert eq["true_gain"] == 0.0 and 0.02 < eq["apparent_mean"] < 0.045     # noise alone creates a "gain"
    ref = S.iid_gain(0.02, 12)
    assert ref["mean"] == pytest.approx(eq["apparent_mean"], rel=0.1)         # same distribution, two routes
    assert S.noise_bias(CAPS, 0.03)["bias"] > 0
    with pytest.raises(ValueError):
        S.noise_bias(CAPS, -0.1)
