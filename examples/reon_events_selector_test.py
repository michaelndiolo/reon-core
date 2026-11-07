"""Does choosing the policy per site (choose_policy) beat always using one policy? Scored on a THIRD set of seeds over 400 hostile draws."""
import json, numpy as np
from hackkit import reon_events as E
from examples.reon_events_adversary import draw, POL
N = 240
reg = {"selector": [], "always ours+crew": [], "always ours": [], "best fixed threshold": [], "always replace": []}
wins_auto = 0
for i in range(N):
    kw = draw(np.random.default_rng(7000 + i))
    ch = E.choose_policy(POL, **kw)
    third = range(500, 508)
    net = {p: float(np.mean([E.simulate(p, s, **kw)["net"] for s in third])) for p in POL}
    oracle = max(net.values())
    reg["selector"].append(oracle - net[ch["policy"]])
    reg["always ours+crew"].append(oracle - net["ours+crew"]); reg["always ours"].append(oracle - net["ours"])
    reg["best fixed threshold"].append(oracle - max(net["thr0.90"], net["thr0.85"], net["thr0.80"])); reg["always replace"].append(oracle - net["replace"])
    wins_auto += ch["auto_wins"]
print(f"{N} hostile site draws; regret = net lost vs the best policy in hindsight on unseen seeds (per kWh nameplate, lower is better)")
for k, v in reg.items():
    v = np.array(v); print(f"  {k:24s} mean {v.mean():6.1f}  p90 {np.percentile(v,90):6.1f}  worst {v.max():6.1f}")
print(f"selector chose an automatic-bypass policy in {wins_auto}/{N} sites; chose replace or a threshold in {N-wins_auto}")
