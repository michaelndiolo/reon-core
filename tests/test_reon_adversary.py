import glob
import os
import numpy as np
import pytest
from hackkit import reon_adversary as A


def test_generators_shapes_and_pairing():
    for name, g in A.default_cases(parallels=(4, 16)).items():
        d = g(0)
        assert d.start.shape == (A.N_SERIES,) and np.all(d.start >= 0) and np.all(np.isfinite(d.start)), name
        assert np.array_equal(g(0).start, d.start) and not np.array_equal(g(1).start, d.start), name   # seeded, reproducible
    assert (A.gen_fail_open()(0).start == 0).sum() == 1
    assert A.gen_cold_sag(cold=0.7)(0).start.mean() < 75
    assert A.gen_clustered_weak()(0).kw["weak_corr"] > 0


def test_harness_demo_and_freeze_replay(tmp_path):
    cases = {"fail_open_p4": A.gen_fail_open(p=4), "base_p4": A.gen_base(p=4)}
    rows = A.evaluate(A.policy_always_balancer_5, cases=cases, seeds=(0,))
    assert [r["case"] for r in rows][0] == max(rows, key=lambda r: r["worst_regret"])["case"]
    by = {r["case"]: r for r in rows}
    assert by["fail_open_p4"]["worst_regret"] > A.THRESHOLD   # a dead cell kills any balancer: switches must win (harness catches it)
    assert A.evaluate(A.policy_always_plain, cases={"base_p4": A.gen_base(p=4)}, seeds=(0,))[0]["worst_regret"] >= 0   # best baseline includes plain (0), so regret is never negative
    path = A.freeze_case("demo", cases["fail_open_p4"](0), A.policy_always_balancer_5, directory=str(tmp_path))
    r = A.replay(path)
    assert not r["ok"] and abs(r["regret"] - by["fail_open_p4"]["worst_regret"]) < 1e-9


FROZEN = A.frozen_case_files()


@pytest.mark.parametrize("path", FROZEN or [None], ids=[os.path.basename(p) for p in FROZEN] or ["none-frozen"])
def test_frozen_cases_replay(path):
    if path is None:
        return   # vacuous pass until a failing case is frozen
    r = A.replay(path)
    assert r["ok"], f"{r['name']}: regret {r['regret']:.2f} $/kWh > {r['threshold']}"
