import numpy as np, pytest
from hackkit import reon_guard as G, reon_storm as S, reon_voltage as V, reon_events as E, reon_response as R

KW = dict(value_per_kwh_year=60, electronics_per_kwh=15, fade_cv=0.45)

def test_bad_caps_rejected():
    for bad in ([], [np.nan, 1], [-1, 2], [[1, 2]]):
        with pytest.raises(ValueError):
            S.hours(bad, 60, 5, True)
    with pytest.raises(ValueError):
        V.run([], "sodium", "plain", 0.5)

def test_events_args_rejected():
    with pytest.raises(ValueError):
        E.simulate("nope", 1)
    with pytest.raises(ValueError):
        E.simulate("ours", 1, nameplate=0)

def test_decide_empty_and_nan():
    with pytest.raises(ValueError):
        R.decide([], R.Context())
    c = R.Cell(i=0, v=float("nan"), t=25, soc=.5, cap_rel=1, r_rel=1, dT_dt=0)
    a = R.decide([c], R.Context())
    assert a[0].kind == R.REDUCE_POWER

def test_safe_recommend_validates():
    s = np.full(16, 100.0)
    with pytest.raises(ValueError):
        G.safe_recommend(s, 5, **KW)
    with pytest.raises(ValueError):
        G.safe_recommend(np.r_[s[:-1], np.nan], 16, **KW)
    with pytest.raises(ValueError):
        G.safe_recommend(s, 16, **{**KW, "fade_cv": 5})

def test_robust_recommend_identical_cells_not_buy():
    r = G.robust_recommend(np.full(16, 100.0), 16, trials=6, steps=24, **KW)
    assert r["verdict"] in ("PLAIN", "HOLD", "BUY") and np.isfinite(r["mean_gain"])

def test_rank_cells_weak_first():
    from hackkit.reon_rank import rank_cells
    c = np.array([100.0] * 14 + [70.0, 98.0])
    r = rank_cells(c, 60, 40)
    assert r[0]["cell"] == 14 and r[0]["dollars_per_year"] > 0 and r[0]["response"] == R.BYPASS
    assert all(np.isfinite(x["dollars_per_year"]) for x in r)
    with pytest.raises(ValueError):
        rank_cells([100, 100], 60, 40)
