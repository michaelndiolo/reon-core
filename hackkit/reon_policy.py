"""reon_policy: the decision layer that cannot do worse than what a customer already has.

Rivals we must not lose to: a plain string (do nothing) and a simple active balancer (the usual fix). Our builds: selective / late / level bypass and the hybrid (a few bypass switches on the weakest cells PLUS a balancer,
with the weak cells exempt from the balancer's bottleneck, reon_wear.hybrid_exempt_total).

`guarded_recommend` evaluates every build on the SAME random cells and ageing paths (common random numbers), so the difference between two builds is a paired difference with a standard error.
A build of ours is recommended only if it beats the better rival by more than `z` standard errors on those paired draws. Otherwise the answer is the better rival itself (balancer if it clearly pays, else plain),
which ties the rival by construction instead of risking a loss to noise. Pick on one seed, score on a fresh one (see examples/reon_policy_eval.py)."""
from __future__ import annotations

import numpy as np

from hackkit import reon_guard as G
from hackkit import reon_wear as W

OURS = ("selective", "late", "level", "hybrid")


def _se(d):
    d = np.asarray(d, dtype=float)
    return float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else float("inf")


def _scan(s, m, *, balancer_r, balancer_per_kwh, ks, fade_mean, fade_cv, loss, electronics_per_kwh, sort_cost_per_kwh, value_per_kwh_year, rate, years, eol_frac, duty, dod_exp, knee_share, start_soh,
          balancer_eta, closed_loss, test_sigma, trials, steps, seed, window, exempt, adaptive, weak_corr=0.0):
    return W.wear_scan(s, int(m), balancer_rs=(balancer_r,), balancer_per_kwh=balancer_per_kwh, select_counts=ks, global_counts=(), hybrid_counts=ks, fade_mean=fade_mean, fade_cv=fade_cv, loss=loss,
                       electronics_per_kwh=electronics_per_kwh, sort_cost_per_kwh=sort_cost_per_kwh, value_per_kwh_year=value_per_kwh_year, rate=rate, years=years, eol_frac=eol_frac, duty=duty,
                       dod_exp=dod_exp, knee_share=knee_share, start_soh=start_soh, balancer_eta=balancer_eta, closed_loss=closed_loss, test_sigma=test_sigma, trials=trials, steps=steps, seed=seed, weak_corr=weak_corr,
                       window=window, hybrid_shares_wear=True, hybrid_exempt=exempt, return_trials=True, adaptive_hybrid=bool(adaptive and window is not None))


def _params(start, m, value_per_kwh_year, electronics_per_kwh, fade_cv, loss, years, eol_frac, duty, fade_mean, rate, balancer_r, balancer_per_kwh, ks, dod_exp, knee_share, start_soh, balancer_eta, closed_loss,
            test_sigma, sort_cost_per_kwh, trials, steps, window, exempt, adaptive, z, weak_corr=0.0):
    s = G.caps_array(start, "start", positive=False, min_len=2)   # a capacity of 0 is a cell that has failed open: allowed, only a bypass can save that string
    G.need(bool((s > 0).any()), "start: at least one cell must have capacity")
    G.need(0.0 <= weak_corr < 1.0, "weak_corr must be in [0, 1)")
    G.need(isinstance(m, (int, np.integer)) and 2 <= m <= len(s) and len(s) % m == 0, "m: cells per string must divide the number of cells")
    G.need(z >= 0, "z must be zero or more")
    G.need(trials >= 4, "trials >= 4 for a paired comparison")
    G.need(value_per_kwh_year >= 0 and electronics_per_kwh >= 0 and balancer_per_kwh >= 0, "costs and value must be zero or more")
    G.need(0.0 <= fade_cv <= 2.0 and 0.0 <= loss < 0.5 and 0.5 <= years <= 40 and 0.05 <= eol_frac < 1.0 and 0.05 <= duty <= 1.0 and 0.0 <= fade_mean <= 0.5 and 0.0 <= rate <= 0.5, "an input is outside its allowed range")
    G.need(0.0 < balancer_r and 0.0 < balancer_eta <= 1.0, "balancer limit above 0 and efficiency in (0, 1]")
    G.need(window is None or 0.0 < window <= 1.0, "window must be above 0 and at most 1")
    ks = tuple(k for k in ks if 0 < k < m)
    return s, dict(balancer_r=balancer_r, balancer_per_kwh=balancer_per_kwh, ks=ks, fade_mean=fade_mean, fade_cv=fade_cv, loss=loss, electronics_per_kwh=electronics_per_kwh, sort_cost_per_kwh=sort_cost_per_kwh,
                   value_per_kwh_year=value_per_kwh_year, rate=rate, years=years, eol_frac=eol_frac, duty=duty, dod_exp=dod_exp, knee_share=knee_share, start_soh=start_soh, balancer_eta=balancer_eta,
                   closed_loss=closed_loss, test_sigma=test_sigma, trials=trials, steps=steps, window=window, exempt=exempt, adaptive=adaptive, weak_corr=weak_corr)


def _decide(res, n_balancer, trials, z, min_margin=0.0):
    """The paired-difference rule on one scan: returns (verdict, build, rival_name, margin, why)."""
    plain = np.zeros(trials)
    bal = np.asarray(res[n_balancer]["net"])
    bal_pays = bal.mean() - z * _se(bal) > 0.0
    rival_name, rival = (n_balancer, bal) if (bal_pays and bal.mean() > 0.0) else ("plain", plain)
    best, best_d = None, None
    for nm, v in res.items():
        if not nm.startswith(OURS):
            continue
        d = np.asarray(v["net"]) - rival
        if d.mean() - z * _se(d) > 0.0 and d.mean() >= min_margin and (best is None or d.mean() > best_d.mean()):
            best, best_d = nm, d
    if best is not None:
        return "BUY", best, rival_name, float(best_d.mean()), f"{best} beats {rival_name} by {best_d.mean():.1f} per kWh (paired, more than {z:g} standard errors)"
    if rival_name != "plain":
        return "BALANCER", n_balancer, rival_name, 0.0, f"no build of ours clearly beats the {n_balancer}; a balancer is enough here"
    return "HOLD", "plain", rival_name, 0.0, "nothing clearly pays over a plain string"


def guarded_recommend(start, m, *, value_per_kwh_year, electronics_per_kwh, fade_cv, loss=0.02, years=12.0, eol_frac=0.7, duty=0.7, fade_mean=0.02, rate=0.07, balancer_r=0.05, balancer_per_kwh=4.0,
                      ks=(1, 2, 4, 8, 16, 25), dod_exp=0.87, knee_share=0.65, start_soh=1.0, balancer_eta=0.9, closed_loss=0.0, test_sigma=0.02, sort_cost_per_kwh=0.0, trials=16, steps=40, seed=5,
                      window=None, z=1.0, exempt=True, adaptive=True, min_margin=1.0, weak_corr=0.0):
    """Returns dict(build, kind, verdict, mean_gain, p10_gain, margin_vs_rival, rival, why, table). verdict: BUY (one of our builds beats the better rival by more than z paired standard errors),
    BALANCER (a balancer pays and none of our builds clearly beats it by at least min_margin per kWh: tie), HOLD (nothing clearly pays: tie with plain). Gains are per kWh nameplate against a plain string."""
    s, P = _params(start, m, value_per_kwh_year, electronics_per_kwh, fade_cv, loss, years, eol_frac, duty, fade_mean, rate, balancer_r, balancer_per_kwh, ks, dod_exp, knee_share, start_soh, balancer_eta,
                   closed_loss, test_sigma, sort_cost_per_kwh, trials, steps, window, exempt, adaptive, z, weak_corr=weak_corr)
    res = _scan(s, m, seed=seed, **P)
    n_balancer = f"balancer {format(balancer_r, '.0%')}" if balancer_r <= 1e6 else "balancer unlimited"
    verdict, build, rival, margin, why = _decide(res, n_balancer, trials, z, min_margin)
    net = np.asarray(res[build]["net"]) if build != "plain" else np.zeros(trials)
    return {"build": build, "kind": "ours" if verdict == "BUY" else "rival", "verdict": verdict, "mean_gain": float(net.mean()), "p10_gain": float(np.percentile(net, 10)), "margin_vs_rival": margin,
            "rival": rival, "why": why, "table": res}


def robust_guarded(start, m, *, seeds=(5, 11), z=1.0, life_years=30.0, min_margin=1.0, **kw):
    """The customer-view verdict. Pick on seeds[0] with `guarded_recommend`; if it picks one of our builds, re-score that build against the same rival on an independent seed (twice the trials) and
    fall back to the rival unless it still wins there by at least min_margin (default 1 per kWh: a smaller edge is inside what the model can resolve and is not worth the extra hardware). Gains and the pessimistic case (p10) come from the fresh seed. Also returns the 30-year lives of plain and of the recommended build.
    Returns dict(verdict BUY|BALANCER|HOLD, build, mean_gain, p10_gain, balancer_gain, margin_vs_rival, reasons, warnings, life_plain, life_ours, table). All gains per kWh nameplate vs a plain string."""
    kw = dict(kw)
    kw.setdefault("trials", 16)
    kw["trials"] = max(int(kw["trials"]), 16)
    g = guarded_recommend(start, m, seed=seeds[0], z=z, min_margin=min_margin, **kw)
    kw2 = dict(kw, trials=2 * kw["trials"])
    s, P = _params(start, m, kw2.pop("value_per_kwh_year"), kw2.pop("electronics_per_kwh"), kw2.pop("fade_cv"), kw2.pop("loss", 0.02), kw2.pop("years", 12.0), kw2.pop("eol_frac", 0.7), kw2.pop("duty", 0.7),
                   kw2.pop("fade_mean", 0.02), kw2.pop("rate", 0.07), kw2.pop("balancer_r", 0.05), kw2.pop("balancer_per_kwh", 4.0), kw2.pop("ks", (1, 2, 4, 8, 16, 25)), kw2.pop("dod_exp", 0.87),
                   kw2.pop("knee_share", 0.65), kw2.pop("start_soh", 1.0), kw2.pop("balancer_eta", 0.9), kw2.pop("closed_loss", 0.0), kw2.pop("test_sigma", 0.02), kw2.pop("sort_cost_per_kwh", 0.0),
                   kw2.pop("trials"), kw2.pop("steps", 40), kw2.pop("window", None), kw2.pop("exempt", True), kw2.pop("adaptive", True), z, weak_corr=kw2.pop("weak_corr", 0.0))
    fresh = _scan(s, m, seed=seeds[1], **P)
    n_balancer = f"balancer {format(P['balancer_r'], '.0%')}"
    trials = P["trials"]
    bal = np.asarray(fresh[n_balancer]["net"])
    reasons = [g["why"]]
    verdict, build = g["verdict"], g["build"]
    if verdict == "BUY":
        rival = bal if g["rival"] != "plain" else np.zeros(trials)
        d = np.asarray(fresh[build]["net"]) - rival
        if d.mean() < min_margin:
            verdict, build = ("BALANCER", n_balancer) if (g["rival"] != "plain" and bal.mean() > 0.0) else ("HOLD", "plain")
            reasons = [f"the pick did not hold up on a fresh seed, so we fall back to {build}"]
        else:
            reasons = [f"{build} beats {g['rival']} by {d.mean():.1f} per kWh on a fresh seed too"]
    net = np.asarray(fresh[build]["net"]) if build != "plain" else np.zeros(trials)
    life = _scan(s, m, seed=9, **dict(P, years=float(life_years), trials=8)) if life_years else None
    return dict(verdict=verdict, build=build, mean_gain=float(net.mean()), p10_gain=float(np.percentile(net, 10)), balancer_gain=float(bal.mean()), margin_vs_rival=float((np.asarray(fresh[build]["net"]) - (bal if g["rival"] != "plain" else 0.0)).mean()) if verdict == "BUY" else 0.0,
                rival=g["rival"], reasons=reasons, warnings=[], life_plain=float(life["plain"]["years"]) if life else 0.0, life_ours=float(life[build]["years"]) if life else 0.0, table=fresh)
