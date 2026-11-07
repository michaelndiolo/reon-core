import numpy as np
import pytest
from hackkit import reon_slope as SLP


def test_fade_and_local_median():
    e = np.full(20, 0.95)
    l = e - 0.05
    assert np.allclose(SLP.fade_pp(e, l), 5.0)
    x = np.arange(10.0)
    lm = SLP.local_median(x, half=1)
    assert lm[0] == 1.0 and lm[5] == pytest.approx(5.0)        # median of neighbours 4 and 6, self excluded


def test_outlier_flags_only_the_fast_fader():
    rng = np.random.default_rng(0)
    f = 5.0 + 0.2 * rng.standard_normal(60)
    f[30] = 9.0
    flag, lm, scale = SLP.outliers(f)
    assert flag[30] and flag.sum() <= 3 and scale > 0
    assert not SLP.outliers(np.full(30, 5.0))[0].any()


def test_snapshot_vs_trend_on_real_data():
    packs = SLP.load_cells()
    s = SLP.snapshot_vs_trend(packs)
    assert s["packs"] == 12 and all(v["n"] == 95 for v in s["per_pack"].values())
    assert s["same_weakest"] <= 3 and s["steepest_is_final_weakest"] >= 6      # the headline: a snapshot ranking misses the cell that ends up weakest, the steepest fader finds it most times


def test_bad_inputs():
    with pytest.raises(Exception):
        SLP.fade_pp([0.9, 0.9], [0.8, 0.8])
