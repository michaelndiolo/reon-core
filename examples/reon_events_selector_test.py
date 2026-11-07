"""Does choosing the policy per site (choose_policy, bridge variants included, threshold rivals pay the same switch loss) beat always using one policy?
Choice made on seeds 0..7 and 100..107, scored on a THIRD set (500..507), over hostile draws. Regret = net lost vs the best policy in hindsight on the scoring seeds."""
import numpy as np
from multiprocessing import Pool
from hackkit import reon_events as E
from examples.reon_events_adversary import draw
N = 300
THR = ("thr0.90", "thr0.85", "thr0.80")

def one(i):
    kw = draw(np.random.default_rng(7000 + i))
    ch = E.choose_policy(E.EXTENDED, **kw)
    net = {p: float(np.mean([E.simulate(p, s, **kw)["net"] for s in range(500, 508)])) for p in E.EXTENDED}
    o = max(net.values())
    return dict(sel=o - net[ch["policy"]], oursc=o - net["ours+crew"], ours=o - net["ours"], thr=o - max(net[t] for t in THR), rep=o - net["replace"], auto=ch["auto_wins"], pick=ch["policy"])

if __name__ == "__main__":
    with Pool(4) as p:
        r = p.map(one, range(N))
    print(f"{N} hostile site draws; regret per kWh nameplate vs best policy in hindsight on unseen seeds (lower is better)")
    for k, name in (("sel", "per-site chooser"), ("oursc", "always ours+crew"), ("ours", "always ours"), ("thr", "best fixed threshold"), ("rep", "always replace")):
        v = np.array([x[k] for x in r]); print(f"  {name:22s} mean {v.mean():6.1f}  p90 {np.percentile(v,90):6.1f}  worst {v.max():6.1f}")
    print(f"chooser picked automatic bypass at {sum(x['auto'] for x in r)}/{N} sites;", {n: sum(x['pick'] == n for x in r) for n in sorted(set(x['pick'] for x in r))})
