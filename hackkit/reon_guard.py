"""Input guards: bad inputs must stop with a clear ValueError, never turn into silent NaN or infinity on a dashboard. Also `safe_recommend`, the engine call with every input checked first."""
import numpy as np


def need(cond, msg):
    if not cond:
        raise ValueError(msg)


def caps_array(caps, name="caps", positive=False, min_len=1):
    c = np.asarray(caps, dtype=float)
    need(c.ndim == 1 and len(c) >= min_len, f"{name}: need a 1-D list of at least {min_len} cell capacities")
    need(bool(np.all(np.isfinite(c))), f"{name}: contains NaN or infinity (bad sensor reading?)")
    need(bool(np.all(c > 0)) if positive else bool(np.all(c >= 0)), f"{name}: capacities must be {'above' if positive else 'at least'} zero")
    return c


def safe_recommend(start, m, *, value_per_kwh_year, electronics_per_kwh, fade_cv, loss=0.02, years=12.0, eol_frac=0.7, duty=0.7, fade_mean=0.02, rate=0.07, balancer_r=0.05, balancer_per_kwh=4.0,
                   ks=(1, 2, 3, 4), dod_exp=0.87, knee_share=0.65, start_soh=1.0, balancer_eta=0.9, closed_loss=0.0, test_sigma=0.02, sort_cost_per_kwh=0.0, trials=14, steps=40, seed=5):
    """reon_wear.recommend_build with every input validated. Returns (result, warnings)."""
    from hackkit import reon_wear as W
    s = caps_array(start, "start", positive=True, min_len=2)
    need(isinstance(m, (int, np.integer)) and 2 <= m <= len(s) and len(s) % m == 0, "m: cells per string must divide the number of cells")
    need(value_per_kwh_year >= 0, "value per kWh-year must be zero or more")
    need(electronics_per_kwh >= 0, "switch cost must be zero or more")
    need(0.0 <= fade_cv <= 2.0, "fade spread (CV) must be between 0 and 2")
    need(0.0 <= loss < 0.5, "usable-energy loss must be between 0 and 0.5")
    need(0.5 <= years <= 40, "years must be between 0.5 and 40")
    need(0.05 <= eol_frac < 1.0, "retirement level must be between 0.05 and 1")
    need(0.05 <= duty <= 1.0, "duty must be between 0.05 and 1")
    need(0.0 <= fade_mean <= 0.5, "mean fade per year must be between 0 and 0.5")
    need(0.0 <= rate <= 0.5, "discount rate must be between 0 and 0.5")
    need(trials >= 2 and steps >= 4, "trials >= 2 and steps >= 4")
    warn = []
    ks = tuple(k for k in ks if 0 < k < m)
    if not ks:
        warn.append("no valid selective-bypass counts for this string length; only whole-string builds are compared")
    if electronics_per_kwh > 60:
        warn.append("switch cost above 60 per kWh is far outside REON's stated 7 to 24 range")
    if value_per_kwh_year == 0:
        warn.append("zero value: no build can be worth buying")
    out = W.recommend_build(s, int(m), balancer_r=balancer_r, balancer_per_kwh=balancer_per_kwh, ks=ks, fade_mean=fade_mean, fade_cv=fade_cv, loss=loss, electronics_per_kwh=electronics_per_kwh,
                            sort_cost_per_kwh=sort_cost_per_kwh, value_per_kwh_year=value_per_kwh_year, rate=rate, years=years, eol_frac=eol_frac, duty=duty, dod_exp=dod_exp, knee_share=knee_share,
                            start_soh=start_soh, balancer_eta=balancer_eta, closed_loss=closed_loss, test_sigma=test_sigma, trials=trials, steps=steps, seed=seed)
    return out, warn


def robust_recommend(start, m, *, seeds=(5, 11), **kw):
    """Pick the build on one seed, score it on an independent seed (avoids the winner's curse), and only say BUY when
    the pick still beats plain on the fresh seed AND its pessimistic case (p10) is not worse than plain's.
    Returns dict(verdict BUY|HOLD|PLAIN, build, mean_gain, p10_gain, reasons, warnings)."""
    pick, w1 = safe_recommend(start, m, seed=seeds[0], **kw)
    chk, _ = safe_recommend(start, m, seed=seeds[1], **kw)
    name = pick["ours_best"]
    t = chk["table"]
    why = []
    if name == "plain":
        return dict(verdict="PLAIN", build=name, mean_gain=0.0, p10_gain=0.0, reasons=["plain string is already the best build here"], warnings=w1)
    gain = t[name]["mean"] - t["plain"]["mean"]
    p10 = t[name]["p10"] - t["plain"]["p10"]
    if gain <= 0:
        why.append("the pick does not beat plain on a fresh seed")
    if p10 < 0:
        why.append("its pessimistic case (p10) is worse than plain's")
    if t[name]["years"] < t["plain"]["years"] - 1e-9:
        why.append("it retires earlier than plain")
    return dict(verdict="HOLD" if why else "BUY", build=name, mean_gain=float(gain), p10_gain=float(p10), reasons=why or ["beats plain on an independent seed, pessimistic case too"], warnings=w1)
