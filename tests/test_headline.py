"""Headline numbers: each one is checked against a case worked out by hand."""
import numpy as np
import pytest

from hackkit import headline as H
from hackkit.flex import Battery, FlexProblem, solve_flex


def mkf(price, base, **kw):
    T = len(price)
    return FlexProblem(times=[f"t{i}" for i in range(T)], price=price, carbon=kw.pop("carbon", np.zeros(T)), base_load=base, solar=np.zeros(T), **kw)


def test_flex_headline_hand_calc():
    # base 1 MW, prices 10 and 100. Doing nothing clever = 110. Battery 1 MWh, perfect, starts empty: 20. Saved 90 = 81.8% of 110.
    plan = solve_flex(mkf([10.0, 100.0], [1.0, 1.0], battery=Battery(1.0, 1.0, 1.0, 1.0, soc0_frac=0.0)))
    m = {x.label: x for x in H.flex_headline(plan)}
    s = m["Saved vs doing nothing clever"]
    assert s.value == pytest.approx(90.0) and s.delta == pytest.approx(100 * 90 / 110)
    assert s.value_text == "90" and s.delta_text.startswith("+81.8%")
    pk = m["Highest import"]
    assert pk.value == pytest.approx(2.0) and pk.delta == pytest.approx(1.0)      # 2 MW while charging vs 1 MW baseline
    assert pk.lower_is_better and pk.delta_text == "+1.00 MW vs baseline"
    assert m["Battery cover"].value == pytest.approx(1.0)                          # 1 MWh x 1.0 eff / 1 MW load = 1 hour
    assert "Emissions" not in m                                                    # zero carbon series -> no emissions tile


def test_flex_headline_emissions_tile_and_no_battery():
    plan = solve_flex(mkf([10.0, 100.0], [1.0, 1.0], carbon=np.array([400.0, 400.0])))
    m = {x.label: x for x in H.flex_headline(plan)}
    assert "Battery cover" not in m
    assert m["Emissions"].value == pytest.approx(0.8)                              # 2 MWh x 400 kg = 800 kg = 0.8 t
    assert m["Saved vs doing nothing clever"].value == pytest.approx(0.0, abs=1e-6)


def test_render_calls_streamlit_metric_with_inverse_colour_for_lower_is_better():
    calls = []

    class Col:
        def __enter__(self): return self
        def __exit__(self, *a): return False

    class St:
        def columns(self, n): return [Col() for _ in range(n)]
        def metric(self, label, value, delta, delta_color, help): calls.append((label, value, delta, delta_color))
    ms = [H.Metric("A", 5.0, " MW", 1, 1.0, " MW", "vs x", True), H.Metric("B", 7.0, "", 0)]
    H.render(St(), ms)
    assert calls[0] == ("A", "5.0 MW", "+1.0 MW vs x", "inverse") and calls[1] == ("B", "7", None, "normal")
