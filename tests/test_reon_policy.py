import numpy as np
import pytest

from hackkit import reon_design as D
from hackkit import reon_policy as POL
from hackkit import reon_wear as W

KW = dict(value_per_kwh_year=40.0, electronics_per_kwh=15.5, fade_cv=0.45, fade_mean=0.012, loss=0.04, years=12.0, eol_frac=0.7, closed_loss=0.02, window=0.75, trials=8, steps=24, ks=(1, 2, 4))


def start(n=16, seed=3, spread=0.03):
    return 100.0 * (1.0 + spread * np.random.default_rng(seed).standard_normal(n))


def test_exempt_hybrid_never_below_plain_hybrid_balancer_or_plain_string():
    rng = np.random.default_rng(1)
    for _ in range(40):
        s = 100.0 * (1.0 + 0.08 * rng.standard_normal((6, 12))).clip(0.3)
        mask = np.zeros(s.shape, dtype=bool)
        mask[np.arange(6)[:, None], np.argsort(s, axis=1)[:, :3]] = True
        r = float(rng.uniform(0.01, 0.2))
        a = W.hybrid_exempt_total(s, mask, 0.04, r, 0.9)
        b = W.hybrid_select_total(s, mask, 0.04, r, 0.9)
        assert np.all(a >= b - 1e-6)
        assert np.all(a >= 12 * D.balancer_q(s, r, 0.9) - 1e-6)
        assert np.all(a >= 12 * s.min(axis=1) - 1e-6)


def test_exempt_hybrid_survives_a_dead_switched_cell_where_a_balancer_cannot():
    s = np.full((1, 12), 100.0)
    s[0, 4] = 0.0
    mask = np.zeros(s.shape, dtype=bool)
    mask[0, 4] = True
    assert W.hybrid_exempt_total(s, mask, 0.04, 0.05, 0.9)[0] > 0.9 * 1100 * 0.96 - 1.0
    assert D.balancer_q(s, 0.05, 0.9)[0] == 0.0


def test_adaptive_design_exists_only_with_a_window():
    caps = start()
    r1 = W.wear_scan(caps, 16, balancer_rs=(0.05,), balancer_per_kwh=4.0, hybrid_shares_wear=True, hybrid_exempt=True, adaptive_hybrid=True, window=0.75, fade_mean=0.01, fade_cv=0.4, loss=0.04,
                     electronics_per_kwh=15.5, sort_cost_per_kwh=0.0, value_per_kwh_year=40.0, rate=0.07, years=10.0, eol_frac=0.7, trials=3, steps=12)
    assert any(k.startswith("hybrid adaptive 4/16") for k in r1)
    r2 = W.wear_scan(caps, 16, balancer_rs=(0.05,), balancer_per_kwh=4.0, adaptive_hybrid=True, fade_mean=0.01, fade_cv=0.4, loss=0.04, electronics_per_kwh=15.5, sort_cost_per_kwh=0.0, value_per_kwh_year=40.0,
                     rate=0.07, years=10.0, eol_frac=0.7, trials=3, steps=12)
    assert any("adaptive" in k for k in r2)   # asked for explicitly, with no window it uses m // 10 bypassed cells
    r3 = POL.guarded_recommend(caps, 16, **dict(KW, window=None))
    assert not any("adaptive" in k for k in r3["table"])   # the policy never runs it without a voltage window


def test_identical_cells_hold_and_never_buy_switches():
    r = POL.guarded_recommend(np.full(16, 100.0), 16, **dict(KW, fade_cv=0.0))   # identical cells that also age identically: nothing to fix
    assert r["verdict"] in ("HOLD", "BALANCER") and r["kind"] == "rival"


def test_guarded_pick_never_loses_to_balancer_or_plain_on_a_fresh_seed():
    for seed, fade, rr in ((3, 0.004, 0.05), (4, 0.012, 0.05), (5, 0.02, 0.10), (6, 0.008, 0.02)):
        kw = dict(KW, fade_mean=fade, balancer_r=rr)
        rb = POL.robust_guarded(start(seed=seed), 16, **kw)
        bal = rb["balancer_gain"]
        assert rb["mean_gain"] >= max(0.0, bal) - 0.5, (seed, fade, rr, rb["verdict"], rb["mean_gain"], bal)
        assert rb["verdict"] in ("BUY", "BALANCER", "HOLD") and rb["life_ours"] >= 0 and rb["life_plain"] >= 0
        if rb["verdict"] != "BUY":
            assert rb["margin_vs_rival"] == 0.0


def test_min_margin_turns_a_small_edge_into_a_tie():
    kw = dict(KW, fade_mean=0.012, balancer_r=0.05)
    big = POL.guarded_recommend(start(seed=4), 16, min_margin=1e6, **kw)
    assert big["verdict"] != "BUY"


def test_policy_validates_inputs():
    with pytest.raises(ValueError):
        POL.guarded_recommend(start(), 5, **KW)
    with pytest.raises(ValueError):
        POL.guarded_recommend(np.r_[start()[:-1], np.nan], 16, **KW)
    with pytest.raises(ValueError):
        POL.guarded_recommend(start(), 16, **dict(KW, trials=2))
    with pytest.raises(ValueError):
        POL.guarded_recommend(start(), 16, **dict(KW, value_per_kwh_year=-1.0))
    with pytest.raises(ValueError):
        POL.guarded_recommend(start(), 16, balancer_r=0.0, **KW)


def test_policy_accepts_a_cell_failed_open_and_buys_switches():
    caps = start(seed=9)
    caps[5] = 0.0   # failed open: a balancer cannot move charge through it, only a bypass can save the string
    r = POL.guarded_recommend(caps, 16, **dict(KW, fade_mean=0.004, ks=(1, 2)))
    assert r["verdict"] == "BUY" and r["mean_gain"] > 10.0
    with pytest.raises(ValueError):
        POL.guarded_recommend(np.zeros(16), 16, **KW)
