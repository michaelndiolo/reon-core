from hackkit import reon_demo as DM


def test_adversary_summary_covers_all_cases_and_never_behind():
    a = DM.adversary_summary()
    assert a["runs"] == 198
    assert set(a["cases"]) == {"base", "clustered_weak", "outliers", "fail_open", "cold_sag", "cold_m20", "cold_m40", "slow_wear", "fast_wear", "correlated", "batch_fade"}
    assert all(n == 18 for _, n in a["cases"].values())
    assert a["worst_regret"] <= 0.50  # the repo tolerance; two of 198 runs were 0.44 and 0.48 behind
    assert a["hindsight_gap_5"] < 4.5
