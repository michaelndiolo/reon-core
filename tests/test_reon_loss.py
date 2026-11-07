"""reon_loss: hand-worked cases, plus agreement with the independent reference pack model."""
import numpy as np
import pytest

from hackkit import reon_loss as L
from recheck import pack_ref

CAPS = [100, 90, 80, 70]


def test_hand_case():
    assert L.break_even_eta(CAPS) == pytest.approx(280 / 340)            # 0.823529...
    assert L.break_even_loss(CAPS) == pytest.approx(60 / 340)
    assert L.net_gain(CAPS, 1.0) == pytest.approx(340 / 280 - 1)         # 21.43 %
    assert L.net_gain(CAPS, 280 / 340) == pytest.approx(0.0, abs=1e-12)  # the tie
    assert L.net_gain(CAPS, 0.97) == pytest.approx(340 * 0.97 / 280 - 1)


def test_equal_cells_have_no_headroom():
    assert L.break_even_eta([100, 100, 100]) == pytest.approx(1.0)
    assert L.net_gain([100, 100, 100], 0.98) == pytest.approx(-0.02)    # any loss makes control worse
    assert L.break_even_eta([100]) == 1.0


def test_matches_reference_model():
    rng = np.random.default_rng(3)
    for _ in range(100):
        caps = list(rng.uniform(40, 110, int(rng.integers(1, 17))))
        eta = float(rng.uniform(0.8, 1.0))
        r = float(rng.uniform(0, 0.3))
        assert L.net_gain(caps, eta) == pytest.approx(pack_ref.usable(caps, eta, r)["gain"], abs=1e-9)   # reserve cancels
        assert L.net_gain(caps, L.break_even_eta(caps)) == pytest.approx(0.0, abs=1e-9)


def test_table_and_errors():
    t = L.loss_table(CAPS, [0.0, 0.02, 0.05])
    assert t["net_gain"][0.0] == pytest.approx(t["gain_at_no_loss"])
    assert t["net_gain"][0.05] == pytest.approx(340 * 0.95 / 280 - 1)
    for bad in (0.0, 1.5, -0.1):
        with pytest.raises(ValueError):
            L.net_gain(CAPS, bad)
    with pytest.raises(ValueError):
        L.loss_table(CAPS, [1.0])
    with pytest.raises(ValueError):
        L.break_even_eta([100, -1])
    with pytest.raises(ValueError):
        L.break_even_eta([])
