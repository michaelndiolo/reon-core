"""The reference pack model against the spec's hand-worked table, plus properties any correct implementation must have."""
import numpy as np
import pytest

import pack_ref as P

TABLE = {   # case: (usable_conv, usable_ctrl, util_conv, util_ctrl, gain), worked by hand in SPEC.md
    "A": (280.0, 340.0, 280 / 340, 1.0, 340 / 280 - 1),
    "B": (280.0, 329.8, 280 / 340, 0.97, 329.8 / 280 - 1),
    "C": (252.0, 306.0, 252 / 340, 0.9, 340 / 280 - 1),
    "D": (400.0, 400.0, 1.0, 1.0, 0.0),
    "E": (100.0, 100.0, 1.0, 1.0, 0.0),
    "F": (200.0, 350.0, 200 / 350, 1.0, 0.75),
    "G": (139.36, 165.34, 139.36 / 165.34, 1.0, 165.34 / 139.36 - 1),
}


@pytest.mark.parametrize("case", sorted(TABLE))
def test_spec_table(case):
    caps, eta, r = P.SPEC_CASES[case]
    got = P.usable(caps, eta, r)
    exp = TABLE[case]
    for key, want in zip(("usable_conv_ah", "usable_ctrl_ah", "util_conv", "util_ctrl", "gain"), exp):
        assert got[key] == pytest.approx(want, rel=1e-9, abs=1e-12), (case, key)


def test_energy_case_a():
    got = P.usable([100, 90, 80, 70], 1.0, 0.0, volts=3.7)
    assert got["usable_conv_kwh"] == pytest.approx(1.036) and got["usable_ctrl_kwh"] == pytest.approx(1.258)


def test_errors():
    for bad in ([], [100, 0], [100, -5], [100, float("nan")], [100, float("inf")]):
        with pytest.raises(ValueError):
            P.usable(bad)
    with pytest.raises(ValueError):
        P.usable([100], eta=0.0)
    with pytest.raises(ValueError):
        P.usable([100], eta=1.01)
    with pytest.raises(ValueError):
        P.usable([100], r=1.0)
    with pytest.raises(ValueError):
        P.usable([100], r=-0.1)


def test_properties_order_scale_and_ordering():
    rng = np.random.default_rng(1)
    for _ in range(50):
        c = rng.uniform(40, 110, int(rng.integers(1, 16)))
        eta, r = float(rng.uniform(0.8, 1)), float(rng.uniform(0, 0.3))
        a = P.usable(c, eta, r)
        assert P.usable(rng.permutation(c), eta, r)["usable_conv_ah"] == pytest.approx(a["usable_conv_ah"])      # order does not matter
        s = P.usable(c * 2.5, eta, r)
        assert s["usable_conv_ah"] == pytest.approx(2.5 * a["usable_conv_ah"])                                  # scales with the cells
        assert s["util_conv"] == pytest.approx(a["util_conv"]) and s["gain"] == pytest.approx(a["gain"])        # ratios do not
        assert a["util_conv"] <= 1.0 + 1e-12                                                                    # cannot use more than the pack holds
        if eta == 1.0:
            assert a["usable_ctrl_ah"] >= a["usable_conv_ah"] - 1e-9                                            # ideal control never loses capacity


def test_compare_detects_a_wrong_candidate():
    assert P.compare(lambda c, e, r: P.usable(c, e, r), n_random=20) == 0
    wrong = lambda c, e, r: {"usable_conv_ah": float(np.mean(c)) * len(c) * (1 - r), "usable_ctrl_ah": float(np.sum(c)) * e * (1 - r)}   # mean instead of min
    assert P.compare(wrong, n_random=20) > 0
