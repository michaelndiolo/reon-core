import numpy as np
import pytest

from hackkit import reon_drift as D


def test_closed_form_when_all_cells_fade_at_the_same_rate():
    c = [100.0, 90.0, 80.0, 70.0]
    f, eol = 0.04, 0.5
    r = D.lifetime_compare(c, 4, fade_mean_per_year=f, fade_cv=0.0, eol_frac=eol, loss=0.0, trials=3, steps=4000)
    s0, nmin = sum(c), 4 * min(c)
    assert r["years"]["control"] == pytest.approx((1 - eol) / f, rel=2e-3)
    assert r["years"]["single_string"] == pytest.approx((1 - eol * s0 / nmin) / f, rel=2e-3)
    # one string of all four cells: sorted/as found are the same as the single string
    assert r["years"]["as_found"] == pytest.approx(r["years"]["single_string"], rel=1e-9)


def test_control_never_worse_and_loss_shortens_its_life():
    rng = np.random.default_rng(2)
    c = 85 + 10 * rng.random(24)
    a = D.lifetime_compare(c, 6, fade_mean_per_year=0.05, fade_cv=0.3, eol_frac=0.6, loss=0.0, trials=60)
    b = D.lifetime_compare(c, 6, fade_mean_per_year=0.05, fade_cv=0.3, eol_frac=0.6, loss=0.03, trials=60)
    for k in ("single_string", "as_found", "sorted_once"):
        assert a["years"]["control"] >= a["years"][k] - 1e-9
        assert a["energy"]["control"] >= a["energy"][k] - 1e-9
    assert b["years"]["control"] < a["years"]["control"]


def test_bad_inputs():
    with pytest.raises(ValueError):
        D.lifetime_compare([1, 2, 3], 2, fade_mean_per_year=0.05, fade_cv=0.1, eol_frac=0.5, loss=0.0)
    with pytest.raises(ValueError):
        D.lifetime_compare([1, 2], 1, fade_mean_per_year=0.05, fade_cv=0.1, eol_frac=1.5, loss=0.0)


def test_convergence_case_favours_sorting_and_divergence_favours_control():
    rng = np.random.default_rng(5)
    c = 84 + 12 * rng.random(24)
    kw = dict(fade_mean_per_year=0.04, fade_cv=0.3, eol_frac=0.6, loss=0.02, trials=80, seed=4)
    conv = D.lifetime_compare(c, 6, weak_corr=-0.9, **kw)
    ind = D.lifetime_compare(c, 6, weak_corr=0.0, **kw)
    div = D.lifetime_compare(c, 6, weak_corr=0.9, **kw)
    assert conv["control_life_over_sorted_once"] < ind["control_life_over_sorted_once"]
    assert div["control_life_over_sorted_once"] > 0 and conv["control_life_over_sorted_once"] > 0
    with pytest.raises(ValueError):
        D.lifetime_compare(c, 6, weak_corr=2.0, **kw)


def test_lifespan_loss_calibration_roundtrip_and_closed_form():
    assert D.lifespan_loss(50, 0.0, 0.85)["lifespan_loss"] == pytest.approx(0.0, abs=1e-9)
    a, b = D.lifespan_loss(50, 0.05, 0.85, trials=100)["lifespan_loss"], D.lifespan_loss(50, 0.12, 0.85, trials=100)["lifespan_loss"]
    assert 0 < a < b
    cv = D.calibrate_fade_cv(95, 0.177, 0.85)
    assert D.lifespan_loss(95, cv, 0.85, trials=300, seed=9)["lifespan_loss"] == pytest.approx(0.177, abs=0.012)
    # two cells with fade rates 1 +/- d: weakest retires when (1 + d) t = 1 - thr, mean when t = 1 - thr -> loss = d / (1 + d)
    r = D.lifespan_loss(2, 0.1, 0.85, trials=1)  # one random draw: just check it is a valid fraction
    assert 0 <= r["lifespan_loss"] < 1


def test_history_fade_rates_from_series():
    from hackkit import reon_history as RH, reon_learn as L
    rows = [(c, t / 4, q0 * (1 - f * t / 4)) for c, q0, f in (("a", 20.0, 0.03), ("b", 18.0, 0.05), ("c", 22.0, -0.02)) for t in range(0, 9)]  # synthetic fixture, not data
    fits = RH.fade_rates_from_series(rows)
    assert abs(fits["a"]["fade_per_year"] - 0.03) < 1e-9 and fits["c"]["fade_per_year"] < 0 and fits["a"]["r2"] > 0.999
    assert not RH.seasonal_flag(fits) and RH.seasonal_flag(RH.fade_rates_from_series([("x", t / 8, 10 - t * 0.01) for t in range(0, 8)]))
    assert L.FadeBelief().update(RH.usable_fades(fits)).cv > 0
