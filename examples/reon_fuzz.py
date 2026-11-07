"""FUZZ: throw extreme and broken inputs at every new module and list what crashes (a clean ValueError is fine; anything else is a bug). Run: PYTHONPATH=. python examples/reon_fuzz.py"""
import traceback, warnings
warnings.simplefilter('error')   # silent NaN or infinity now counts as a failure
import numpy as np
from hackkit import reon_guard as G, reon_events as E, reon_storm as S, reon_voltage as V, reon_response as R, reon_wear as W

fails = []


def check(name, fn):
    try:
        fn()
    except ValueError:
        pass
    except Exception as e:
        fails.append((name, type(e).__name__, str(e)[:90]))


rng = np.random.default_rng(1)
CAPS = [np.array([]), np.array([1.0]), np.array([0.0, 0.0, 0.0]), np.array([1.0, np.nan, 1.0]), np.array([1.0, -0.2, 1.0]), np.full(16, 1e9), np.array([1.0] * 15 + [1e-9]), 1 + 0.5 * rng.standard_normal(95)]
for i, c in enumerate(CAPS):
    for load in (0.0, 1e-9, 1.0, 1e9):
        for fail in (None, 0.0, 5.0, 1e9):
            check(f"storm caps{i} load{load} fail{fail}", lambda: S.hours(c, 60.0, load, True, 0.8, fail))
            check(f"storm plain caps{i} load{load} fail{fail}", lambda: S.hours(c, 60.0, load, False, 1.0, fail))
    for curve in V.CURVES:
        for mode in ("plain", "ideal", "floor"):
            check(f"voltage caps{i} {curve} {mode}", lambda: V.run(c, curve, mode, 0.7))
    check(f"voltage v_min 0 caps{i}", lambda: V.run(c, "NMC", "floor", 0.0))
    check(f"voltage v_min 5 caps{i}", lambda: V.run(c, "NMC", "floor", 5.0))
    check(f"bypass_room n{i}", lambda: V.bypass_room(len(c), 0.0))
    check(f"response caps{i}", lambda: R.decide([R.Cell(j, cap_rel=float(x)) for j, x in enumerate(c)], R.Context(n_engaged=len(c))))
check("response empty cells", lambda: R.decide([], R.Context()))
for kw in (dict(lam=0.0), dict(lam=1.0), dict(lam=-1.0), dict(n=1), dict(n=2, n_min=12), dict(months=0), dict(months=1), dict(fade=0.0, fcv=0.0), dict(fade=5.0), dict(visit_cost=0.0), dict(lead=0.0), dict(bypass_budget=0), dict(bypass_budget=100),
           dict(n_min=0), dict(n_min=100), dict(crew_at=0), dict(persist=0), dict(rate=-0.5), dict(retire=0.0), dict(retire=2.0), dict(nameplate=0.0), dict(g=-3.0), dict(weak_line=0.0), dict(weak_line=5.0), dict(start_cv=5.0), dict(detect=-1.0), dict(detect=1e6), dict(down_cost=-1.0), dict(down_cost=1e9), dict(thr_pays_loss=False)):
    for pol in E.EXTENDED:
        check(f"events {pol} {kw}", lambda: E.simulate(pol, 1, **kw))
from hackkit import reon_presets as P
for a in ((1.0, 25.0), (0.0, 25.0), (1.0, -50.0), (1.0, 200.0), (1e6, 25.0)):
    check(f"fade_per_year {a}", lambda: P.fade_per_year(*a))
check("fade_per_year negative", lambda: P.fade_per_year(-1.0))
for pr in ("loss", "e", "lam", "visit_cost"):
    check(f"break_even {pr}", lambda: E.break_even(pr, 0.0, 0.1 if pr != "e" else 80.0, seeds=range(2), iters=4))
check("value_streams extreme", lambda: E.value_streams(seeds=range(2), lam=0.0, visit_cost=0.0, down_cost=0.0))
check("events unknown policy", lambda: E.simulate("nonsense", 1))
KW = dict(balancer_r=0.05, balancer_per_kwh=4.0, ks=(1, 2), fade_mean=0.02, fade_cv=0.45, loss=0.02, electronics_per_kwh=15.0, sort_cost_per_kwh=0.0, value_per_kwh_year=40.0, rate=0.07, years=12.0, eol_frac=0.7,
          duty=0.7, dod_exp=0.87, knee_share=0.65, start_soh=1.0, balancer_eta=0.9, closed_loss=0.0, test_sigma=0.02, trials=3, steps=20, seed=5)
for over in (dict(), dict(value_per_kwh_year=0.0), dict(value_per_kwh_year=-5.0), dict(electronics_per_kwh=0.0), dict(electronics_per_kwh=-1.0), dict(fade_cv=0.0), dict(fade_cv=5.0), dict(years=0.0), dict(years=100.0), dict(eol_frac=0.0), dict(eol_frac=1.0),
             dict(loss=0.0), dict(loss=1.0), dict(loss=2.0), dict(rate=0.0), dict(duty=0.0), dict(duty=1.5), dict(trials=1), dict(steps=1), dict(ks=()), dict(ks=(16,)), dict(ks=(0,)), dict(test_sigma=0.0), dict(balancer_r=0.0), dict(balancer_r=2.0)):
    for start in (100.0 * np.ones(16), 100.0 * (1 + 0.02 * rng.standard_normal(16)), np.array([100.0] * 15 + [10.0]), np.array([100.0] * 15 + [0.0]), np.array([100.0] * 15 + [np.nan])):
        a = dict(KW); a.update(over)
        check(f"recommend {over} start{start[-1]}", lambda: G.safe_recommend(start, 16, **{k: a[k] for k in a if k in ('value_per_kwh_year','electronics_per_kwh','fade_cv','loss','years','eol_frac','duty','rate','ks','test_sigma','trials','steps')}))
check("recommend m not dividing n", lambda: W.recommend_build(np.full(15, 100.0), 16, **KW))
print(f"{len(fails)} unexpected failures")
seen = set()
for n, t, m in fails:
    key = (t, m)
    if key not in seen:
        seen.add(key)
        print(f"  {t}: {m}   (e.g. {n})")
