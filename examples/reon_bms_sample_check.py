"""First look at any per-cell BMS sample REON gives us. Usage: python reon_bms_sample_check.py sample.csv [--vmax 3.65 --vmin 2.0]
Needed columns (names are matched loosely, case-insensitive): time (seconds or a timestamp), cell (an id), voltage, current (positive = charging; flip with --flip).
Optional: string, temp_body, temp_terminal, capacity (Ah or relative). Whatever is missing is skipped, nothing is invented.
Prints, in plain words: (1) which cell hits the top first when charging and the bottom first when discharging (the limiting cells), (2) how far apart cells are at the end of charge and discharge,
(3) cells that sit away from their peers (relative, not absolute, the 'curve and left-right trend' idea), (4) terminal minus body temperature per cell (connection health), (5) trends over time.
Raw data stay on your computer. Do not commit a sample to git: it is REON's and was shared for testing."""
import sys, argparse
import numpy as np
import pandas as pd

ALIASES = dict(time=("time", "t", "timestamp", "datetime", "ts"), cell=("cell", "cell_id", "cellid", "id", "cell_no"), voltage=("voltage", "v", "cell_voltage", "volt", "vcell"), current=("current", "i", "amps", "a", "string_current"),
               string=("string", "string_id", "stringid", "pack"), temp_body=("temp_body", "t_body", "body_temp", "temperature_body", "temp", "temperature"), temp_terminal=("temp_terminal", "t_terminal", "terminal_temp", "temperature_terminal"),
               capacity=("capacity", "cap", "soh", "capacity_ah", "ah"))

def pick(df):
    low = {c.lower().strip(): c for c in df.columns}
    out = {}
    for k, names in ALIASES.items():
        for n in names:
            if n in low:
                out[k] = low[n]; break
    return out

def robust_z(x):
    m = np.nanmedian(x); s = 1.4826 * np.nanmedian(np.abs(x - m))
    return (x - m) / (s if s > 1e-12 else np.nan)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("path"); ap.add_argument("--vmax", type=float, default=None); ap.add_argument("--vmin", type=float, default=None); ap.add_argument("--flip", action="store_true")
    a = ap.parse_args()
    df = pd.read_csv(a.path); col = pick(df)
    need = [k for k in ("time", "cell", "voltage") if k not in col]
    if need:
        sys.exit(f"missing columns {need}; found {list(df.columns)}")
    d = pd.DataFrame({k: df[v] for k, v in col.items()})
    d["time"] = pd.to_datetime(d["time"], errors="coerce").astype("int64") / 1e9 if not np.issubdtype(d["time"].dtype, np.number) else d["time"].astype(float)
    d = d.dropna(subset=["time", "cell", "voltage"]).sort_values("time")
    print(f"{len(d)} rows, {d['cell'].nunique()} cells, {d['time'].max()-d['time'].min():.0f} s span; columns used: {sorted(col)}")
    wide = d.pivot_table(index="time", columns="cell", values="voltage", aggfunc="mean")
    wide = wide.dropna(thresh=max(2, int(0.8 * wide.shape[1])))
    cells = list(wide.columns)
    # peers: deviation from the median of the other cells at each timestamp
    dev = wide.sub(wide.median(axis=1), axis=0)
    print("\n(3) Cells away from their peers (voltage minus string median, millivolts), worst first. Persistent and one-sided is what matters, not the size of one point.")
    s = pd.DataFrame({"mean_mV": 1000 * dev.mean(), "p95_abs_mV": 1000 * dev.abs().quantile(0.95), "share_below_-20mV": (dev < -0.02).mean()})
    s["z"] = robust_z(s["mean_mV"].values)
    print(s.reindex(s["z"].abs().sort_values(ascending=False).index).head(8).round(2).to_string())
    if "current" in col:
        cur = d.groupby("time")["current"].mean().reindex(wide.index)
        cur = cur * (-1 if a.flip else 1)
        sign = np.sign(cur.where(cur.abs() > 0.05 * cur.abs().quantile(0.9), 0)).replace(0, np.nan).ffill()
        seg = (sign != sign.shift()).cumsum()
        tops, bots, gaps_t, gaps_b = [], [], [], []
        for _, idx in seg.groupby(seg).groups.items():
            w = wide.loc[idx]
            if len(w) < 5:
                continue
            last = w.iloc[-3:].mean()
            if sign.loc[idx[0]] > 0:
                tops.append(last.idxmax()); gaps_t.append(last.max() - last.median())
            else:
                bots.append(last.idxmin()); gaps_b.append(last.median() - last.min())
        print(f"\n(1) Limiting cells: {len(tops)} charge segments, {len(bots)} discharge segments")
        if tops:
            print("  cell that reaches the TOP first when charging (fills first):", pd.Series(tops).value_counts().head(4).to_dict(), f"| mean gap to median at end of charge {1000*np.mean(gaps_t):.0f} mV")
        if bots:
            print("  cell that reaches the BOTTOM first when discharging (empties first, ends the cycle):", pd.Series(bots).value_counts().head(4).to_dict(), f"| mean gap to median at end of discharge {1000*np.mean(gaps_b):.0f} mV")
        print("  A cell that wins this race every cycle is persistent: that is the bypass candidate. If the winner changes, the spread is noise.")
        if tops and bots:
            tw, bw = pd.Series(tops).mode().iloc[0], pd.Series(bots).mode().iloc[0]
            print(f"  Same cell wins both ends ({tw}): it simply has the smallest capacity, which is what per-cell switching fixes." if tw == bw else f"  Different cells win the top ({tw}) and the bottom ({bw}): the cells start the cycle at different charge levels (imbalance), which balancing addresses; per-cell switching also fixes the capacity part.")
        if len(bots) >= 6:
            h = len(bots) // 2; e = pd.Series(gaps_b[:h]).mean(); l = pd.Series(gaps_b[h:]).mean()
            print(f"  end-of-discharge gap, first half {1000*e:.0f} mV, second half {1000*l:.0f} mV ({'growing' if l > 1.2 * e else 'stable or shrinking'})")
    else:
        print("\n(1) skipped: no current column")
    if "temp_terminal" in col and "temp_body" in col:
        dt = (d["temp_terminal"] - d["temp_body"]).groupby(d["cell"]).agg(["median", lambda x: x.quantile(0.95)]); dt.columns = ["median_terminal_minus_body_C", "p95"]
        dt["z"] = robust_z(dt["median_terminal_minus_body_C"].values)
        print("\n(4) Terminal minus body temperature (a warm terminal means a resistive connection, a different fault from an aged cell), most unusual first:")
        print(dt.reindex(dt["z"].abs().sort_values(ascending=False).index).head(6).round(2).to_string())
    elif "temp_body" in col:
        tb = d.groupby("cell")["temp_body"].median(); print("\n(4) Body temperature by cell, hottest first (terminal temperature not given):"); print(tb.sort_values(ascending=False).head(5).round(2).to_string())
    if "capacity" in col:
        cp = d.groupby("cell")["capacity"].median(); rel = cp / cp.median()
        print(f"\n(5) Capacity column: relative to median, spread CV {rel.std()/rel.mean():.3f}, worst cell {rel.min():.2f}, cells under 0.85: {int((rel<0.85).sum())} of {len(rel)}")
    t = wide.index.values; days = (t - t[0]) / 86400.0
    if days[-1] > 1.0:
        sl = {c: np.polyfit(days, dev[c].values, 1)[0] * 1000 for c in cells}
        sl = pd.Series(sl); print(f"\n(5) Drift of each cell against its peers, mV per day (negative = falling behind). Biggest movers: {sl.reindex(sl.abs().sort_values(ascending=False).index).head(4).round(3).to_dict()}")
    print("\nWhat to write back to the team: the persistent limiting cells, the size of the end-of-charge and end-of-discharge gaps, any terminal-temperature outlier, and any cell whose drift is far from the others.")

if __name__ == "__main__":
    main()
