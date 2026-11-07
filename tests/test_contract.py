"""Data-contract watch: each test builds a series with ONE known defect and checks the right finding appears, and that clean data stays quiet."""
import numpy as np
import pandas as pd
import pytest

from hackkit import contract as K
from hackkit.flex import synth_flex


def codes(f):
    return {x.code for x in f}


def hours(n, start="2026-01-01"):
    return pd.date_range(start, periods=n, freq="h", tz="UTC")


def test_clean_series_is_quiet():
    rng = np.random.default_rng(0)
    v = rng.uniform(20, 60, 200)
    assert K.check_series("price", v, hours(200), lo=-500, hi=5000, unit="$/MWh") == []


def test_missing_share_thresholds():
    v = np.full(100, 40.0) + np.arange(100) * 0.01
    v10 = v.copy(); v10[:10] = np.nan
    v30 = v.copy(); v30[:30] = np.nan
    assert [x.severity for x in K.check_series("p", v10) if x.code == "missing"] == ["warn"]      # 10% > 5%
    assert [x.severity for x in K.check_series("p", v30) if x.code == "missing"] == ["stop"]      # 30% > 20%
    assert K.check_series("p", [np.nan] * 5)[0].code == "all_missing"
    assert K.check_series("p", [])[0].code == "empty"


def test_timestamps_backwards_duplicates_and_gap():
    t = list(hours(50))
    v = np.arange(50, dtype=float) + 20
    t_back = t.copy(); t_back[10], t_back[11] = t_back[11], t_back[10]
    assert "out_of_order" in codes(K.check_series("p", v, t_back))
    t_dup = t.copy(); t_dup[20] = t_dup[19]
    assert "duplicates" in codes(K.check_series("p", v, t_dup))
    t_gap = list(hours(25)) + list(hours(25, "2026-01-03"))        # 25 hourly points, then a jump of about 24 h
    g = [x for x in K.check_series("p", v, t_gap) if x.code == "gap"]
    assert len(g) == 1 and "2026-01-02T00:00" in g[0].message


def test_stale_data():
    t = hours(48)
    v = np.linspace(20, 30, 48)
    now = pd.Timestamp("2026-01-12", tz="UTC")           # last point is 2026-01-02 23:00 -> 9.04 days old
    assert "stale" in codes(K.check_series("p", v, t, max_age_days=2, now=now))
    assert "stale" not in codes(K.check_series("p", v, t, max_age_days=30, now=now))


def test_out_of_range_and_negative():
    v = np.linspace(20, 30, 100); v[5] = 100000.0
    f = K.check_series("price", v, lo=-500, hi=5000)
    assert [x.severity for x in f if x.code == "out_of_range"] == ["warn"]     # one value of 100 is under 5%
    v2 = np.linspace(20, 30, 100); v2[:10] = 100000.0
    assert [x.severity for x in K.check_series("price", v2, lo=-500, hi=5000) if x.code == "out_of_range"] == ["stop"]
    neg = np.linspace(1, 2, 50); neg[3] = -4
    assert "negative" in codes(K.check_series("load", neg, nonneg=True))


def test_whole_series_unit_flip_kw_for_mw():
    kw = np.linspace(500, 5000, 100)                     # a load that should be 0.5-5 MW, given in kW
    f = K.check_series("load", kw, lo=0.1, hi=50, unit="MW")
    flip = [x for x in f if x.code == "unit_flip"]
    assert flip and flip[0].severity == "stop" and "1000x too big" in flip[0].message
    small = np.linspace(0.0005, 0.005, 100)              # the other way round
    assert any("1000x too small" in x.message for x in K.check_series("load", small, lo=0.1, hi=50, unit="MW"))


def test_unit_change_partway_through_is_caught():
    v = np.full(240, 3.0) + np.random.default_rng(1).normal(0, 0.05, 240)
    v[96:120] *= 1000                                    # one day reported in kW
    f = K.check_series("load", v)
    b = [x for x in f if x.code == "unit_flip_block"]
    assert b and "position 96" in b[0].message


def test_stuck_sensor_but_not_a_run_of_zeros():
    v = np.linspace(20, 30, 100); v[40:60] = 4.2         # 20 identical values in a row
    s = [x for x in K.check_series("t", v) if x.code == "stuck"]
    assert len(s) == 1 and "20 times" in s[0].message and "position 40" in s[0].message
    z = np.linspace(20, 30, 100); z[40:60] = 0.0
    assert "stuck" not in codes(K.check_series("t", z))


def test_zeros_that_may_mean_missing():
    v = np.linspace(20, 30, 100); v[30:42] = 0.0         # 12 exact zeros inside a positive series (the CARE pattern)
    z = [x for x in K.check_series("sensor", v) if x.code == "zeros_as_missing"]
    assert z and "longest 12" in z[0].message
    solar = np.tile(np.r_[np.zeros(12), np.full(12, 2.0)], 10)     # night zeros are normal: half the series is zero
    assert "zeros_as_missing" not in codes(K.check_series("solar", solar, nonneg=True))


def test_flex_problem_clean_and_with_price_in_wrong_unit():
    p = synth_flex(days=3, seed=0)
    assert not K.has_stop(K.check_flex_problem(p))
    bad = p.copy(price=p.price / 1000.0)                 # $/kWh by mistake
    f = K.check_flex_problem(bad)
    assert K.has_stop(f) and any(x.series == "price" and x.code == "unit_flip" for x in f)
    assert "stop" in K.summary_line(f)


def test_report_table_and_summary_line():
    v = np.linspace(1, 2, 50); v[3] = -4
    f = K.check_series("load", v, nonneg=True)
    df = K.report(f)
    assert list(df.columns) == ["severity", "series", "code", "what we saw"] and len(df) >= 1
    assert K.summary_line([]) == "Data contract: no problems found."


def test_whole_load_series_in_kw_is_caught_by_the_cross_series_scale_check():
    p = synth_flex(days=3, seed=0)
    assert not K.has_stop(K.check_flex_problem(p))
    bad = p.copy(base_load=p.base_load * 1000.0)              # the site's fixed load given in kW, everything else in MW
    f = K.check_flex_problem(bad)
    s = [x for x in f if x.code == "scale"]
    assert K.has_stop(f) and s and "kW" in s[0].message
    # and the other way round: battery and chargers given in kW against a load in MW
    bad2 = p.copy(battery=p.battery.__class__(p.battery.energy_mwh * 1000, p.battery.power_mw * 1000))
    assert any(x.code == "scale" for x in K.check_flex_problem(bad2))


# ---- found on real files (EIA-930, DOE reference building, USWTDB, LBNL slips) ----

def test_daily_cycle_series_not_flagged_for_flat_nights_or_zero_nights():
    solar = np.tile(np.r_[np.full(14, 2.0), np.linspace(5, 80, 10)], 10)       # real EIA-930 winter nights sit flat at 2 MW
    assert "stuck" in codes(K.check_series("solar", solar, nonneg=True))               # default rule fires (false alarm)
    assert codes(K.check_series("solar", solar, nonneg=True, kind="daily_cycle")) == set()


def test_daily_cycle_still_catches_a_dropout_in_a_load_that_is_never_zero():
    load = np.tile(np.r_[np.full(14, 0.034), np.linspace(0.1, 0.3, 10)], 20); load[200:212] = 0.0
    assert "zeros_as_missing" in codes(K.check_series("load", load, nonneg=True, kind="daily_cycle"))


def test_records_kind_skips_time_order_checks():
    years = np.sort(np.r_[np.full(30, 2012.0), np.arange(1990, 2020.0)])     # sorted table of turbines, 30 of one year
    assert "stuck" in codes(K.check_series("year", years))
    assert codes(K.check_series("year", years, kind="records")) == set()
    with pytest.raises(ValueError):
        K.check_series("x", years, kind="nonsense")


def test_single_zero_hour_in_demand_is_caught_by_the_range():
    d = 20000 + 1500 * np.sin(np.arange(200) / 8.0); d[90] = 0.0              # NYISO 2024-01-18 00:00 reads 0 MW
    f = K.check_series("demand", d, lo=3000, hi=40000, unit="MW")
    assert any(x.code == "out_of_range" for x in f)


def test_zero_ok_silences_zero_runs_only():
    s = np.tile(np.r_[np.zeros(8), np.full(88, 3.0)], 3)                      # solar-like series that is positive 92% of the time
    assert "zeros_as_missing" in codes(K.check_series("s", s, nonneg=True, kind="daily_cycle"))
    assert "zeros_as_missing" not in codes(K.check_series("s", s, nonneg=True, kind="daily_cycle", zero_ok=True))
    assert "negative" in codes(K.check_series("s", -s, nonneg=True, kind="daily_cycle", zero_ok=True))


def test_flex_problem_check_does_not_flag_night_zeros_in_solar():
    p = synth_flex(days=3, solar_mw=3.0)
    p.solar[:] = np.tile(np.r_[np.zeros(6), np.full(18, 2.0)], 3)
    assert "zeros_as_missing" not in {x.code for x in K.check_flex_problem(p) if x.series == "solar"}


def test_dropped_price_feed_shows_as_isolated_zeros_and_stale_feed_is_caught():
    p = synth_flex(days=3)
    p.price = p.price.copy(); p.price[10:13] = 0.0
    assert "isolated_zero" in {x.code for x in K.check_flex_problem(p)}
    q = synth_flex(days=3)
    assert "isolated_zero" not in {x.code for x in K.check_flex_problem(q)}
    from datetime import datetime
    r = synth_flex(days=3)
    r.times = [str(t) for t in pd.date_range("2025-03-17", periods=r.T, freq="h")]
    assert "stale" not in {x.code for x in K.check_flex_problem(r)}                                    # replay: no age check
    assert "stale" in {x.code for x in K.check_flex_problem(r, max_age_days=2, now=datetime(2025, 4, 1))}


def _price_year(seed=0, near_zero_day=True, negatives=True):
    rng = np.random.default_rng(seed)
    p = 70 + 20 * rng.standard_normal(24 * 120)
    p = np.clip(p, 5, None)
    if near_zero_day:
        p[24 * 40:24 * 41] = np.abs(rng.normal(0.0, 0.1, 24))                 # a sunny Sunday: the whole day sits near zero
        p[24 * 60 + 7:24 * 60 + 15] = 0.0                              # eight exact-zero hours
    if negatives:
        p[24 * 80 + 5:24 * 80 + 53] = -25.0                            # a few real negative hours
    return p


def test_day_ahead_price_with_negative_hours_and_a_near_zero_day_is_not_a_unit_flip():
    codes = {x.code for x in K.check_series("price", _price_year(), lo=-500, hi=4000, unit="EUR/MWh")}
    assert "unit_flip_block" not in codes and "zeros_as_missing" not in codes


def test_the_same_near_zero_day_in_a_series_that_never_goes_negative_is_still_flagged():
    codes = {x.code for x in K.check_series("price", _price_year(negatives=False), lo=-500, hi=4000, unit="EUR/MWh")}
    assert "unit_flip_block" in codes and "zeros_as_missing" in codes


def test_a_real_thousandfold_block_is_still_caught_when_the_series_goes_negative():
    p = _price_year(near_zero_day=False)
    p[24 * 30:24 * 31] *= 1000.0
    codes = {x.code for x in K.check_series("price", p, lo=-500, hi=4000000, unit="EUR/MWh")}
    assert "unit_flip_block" in codes
