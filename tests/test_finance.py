"""Finance arithmetic against hand calculations."""
import pytest

from hackkit import finance as fin


def test_npv_and_irr_by_hand():
    assert fin.npv(0.10, [-100.0, 110.0]) == pytest.approx(0.0, abs=1e-9)
    assert fin.npv(0.0, [-100.0, 40.0, 40.0, 40.0]) == pytest.approx(20.0)
    assert fin.npv(0.05, [0.0, 105.0]) == pytest.approx(100.0)
    assert fin.irr([-100.0, 110.0]) == pytest.approx(0.10, abs=1e-6)
    assert fin.irr([-100.0, 60.0, 60.0]) == pytest.approx(0.1306623, abs=1e-5)   # hand: solve 60/(1+r) + 60/(1+r)^2 = 100
    assert fin.irr([100.0, 50.0]) is None and fin.irr([-100.0, -5.0]) is None


def test_payback_by_hand():
    assert fin.payback_years([-100.0, 40.0, 40.0, 40.0]) == pytest.approx(2.5)
    assert fin.payback_years([-100.0, 10.0, 10.0]) is None
    assert fin.payback_years([0.0, 5.0]) == 0.0


def test_storage_cashflows_without_and_with_tax_by_hand():
    cf = fin.storage_cashflows(1000.0, [300.0] * 5, om=50.0)
    assert cf.tolist() == pytest.approx([-1000.0] + [250.0] * 5)
    cf = fin.storage_cashflows(1000.0, [300.0] * 5, om=50.0, tax_rate=0.30)       # depreciation 200 a year: taxable 300-50-200 = 50, tax 15
    assert cf.tolist() == pytest.approx([-1000.0] + [235.0] * 5)
    loss = fin.storage_cashflows(1000.0, [100.0] * 5, om=50.0, tax_rate=0.30)       # taxable negative: no refund
    assert loss.tolist() == pytest.approx([-1000.0] + [50.0] * 5)


def test_breakeven_capex_makes_npv_zero_and_is_none_when_revenue_cannot_cover_om():
    rev = [300.0] * 15
    c = fin.breakeven_capex(rev, om_share_of_capex=0.025, rate=0.07)
    assert fin.npv(0.07, fin.storage_cashflows(c, rev, 0.025 * c)) == pytest.approx(0.0, abs=1e-5)
    ann = (1 - 1.07 ** -15) / 0.07                                               # hand: 300 x annuity = c x (1 + 0.025 x annuity)
    assert c == pytest.approx(300.0 * ann / (1 + 0.025 * ann), rel=1e-6)
    assert fin.breakeven_capex([10.0] * 15, 0.025, 0.07) is not None
    assert fin.breakeven_capex([0.0] * 15, 0.025, 0.07) is None
    ct = fin.breakeven_capex(rev, 0.025, 0.07, tax_rate=0.30)
    assert ct < c                                                                # tax lowers what you can pay


def test_tax_schedule_per_year_by_hand_and_wrong_length_refused():
    # capex 1000 over 5 years: depreciation 200; revenue 300, om 50 -> taxable 50 every year; rates 10%, 20%, 30%, 40%, 50% -> tax 5, 10, 15, 20, 25
    cf = fin.storage_cashflows(1000.0, [300.0] * 5, om=50.0, tax_rate=[0.1, 0.2, 0.3, 0.4, 0.5])
    assert cf.tolist() == pytest.approx([-1000.0, 245.0, 240.0, 235.0, 230.0, 225.0])
    assert fin.storage_cashflows(1000.0, [300.0] * 5, 50.0, [0.3] * 5).tolist() == pytest.approx(fin.storage_cashflows(1000.0, [300.0] * 5, 50.0, 0.3).tolist())
    with pytest.raises(ValueError):
        fin.storage_cashflows(1000.0, [300.0] * 5, 50.0, [0.3, 0.3])


def test_breakeven_with_a_fixed_cost_that_does_not_move_with_capex():
    rev = [300.0] * 15
    ann = (1 - 1.07 ** -15) / 0.07
    c = fin.breakeven_capex(rev, 0.0, 0.07, om_fixed=40.0)                       # hand: (300 - 40) x annuity = c
    assert c == pytest.approx(260.0 * ann, rel=1e-6)
    assert fin.npv(0.07, fin.storage_cashflows(c, rev, 40.0)) == pytest.approx(0.0, abs=1e-5)
    assert fin.breakeven_capex([30.0] * 15, 0.0, 0.07, om_fixed=40.0) is None   # revenue below the fixed cost
