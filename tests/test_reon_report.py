"""reon_report: the report must agree with the modules it combines, and must not invent numbers."""
import pytest

from hackkit import reon_loss, reon_unit, reon_window
from hackkit.reon_report import analyze_pack, load_caps_csv, render_markdown

CAPS = [100, 90, 80, 70]


def test_agrees_with_components():
    r = analyze_pack(CAPS, volts=3.7, electronics_per_kwh=8.0, value_per_kwh_year=20.0, alt_costs=[40.0, 5.0], rate=0.0, years=5.0)
    assert r["cells"]["conventional_ah"] == pytest.approx(280) and r["cells"]["ideal_ah"] == pytest.approx(340)
    assert r["cells"]["gain_ideal"] == pytest.approx(340 / 280 - 1)
    assert r["cells"]["extra_kwh"] == pytest.approx(60 * 3.7 / 1000)
    assert r["loss"]["break_even_loss"] == pytest.approx(reon_loss.break_even_loss(CAPS))
    assert r["window"]["rows"][0]["n_min"] == 4 and r["window"]["rows"][0]["gain"] == pytest.approx(0.0)       # 90% of 4 cells = all 4
    assert r["window"]["rows"][2]["n_min"] == 2 and r["window"]["rows"][2]["gain"] == pytest.approx(reon_window.window_gain(CAPS, 2))
    e = r["economics"]
    g = 340 / 280 - 1
    assert e["cost_per_extra_kwh"] == pytest.approx(reon_unit.cost_per_extra_kwh(8.0, g))
    assert e["payback_years"] == pytest.approx(e["cost_per_extra_kwh"] / 20.0)
    assert e["levelized_cost_per_extra_kwh_year"] == pytest.approx(e["cost_per_extra_kwh"] / 5.0)
    assert e["breakeven_gain"][40.0] == pytest.approx(8.0 / 32.0) and e["breakeven_gain"][5.0] is None
    assert r["fragility"]["gain_without_weakest"] == pytest.approx(0.125)


def test_nothing_invented_and_tags():
    r = analyze_pack(CAPS)
    assert "economics" not in r and "life" not in r                       # no electronics/value given: no economics, no defaults
    assert r["cells"]["tag"] == "ASSUMED"
    assert analyze_pack(CAPS, sources={"capacities": "CITED"})["cells"]["tag"] == "CITED"
    with pytest.raises(ValueError):
        analyze_pack(CAPS, sources={"capacities": "TRUST_ME"})
    with pytest.raises(ValueError):
        analyze_pack([100, -1])
    with pytest.raises(ValueError):
        analyze_pack(CAPS, fade_rates=[1, 2])


def test_life_and_equal_cells():
    r = analyze_pack(CAPS, fade_rates=[0.03, 0.01, 0.01, 0.01])
    assert r["life"]["ratio"] == pytest.approx(0.03 / 0.015)
    eq = analyze_pack([100, 100, 100], electronics_per_kwh=8.0, value_per_kwh_year=20.0)
    assert eq["economics"]["payback_years"] is None and eq["loss"]["break_even_loss"] == pytest.approx(0.0)
    assert "nothing to pay for" in render_markdown(eq)


def test_render_and_csv(tmp_path):
    p = tmp_path / "c.csv"
    p.write_text("# comment\ncapacity,fade_rate\n100,0.03\n90,0.01\n80,0.01\n70,0.01\n")
    d = load_caps_csv(str(p))
    assert d["caps"] == [100.0, 90.0, 80.0, 70.0] and d["fade_rates"] == [0.03, 0.01, 0.01, 0.01]
    q = tmp_path / "d.csv"
    q.write_text("100\n90\n80\n")
    assert load_caps_csv(str(q))["caps"] == [100.0, 90.0, 80.0] and load_caps_csv(str(q))["fade_rates"] is None
    md = render_markdown(analyze_pack(d["caps"], fade_rates=d["fade_rates"], electronics_per_kwh=8.0, value_per_kwh_year=20.0, alt_costs=[40.0]))
    for needle in ("Gain:** 21.4%", "Break-even loss", "Cost per extra usable kWh", "Life ratio", "Limits"):
        assert needle in md
    empty = tmp_path / "e.csv"
    empty.write_text("# only a comment\n")
    with pytest.raises(ValueError):
        load_caps_csv(str(empty))


def test_negative_fragility_wording():
    md = render_markdown(analyze_pack([20.27, 17.42, 19.57, 18.93, 25.04, 23.65, 22.87, 17.59]))
    assert "RAISE the gain" in md


def test_parse_text_forms_and_gain_after():
    from hackkit.reon_report import gain_after, parse_caps_text
    for txt in ("100\n90\n80\n70", "100, 90, 80, 70", "100 90 80 70", "# c\ncapacity\n100\n90\n80\n70\n", "Ah,fade_rate\n100,0.03\n90,0.01\n80,0.01\n70,0.01"):
        assert parse_caps_text(txt)["caps"] == [100.0, 90.0, 80.0, 70.0], txt
    assert parse_caps_text("Ah,fade_rate\n100,0.03\n90,0.01\n80,0.01\n70,0.01")["fade_rates"] == [0.03, 0.01, 0.01, 0.01]
    assert gain_after(CAPS) == pytest.approx(340 / 280 - 1)                                  # ideal
    assert gain_after(CAPS, loss=0.05) == pytest.approx(340 * 0.95 / 280 - 1)
    assert gain_after(CAPS, window_frac=0.75) == pytest.approx(310 / 280 - 1)               # 75% of 4 = 3 cells in circuit
    assert gain_after(CAPS, window_frac=1.0) == pytest.approx(0.0)
    assert gain_after(CAPS, loss=0.1, window_frac=0.5) == pytest.approx(330 * 0.9 / 280 - 1)
    for bad in (dict(loss=1.0), dict(window_frac=0.0), dict(window_frac=1.5)):
        with pytest.raises(ValueError):
            gain_after(CAPS, **bad)
    with pytest.raises(ValueError):
        parse_caps_text("# only comments")
