import pytest
from hackkit import reon_enviro as EN


def test_longer_life_avoids_cells_and_carbon():
    e = EN.environmental(60.0, 10.0, 24.0, 20.0)
    assert e["kwh_cells_avoided"] == pytest.approx(60 * 20 * (1 / 10 - 1 / 24))
    assert e["net_t"] > 0 and e["low_t"] <= e["net_t"] <= e["high_t"]
    # hand check: avoided = kwh x 0.8 x 68.9 / 1000 ; control = 4 x 60 / 1000
    assert e["avoided_t_base"] == pytest.approx(e["kwh_cells_avoided"] * 0.8 * 68.9 / 1000)
    assert e["control_t_base"] == pytest.approx(0.24)


def test_no_gain_when_life_not_longer():
    assert EN.cells_not_replaced(60.0, 10.0, 10.0, 20.0) == 0.0
    assert EN.cells_not_replaced(60.0, 10.0, 8.0, 20.0) == 0.0


def test_sign_flags():
    assert not EN.environmental(60.0, 10.0, 24.0, 20.0)["sign_can_flip"]
    assert EN.environmental(60.0, 10.0, 10.5, 20.0)["sign_can_flip"]   # tiny life gain: electronics carbon can exceed it


def test_bad_inputs_rejected():
    with pytest.raises(ValueError):
        EN.cells_not_replaced(0.0, 10.0, 24.0, 20.0)
    with pytest.raises(ValueError):
        EN.cells_not_replaced(60.0, 0.0, 24.0, 20.0)
