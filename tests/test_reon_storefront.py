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
