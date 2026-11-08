"""reon_adversary: policy-agnostic adversarial cases + a paired-regret harness for any build-picking policy.

A Case is a named, seeded generator of Draws. A Draw is one hostile pack: day-1 capacities of the 250 series positions (mean 100; each position = p cells in parallel) plus the reon_wear
settings that say how it ages (fade mean/CV, fade-vs-weakness correlation, loss, cold). reon_wear draws the per-cell FADE rates itself from (fade_mean, fade_cv, weak_corr, seed), so the fade
stream is paired for free: every build and the policy are scored on the same start caps AND the same fades. Fades cannot be injected cell by cell (wear_scan has no such argument), so
batch-correlated fade is approximated with weak_corr (weak cells fade faster). A policy takes a Draw and returns $/kWh nameplate (12-year net value vs plain, switch/balancer cost included).
Regret = best baseline - policy, per draw. evaluate() ranks cases by worst regret. Assumed numbers: docs/stress/adversary_assumptions.md."""
from __future__ import annotations

import importlib
import json
import os
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Sequence

import numpy as np

from hackkit import reon_storm as S
from hackkit import reon_wear as W

N_SERIES = 250
FROZEN_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests", "data", "adversary_cases")
BAL_WEAK, BAL_STRONG = 0.025, 0.05   # transfer limits of the two balancer baselines (share of mean capacity per cycle)
THRESHOLD = 0.50                     # $/kWh regret a policy may not exceed on a frozen case

# wear_scan settings: reon_storefront._kw + reon_guard.safe_recommend defaults (dod_exp .87, knee_share .65) + balancer sweep (cost 4, eta .9, wear credited to hybrid). window .9, string = whole pack.
BASE_KW = dict(fade_mean=0.008, fade_cv=0.45, loss=0.04, electronics_per_kwh=15.5, balancer_per_kwh=4.0, sort_cost_per_kwh=0.0, value_per_kwh_year=40.0, rate=0.07, years=12.0, eol_frac=0.7,
               duty=0.7, dod_exp=0.87, knee_share=0.65, start_soh=1.0, balancer_eta=0.9, closed_loss=0.02, test_sigma=0.02, window=0.9, hybrid_shares_wear=True, weak_corr=0.0,
               trials=6, steps=40)
KS = (1, 2, 4, 8, 16, 25)


def _scan(start, kw, seed):
    n = len(start)
    ks = tuple(k for k in KS if k < n)
    return W.wear_scan(start, n, balancer_rs=(BAL_WEAK, BAL_STRONG), select_counts=ks, hybrid_counts=ks, seed=seed, **kw)


@dataclass
class Draw:
    """One hostile pack. start: (250,) day-1 capacities. kw: wear_scan overrides on BASE_KW. meta: how it was made."""
    start: np.ndarray
    kw: dict
    seed: int
    meta: dict = field(default_factory=dict)
    _table: dict = field(default=None, repr=False, compare=False)

    def table(self) -> dict:
        """reon_wear net value ($/kWh, mean/p10/p90...) for EVERY build at this draw: one engine call, cached, shared by policy and baselines."""
        if self._table is None:
            self._table = _scan(self.start, dict(BASE_KW, **self.kw), self.seed)
        return self._table

    def storm_hours(self, load_kw=5.0, nameplate_kwh=60.0, fail_at_h=None, cold=1.0):
        """(plain, managed) backup hours on this draw's start caps (reon_storm). Informational: not part of $/kWh."""
        c = self.start / self.start.mean()
        return (S.hours(c, nameplate_kwh, load_kw, False, cold, fail_at_h), S.hours(c, nameplate_kwh, load_kw, True, cold, fail_at_h, window=0.9))

    def to_json(self):
        return dict(start=[float(x) for x in self.start], kw=self.kw, seed=int(self.seed), meta=self.meta)

    @staticmethod
    def from_json(d):
        return Draw(np.asarray(d["start"], float), dict(d["kw"]), int(d["seed"]), dict(d.get("meta", {})))


# ---------------------------------------------------------------- generators: each returns a function seed -> Draw
def _base(rng, p, spread_mult=1.0):
    return 100.0 * (1.0 + spread_mult * 0.02 / np.sqrt(p) * rng.standard_normal(N_SERIES))   # start spread 2%/sqrt(p) (reon_storefront._start)


def _kw(p, fade, **over):
    return dict(fade_mean=float(fade), fade_cv=0.45 / np.sqrt(p), **over)   # fade CV 0.45/sqrt(p) (reon_storefront._kw)


def gen_base(p=1, fade=0.008):
    def f(seed):
        rng = np.random.default_rng(seed)
        return Draw(_base(rng, p), _kw(p, fade), seed, dict(case="base", p=p, fade=fade))
    return f


def gen_clustered_weak(p=1, fade=0.008, n_clusters=3, cluster_len=10, depth=0.12, weak_corr=0.8):
    """Adjacent positions share a bad batch: n_clusters runs of cluster_len positions each `depth` (share) weaker; weak cells also fade faster (weak_corr)."""
    def f(seed):
        rng = np.random.default_rng(seed)
        c = _base(rng, p)
        starts = rng.choice(N_SERIES - cluster_len, n_clusters, replace=False)
        for s0 in starts:
            c[s0:s0 + cluster_len] *= 1.0 - depth * (1.0 + 0.1 * rng.standard_normal(cluster_len))
        return Draw(c, _kw(p, fade, weak_corr=weak_corr), seed, dict(case="clustered_weak", p=p, fade=fade, n_clusters=n_clusters, cluster_len=cluster_len, depth=depth, weak_corr=weak_corr))
    return f


def gen_outliers(p=1, fade=0.008, n_out=3, depth=0.45, weak_corr=0.5):
    """A few extreme single-position outliers, `depth` (share) below the pack."""
    def f(seed):
        rng = np.random.default_rng(seed)
        c = _base(rng, p)
        c[rng.choice(N_SERIES, n_out, replace=False)] *= 1.0 - depth
        return Draw(c, _kw(p, fade, weak_corr=weak_corr), seed, dict(case="outliers", p=p, fade=fade, n_out=n_out, depth=depth, weak_corr=weak_corr))
    return f


def gen_fail_open(p=1, fade=0.008, n_dead=1):
    """Cell(s) failed open: capacity 0 at the string (mid-storm failure frozen at its end state; reon_wear has no mid-run fault, so the pack is scored as if already open). Plain string = 0 for ever;
    a balancer cannot move charge through it (balancer_q returns 0); only a bypass can. meta['storm'] holds reon_storm hours for a failure at hour 10."""
    def f(seed):
        rng = np.random.default_rng(seed)
        c = _base(rng, p)
        live = c.copy()
        c[rng.choice(N_SERIES, n_dead, replace=False)] = 0.0
        d = Draw(c, _kw(p, fade), seed, dict(case="fail_open", p=p, fade=fade, n_dead=n_dead))
        d.meta["storm_plain_h_fail10"], d.meta["storm_managed_h_fail10"] = (float(x) for x in Draw(live, {}, seed).storm_hours(fail_at_h=10.0))
        return d
    return f


def gen_cold_sag(p=1, fade=0.008, cold=0.75, loss=0.10, closed_loss=0.05):
    """Sag-heavy cold night: capacities scaled by `cold` (temperature factor, reon_storm 'cold' convention), switch loss and closed-path loss raised (higher resistance)."""
    def f(seed):
        rng = np.random.default_rng(seed)
        return Draw(_base(rng, p) * cold, _kw(p, fade, loss=loss, closed_loss=closed_loss), seed, dict(case="cold_sag", p=p, fade=fade, cold=cold, loss=loss, closed_loss=closed_loss))
    return f


def gen_slow_wear(p=1, fade=0.002):
    return _renamed(gen_base(p, fade), "slow_wear")


def gen_fast_wear(p=1, fade=0.03):
    return _renamed(gen_base(p, fade), "fast_wear")


def gen_correlated(p=1, fade=0.008, weak_corr=0.9, spread_mult=3.0):
    """Correlated fade + wide start spread: the weakest cells fade fastest (weak_corr) and the start spread is spread_mult x the 2%/sqrt(p) default."""
    def f(seed):
        rng = np.random.default_rng(seed)
        return Draw(_base(rng, p, spread_mult), _kw(p, fade, weak_corr=weak_corr), seed, dict(case="correlated", p=p, fade=fade, weak_corr=weak_corr, spread_mult=spread_mult))
    return f


def _renamed(g, name):
    def f(seed):
        d = g(seed)
        d.meta["case"] = name
        return d
    return f


GENERATORS = dict(base=gen_base, clustered_weak=gen_clustered_weak, outliers=gen_outliers, fail_open=gen_fail_open, cold_sag=gen_cold_sag, slow_wear=gen_slow_wear, fast_wear=gen_fast_wear,
                  correlated=gen_correlated)


def default_cases(parallels=(4, 16)) -> Dict[str, Callable[[int], Draw]]:
    """Every generator at each parallel count in `parallels` (4 and 16 cells per position by default; pass (1, 4, 16, 40) for the full grid)."""
    out = {}
    for name, g in GENERATORS.items():
        for p in parallels:
            out[f"{name}_p{p}"] = g(p=p)
    return out


# ---------------------------------------------------------------- baselines and harness
def _pick(t, prefixes, exclude=()):
    v = [x["mean"] for k, x in t.items() if k.startswith(prefixes) and not any(e in k for e in exclude)]
    return max(v)


def default_baselines(draw: Draw) -> Dict[str, float]:
    """$/kWh (net vs plain) of the rival builds on this draw: plain (0 by definition), 2.5% balancer, 5% balancer, REON switches alone (best late/level/selective), hybrid (best)."""
    t = draw.table()
    return {"plain": 0.0, "balancer 2.5%": t[_bal_name(BAL_WEAK)]["mean"], "balancer 5%": t[_bal_name(BAL_STRONG)]["mean"],
            "switches alone": _pick(t, ("late", "level", "selective")), "hybrid": _pick(t, ("hybrid",))}


def _bal_name(r):
    return f"balancer {format(r, '.0%')}"


def policy_always_balancer_5(draw: Draw) -> float:
    """Trivial demo policy: always build the 5% balancer."""
    return draw.table()[_bal_name(BAL_STRONG)]["mean"]


def policy_always_plain(draw: Draw) -> float:
    return 0.0


def evaluate(policy_fn: Callable[[Draw], float], baselines_fn: Callable[[Draw], Dict[str, float]] = default_baselines, cases: Dict[str, Callable[[int], Draw]] = None,
             seeds: Sequence[int] = (0, 1, 2), top: int = None) -> List[dict]:
    """For each case and seed: the same Draw goes to policy_fn (-> $/kWh) and baselines_fn (-> {name: $/kWh}); regret = best baseline - policy (positive = policy loses). Returns one row per case,
    worst first: case, worst_regret, mean_regret, worst_seed, best_baseline_at_worst, policy_at_worst, per-seed regrets. `top` keeps only the worst few."""
    rows = []
    for name, gen in (cases if cases is not None else default_cases()).items():
        per = []
        for s in seeds:
            d = gen(s)
            b = baselines_fn(d)
            nb = max(b, key=b.get)
            pol = float(policy_fn(d))
            per.append((float(b[nb]) - pol, s, nb, float(b[nb]), pol))
        reg = [x[0] for x in per]
        w = int(np.argmax(reg))
        rows.append(dict(case=name, worst_regret=reg[w], mean_regret=float(np.mean(reg)), worst_seed=per[w][1], best_baseline_at_worst=per[w][2], baseline_at_worst=per[w][3], policy_at_worst=per[w][4], regrets=reg))
    rows.sort(key=lambda r: -r["worst_regret"])
    return rows[:top] if top else rows


# ---------------------------------------------------------------- freeze / replay
def _policy_path(policy_fn):
    return f"{policy_fn.__module__}:{policy_fn.__qualname__}"


def _load_policy(path):
    mod, fn = path.split(":")
    return getattr(importlib.import_module(mod), fn)


def freeze_case(name: str, draw: Draw, policy_fn: Callable, directory: str = FROZEN_DIR) -> str:
    """Write the exact failing Draw (start caps + settings + seed) and the policy's dotted path (module:function) to <directory>/<name>.json. Self-contained: replay needs no generator."""
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{name}.json")
    with open(path, "w") as f:
        json.dump(dict(name=name, policy=_policy_path(policy_fn), threshold=THRESHOLD, draw=draw.to_json()), f)
    return path


def frozen_case_files(directory: str = FROZEN_DIR) -> List[str]:
    return sorted(os.path.join(directory, x) for x in os.listdir(directory) if x.endswith(".json")) if os.path.isdir(directory) else []


def replay(path: str, baselines_fn=default_baselines) -> dict:
    """Re-run one frozen case. Returns name, regret, threshold, ok (regret <= threshold)."""
    with open(path) as f:
        c = json.load(f)
    d = Draw.from_json(c["draw"])
    b = baselines_fn(d)
    reg = max(b.values()) - _load_policy(c["policy"])(d)
    return dict(name=c["name"], regret=float(reg), threshold=c.get("threshold", THRESHOLD), ok=bool(reg <= c.get("threshold", THRESHOLD)))
