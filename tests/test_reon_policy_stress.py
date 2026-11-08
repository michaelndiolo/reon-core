import numpy as np
import pytest

from hackkit import reon_policy_stress as R, reon_wear as W

SC = R.scenario(1, 0.008, steps=20, n=50, m=50)   # small and fast; same physics


def _wear_scan(c0, seed, sc, **over):
    kw = dict(fade_mean=sc["fade_mean"], fade_cv=sc["fade_cv"], loss=sc["loss"], electronics_per_kwh=sc["elec"], balancer_per_kwh=sc["bal_cost"], sort_cost_per_kwh=0.0,
              value_per_kwh_year=sc["value"], rate=sc["rate"], years=sc["years"], eol_frac=sc["eol"], duty=sc["duty"], dod_exp=sc["dod_exp"], knee_share=sc["knee_share"],
              start_soh=sc["start_soh"], balancer_rs=(0.05,), balancer_eta=sc["bal_eta"], closed_loss=sc["closed_loss"], test_sigma=sc["test_sigma"], trials=1, seed=seed,
              steps=sc["steps"], window=sc["window"])
    kw.update(over)
    return W.wear_scan(c0, sc["m"], **kw)


def test_paired_draws_are_deterministic():
    a, b = R.draw(10_123, SC), R.draw(10_123, SC)
    for k in ("c0", "f", "meas", "is_knee", "soh_k", "obs_noise"):
        assert np.array_equal(a[k], b[k])
    assert not np.array_equal(R.draw(10_124, SC)["f"], a["f"])
    pols = R.baselines(SC, ks=(1, 5)) + R.candidates(SC)[:2]
    assert R.net_values(pols, a, SC) == R.net_values(pols, b, SC)


@pytest.mark.parametrize("seed", [10_500, 10_501])
def test_baselines_match_reon_wear_for_same_seed(seed):
    dr = R.draw(seed, SC)
    ks = (1, 5)
    v = R.net_values(R.baselines(SC, ks=ks), dr, SC)
    ref = _wear_scan(dr["c0"], seed, SC, select_counts=ks)
    ref.update(_wear_scan(dr["c0"], seed, SC, hybrid_counts=ks, hybrid_shares_wear=True))
    for name in ("plain", "balancer 5%", "late switches", "level switches", "selective 1/50 cells", "selective 5/50 cells", "hybrid 1/50 + balancer 5%", "hybrid 5/50 + balancer 5%"):
        assert v[name] == pytest.approx(ref[name]["mean"], abs=1e-9), name


def test_regret_definitions_are_nonnegative():
    vals = {p["name"]: np.random.default_rng(i).normal(i, 1.0, 30) for i, p in enumerate(R.baselines(SC, ks=(1,)))}
    base = R.baselines(SC, ks=(1,))
    for x in [np.zeros(30), np.full(30, 100.0), np.random.default_rng(9).normal(0, 5, 30)]:
        r = R.regret(x, vals, base)
        assert r["scenario"] >= 0.0 and r["oracle_mean"] >= 0.0
    best = max(vals, key=lambda k: vals[k].mean())
    assert R.regret(vals[best], vals, base)["scenario"] == 0.0


def test_policies_never_see_the_future_draw():
    # the in-sample choice depends only on the day-1 test (meas) and the prior: changing the draw's fade rates and true capacities must not change it
    dr = R.draw(10_777, SC)
    alt = dict(dr, f=dr["f"][::-1].copy(), c0=dr["c0"] * 0.97)
    pols = [R.P("balancer 5%", "bal", 4.0, 0.05), R.P("hyb1", "hybsel", 15.5 / 50 + 4.0, (1, 0.05), k=1)]
    assert R.in_sample_choice(pols, dr, SC, trials=2)[1] == R.in_sample_choice(pols, alt, SC, trials=2)[1]


def test_rest_conserves_charge_with_loss():
    s = np.array([[90.0, 95.0, 100.0, 105.0]])
    dod = np.full((1, 4), 0.5)
    hist = [np.ones(4)]
    new, d = R._rest(("observed", 0.5, 1), dod, s, np.ones((1, 4), bool), np.array([1]), [0.0], hist, 0.0, 12.0, 0.04, 4, np.ones(4))
    moved_in = ((new - dod) * s)[0, 1:].sum()
    assert d == pytest.approx(0.5 * 0.5 * 90.0)
    assert moved_in == pytest.approx(d / 0.96)


def test_floor_fn_is_pluggable():
    dr = R.draw(10_900, SC)
    pol = R.P("late", "late", SC["elec"], mask="all")
    wide = R.simulate(pol, dr, SC, floor_fn=lambda s, m: np.full(s.shape[0], m - 1))[0]
    none = R.simulate(pol, dr, SC, floor_fn=lambda s, m: np.zeros(s.shape[0], int))[0]
    assert wide >= none
