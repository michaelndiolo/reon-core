"""reon_carbon: the balance, hotspots and sensitivity are checked against numbers worked out by hand."""
import pytest

from hackkit import reon_carbon as C
from hackkit.atstake import Lever


def base_values():
    return {C.EMBODIED: 80.0, C.EXTRA_KWH: 60.0, C.DISPLACED: 1.0, C.CONTROL_EMBODIED: 200.0, C.GRID_SAVED: 0.1, C.YEARS: 10.0}


def levers():
    return [Lever(C.EMBODIED, 80.0, 60.0, 100.0, "CITED", "kg/kWh"),
            Lever(C.EXTRA_KWH, 60.0, 50.0, 70.0, "ASSUMED", "kWh"),
            Lever(C.DISPLACED, 1.0, 0.5, 1.0, "ASSUMED"),
            Lever(C.CONTROL_EMBODIED, 200.0, 100.0, 400.0, "ASSUMED", "kg"),
            Lever(C.GRID_SAVED, 0.1, 0.0, 0.2, "ASSUMED", "t/yr"),
            Lever(C.YEARS, 10.0, 5.0, 15.0, "ASSUMED", "yr")]


def test_balance_by_hand():
    b = C.carbon_balance(base_values())
    assert b["items"]["Avoided new-battery manufacturing"] == pytest.approx(4.8)     # 60 kWh x 1.0 x 80 kg / 1000
    assert b["items"]["Control electronics (cost)"] == pytest.approx(-0.2)           # 200 kg
    assert b["items"]["Cleaner operation"] == pytest.approx(1.0)                     # 0.1 t/yr x 10 yr
    assert b["net_t"] == pytest.approx(5.6)


def test_balance_refuses_bad_or_missing_inputs():
    v = base_values()
    del v[C.YEARS]
    with pytest.raises(ValueError):
        C.carbon_balance(v)
    v = base_values(); v[C.DISPLACED] = 1.2
    with pytest.raises(ValueError):
        C.carbon_balance(v)
    v = base_values(); v[C.EMBODIED] = -1.0
    with pytest.raises(ValueError):
        C.carbon_balance(v)


def test_nobody_buys_new_means_no_manufacturing_credit():
    v = base_values(); v[C.DISPLACED] = 0.0
    assert C.carbon_balance(v)["items"]["Avoided new-battery manufacturing"] == 0.0
    assert C.carbon_balance(v)["net_t"] == pytest.approx(0.8)                        # only operation minus electronics: 1.0 - 0.2


def test_hotspots_order_and_shares():
    h = C.hotspots(base_values())
    assert h.iloc[0]["line"] == "Avoided new-battery manufacturing"
    assert h["share_of_absolute_total"].sum() == pytest.approx(1.0)
    assert h.iloc[0]["share_of_absolute_total"] == pytest.approx(4.8 / (4.8 + 0.2 + 1.0))


def test_sensitivity_by_hand():
    s = C.sensitivity(levers())
    assert s["base_net_t"] == pytest.approx(5.6)
    row = s["table"].set_index("input").loc[C.EMBODIED]
    assert row["net_at_low"] == pytest.approx(4.4) and row["net_at_high"] == pytest.approx(6.8)     # 3.6 and 6.0 avoided, +0.8
    assert row["swing"] == pytest.approx(2.4) and row["source"] == "CITED"
    # lowest corner: 60 kg/kWh, 50 kWh, 0.5 displaced, 400 kg electronics, 0 t/yr -> 0.75 - 0.4 = 0.35 ... but years 5 does not matter then
    # highest corner: 100 kg/kWh, 70 kWh, 1.0, 100 kg, 0.2 t/yr, 15 yr -> 7.0 - 0.1 + 3.0 = 9.9
    assert s["max_net_t"] == pytest.approx(9.9)
    assert s["min_net_t"] == pytest.approx(0.5 * 50 * 60 / 1000 - 0.4)                              # 1.5 - 0.4 = 1.1
    assert s["sign_can_flip"] is False
    assert C.EMBODIED not in s["assumed_inputs"] and C.EXTRA_KWH in s["assumed_inputs"]


def test_sign_can_flip_when_ranges_allow_it():
    L = levers()
    L[2] = Lever(C.DISPLACED, 0.2, 0.0, 0.5, "ASSUMED")                  # almost nobody would have bought new
    L[3] = Lever(C.CONTROL_EMBODIED, 200.0, 100.0, 2000.0, "ASSUMED", "kg")
    L[4] = Lever(C.GRID_SAVED, 0.0, 0.0, 0.0, "ASSUMED", "t/yr")
    s = C.sensitivity(L)
    assert s["min_net_t"] < 0 and s["sign_can_flip"] is True


def test_sensitivity_needs_one_lever_per_input():
    with pytest.raises(ValueError):
        C.sensitivity(levers()[:-1])
