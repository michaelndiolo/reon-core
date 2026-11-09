"""Close the HOLD regime (cheap crew visits, high switch loss). Over hostile site draws where the per-site chooser picks replace-on-failure or a threshold instead of automatic bypass:
 1. break-even switch loss and break-even switch cost: the targets REON would have to meet for automatic bypass to pay at that site
 2. how many such sites flip to automatic bypass if the site can shed current (slack): conduction loss share = I x R / V falls with current (physics); slack 0.3 and 0.5
 3. share of the HOLD sites that are already at plausible loss (<= 4%, 'very minimum' per REON)"""
import numpy as np
from multiprocessing import Pool
from hackkit import reon_events as E
from examples.reon_events_adversary import draw
N = 300

def one(i):
    kw = draw(np.random.default_rng(7000 + i))
    ch = E.choose_policy(E.EXTENDED, **kw)
    if ch["auto_wins"]:
        return dict(i=i, hold=False)
    rest = {k: v for k, v in kw.items()}
    r = dict(i=i, hold=True, visit=kw["visit_cost"], loss=kw["loss"], e=15.5)
    ll = {k: v for k, v in rest.items() if k != "loss"}
    r["loss_star"], r["loss_dir"] = E.break_even("loss", 0.0, 0.3, seeds=range(6), iters=10, **ll)
    ee = dict(rest)
    r["e_star"], r["e_dir"] = E.break_even("e", 0.0, 80.0, seeds=range(6), iters=10, **ee)
    for sl in (0.3, 0.5):
        c2 = E.choose_policy(E.EXTENDED, slack=sl, **kw)
        r[f"flip_slack{sl}"] = bool(c2["auto_wins"])
    return r

if __name__ == "__main__":
    with Pool(4) as p:
        rows = p.map(one, range(N))
    h = [r for r in rows if r["hold"]]
    print(f"{N} hostile site draws; chooser picked replace or a threshold at {len(h)} (HOLD sites)")
    ls = [r["loss_star"] for r in h if r["loss_star"] is not None and r["loss_dir"] == "below"]
    print(f"  automatic bypass would pay if switch loss were below a break-even at {len(ls)} of {len(h)} HOLD sites; median break-even {100*np.median(ls):.1f}% (their actual median {100*np.median([r['loss'] for r in h]):.1f}%)" if ls else "  no loss break-even")
    es = [r["e_star"] for r in h if r["e_star"] is not None and r["e_dir"] == "below"]
    print(f"  ... or if switch cost were below a break-even at {len(es)} of {len(h)}; median {np.median(es):.1f} per kWh vs the assumed 15.5 (REON range 7 to 24)" if es else "  no cost break-even")
    for sl in (0.3, 0.5):
        print(f"  shedding {int(sl*100)}% of the current by stretching discharge flips {sum(r[f'flip_slack{sl}'] for r in h)} of {len(h)} HOLD sites to automatic bypass")
    pl = [r for r in h if r["loss"] <= 0.04]
    print(f"  HOLD sites with plausible loss (<= 4%): {len(pl)} of {len(h)}; their median visit cost {np.median([r['visit'] for r in pl]):.0f}" if pl else "  no HOLD sites at plausible loss")
    never = [r for r in h if r["loss_dir"] == "never a" or r["e_dir"] == "never a"]
    print(f"  sites where no loss or cost in range makes automatic bypass pay: {len([r for r in h if r['loss_star'] is None and r['loss_dir']=='never a'])}")
