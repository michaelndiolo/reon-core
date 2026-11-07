import itertools

import numpy as np
import pytest

from hackkit import reon_sorting as S


def _all_partitions(idx, m):
    if not idx:
        yield []
        return
    first, rest = idx[0], idx[1:]
    for comb in itertools.combinations(rest, m - 1):
        grp = (first,) + comb
        left = [i for i in rest if i not in comb]
        for p in _all_partitions(left, m):
            yield [grp] + p


@pytest.mark.parametrize("caps,m", [([100, 90, 80, 70, 95, 60], 3), ([100, 90, 80, 70, 95, 60], 2), ([5, 9, 7, 3, 8, 6, 4, 10], 4), ([5, 9, 7, 3, 8, 6, 4, 10], 2)])
def test_sorting_is_optimal_by_brute_force(caps, m):
    c = np.array(caps, float)
    best = max(sum(m * c[list(g)].min() for g in p) for p in _all_partitions(list(range(len(c))), m))
    assert S.sorted_usable(c, m) == pytest.approx(best)


def test_one_string_is_conventional_and_control_is_sum():
    c = [100, 90, 80, 70]
    assert S.strings_usable(c, 4) == 280 and S.sorted_usable(c, 4) == 280
    r = S.sorting_vs_control(c, 4)
    assert r["control"] == 340 and r["control_over_sorted_ideal"] == pytest.approx(340 / 280 - 1)


def test_ordering_and_noise_hurts_sorting_and_perfect_pairs_leave_nothing():
    rng = np.random.default_rng(1)
    c = 80 + 20 * rng.random(24)
    r = S.sorting_vs_control(c, 4, sigma_rel=0.05, trials=400)
    assert r["random"] <= r["sorted_ideal"] + 1e-9 <= r["control"] + 1e-9
    assert r["sorted_noisy"] <= r["sorted_ideal"] + 1e-9 and r["sorted_noisy"] >= r["random"] - 1e-6
    pairs = S.sorting_vs_control([90, 90, 80, 80], 2, sigma_rel=0)
    assert pairs["control_over_sorted_ideal"] == pytest.approx(0.0)


def test_bad_inputs():
    with pytest.raises(ValueError):
        S.strings_usable([1, 2, 3], 2)
    with pytest.raises(ValueError):
        S.sorted_usable([1, 2, 3, 4], 2, measured=[1, 2])
