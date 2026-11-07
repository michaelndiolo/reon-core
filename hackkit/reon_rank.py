"""Which cell is hurting: rule -> money -> rank (pattern: Zeinloop). Marginal value of bypassing each cell of a plain string, in dollars per year, plus what the response layer would do."""
import numpy as np
from hackkit.reon_guard import caps_array, need
from hackkit import reon_response as R


def rank_cells(caps, nameplate_kwh, value_per_kwh_year, loss=0.02, v=3.2, t=25.0, soc=0.5):
    c = caps_array(caps, "caps", positive=True, min_len=3)
    need(nameplate_kwh > 0 and value_per_kwh_year >= 0 and 0 <= loss < 1, "rank: nameplate > 0, value >= 0, 0 <= loss < 1")
    n = len(c)
    full = c.mean()                      # one cell's share of nameplate = nameplate / n at the string's mean capacity
    plain = n * c.min()
    rows = []
    for j in range(n):
        rest = np.delete(c, j)
        gain_units = (n - 1) * rest.min() * (1 - loss) - plain      # bypass j: n-1 cells, limited by the next weakest, minus switch loss
        kwh = nameplate_kwh * gain_units / (n * full)               # usable kWh per cycle gained
        rows.append(dict(cell=j, capacity_rel=float(c[j] / np.median(c)), bypass_gain_kwh=float(kwh), dollars_per_year=float(kwh * value_per_kwh_year)))
    lim = R.Limits()   # a capacity table is a slow measurement: a cell already under the weak line counts as persistent
    cells = [R.Cell(i=j, v=v, t=t, soc=soc, cap_rel=r["capacity_rel"], r_rel=1.0, dT_dt=0.0, bad_cycles=lim.persist_cycles if r["capacity_rel"] < 1 - lim.weak_frac else 0) for j, r in enumerate(rows)]
    acts = R.decide(cells, R.Context())
    verdict = {i: a for a in acts[::-1] for i in a.cells}   # strongest action wins
    for r in rows:
        a = verdict.get(r["cell"])
        r["response"] = a.kind if a else R.NORMAL
        r["reason"] = a.reason if a else "inside limits"
    return sorted(rows, key=lambda r: -r["dollars_per_year"])
