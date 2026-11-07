import numpy as np
import pytest

from hackkit import reon_design as D
from hackkit import reon_granularity as G
from hackkit import reon_sorting as S

CAPS = [93.8, 92.6, 84.3, 92.4, 91.5, 92.8, 88.1, 87.6, 88.5, 88.6, 90.3, 88.4]


def test_deliverable_matches_the_static_modules():
    c = np.array(CAPS)[None, :]
    assert D.deliverable(c, 12, 12, 0.0)[0] == pytest.approx(12 * c.min())
    assert D.deliverable(c, 12, 1, 0.0)[0] == pytest.approx(c.sum())
    assert D.deliverable(c, 12, 4, 0.0)[0] == pytest.approx(G.group_usable(CAPS, 4))
    assert D.deliverable(c, 4, 4, 0.0)[0] == pytest.approx(S.strings_usable(CAPS, 4))
    # sorted order, no switches == sorting module
    order = np.argsort(-np.array(CAPS))
    assert D.deliverable(c[:, order], 4, 4, 0.0)[0] == pytest.approx(S.sorted_usable(CAPS, 4))


def test_adaptive_never_worse_than_plain_string_even_with_huge_loss():
    c = np.array(CAPS)[None, :]
    assert D.deliverable(c, 12, 1, 0.9)[0] == pytest.approx(12 * c.min())
    assert D.deliverable(c, 12, 1, 0.0)[0] >= 12 * c.min()


def test_designs_listing_and_validation():
    assert ("as_found", 6) not in D.design_list(12, 6) and ("sorted", 6) in D.design_list(12, 6)
    assert ("sorted", 12) not in D.design_list(12, 12)
    with pytest.raises(ValueError):
        D.design_list(10, 4)


KW = dict(fade_mean=0.04, loss_cell=0.02, electronics_per_kwh_cell=8.8, sort_cost_per_kwh=0.0, value_per_kwh_year=22.0, rate=0.07, years=7.0, eol_frac=0.5,
          trials=30, steps=120)


def test_scan_reference_is_zero_and_free_electronics_never_hurt():
    recs = D.design_scan(CAPS, 12, fade_cvs=[0.0, 0.3], loss_exps=[1.0], cost_exps=[1.0], **{**KW, "electronics_per_kwh_cell": 0.0})
    assert all(r["mean"] == 0.0 for r in recs if r["design"].endswith("(reference)"))
    # adaptive control with free electronics can only help (same draws as the reference)
    assert all(r["mean"] >= -1e-9 for r in recs if r["order"] == "as_found")


def test_recommend_is_consistent():
    recs = D.design_scan(CAPS, 12, fade_cvs=[0.0, 0.3], loss_exps=[1.0, 0.0], cost_exps=[1.0, 0.0], **KW)
    r = D.recommend(recs)
    assert r["robust"] in r["max_regret"] and r["max_regret"][r["robust"]] == min(r["max_regret"].values())
    # at q = 0 (cost does not fall with fewer switches) the reference or sorting alone can win but never a free lunch: best mean in any scenario >= 0
    assert all(v[1] >= -1e-9 for v in r["best"].values())
    assert sum(r["win_counts"].values()) == len(r["scenarios"])


def test_sort_cost_breakeven_is_the_cost_that_ties_the_scan():
    kw = {**KW, "trials": 40}
    free = D.design_scan(CAPS, 4, fade_cvs=[0.2], loss_exps=[1.0], cost_exps=[1.0], **kw)
    be = D.sort_cost_breakeven(free)["median"]
    paid = D.design_scan(CAPS, 4, fade_cvs=[0.2], loss_exps=[1.0], cost_exps=[1.0], **{**kw, "sort_cost_per_kwh": be})
    so = [r["mean"] for r in paid if r["design"] == "sort only (no switches)"][0]
    best_rest = max([r["mean"] for r in paid if r["order"] == "as_found"])
    assert so == pytest.approx(best_rest, abs=1e-6)


def test_conditions_cover_every_scenario():
    recs = D.design_scan(CAPS, 12, fade_cvs=[0.0, 0.3], loss_exps=[1.0], cost_exps=[1.0, 0.0], **KW)
    cond = D.conditions(recs)
    assert sum(v["n"] for v in cond.values()) == 4


def test_closed_loss_can_make_switches_lose_when_nothing_is_gained():
    c = np.array([90.0, 90.0, 90.0, 90.0])[None, :]
    assert D.deliverable(c, 4, 1, 0.02, 0.01)[0] == pytest.approx(4 * 90 * 0.99)
    assert D.deliverable(c, 4, 4, 0.02, 0.01)[0] == pytest.approx(360.0)


def test_balancer_limits_and_hand_case():
    c = np.array([100.0, 90.0, 80.0, 70.0])
    assert D.balancer_q(c, 1e9, 1.0) == pytest.approx(85.0)         # ideal: the mean
    assert D.balancer_q(c, 0.0, 1.0) == pytest.approx(70.0)         # cannot move charge: the weakest cell
    assert D.balancer_q(c, 1e9, 0.0) == pytest.approx(70.0)         # transfer wastes everything
    beta = 0.0625 * c.mean()                                        # 5.3125 Ah: the weakest cell can reach 70 + beta, and donors cover it
    assert D.balancer_q(c, 0.0625, 1.0) == pytest.approx(70.0 + beta, rel=1e-6)


def test_balancer_is_monotone_and_satisfies_its_own_conditions():
    rng = np.random.default_rng(8)
    for _ in range(20):
        c = 70 + 30 * rng.random(12)
        qs = [D.balancer_q(c, r, 0.9) for r in (0.0, 0.02, 0.05, 0.2, 1e9)]
        assert all(b >= a - 1e-9 for a, b in zip(qs, qs[1:])) and qs[0] == pytest.approx(c.min()) and qs[-1] <= c.mean() + 1e-9
        r, eta = 0.05, 0.8
        q, beta = float(D.balancer_q(c, r, eta)), r * c.mean()
        short, spare = np.maximum(q - c, 0), np.minimum(beta, np.maximum(c - q, 0))
        assert short.max() <= beta + 1e-6 and short.sum() <= eta * spare.sum() + 1e-6
        q2 = q + 1e-3                                                # slightly more must be infeasible (unless already the mean)
        if q < c.mean() - 2e-3:
            sh, sp = np.maximum(q2 - c, 0), np.minimum(beta, np.maximum(c - q2, 0))
            assert sh.max() > beta or sh.sum() > eta * sp.sum()


def test_competitors_in_the_scan_and_breakeven():
    recs = D.design_scan(CAPS, 12, fade_cvs=[0.2], loss_exps=[1.0], cost_exps=[1.0], balancer_rs=[0.05, 1e9], balancer_eta=0.9, balancer_per_kwh=2.0,
                         converter_loss=0.03, converter_per_kwh_cell=8.8, **{**KW, "trials": 30})
    kinds = {r["kind"] for r in recs}
    assert {"reference", "switch", "balancer", "converter"} <= kinds
    ideal_bal = [r for r in recs if r["kind"] == "balancer" and r["design"].startswith("active balancer (moves up to") and "as found" in r["design"] and r["k"] == 0]
    assert ideal_bal
    be = D.add_capacity_breakeven(recs, [r["design"] for r in recs if r["kind"] == "switch" and r["k"] == 1 and r["order"] == "as_found"][0])
    assert be["median"] is None or be["median"] > 0


def test_late_switches_dominate_always_engaged_and_plain():
    rng = np.random.default_rng(4)
    for _ in range(10):
        c = (70 + 30 * rng.random((5, 12)))
        for k in (1, 3, 12):
            for loss in (0.0, 0.02, 0.1):
                late = D.deliverable_late(c, 12, k, loss)
                alw = D.deliverable(c, 12, k, loss)
                plain = D.deliverable(c, 12, 12, 0.0)
                assert (late >= alw - 1e-9).all() and (late >= plain - 1e-9).all()
    c = np.array([[100.0, 90.0, 80.0, 70.0]])
    assert D.deliverable_late(c, 4, 1, 0.1)[0] == pytest.approx(280 + 0.9 * 60)  # 4 x min + (1 - loss)(sum - 4 x min)


def test_hybrid_dominates_both_parents_and_hits_the_limits():
    rng = np.random.default_rng(6)
    for _ in range(15):
        c = 60 + 40 * rng.random((4, 12))
        for r, eta, loss in ((0.05, 0.9, 0.02), (0.2, 0.8, 0.05), (0.0, 0.9, 0.02)):
            h = D.hybrid_total(c, loss, r, eta)
            lazy = 12 * c.min(axis=-1) + (1 - loss) * (c.sum(axis=-1) - 12 * c.min(axis=-1))
            bal = 12 * D.balancer_q(c, r, eta)
            assert (h >= lazy - 1e-9).all() and (h >= bal - 1e-9).all() and (h <= c.sum(axis=-1) + 1e-9).all()
            if r == 0.0:
                assert h == pytest.approx(lazy)
    c = np.array([100.0, 90.0, 80.0, 70.0])
    assert D.hybrid_total(c, 0.0, 1e9, 1.0) == pytest.approx(340.0)
    assert D.hybrid_total(c, 0.05, 1e9, 1e-9) == pytest.approx(280 + 0.95 * 60)  # useless balancer -> late switches only


def test_scan_contains_late_and_hybrid_and_hybrid_never_loses_to_parents_at_equal_cost():
    recs = D.design_scan(CAPS, 12, fade_cvs=[0.2], loss_exps=[1.0], cost_exps=[1.0], balancer_rs=[0.1], balancer_eta=0.9, balancer_per_kwh=0.0,
                         hybrid_per_kwh=0.0, **{**KW, "electronics_per_kwh_cell": 0.0, "trials": 30})
    by = {r["design"]: r["mean"] for r in recs if r["order"] == "as_found"}
    hyb = [v for k, v in by.items() if k.startswith("hybrid")][0]
    bal = [v for k, v in by.items() if k.startswith("active balancer")][0]
    late = [v for k, v in by.items() if k.startswith("late-engaging switch on every cell")][0]
    assert hyb >= bal - 1e-9 and hyb >= late - 1e-9


def test_late_closed_loss_recovers_always_engaged_bound_and_policy_picks_the_max():
    c = np.array([[100.0, 90.0, 80.0, 70.0]])
    # closed_loss = loss recovers: plain part also pays the loss -> equals (1-loss) * sum when the bypass pays
    late_pess = D.deliverable_late(c, 4, 1, 0.02, closed_loss=0.02)[0]
    assert late_pess == pytest.approx(0.98 * 280 + 0.98 * 60)
    assert late_pess <= D.deliverable_late(c, 4, 1, 0.02)[0]
    pol = D.policy([100.0, 90.0, 80.0, 70.0], loss=0.02, closed_loss=0.0, balancer_r=1e9, balancer_eta=1.0)
    assert pol["best"] == "balancer only" or pol["best"] == "hybrid"
    assert max(pol["modes"].values()) == pol["modes"][pol["best"]]
    pol2 = D.policy([90.0, 90.0, 90.0, 90.0], loss=0.02, closed_loss=0.0, balancer_r=0.1, balancer_eta=0.9)
    assert pol2["gain_over_plain"] == pytest.approx(0.0) and pol2["best"] in pol2["modes"]


def test_dead_cell_kills_balancer_and_plain_but_not_cell_level_bypass():
    c = np.array([[100.0, 0.0, 90.0, 95.0]])
    assert D.deliverable(c, 4, 4, 0.0)[0] == 0.0
    assert D.balancer_q(c, 1e9, 1.0)[0] == 0.0 and D.deliverable_balancer(c, 4, 1e9, 1.0)[0] == 0.0
    assert D.deliverable_late(c, 4, 1, 0.02)[0] == pytest.approx(0.98 * 285.0)
    assert D.deliverable_late(c, 4, 2, 0.02)[0] == pytest.approx(0.98 * 2 * 90.0 * 1 + 0.0)  # groups (100,0) and (90,95): only the second delivers
    assert D.hybrid_total(c[0], 0.02, 1e9, 1.0) == pytest.approx(0.98 * 285.0)


def test_failures_hurt_plain_more_than_cell_level_switches():
    kw = {**KW, "trials": 40, "electronics_per_kwh_cell": 0.0}
    none = D.design_scan(CAPS, 12, fade_cvs=[0.1], loss_exps=[1.0], cost_exps=[1.0], **kw)
    fail = D.design_scan(CAPS, 12, fade_cvs=[0.1], loss_exps=[1.0], cost_exps=[1.0], fail_rate_per_cell_year=0.05, **kw)
    g = lambda recs: [r["mean"] for r in recs if r["design"].startswith("late-engaging switch on every cell") and r["order"] == "as_found"][0]
    assert g(fail) > g(none)  # the plain reference collapses, so the cell-level bypass gains relative to it


def test_repair_shortens_outages_and_restores_the_plain_pack():
    kw = {**KW, "trials": 40, "electronics_per_kwh_cell": 0.0}
    mk = lambda rep: D.design_scan(CAPS, 12, fade_cvs=[0.1], loss_exps=[1.0], cost_exps=[1.0], fail_rate_per_cell_year=0.1, repair_years=rep, **kw)
    base = lambda recs: [r["base_value"] for r in recs if r["kind"] == "reference"][0]
    assert base(mk(0.02)) > base(mk(None))   # quick repair keeps the plain pack delivering; retirement is set by ageing only


def test_learn_updates_and_converges():
    from hackkit import reon_learn as L
    b = L.FailureBelief()
    b2 = b.update(5, 500)
    assert abs(b2.mean - 5.5 / 600) < 1e-12 and b2.interval()[1] - b2.interval()[0] < b.interval()[1] - b.interval()[0]
    assert L.FailureBelief().update(0, 5000).mean < L.FailureBelief().mean          # zero failures lowers the belief
    f = L.FadeBelief(prior_cv=0.1, prior_n=6)
    assert abs(f.cv - 0.1) < 1e-9
    wide = [0.02, 0.06, 0.03, 0.07, 0.01, 0.08, 0.04, 0.05]                          # CV about 0.5
    assert f.update(wide).cv > 0.2
    import pytest
    with pytest.raises(ValueError):
        b.update(-1, 5)


def test_learn_calibration_and_retest():
    from hackkit import reon_learn as L
    for cy in (0, 200, 5000):                                                         # the 90% interval should hold the truth about 90% of the time
        assert abs(L.interval_coverage(cy, fleets=600, seed=cy) - 0.9) < 0.06
    a = L.decision_accuracy(0.01, 0.005, 200, fleets=150)["correct"]
    b = L.decision_accuracy(0.01, 0.005, 5000, fleets=150)["correct"]
    assert b > a and b > 0.95                                                          # more data, more correct decisions
    assert L.decision_accuracy(0.01, 0.005, 5000, fleets=150, seed=1)["wrong"] < 0.02  # test-retest: wrong calls stay rare across repeats
    assert L.decide(L.FailureBelief().update(30, 1000), 0.01) == "switches"
    assert L.decide(L.FailureBelief().update(0, 5000), 0.01) == "balancer"
    assert L.cell_years_needed(0.02, 0.005, fleets=60) is not None


def test_learn_fade_sampling_matches_belief():
    import numpy as np
    from hackkit import reon_learn as L
    rng = np.random.default_rng(0)
    for pn in (6, 20):                                   # a belief with no data must sample CVs around its own prior, tighter for a more confident prior
        s = L.FadeBelief(prior_cv=0.10, prior_n=pn).sample(20000, rng)
        assert 0.08 < np.median(s) < 0.115
    f = L.FadeBelief(prior_cv=0.10, prior_n=6).update([0.02, 0.06, 0.03, 0.07, 0.01, 0.08, 0.04, 0.05] * 5)
    assert abs(np.median(f.sample(20000, rng)) - f.cv) < 0.05


def test_learn_advantage_against_all_rivals_is_no_better_than_against_balancer_alone():
    from hackkit import reon_learn as L
    caps = [20.27, 17.42, 19.57, 18.93, 25.04, 23.65, 22.87, 17.59]
    kw = dict(trials=20, seed=2, balancer_per_kwh=8.8)
    a_all = L._advantage(caps, 8, 0.0, 0.2, rivals="all", **kw)
    a_bal = L._advantage(caps, 8, 0.0, 0.2, rivals="balancer", **kw)
    assert a_all <= a_bal + 1e-9                     # more rivals can only lower our edge
    r = L.prob_ours_wins(caps, 8, L.FailureBelief(), L.FadeBelief(), draws=3, trials=15, seed=1, balancer_per_kwh=8.8)
    assert 0.0 <= r["p_win"] <= 1.0
