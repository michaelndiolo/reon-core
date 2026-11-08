from hackkit import reon_demo as DM


def test_adversary_summary_covers_all_cases_and_never_behind():
    a = DM.adversary_summary()
    assert a["runs"] == 48
    assert set(a["cases"]) == {"base", "clustered_weak", "outliers", "fail_open", "cold_sag", "slow_wear", "fast_wear", "correlated"}
    assert all(n == 6 for _, n in a["cases"].values())
    assert a["worst_regret"] <= 0.01
    assert a["hindsight_gap_5"] < 3.0
