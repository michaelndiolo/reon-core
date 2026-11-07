"""split_headline: the net saving tile and the biggest sources, with signed shares."""
import pytest

from hackkit import headline as H
from hackkit import reon_econ as R


def test_split_headline_hand_calc():
    base = {"energy": 100.0, "demand_charge": 50.0}
    plan = {"energy": 110.0, "demand_charge": 20.0, "regulation_revenue": 5.0}
    m = H.split_headline(R.value_split(plan, base))
    assert [x.label for x in m] == ["Net saving", "Demand charge", "Energy bought", "Regulation revenue"]
    assert m[0].value == pytest.approx(25.0) and m[0].value_text == "25"
    assert m[1].value == pytest.approx(30.0) and m[1].delta == pytest.approx(120.0) and m[1].delta_text == "+120% of net saving"
    assert m[2].value == pytest.approx(-10.0) and m[2].delta == pytest.approx(-40.0)       # got worse while others improved


def test_split_headline_top_and_zero_lines_and_zero_net():
    base = {"energy": 100.0, "demand_charge": 50.0}
    plan = {"energy": 110.0, "demand_charge": 20.0, "regulation_revenue": 5.0}
    assert len(H.split_headline(R.value_split(plan, base), top=1)) == 2                    # net + one source
    flat = R.value_split({"energy": 5.0}, {"energy": 5.0})
    m = H.split_headline(flat)
    assert [x.label for x in m] == ["Net saving"]                                          # nothing saved, nothing to attribute
