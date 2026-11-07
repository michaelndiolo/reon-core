"""Value at stake: a saving range over uncertain inputs. Core arithmetic is checked by hand on a toy; the flex version is
checked against an independent route to the same number (evaluate_s)."""
import numpy as np
import pytest

from hackkit import atstake as A


def toy(v):
    # plan cost 10x, baseline cost 20x + 5y -> saving = 10x + 5y
    return {"plan": 10 * v["x"], "base line": 20 * v["x"] + 5 * v["y"]}


LEV = [A.Lever("x", 2.0, 1.0, 3.0, "ASSUMED"), A.Lever("y", 4.0, 0.0, 8.0, "REAL")]


def test_toy_range_base_and_one_at_a_time_by_hand():
    r = A.value_at_stake(LEV, toy, ["base line"])
    lo, base, hi = r.range("base line")
    assert base == pytest.approx(10 * 2 + 5 * 4)            # 40
    assert lo == pytest.approx(10 * 1 + 5 * 0)              # 10 (both low)
    assert hi == pytest.approx(10 * 3 + 5 * 8)              # 70 (both high)
    assert len(r.scenarios) == 1 + 4 - 0                     # base + 4 corners (none equals base)
    o = r.one_at_a_time.set_index("input")
    assert o.loc["x", "saving at low"] == pytest.approx(10 * 1 + 5 * 4) and o.loc["x", "saving at high"] == pytest.approx(10 * 3 + 5 * 4)
    assert o.loc["y", "swing"] == pytest.approx(40) and o.loc["x", "swing"] == pytest.approx(20)
    assert r.one_at_a_time.iloc[0]["input"] == "y"           # biggest swing first
    assert not r.all_real()


def test_sentences_for_positive_unsettled_and_negative_savings():
    pos = A.value_at_stake(LEV, toy, ["base line"]).sentence("base line", "$")
    assert "saves 40 $" in pos and "stays positive across every combination" in pos and "from 10 $ to 70 $" in pos and "ASSUMED inputs: x" in pos
    mixed = A.value_at_stake([A.Lever("x", 2.0, 1.0, 3.0), A.Lever("y", 4.0, -20.0, 8.0)], toy, ["base line"]).sentence("base line")
    assert "sign is not settled" in mixed and "plan worse than the baseline" in mixed
    neg = A.value_at_stake([A.Lever("x", 2.0, 1.0, 3.0, "REAL"), A.Lever("y", -10.0, -20.0, -9.0, "REAL")], toy, ["base line"]).sentence("base line")
    assert "negative in every combination" in neg and "All inputs varied are REAL" in neg


def test_bad_inputs_are_refused():
    with pytest.raises(ValueError):
        A.Lever("x", 5.0, 1.0, 3.0)                          # base outside the range
    with pytest.raises(ValueError):
        A.Lever("x", 2.0, 1.0, 3.0, source="SURE")
    with pytest.raises(ValueError):
        A.value_at_stake([], toy, ["base line"])
    with pytest.raises(ValueError):
        A.value_at_stake([A.Lever(n, 1.0, 0.0, 2.0) for n in "abcd"], toy, ["base line"])
    with pytest.raises(ValueError):
        A.value_at_stake([A.Lever("x", 1, 0, 2), A.Lever("x", 1, 0, 2)], toy, ["base line"])


def test_flex_base_case_equals_evaluate_s_and_solve():
    from hackkit import flex as F
    p = F.synth_flex(days=2)
    r = A.flex_at_stake(p, [A.Lever("Demand charge ($/kW-month)", 14.0, 7.0, 21.0), A.Lever("Energy price (x)", 1.0, 0.8, 1.2)], with_rule=False)
    want = F.evaluate_s(p, F.baseline_asap(p))["money"] - F.solve_flex(p, with_values=False).money
    assert r.base_row()["saving vs doing nothing clever"] == pytest.approx(want, rel=1e-6)
    # a higher demand charge makes smart scheduling worth more
    lo, base, hi = r.range("doing nothing clever")
    assert lo < base < hi
    q = F.synth_flex(days=2); q.demand_charge = None
    with pytest.raises(ValueError):
        A.flex_at_stake(q, [A.Lever("Demand charge ($/kW-month)", 14.0, 7.0, 21.0)], with_rule=False)
