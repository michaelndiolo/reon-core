"""Origin-dependent embodied carbon and flip points, against hand cases and the printed table of the IVL 2017 report (Table 17)."""
import pytest

from hackkit import reon_carbon as C
from hackkit.atstake import Lever

# CITED: IVL / Energimyndigheten c243 (2017), Table 17: grid g CO2e/kWh -> share of Ellingsen's 172 kg/kWh total
GRID = {"Sweden": 50, "Brazil": 300, "USA": 700, "China": 1000, "Poland": 1050, "India": 1400}
TABLE17_PERCENT_OF_172 = {"Sweden": 42, "Brazil": 65, "USA": 103, "China": 130, "Poland": 136, "India": 170}
# non-electric part = 37.7% cell material x 172 kg = 65 kg (Table 16 share); electricity 160 kWh per kWh of battery ~ 586 MJ / 3.6 = 163 kWh (text), rounded
NON_ELECTRIC, EL_PER_KWH = 65.0, 160.0


def test_hand_cases():
    assert C.embodied_at(1000, 65, 160) == pytest.approx(225.0)
    assert C.embodied_at(0, 65, 160) == pytest.approx(65.0)
    with pytest.raises(ValueError):
        C.embodied_at(-1, 65, 160)


def test_structure_reproduces_table_17():
    for region, pct in TABLE17_PERCENT_OF_172.items():
        got = C.embodied_at(GRID[region], NON_ELECTRIC, EL_PER_KWH) / 172.0 * 100
        assert got == pytest.approx(pct, abs=2.5), region          # the printed percentages are rounded and not exactly proportional


def test_mix_and_lever():
    r = C.embodied_by_origin({"China": 0.5, "USA": 0.3, "Sweden": 0.2}, GRID, 65, 160)
    assert r["by_region"]["China"] == pytest.approx(225.0)
    assert r["mix"] == pytest.approx(0.5 * 225 + 0.3 * (65 + 160 * 0.7) + 0.2 * (65 + 160 * 0.05))
    assert r["cleanest"] == pytest.approx(65 + 160 * 0.05) and r["dirtiest"] == pytest.approx(225.0)
    lev = C.origin_lever({"China": 0.5, "USA": 0.5}, GRID, 65, 160, source="ASSUMED")
    assert lev.name == C.EMBODIED and lev.low <= lev.base <= lev.high and lev.source == "ASSUMED"
    for bad in ({"China": 0.6, "USA": 0.6}, {"China": 1.0, "Mars": 0.0}, {}):
        with pytest.raises(ValueError):
            C.embodied_by_origin(bad, GRID, 65, 160)


def _levers(extra=100.0, displaced=0.5, embodied=80.0, control=800.0, grid=0.0, years=7.0):
    return [Lever(C.EMBODIED, embodied, 60.0, 110.0), Lever(C.EXTRA_KWH, extra, 20.0, 300.0), Lever(C.DISPLACED, displaced, 0.0, 1.0),
            Lever(C.CONTROL_EMBODIED, control, 200.0, 2000.0), Lever(C.GRID_SAVED, grid, 0.0, 0.2), Lever(C.YEARS, years, 3.0, 10.0)]


def test_flip_points_by_hand():
    lv = _levers()                                                      # net = 100*0.5*80/1000 - 0.8 = 3.2
    assert C.flip_point(lv, C.EMBODIED)["net_at_base"] == pytest.approx(3.2)
    assert C.flip_point(lv, C.EMBODIED)["flip_value"] == pytest.approx(16.0)       # 100*0.5*E/1000 = 0.8
    assert C.flip_point(lv, C.EMBODIED)["inside_range"] is False                   # 16 is below the 60-110 range
    assert C.flip_point(lv, C.DISPLACED)["flip_value"] == pytest.approx(0.1)       # 100*d*80/1000 = 0.8
    assert C.flip_point(lv, C.DISPLACED)["inside_range"] is True
    assert C.flip_point(lv, C.CONTROL_EMBODIED)["flip_value"] == pytest.approx(4000.0)
    assert C.flip_point(lv, C.YEARS)["flip_value"] is None                         # no grid effect, so years do not matter
    assert C.flip_point(_levers(grid=-0.0), C.GRID_SAVED)["flip_value"] is not None     # with a grid effect possible, the flip value exists
    t = C.flip_table(lv)
    assert t.iloc[0]["inside_range"] and len(t) == 6


def test_flip_point_is_a_true_zero():
    lv = _levers(grid=0.05)
    for l in lv:
        fp = C.flip_point(lv, l.name)
        if fp["flip_value"] is None or not (l.name != C.DISPLACED or 0 <= fp["flip_value"] <= 1) or fp["flip_value"] < 0:
            continue
        vals = {x.name: x.base for x in lv}
        vals[l.name] = fp["flip_value"]
        assert C.carbon_balance(vals)["net_t"] == pytest.approx(0.0, abs=1e-9), l.name
