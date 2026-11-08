import numpy as np
from hackkit import reon_storefront as SF


def packs():
    rng = np.random.default_rng(1)
    return {f"p{i}": 100 * (1 + 0.05 * rng.standard_normal(95)) for i in range(5)}


def test_backup_managed_at_least_plain():
    bp, bm = SF.backup_hours(packs(), 60.0, 5.0)
    assert bm >= bp > 0


def test_headline_buy_and_hold():
    r = dict(verdict="BUY", build="x", reasons=["ok"], nameplate_kwh=60.0, load_kw=5.0, backup_managed_h=8.4, backup_plain_h=7.9, life_ours=24.0, life_plain=11.0, dollars_total=1635.0, p10_total=698.0)
    h = SF.headline(r, "California", 3.2)
    assert "24 years instead of 11" in h and "$1,635" in h and "California" in h
    r2 = dict(r, verdict="HOLD", reasons=["p10 worse"])
    assert "would not sell" in SF.headline(r2)


def test_storefront_small_case_runs_and_hold_has_no_env():
    r = SF.storefront(40, 0.008, 40.0, 15.5, packs(), n=40)
    assert r["verdict"] in ("BUY", "HOLD") and r["life_plain"] > 0
    if r["verdict"] == "HOLD":
        assert r["env"] is None


def test_cache_matches_live_engine_and_covers_front_page():
    cases = SF.load_cases()
    for p in (1, 4, 16, 40):
        for f in (0.004, 0.008, 0.02):
            for v in (12, 22, 40, 80):
                assert SF.case_key(p, f, v) in cases, (p, f, v)
    for v in (15, 30, 45, 60, 75, 90, 120, 150):
        assert SF.case_key(1, 0.008, v) in cases
    live = SF.core(40, 0.02, 40.0)                       # one case recomputed: the saved file must not be stale
    saved = SF.cached_core(40, 0.02, 40.0)
    assert live["verdict"] == saved["verdict"] and abs(live["dollars_per_kwh"] - saved["dollars_per_kwh"]) < 1e-6 and abs(live["life_ours"] - saved["life_ours"]) < 1e-6


def test_gain_vs_fade_rows_come_from_cache_and_are_complete():
    for value in (12, 22, 40, 80):
        rows = SF.gain_vs_fade(value)
        assert len(rows) == len(SF.GAIN_FADES) * len(SF.GAIN_PARALLEL)
        assert all(r["verdict"] in ("BUY", "BALANCER", "HOLD") for r in rows) and all(r["gain"] >= 0.0 for r in rows)
    one = [r for r in SF.gain_vs_fade(40) if r["parallel"] == 1 and r["fade"] == 0.008][0]
    assert one["verdict"] == "BUY" and one["gain"] > 1.0 and one["total"] > one["gain"]
    slow = [r for r in SF.gain_vs_fade(40) if r["parallel"] == 1 and r["fade"] == 0.004][0]
    assert slow["verdict"] == "BALANCER" and slow["gain"] == 0.0


def test_balancer_rows_complete_and_crossover_sensible():
    rows = SF.balancer_rows(1, 0.008)
    assert len(rows) == len(SF.BAL_LIMITS) * len(SF.BAL_SERIES)
    assert {r["series"] for r in rows} == {lab for _, lab in SF.BAL_SERIES}
    x = SF.balancer_crossover(rows)
    assert x is not None and 0.01 < x < 0.05
    assert SF.balancer_rows(1, 0.123) == []
    # at fast wear switches alone beat the balancer up to a much stronger one
    fast = SF.balancer_crossover(SF.balancer_rows(1, 0.02))
    assert fast is None or fast > x


def test_balancer_chart_builds():
    from hackkit import reon_visuals as VZ
    ch = VZ.balancer_chart(SF.balancer_rows(1, 0.008))
    assert ch.to_dict()
