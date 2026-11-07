import numpy as np
import pytest

from hackkit import reon_granularity as G
from hackkit import reon_loss as L


def test_ends_of_the_scale_and_hand_case():
    c = [100, 90, 80, 70]
    assert G.group_usable(c, 1) == sum(c) == 340
    assert G.group_usable(c, 4) == 4 * 70
    assert G.group_usable(c, 2) == 2 * 90 + 2 * 70  # groups (100,90) and (80,70)
    assert G.group_usable([70, 100, 80, 90], 2, "sorted") == 2 * 90 + 2 * 70


def test_nested_groupings_never_gain_from_bigger_groups():
    rng = np.random.default_rng(3)
    c = 80 + 20 * rng.random(24)
    vals = [G.group_usable(c, k) for k in (1, 2, 4, 8, 24)]  # each divides the next
    assert all(a >= b - 1e-9 for a, b in zip(vals, vals[1:]))


def test_cell_level_row_matches_reon_loss():
    c = [93.8, 92.6, 84.3, 92.4, 91.5, 92.8]
    rows = G.granularity_table(c, electronics_per_kwh_cell_level=8.8, loss_cell_level=0.02, value_per_kwh_year=22, rate=0.07, years=7, ks=[1])
    assert rows[0]["gain_net"] == pytest.approx(L.net_gain(c, 0.98))


def test_coarser_groups_cost_less_and_can_win_where_cell_level_loses():
    m1 = [93.8, 92.6, 93.8, 91.9, 84.3, 92.4, 93.4, 91.5, 92.8, 92.5, 94.2, 93.4]
    m2 = [91.6, 88.1, 87.6, 88.5, 88.6, 90.3, 88.4, 88.3, 90.1, 90.2, 89.2, 88.6]
    m3 = [91.0, 89.2, 88.9, 89.2, 88.6, 89.1, 89.5, 90.8, 90.1, 89.7, 89.8, 90.2]
    rows = G.granularity_table(m1 + m2 + m3, electronics_per_kwh_cell_level=8.8, loss_cell_level=0.02, value_per_kwh_year=22, rate=0.07, years=7)
    by = {r["k"]: r for r in rows}
    assert by[12]["gain_ideal"] == pytest.approx((3126.0) / (36 * 84.3) - 1.0)
    assert by[12]["electronics_per_kwh"] == pytest.approx(8.8 / 12)
    assert not by[1]["repays"] and by[12]["net_value_per_nameplate_kwh_year"] > by[1]["net_value_per_nameplate_kwh_year"]
    assert G.best_granularity(rows) is not None
    # fixed-loss assumption (p = 0) must not flip the ordering silently: report it, the row exists and is finite
    fixed = G.granularity_table(m1 + m2 + m3, electronics_per_kwh_cell_level=8.8, loss_cell_level=0.02, value_per_kwh_year=22, rate=0.07, years=7, loss_exponent=0.0)
    assert all(np.isfinite(r["net_value_per_nameplate_kwh_year"]) for r in fixed)


def test_bad_inputs():
    with pytest.raises(ValueError):
        G.group_usable([1, 2, 3], 2)
    with pytest.raises(ValueError):
        G.group_usable([1, 2, 3, 4], 2, "nope")


def test_cost_exponent_zero_means_no_saving_from_coarser_groups():
    c = [93.8, 92.6, 93.8, 91.9, 84.3, 92.4, 93.4, 91.5]
    rows = G.granularity_table(c, electronics_per_kwh_cell_level=8.8, loss_cell_level=0.02, value_per_kwh_year=22, rate=0.07, years=7, cost_exponent=0.0)
    assert all(r["electronics_per_kwh"] == pytest.approx(8.8) for r in rows)
