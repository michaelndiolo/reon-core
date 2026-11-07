import numpy as np
import pytest
from hackkit import reon_secondlife as SL


def test_options_order_nested_groups():
    rng = np.random.default_rng(0)
    c = 0.9 * np.exp(0.05 * rng.standard_normal(24))
    o = SL.options(c, groups=(12, 6, 3), window=1.0)
    assert o["module of 12"] == pytest.approx(o["plain"]) and o["module of 6"] == pytest.approx(o["plain"]) and o["cell level"] == pytest.approx(o["plain"])   # window 1.0: nothing may leave
    o = SL.options(c, groups=(12, 6, 3), window=0.5)
    for k in ("module of 12", "module of 6", "module of 3", "cell level"):
        assert o["plain"] - 1e-12 <= o[k] <= o["upper bound"] + 1e-12
    assert o["cell level"] >= o["module of 12"] - 1e-12


def test_cell_level_window_between_plain_and_sum():
    c = np.array([1.0, 0.9, 0.95, 0.7, 1.0, 0.98, 0.92, 0.97, 0.99, 0.96])
    o = SL.options(c, groups=(5,), window=0.8)
    assert o["plain"] < o["cell level"] <= o["upper bound"]


def test_flip_point_matches_formula():
    packs = {"a": np.array([1.0, 1.0, 1.0, 0.8]), "b": np.array([1.0, 1.0, 1.0, 0.8])}
    t = SL.table(packs, groups=(2,), window=0.5, loss=0.0, value=40.0, years=8.0)
    plain = 4 * 0.8
    share = (3.8 - plain) / 3.8                                   # ideal sum, window 0.5 lets one cell leave
    assert t["cell level"]["flip_cost_median"] == pytest.approx(40.0 * 8.0 * ((SL.options(packs["a"], (2,), 0.5)["cell level"]) - plain) / 3.8)
    assert t["cell level"]["extra_share_median"] > 0 and share > 0


def test_loss_lowers_flip_point_and_bad_inputs():
    c = {"a": np.array([1.0, 0.9, 0.8, 0.95])}
    a = SL.table(c, groups=(2,), window=0.5, loss=0.0)["cell level"]["flip_cost_median"]
    b = SL.table(c, groups=(2,), window=0.5, loss=0.1)["cell level"]["flip_cost_median"]
    assert b < a
    with pytest.raises(Exception):
        SL.options([1.0, -1.0, 1.0, 1.0])
    with pytest.raises(Exception):
        SL.options([1.0, 1.0, 1.0], groups=(2,))
