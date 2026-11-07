import numpy as np
import pytest
from hackkit import reon_grid as GR
from hackkit import reon_enviro as EN
from hackkit import reon_visuals as VZ


def pool():
    rng = np.random.default_rng(1)
    return np.exp(0.04 * rng.standard_normal(500))


def test_make_string_deterministic_with_planted_cells():
    h = GR.make_string(pool())
    assert h.size == 250 and abs(h.mean() - 0.85) < 0.03 and h.min() <= 0.70 + 1e-9
    assert np.array_equal(h, GR.make_string(pool()))


def test_voltage_floor_and_refusal():
    h = GR.make_string(pool())
    a = GR.analyse(h, [], 0.9)
    assert a["K"] == 25 and a["room"] == 25 and a["online"] and a["ours_kwh"] > a["plain_kwh"] > 0
    assert GR.analyse(h, list(range(25)), 0.9)["online"] and GR.analyse(h, list(range(25)), 0.9)["room"] == 0
    r = GR.analyse(h, list(range(26)), 0.9)
    assert r["refused"] and r["ours_kwh"] == 0.0 and "Cannot bypass" in r["message"]


def test_open_cell_kills_plain_not_managed():
    h = GR.make_string(pool())
    a = GR.analyse(h, [7], 0.9)
    assert a["plain_kwh"] == 0.0 and a["ours_kwh"] > 0.8 * GR.analyse(h, [], 0.9)["ours_kwh"]


def test_window_one_means_no_gain_and_bad_input():
    h = GR.make_string(pool())
    a = GR.analyse(h, [], 1.0, loss=0.0)
    assert a["K"] == 0 and a["ours_kwh"] == pytest.approx(a["plain_kwh"])
    with pytest.raises(Exception):
        GR.analyse(h, [999], 0.9)
    with pytest.raises(Exception):
        GR.analyse(h, [], 1.5)


def test_charts_build_and_material():
    h = GR.make_string(pool())
    a = GR.analyse(h, [3], 0.9)
    VZ.grid_chart(h, [3], a["early"]).to_dict()
    VZ.voltage_chart(a["v_now"], 0.9).to_dict()
    VZ.policies_chart(7.9, 8.4, 16.8).to_dict()
    assert EN.material_kg(59.0) == pytest.approx(590.0)
    assert EN.environmental(60.0, 10.0, 24.0, 20.0)["material_kg"] > 0
