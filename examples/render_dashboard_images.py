"""Render the dashboard charts to PNG for the written submission (docs/img). Needs: pip install vl-convert-python. Run: PYTHONPATH=. python examples/render_dashboard_images.py"""
import csv
import numpy as np
import vl_convert as vlc
from hackkit import reon_grid as GR, reon_storefront as SF, reon_visuals as V

rows = list(csv.reader(l for l in open("examples/data/nature_fig4_cells.csv") if not l.startswith("#") and not l.startswith('"#')))[1:]
car = {}
for p, _, _, late in rows:
    car.setdefault(p, []).append(float(late))
packs = {k: np.array(v) for k, v in car.items()}
h = GR.make_string(GR.pooled_relative(packs))
failed = [12, 87, 190]
a = GR.analyse(h, failed, 0.9)


def png(chart, name, w=720):
    open(f"docs/img/{name}.png", "wb").write(vlc.vegalite_to_png(chart.properties(width=w).to_dict(), scale=2))


png(V.grid_chart(h, failed, a["early"]), "string_grid")
png(V.voltage_chart(a["v_now"], 0.9), "string_voltage")
png(V.policies_chart(*SF.backup_policies(packs, 60.0, 5.0)), "three_policies")
from hackkit import reon_slope as SLP
tp = SLP.load_cells()
pk = sorted(tp)[0]
e_, l_ = tp[pk]
fl_, lm_, _ = SLP.outliers(SLP.fade_pp(e_, l_))
wl_ = int(np.argmin(l_))
png(V.slope_lines_chart(e_, l_, fl_, wl_), "slope_lines", 560)
png(V.position_chart(e_, l_, fl_, wl_, lm_), "slope_position", 760)
png(V.gain_fade_chart(SF.gain_vs_fade(40)), "gain_vs_fade", 560)
print("wrote docs/img/*.png")
